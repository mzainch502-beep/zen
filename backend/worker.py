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

def revive(task,factory,db,component):
    if not task.done():return task
    error='Cancelled' if task.cancelled() else type(task.exception()).__name__ if task.exception() else 'UnexpectedReturn'
    with db.sessions() as s:record(s,None,'background_restart',{'component':component,'error_type':error});s.commit()
    return asyncio.create_task(factory())

async def run_futures_observer(db):
    from exchange_adapters.universe import catalogue,rotation
    from backend.shadow import pending_symbols
    from database.models import FuturesPaperPosition
    futures=MexcFutures();cycle=0;metadata={};cursor=0
    semaphore=asyncio.Semaphore(3)
    async def candles(symbol):
        async with semaphore:
            try:return symbol,[r for r in await futures.candles(symbol) if r[0]/1000+60<=time.time()]
            except Exception:return symbol,None
    async def scanner():
        nonlocal cursor
        while True:
            with db.sessions() as s:owners=list(s.scalars(select(User)))
            with db.sessions() as s:
                held=list(s.scalars(select(FuturesPaperPosition.symbol)))+pending_symbols(s)
                batch,cursor=rotation(list(s.scalars(select(FuturesMarket))),cursor,24,held)
            rows=await asyncio.gather(*(candles(symbol) for symbol in batch))
            for u in owners:
                scanned=0;failed=0;fills=0;vetoes=0
                for symbol,completed in rows:
                    if completed is None:failed+=1;continue
                    try:
                        # A fresh quote is required after candle requests.
                        ticker=await futures.ticker(symbol)
                        with db.sessions() as s:
                            market=s.get(FuturesMarket,symbol)
                            if market:
                                market.ticker=json_safe(ticker);market.received=time.time()
                                d=research_futures(s,u,symbol,completed)
                                if d:scanned+=1;fills+=d['execution']=='filled';vetoes+=d['execution']=='risk_veto'
                            s.commit()
                    except Exception as e:
                        failed+=1
                        with db.sessions() as s:record(s,u.id,'research_error',{'symbol':symbol,'error_type':type(e).__name__});s.commit()
                with db.sessions() as s:record(s,u.id,'scan_summary',{'catalogue':len(metadata),'batch':len(batch),'evaluated':scanned,'data_errors':failed,'fills':fills,'risk_vetoes':vetoes,'cursor':cursor});s.commit()
            await asyncio.sleep(30)
    scanner_task=asyncio.create_task(scanner())
    try:
        while True:
            scanner_task=revive(scanner_task,scanner,db,"futures_research")
            started=time.monotonic()
            try:
                if not metadata or cycle%60==0:
                    fresh=catalogue(await futures.contracts())
                    if not fresh:raise ValueError('No supported perpetual contracts discovered')
                    metadata=fresh
                tickers=await futures.tickers()
                with db.sessions() as s:
                    existing={m.symbol:m for m in s.scalars(select(FuturesMarket))}
                    for t in tickers:
                        symbol=t['symbol']
                        if symbol not in metadata:continue
                        m=existing.get(symbol)
                        if not m:m=FuturesMarket(symbol=symbol);s.add(m)
                        if m.contract!=json_safe(metadata[symbol]):m.contract=json_safe(metadata[symbol])
                        m.ticker=json_safe(t);m.received=time.time()
                    # Delisted markets retained for exits/audit but blocked for new entries.
                    for m in s.scalars(select(FuturesMarket)):
                        if m.symbol not in metadata:m.contract={**m.contract,'state':1,'apiAllowed':False}
                    record(s,None,'futures_observer_heartbeat',{'cycle':cycle,'catalogue':len(metadata),'fresh_quotes':len(tickers)})
                    s.commit()
            except Exception as e:
                with db.sessions() as s:record(s,None,'futures_market_error',{'error_type':type(e).__name__});s.commit()
            with db.sessions() as s:
                owners=list(s.scalars(select(User)))
            for u in owners:
                with db.sessions() as s:manage_futures(s,u.id);s.commit()
            cycle+=1
            await asyncio.sleep(max(1,5-(time.monotonic()-started)))
    finally:
        scanner_task.cancel()
        await asyncio.gather(scanner_task,return_exceptions=True)
        await futures.close()

async def run():
    db=Database()
    with db.engine.connect() as leader:
        await acquire(leader,937412)
        adapter=ReadAdapter(os.getenv('MARKET_EXCHANGE','bitget'))
        futures_task=asyncio.create_task(run_futures_observer(db))
        from backend.context import run as run_context
        context_task=asyncio.create_task(run_context(db))
        observer=MarketObserver(db)
        ws=asyncio.create_task(observer.stream_binance()) if adapter.name=='binance' else None
        try:
            cycle=0
            while True:
                context_task=revive(context_task,lambda:run_context(db),db,'public_context')
                futures_task=revive(futures_task,lambda:run_futures_observer(db),db,'futures_observer')
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
                        from backend.treasury import capture
                        if cycle%12==0:capture(s,u.id)
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
                                    if cfg and cfg.workspace=='combined':
                                        from agents.portfolio_pipeline import process_spot
                                        process_spot(s,u.id,symbol,completed)
                                    else:process_observation(s,u.id,symbol,completed)
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
            futures_task.cancel();context_task.cancel()
            await asyncio.gather(futures_task,context_task,return_exceptions=True)
if __name__=='__main__': asyncio.run(run())
