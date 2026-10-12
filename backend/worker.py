"""Independent observer and paper-exit worker; PostgreSQL leader lock avoids duplicate workers."""
import asyncio, json, os, time, uuid
from decimal import Decimal
from sqlalchemy import select, text
from database.models import Database, User, Market, Strategy, Position, record
from backend.domain import Quote, Proposal
from backend.service import execute, positions, portfolio, Rejected
from exchange_adapters.ccxt_adapter import ReadAdapter, bounded_read
from agents.pipeline import Observation, DecisionAgent
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

async def run():
    db=Database()
    with db.engine.connect() as leader:
        if db.engine.dialect.name=='postgresql':
            if not leader.scalar(text('SELECT pg_try_advisory_lock(937412)')): raise RuntimeError('Another worker owns leadership')
        adapter=ReadAdapter(os.getenv('MARKET_EXCHANGE','bitget'))
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
                    record(s,None,'worker_heartbeat',{'cycle':cycle,'live_enabled':False});s.commit()
                    owners=list(s.scalars(select(User)))
                for u in owners:
                    with db.sessions() as s:
                        for p in positions(s,u.id):
                            m=s.get(Market,p.symbol)
                            if not m or time.time()-m.received>15: continue
                            q=Quote.model_validate(m.payload)
                            if (p.stop and q.bid<=p.stop) or (p.take_profit and q.bid>=p.take_profit):
                                try:
                                    execute(s,u.id,Proposal(symbol=p.symbol,side='sell',quantity=p.quantity,reduce_only=True,
                                        idempotency_key='exit-'+p.id));s.commit()
                                except Rejected as e:
                                    s.rollback();record(s,u.id,'exit_error',{'reason':str(e),'position_id':p.id});s.commit()
                    if cycle%12==0:
                        for symbol in SYMBOLS:
                            try:
                                rows=await adapter.candles(symbol,'1m',100)
                                completed=[r for r in rows if r[0]/1000+60<time.time()]
                                with db.sessions() as s:
                                    m=s.get(Market,symbol)
                                    if not m: continue
                                    q=Quote.model_validate(m.payload)
                                    o=Observation(symbol,tuple(float(r[4]) for r in completed),float(q.spread_bps))
                                    decision=DecisionAgent().decide(o,list(s.scalars(select(Strategy))))
                                    record(s,u.id,'decision',{'symbol':symbol,**decision});s.commit()
                            except Exception:
                                with db.sessions() as s: record(s,u.id,'research_error',{'symbol':symbol});s.commit()
                cycle+=1
                await asyncio.sleep(5)
        finally:
            if ws: ws.cancel()
            await adapter.close()
if __name__=='__main__': asyncio.run(run())
