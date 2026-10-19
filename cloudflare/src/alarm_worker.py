"""Finite, restartable Cloudflare alarm cycles; never depend on an open phone."""
import asyncio, gc, time
from decimal import Decimal
from sqlalchemy import select
from database.models import (User, Market, FuturesMarket, FuturesPaperPosition,
                             FuturesConfig, Record, record)
from backend.domain import Quote
from exchange_adapters.mexc_futures import json_safe
from public_futures import PublicFutures
from exchange_adapters.bitget_public import BitgetPublic
from exchange_adapters.universe import catalogue, rotation, CandleBackoff
from backend.futures_paper import manage as manage_futures
from backend.shadow import pending_symbols
from agents.futures_pipeline import process as research_futures
from agents.autonomous import manage_exits, process_observation, VERSION
from agents.portfolio_pipeline import process_spot
from backend.service import portfolio
from backend.treasury import capture

class AlarmWorker:
    def __init__(self, database, env):
        self.database = database
        self.env = env
        self.metadata = {}
        self.cursor = 0
        self.last_catalogue = 0
        self.last_scan = 0
        self.last_spot_scan = 0
        self.last_heartbeat = 0
        self.last_snapshot = 0
        self.backoff = CandleBackoff()
        self.futures = PublicFutures(env)
        self.spot = BitgetPublic()

    async def tick(self):
        db = self.database
        gc.collect()
        now = time.time()
        errors = 0
        async def futures_quotes():
            if not self.metadata or now-self.last_catalogue >= 300:
                fresh = catalogue(await self.futures.contracts())
                if not fresh: raise ValueError('Empty exchange catalogue')
                self.metadata = fresh
                self.last_catalogue = now
            return await self.futures.tickers()
        symbols=('BTC/USDT','ETH/USDT','SOL/USDT')
        async def bounded(awaitable):
            return await asyncio.wait_for(awaitable,timeout=8)
        results=await asyncio.gather(bounded(futures_quotes()),
            *(bounded(self.spot.quote(symbol)) for symbol in symbols),return_exceptions=True)
        if isinstance(results[0],BaseException): errors+=1
        else:
            with db.sessions() as s:
                existing={m.symbol:m for m in s.scalars(select(FuturesMarket))}
                for ticker in results[0]:
                    symbol=ticker['symbol']
                    if symbol not in self.metadata: continue
                    market=existing.get(symbol)
                    if market is None: market=FuturesMarket(symbol=symbol);s.add(market)
                    market.ticker=json_safe(ticker);market.contract=json_safe(self.metadata[symbol]);market.received=time.time()
                for market in existing.values():
                    if market.symbol not in self.metadata:
                        market.contract={**market.contract,'state':1,'apiAllowed':False}
                s.commit()
        for symbol,quote in zip(symbols,results[1:]):
            if isinstance(quote,BaseException): errors+=1;continue
            if quote.ask<quote.bid or not -5<=time.time()-quote.timestamp<=15:
                errors+=1;continue
            with db.sessions() as s:
                market=s.get(Market,symbol)
                if market is None: market=Market(symbol=symbol);s.add(market)
                market.payload=quote.model_dump(mode='json');market.received=time.time();s.commit()
        with db.sessions() as s:
            owners = list(s.scalars(select(User)))
        for owner in owners:
            with db.sessions() as s:
                manage_futures(s, owner.id)
                manage_exits(s, owner.id)
                s.commit()
        # Explicit cadence configuration makes workload and free-tier tradeoffs
        # inspectable; it does not change strategy or risk thresholds.
        interval = max(30, int(getattr(self.env,'SCAN_INTERVAL_SECONDS','60')))
        batch_size = min(24, max(1, int(getattr(self.env,'SCAN_BATCH_SIZE','4'))))
        scanned=False
        if owners and now-self.last_scan >= interval:
            scanned=True
            self.last_scan = now
            with db.sessions() as s:
                held = list(s.scalars(select(FuturesPaperPosition.symbol))) + pending_symbols(s)
                batch,self.cursor=rotation(list(s.scalars(select(FuturesMarket))),self.cursor,batch_size,held,self.backoff.blocked(time.monotonic()))
            read_count = 0
            async def research_read(symbol):
                rows,ticker=await asyncio.gather(self.futures.candles(symbol),self.futures.ticker(symbol))
                return [r for r in rows if r[0]/1000+60<=time.time()],ticker
            readings=await asyncio.gather(*(bounded(research_read(symbol)) for symbol in batch),return_exceptions=True)
            for symbol,result in zip(batch,readings):
                if isinstance(result,BaseException):
                    self.backoff.failed(symbol,time.monotonic());errors+=1;continue
                rows,ticker=result
                self.backoff.succeeded(symbol);read_count+=1
                for owner in owners:
                    with db.sessions() as s:
                        market=s.get(FuturesMarket,symbol)
                        if market:
                            market.ticker=json_safe(ticker);market.received=time.time()
                            research_futures(s,owner,symbol,rows)
                        s.commit()
            with db.sessions() as s:
                record(s,None,'research_scan_heartbeat',{'batch':len(batch),'candle_reads':read_count,'data_errors':len(batch)-read_count,'backoff':len(self.backoff.blocked(time.monotonic())),'interval_seconds':interval})
                for owner in owners:
                    record(s,owner.id,'scan_summary',{'catalogue':len(self.metadata),'batch':len(batch),'evaluated':read_count,'data_errors':len(batch)-read_count,'cursor':self.cursor,'hosting':'cloudflare','interval_seconds':interval})
                s.commit()
        if owners and not scanned and now-self.last_spot_scan >= 60:
            self.last_spot_scan=now
            readings=await asyncio.gather(*(bounded(self.spot.candles(symbol,'1m',100)) for symbol in symbols),return_exceptions=True)
            for symbol,result in zip(symbols,readings):
                try:
                    if isinstance(result,BaseException): raise ValueError('Spot candles unavailable')
                    rows=[r for r in result if r[0]/1000+60<=time.time()]
                    with db.sessions() as s:
                        market=s.get(Market,symbol)
                        if not market or time.time()-market.received>15: continue
                        for owner in owners:
                            cfg=s.get(FuturesConfig,owner.id)
                            if cfg and cfg.workspace=='combined':process_spot(s,owner.id,symbol,rows)
                            elif not cfg or cfg.workspace=='spot':process_observation(s,owner.id,symbol,rows)
                        s.commit()
                except Exception:
                    errors+=1
        if now-self.last_snapshot >= 300:
            self.last_snapshot=now
            with db.sessions() as s:
                for owner in owners:
                    user=s.get(User,owner.id)
                    snap=portfolio(s,user)
                    if snap['equity'] is not None:user.high_water=max(user.high_water,Decimal(snap['equity']))
                    record(s,user.id,'portfolio_snapshot',snap);capture(s,user.id)
                s.commit()
        if now-self.last_heartbeat >= 20:
            self.last_heartbeat=now
            with db.sessions() as s:
                record(s,None,'worker_heartbeat',{'version':VERSION,'hosting':'cloudflare','autonomous_paper':True,'market_errors':errors})
                record(s,None,'futures_observer_heartbeat',{'catalogue':len(self.metadata),'market_errors':errors})
                # No privileged executor heartbeat is fabricated here. Live
                # activation remains unavailable until its own validation gate.
                s.commit()
        return {'market_errors':errors,'catalogue':len(self.metadata),'scanned':scanned,'owners':len(owners)}
