"""Isolated linear-perpetual simulation using real MEXC futures bid/ask/mark data."""
import time
from decimal import Decimal
from sqlalchemy import select
from database.models import User,Record,FuturesConfig,FuturesPaperBook,FuturesPaperPosition,FuturesMarket,record
from backend.futures_domain import FuturesLimits,Contract,plan
from backend.service import Rejected,midnight
from backend.security import digest
from exchange_adapters.mexc_futures import json_safe
D=lambda x:Decimal(str(x))

def config(db,owner):
    c=db.get(FuturesConfig,owner)
    if not c:
        c=FuturesConfig(user_id=owner,workspace='spot',limits=FuturesLimits().model_dump(mode='json'),exchange_max=False)
        db.add(c);db.flush()
    return c

def book(db,owner):
    b=db.get(FuturesPaperBook,owner)
    if not b:b=FuturesPaperBook(user_id=owner);db.add(b);db.flush()
    return b

def account(db,owner):
    b=book(db,owner);ps=list(db.scalars(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==owner)))
    markets={m.symbol:m for m in db.scalars(select(FuturesMarket))}
    stale=any(p.symbol not in markets or time.time()-markets[p.symbol].received>15 for p in ps)
    equity=b.cash;unrealized=Decimal(0);exposure=Decimal(0);rows=[]
    for p in ps:
        d=p.data;m=markets.get(p.symbol);mark=D(m.ticker['fairPrice']) if m and time.time()-m.received<=15 else None
        qty=D(d['contracts'])*D(d['size']);pnl=(mark-D(d['entry']))*qty*(1 if d['direction']=='LONG' else -1) if mark else None
        if pnl is not None:equity+=D(d['margin'])+pnl;unrealized+=pnl;exposure+=qty*mark
        rows.append({'id':p.id,'symbol':p.symbol,'side':d['direction'],'quantity':str(d['contracts']),
                     'entry':d['entry'],'mark':str(mark) if mark else None,'unrealized':str(pnl) if pnl is not None else None,
                     'notional':str(qty*mark) if mark else None,'leverage':str(d['leverage']),'margin_mode':'isolated',
                     'allocated_margin':d['margin'],'liquidation_price':d['liquidation_estimate'],'liquidation_label':'Modeled paper estimate',
                     'stop':d['stop'],'take_profit':d['take_profit'],'entry_fees':d['entry_fee'],'funding':'Not settled in this simulation',
                     'product':'futures','paper':True,'stale':mark is None})
    fills=list(db.scalars(select(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill')))
    reset=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='paper_capital_reset').order_by(Record.created.desc()).limit(1))
    start=max(midnight(),reset.created if reset else 0)
    daily=sum((D(f.payload.get('realized_net',0))-D(f.payload.get('entry_fee',0)) for f in fills if f.created>=start),Decimal(0))
    fees=sum((D(f.payload.get('entry_fee',0))+D(f.payload.get('exit_fee',0)) for f in fills),Decimal(0))
    return {'portfolio':{'equity':None if stale else str(equity),'cash':str(b.cash),'unrealized':None if stale else str(unrealized),
                        'daily_net':str(daily),'net_pnl':None if stale else str(equity-b.initial_equity),'fees':str(fees),'funding':None,
                        'funding_label':'Funding settlement not modeled; reserve checked at entry','target':'25','target_label':'Aspirational',
                        'mode':db.get(User,owner).mode,'paper':True,'product':'futures','stale':stale,'exposure':None if stale else str(exposure)},
            'positions':rows}

def execute_paper(db,owner,p):
    u=db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True));c=config(db,owner);b=book(db,owner)
    fp=digest(p.model_dump_json())
    prior=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill',Record.payload['client_id'].as_string()==p.idempotency_key))
    if prior:
        if prior.payload['fingerprint']!=fp:raise Rejected('Client ID reused with different futures plan')
        return prior.payload
    if u.mode!='Paper':raise Rejected('New paper exposure is paused')
    m=db.get(FuturesMarket,p.symbol)
    if not m or time.time()-m.received>15:raise Rejected('No fresh real futures market data')
    snap=account(db,owner);limits=FuturesLimits.model_validate(c.limits)
    if snap['portfolio']['stale']:raise Rejected('Stale futures portfolio')
    if any(x['symbol']==p.symbol for x in snap['positions']):raise Rejected('Existing symbol exposure')
    recent=db.scalars(select(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill',Record.created>time.time()-60)).all()
    if len(recent)>=limits.max_order_rate:raise Rejected('Futures order rate limit')
    contract=Contract.parse(m.contract)
    contract=contract.model_copy(update={'taker_fee':max(contract.taker_fee,Decimal('.0008'))})
    d=plan(p,contract,m.ticker,limits,b.cash,D(snap['portfolio']['equity']),D(snap['portfolio']['exposure']),
           len(snap['positions']),D(snap['portfolio']['daily_net']),b.high_water,time.time())
    b.cash-=d['margin']+d['entry_fee']
    position=FuturesPaperPosition(user_id=owner,symbol=p.symbol,data=json_safe(d));db.add(position);db.flush()
    payload={'schema_version':1,'client_id':p.idempotency_key,'fingerprint':fp,'position_id':position.id,'symbol':p.symbol,'direction':p.direction,
             'entry_fee':str(d['entry_fee']),'plan':json_safe(d),'paper':True}
    record(db,owner,'futures_paper_fill',payload);return payload

def close_paper(db,owner,position_id,fraction,client_id,cause='owner_close'):
    db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True));b=book(db,owner)
    prior=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill',Record.payload['client_id'].as_string()==client_id))
    request_hash=digest(str((position_id,str(fraction),cause)))
    if prior:
        if prior.payload.get('fingerprint')!=request_hash:raise Rejected('Close client ID reused')
        return prior.payload
    p=db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.id==position_id,FuturesPaperPosition.user_id==owner).with_for_update().execution_options(populate_existing=True))
    if not p:raise Rejected('Position not found')
    if not 0<fraction<=1:raise Rejected('Reduction fraction outside (0,1]')
    m=db.get(FuturesMarket,p.symbol)
    if not m or time.time()-m.received>15:raise Rejected('Fresh futures quote required for simulated exit')
    d=dict(p.data);c=Contract.parse(m.contract);limits=FuturesLimits.model_validate(config(db,owner).limits)
    vol=c.round_vol(D(d['contracts'])*fraction)
    if vol<=0:raise Rejected('Reduction below exchange contract step')
    ratio=vol/D(d['contracts']);qty=vol*D(d['size']);direction=d['direction'];ticker=m.ticker
    mark=D(ticker['fairPrice']);liq=D(d['liquidation_estimate'])
    liquidated=(direction=='LONG' and mark<=liq) or (direction=='SHORT' and mark>=liq)
    if liquidated:
        vol=D(d['contracts']);ratio=Decimal(1);qty=vol*D(d['size']);cause='modeled_liquidation'
        gross=-D(d['margin']);fee=Decimal(0)
    else:
        exit_price=D(ticker['bid1'])*(1-limits.max_slippage_bps/10000) if direction=='LONG' else D(ticker['ask1'])*(1+limits.max_slippage_bps/10000)
        gross=qty*(exit_price-D(d['entry']))*(1 if direction=='LONG' else -1);fee=qty*exit_price*D(d['taker_fee'])
    margin=D(d['margin'])*ratio;entry_fee=D(d['entry_fee'])*ratio
    b.cash+=margin+gross-fee
    if ratio==1:db.delete(p)
    else:
        for key in ['contracts','margin','entry_fee']:d[key]=str(D(d[key])*(1-ratio))
        p.data=d
    payload={'schema_version':1,'client_id':client_id,'fingerprint':request_hash,'symbol':p.symbol,'position_id':p.id,'cause':cause,
             'contracts':str(vol),'realized_net':str(gross-fee),'round_trip_net':str(gross-fee-entry_fee),
             'exit_fee':str(fee),'allocated_entry_fee':str(entry_fee),'paper':True}
    record(db,owner,'futures_paper_fill',payload);record(db,owner,'trade_evaluation',payload);db.flush()
    if ratio==1:
        from backend.learning import completed
        completed(db,owner,p.id,d)
    return payload

def manage(db,owner):
    db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True))
    for p in list(db.scalars(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==owner))):
        m=db.get(FuturesMarket,p.symbol)
        if not m or time.time()-m.received>15:continue
        d=p.data;mark=D(m.ticker['fairPrice']);long=d['direction']=='LONG'
        stopped=mark<=D(d['stop']) if long else mark>=D(d['stop'])
        profit=mark>=D(d['take_profit']) if long else mark<=D(d['take_profit'])
        if stopped or profit or time.time()-p.created>=900:
            try:close_paper(db,owner,p.id,Decimal(1),'fexit-'+p.id,'stop_loss' if stopped else 'take_profit' if profit else 'maximum_hold')
            except Rejected as e:record(db,owner,'exit_error',{'reason':str(e),'position_id':p.id})
    snap=account(db,owner)
    if snap['portfolio']['equity'] is not None:
        b=book(db,owner);b.high_water=max(b.high_water,D(snap['portfolio']['equity']))
