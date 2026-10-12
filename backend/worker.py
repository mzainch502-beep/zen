"""Independent observer and paper-exit worker; PostgreSQL leader lock avoids duplicate workers."""
import asyncio, json, os, time, uuid
from decimal import Decimal
from sqlalchemy import select, text
from database.models import Database, User, Market, Strategy, Position, record
from backend.domain import Quote, Proposal
from backend.leadership import acquire
from backend.service import execute, positions, portfolio, Rejected
from exchange_adapters.ccxt_adapter import ReadAdapter, bounded_read
from agents.autonomous import process_observation, manage_exits, VERSION
from backend.futures_paper import manage as manage_futures
from agents.futures_pipeline import process as research_futures
from exchange_adapters.mexc_futures import MexcFutures,json_safe
from database.models import FuturesMarket,FuturesConfig
import websockets
SYMBOLS=['BTC/USDT','ETH/USDT','SOL/USDT']

class MarketObserver:
    def __init__(self,db): self.db=db
    def store(self,q):
        if q.ask<q.bid or time.time()-q.timestamp>15 or q.timestamp>time.time()+5: return
        with self.db.sessions() as s:
            m=s.get(Market,q.symbol)
            payload=q.model_dump(mode='json')
            if m: m.payload=payload;m.received=time.time()
            else: s.add(Market(symbol=q.symbol,payload=payload,received=time.time()))
            s.commit()
    async def stream_binance(self):
        symbols='/'.join(x.replace('/','').lower()+'@bookTicker' for x in SYMBOLS)
        url='wss://stream.binance.com:9443/stream?streams='+symbols
        while True:
            try:
                async with websockets.connect(url,ping_interval=20,max_size=1048576) as ws:
                    async for msg in ws:
                        d=json.loads(msg)['data']; raw=d['s'];symbol=raw[:-4]+'/USDT'
                        if symbol not in SYMBOLS: continue
                        bid=Decimal(d['b']);ask=Decimal(d['a'])
                        # bookTicker lacks event timestamp on some spot feeds: receipt time is labelled.
                        self.store(Quote(symbol=symbol,bid=bid,ask=ask,last=(bid+ask)/2,timestamp=time.time(),source='binance-ws-receipt'))
            except Exception:
                with self.db.sessions() as s: record(s,None,'observer_disconnect',{'source':'binance-ws'});s.commit()
                await asyncio.sleep(5)

async def run_futures_observer(db):
    futures=MexcFutures();cycle=0
    async def read(symbol):
        try:
            ticker=await futures.ticker(symbol)
            with db.sessions() as s:m=s.get(FuturesMarket,symbol);refresh_meta=not m or cycle%60==0
            metadata=(await futures.contracts(symbol))[0] if refresh_meta else None
            with db.sessions() as s:
                m=s.get(FuturesMarket,symbol)
                if m:
                    m.ticker=json_safe(ticker);m.received=time.time()
                    if metadata:m.contract=json_safe(metadata)
                else:s.add(FuturesMarket(symbol=symbol,ticker=json_safe(ticker),contract=json_safe(metadata),received=time.time()))
                s.commit()
        except Exception as e:
            with db.sessions() as s:record(s,None,'futures_market_error',{'symbol':symbol,'error_type':type(e).__name__});s.commit()
    try:
        while True:
            await asyncio.gather(*(read(symbol) for symbol in ['BTC_USDT','ETH_USDT','SOL_USDT']))
            with db.sessions() as s:
                record(s,None,'futures_observer_heartbeat',{'cycle':cycle})
                owners=list(s.scalars(select(User)))
                s.commit()
            for u in owners:
                with db.sessions() as s:
                    cfg=s.get(FuturesConfig,u.id);active=bool(cfg and cfg.workspace=='futures')
                    manage_futures(s,u.id);s.commit()
                if active and cycle%12==0:
                    for symbol in ['BTC_USDT','ETH_USDT','SOL_USDT']:
                        try:
                            rows=await futures.candles(symbol)
                            completed=[r for r in rows if r[0]/1000+60<=time.time()]
                            # Refresh execution quote after the slower candle request.
                            ticker=await futures.ticker(symbol)
                            with db.sessions() as s:
                                market=s.get(FuturesMarket,symbol)
                                if market:market.ticker=json_safe(ticker);market.received=time.time();research_futures(s,u,symbol,completed)
                                s.commit()
                        except Exception as e:
                            with db.sessions() as s:record(s,u.id,'research_error',{'symbol':symbol,'error_type':type(e).__name__});s.commit()
            cycle+=1
            await asyncio.sleep(5)
    finally:await futures.close()

async def run():
    db=Database()
    with db.engine.connect() as leader:
        await acquire(leader,937412)
        adapter=ReadAdapter(os.getenv('MARKET_EXCHANGE','bitget'))
        futures_task=asyncio.create_task(run_futures_observer(db))
        observer=MarketObserver(db)
        ws=asyncio.create_task(observer.stream_binance()) if adapter.name=='binance' else None
        try:
            cycle=0
            while True:
                for symbol in SYMBOLS:
                    try: observer.store(await bounded_read(lambda:adapter.quote(symbol)))
                    except Exception:
                        with db.sessions() as s: record(s,None,'market_error',{'symbol':symbol,'source':adapter.name});s.commit()
                with db.sessions() as s:
                    record(s,None,'worker_heartbeat',{'cycle':cycle,'live_enabled':False,'autonomous_paper':True,'version':VERSION});s.commit()
                    owners=list(s.scalars(select(User)))
                for u in owners:
                    with db.sessions() as s:
                        locked=s.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
                        snap=portfolio(s,locked)
                        if snap['equity'] is not None: locked.high_water=max(locked.high_water,Decimal(snap['equity']))
                        if cycle%12==0: record(s,u.id,'portfolio_snapshot',snap)
                        s.commit()
                    with db.sessions() as s:
                        manage_exits(s,u.id)
                        s.commit()
                    if cycle%12==0:
                        with db.sessions() as s:
                            cfg=s.get(FuturesConfig,u.id);future_workspace=bool(cfg and cfg.workspace=='futures')
                        if future_workspace:continue
                        for symbol in SYMBOLS:
                            try:
                                rows=await bounded_read(lambda:adapter.candles(symbol,'1m',100))
                                completed=[r for r in rows if r[0]/1000+60<=time.time()]
                                # Refresh the execution quote after historical data retrieval.
                                observer.store(await bounded_read(lambda:adapter.quote(symbol)))
                                with db.sessions() as s:
                                    process_observation(s,u.id,symbol,completed)
                                    s.commit()
                            except Exception as e:
                                with db.sessions() as s:
                                    record(s,u.id,'research_error',{'symbol':symbol,'error_type':type(e).__name__})
                                    s.commit()
                cycle+=1
                await asyncio.sleep(5)
        finally:
            if ws: ws.cancel()
            await adapter.close()
            futures_task.cancel()
            await asyncio.gather(futures_task,return_exceptions=True)
if __name__=='__main__': asyncio.run(run())
