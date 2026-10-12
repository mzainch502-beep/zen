"""Durable native order intents. Live use remains explicitly experimental until account-tested."""
import time
from decimal import Decimal
from sqlalchemy import select
from database.models import User,Connection,FuturesIntent,FuturesAccount,FuturesMarket,Record,record
from backend.futures_paper import config
from backend.futures_domain import FuturesLimits
from backend.security import digest
from backend.service import Rejected


def enqueue(db,owner,p,connection_id):
    u=db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True));c=config(db,owner)
    connection=db.scalar(select(Connection).where(Connection.id==connection_id,Connection.user_id==owner))
    if not connection or connection.capabilities.get('product')!='futures':raise Rejected('Owner futures connection required')
    if u.mode!='Live' or c.live_connection_id!=connection_id or not c.activated:raise Rejected('Live derivatives activation required')
    fingerprint=digest(p.model_dump_json())
    existing=db.scalar(select(FuturesIntent).where(FuturesIntent.user_id==owner,FuturesIntent.client_id==p.idempotency_key))
    if existing:
        if existing.fingerprint!=fingerprint:raise Rejected('Live client ID reused with another plan')
        return existing
    unresolved=db.scalar(select(FuturesIntent).where(FuturesIntent.user_id==owner,FuturesIntent.state.in_(['pending','submitting','acknowledged','open','partial','unknown'])))
    if unresolved:raise Rejected('Resolve outstanding exchange order before new exposure')
    limits=FuturesLimits.model_validate(c.limits)
    recent=db.scalars(select(FuturesIntent).where(FuturesIntent.user_id==owner,FuturesIntent.created>time.time()-60)).all()
    if len(recent)>=limits.max_order_rate:raise Rejected('Live order rate limit')
    state=db.get(FuturesAccount,connection_id)
    if not state or time.time()-state.received>30:raise Rejected('Fresh private account reconciliation required')
    intent=FuturesIntent(user_id=owner,connection_id=connection_id,client_id=p.idempotency_key,fingerprint=fingerprint,
                         symbol=p.symbol,payload={'proposal':p.model_dump(mode='json'),'reduce_only':False},state='pending')
    db.add(intent);db.flush();record(db,owner,'live_proposal',{'intent_id':intent.id,'symbol':p.symbol,'direction':p.direction});return intent

def enqueue_close(db,owner,position_id,fraction,client_id):
    db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True));c=config(db,owner)
    if not c.live_connection_id:raise Rejected('No activated live connection')
    state=db.get(FuturesAccount,c.live_connection_id)
    if not state or time.time()-state.received>30:raise Rejected('Private account state stale')
    if not 0<fraction<=1:raise Rejected('Invalid reduction fraction')
    position=next((p for p in state.data['positions'] if str(p['positionId'])==position_id and Decimal(str(p['holdVol']))>0),None)
    if not position:raise Rejected('Exchange position not found')
    payload={'reduce_only':True,'position_id':position_id,'fraction':str(fraction)};fingerprint=digest(str(payload))
    prior=db.scalar(select(FuturesIntent).where(FuturesIntent.user_id==owner,FuturesIntent.client_id==client_id))
    if prior:
        if prior.fingerprint!=fingerprint:raise Rejected('Close client ID reused')
        return prior
    # Only one outstanding reduction per position; ambiguous writes are never duplicated.
    prior=db.scalar(select(FuturesIntent).where(FuturesIntent.user_id==owner,FuturesIntent.state.in_(['pending','submitting','acknowledged','open','partial','unknown']),
                                               FuturesIntent.payload['position_id'].as_string()==position_id))
    if prior:raise Rejected('A reduction for this position is unresolved')
    i=FuturesIntent(user_id=owner,connection_id=c.live_connection_id,client_id=client_id,fingerprint=fingerprint,
                    symbol=position['symbol'],payload=payload,state='pending');db.add(i);db.flush();return i

def serialize(i):return {'id':i.id,'client_id':i.client_id,'symbol':i.symbol,'state':i.state,'receipt':i.receipt,'created':i.created}

def live_snapshot(db,owner):
    c=config(db,owner);state=db.get(FuturesAccount,c.live_connection_id) if c.live_connection_id else None
    stale=not state or time.time()-state.received>30
    if not state:return {'portfolio':{'mode':'Live','paper':False,'stale':True,'target':'25','product':'futures'},'positions':[]}
    data=state.data;asset=data['asset'];positions=[];exposure=Decimal(0)
    for p in data['positions']:
        if Decimal(str(p['holdVol']))<=0:continue
        cached=db.get(FuturesMarket,p['symbol'])
        market=cached.ticker if cached and time.time()-cached.received<=15 else None;mark=market.get('fairPrice') if market else None
        contract=cached.contract if cached else None;size=Decimal(str(contract['contractSize'])) if contract else None
        notional=Decimal(str(p['holdVol']))*size*Decimal(str(mark)) if size and mark else None
        if notional:exposure+=notional
        positions.append({'id':str(p['positionId']),'symbol':p['symbol'],'side':'LONG' if p['positionType']==1 else 'SHORT',
                         'quantity':str(p['holdVol']),'entry':str(p.get('holdAvgPriceFullyScale',p['holdAvgPrice'])),
                         'mark':None if stale else str(mark) if mark else None,'unrealized':None if stale else str(p.get('unRealizedPnl')) if p.get('unRealizedPnl') is not None else None,
                         'notional':str(notional) if notional is not None and not stale else None,'leverage':str(p['leverage']),
                         'margin_mode':'isolated' if p['openType']==1 else 'cross','allocated_margin':str(p.get('im',p.get('oim'))),
                         'liquidation_price':str(p['liquidatePrice']) if p.get('liquidatePrice') else None,'liquidation_label':'Exchange reported',
                         'entry_fees':str(p.get('totalFee')) if p.get('totalFee') is not None else None,'funding':str(p.get('holdFee')) if p.get('holdFee') is not None else None,
                         'product':'futures','paper':False,'stale':stale,'stop':None,'take_profit':None})
    return {'portfolio':{'mode':db.get(User,owner).mode,'paper':False,'product':'futures','stale':stale,
                         'equity':None if stale else str(asset['equity']),'cash':None if stale else str(asset['availableBalance']),
                         'unrealized':None if stale else str(asset.get('unrealized')) if asset.get('unrealized') is not None else None,
                         'net_pnl':None,'daily_net':None,'fees':None,'funding':None,'exposure':None if stale else str(exposure),'target':'25','target_label':'Aspirational',
                         'accounting_note':'Exchange equity and open-position values; complete daily fee/funding ledger not certified'},'positions':positions}
