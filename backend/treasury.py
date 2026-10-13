"""Consolidated simulated books; Decimal accounting and aggregate entry checks."""
import time
from decimal import Decimal as D
from sqlalchemy import select
from database.models import User,Record,Order,record
from backend.futures_paper import account as futures_account,config
from backend.service import portfolio as spot_account,serialize_positions,Rejected

def combined(db,owner):
    u=db.get(User,owner);s=spot_account(db,u);f=futures_account(db,owner)
    ps=[{**p,'product':'spot','paper':True} for p in serialize_positions(db,u)]+f['positions']
    stale=s['stale'] or f['portfolio']['stale']
    fp=f['portfolio'];add=lambda k:str(D(s.get(k) or 0)+D(fp.get(k) or 0))
    gross=sum((D(p.get('notional') or 0) for p in ps),D(0))
    net=sum((D(p.get('notional') or 0)*(-1 if p['side']=='SHORT' else 1) for p in ps),D(0))
    margin=sum((D(p.get('allocated_margin') or 0) for p in ps),D(0))
    equity=None if stale else add('equity')
    allocation={}
    for p in ps:
        asset=p['symbol'].replace('/','_').split('_')[0]
        allocation[asset]=allocation.get(asset,D(0))+D(p.get('notional') or 0)
    return {'portfolio':{'equity':equity,'cash':add('cash'),'unrealized':None if stale else add('unrealized'),
        'daily_net':add('daily_net'),'net_pnl':None if stale else add('net_pnl'),'fees':add('fees'),'funding':None,
        'funding_label':'Futures settlements not modeled','mode':u.mode,'paper':True,'product':'combined','stale':stale,
        'exposure':None if stale else str(gross),'gross_exposure':None if stale else str(gross),'net_exposure':None if stale else str(net),
        'allocated_margin':str(margin),'margin_utilization':str(margin/D(equity)) if equity and D(equity)>0 else None,
        'target':'80','target_label':'Aspirational income objective, never an execution quota',
        'allocation':[{ 'asset':k,'gross_notional':str(v),'fraction':str(v/gross) if gross else '0'} for k,v in sorted(allocation.items())],
        'book_balances':{'spot':s['equity'],'futures':fp['equity']}},'positions':ps}

def entry_guard(db,owner,new_notional):
    cfg=config(db,owner)
    if cfg.workspace!='combined':return
    snap=combined(db,owner)['portfolio']
    limits=cfg.limits
    # One shared entry budget across both books; reductions never call this gate.
    since=time.time()-60
    spot_orders=len(db.scalars(select(Order).where(Order.user_id==owner,Order.created>since)).all())
    future_orders=len(db.scalars(select(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill',Record.created>since)).all())
    rate=min(int(limits['max_order_rate']),int(db.get(User,owner).limits['max_order_rate']))
    if spot_orders+future_orders>=rate:raise Rejected('Combined order rate limit')
    if snap['stale']:raise Rejected('Combined portfolio marks are stale')
    if D(snap['exposure'])+new_notional>D(str(limits['max_notional'])):raise Rejected('Combined exposure ceiling')
    if D(snap['daily_net'])+min(D(snap['unrealized']),D(0))<=-D(str(limits['max_daily_loss'])):raise Rejected('Combined daily loss circuit breaker')
    # Track the actual joint peak from snapshots, not a sum of independent peaks.
    reset=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='portfolio_capital_reset').order_by(Record.created.desc()).limit(1))
    peak=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='treasury_peak',Record.created>=(reset.created if reset else 0)).order_by(Record.created.desc()).limit(1))
    if peak and D(peak.payload['equity'])-D(snap['equity'])>=D(str(limits['max_drawdown'])):raise Rejected('Combined drawdown circuit breaker')
    if len(combined(db,owner)['positions'])>=int(limits['max_positions']):raise Rejected('Combined position count ceiling')

def capture(db,owner):
    cfg=config(db,owner)
    if cfg.workspace!='combined':return
    snap=combined(db,owner)['portfolio']
    if snap['equity'] is None:return
    prior=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='treasury_peak').order_by(Record.created.desc()).limit(1))
    if not prior or D(snap['equity'])>D(prior.payload['equity']):record(db,owner,'treasury_peak',{'equity':snap['equity']})
    record(db,owner,'unified_snapshot',snap)
