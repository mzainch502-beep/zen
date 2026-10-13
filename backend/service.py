import time
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from database.models import User, Position, Order, Market, Record, record
from backend.domain import Quote, Limits, Proposal
from backend.security import digest
from risk.governor import evaluate, FEE

class Rejected(ValueError): pass

def quotes(db): return {m.symbol:Quote.model_validate(m.payload) for m in db.scalars(select(Market))}
def positions(db,owner): return list(db.scalars(select(Position).where(Position.user_id==owner)))
def midnight():
    now=datetime.now(timezone.utc)
    return now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
def portfolio(db,u):
    qs=quotes(db); ps=positions(db,u.id)
    stale=any(p.symbol not in qs or time.time()-qs[p.symbol].timestamp>15 for p in ps)
    marked=sum((p.quantity*qs[p.symbol].bid for p in ps if p.symbol in qs),Decimal(0))
    equity=None if stale else u.cash+marked
    orders=list(db.scalars(select(Order).where(Order.user_id==u.id,Order.state=='filled')))
    reset=db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='portfolio_capital_reset').order_by(Record.created.desc()).limit(1))
    if reset:orders=[o for o in orders if o.created>=reset.created]
    today=[o for o in orders if o.created>=midnight()]
    fees=sum((o.fee for o in orders),Decimal(0))
    daily=sum((o.realized-o.fee for o in today),Decimal(0))
    return {'equity':str(equity) if equity is not None else None,'cash':str(u.cash),
            'unrealized':None if stale else str(sum((p.quantity*(qs[p.symbol].bid-p.entry) for p in ps),Decimal(0))),
            'daily_net':str(daily),'fees':str(fees),'funding':'0','target':'25','target_label':'Aspirational',
            'mode':u.mode,'stale':stale,'paper':True,'exposure':None if stale else str(marked),
            'net_pnl':None if equity is None else str(equity-u.initial_equity)}

def execute(db,owner,p: Proposal):
    # PostgreSQL row lock serializes every capital/risk mutation for an owner across workers.
    u=db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True))
    fp=digest(p.model_dump_json())
    old=db.scalar(select(Order).where(Order.user_id==owner,Order.client_id==p.idempotency_key))
    if old:
        if old.fingerprint!=fp: raise Rejected('Idempotency key reused with different request')
        return old
    q=quotes(db).get(p.symbol)
    if not q: raise Rejected('No real market quote; start market observer')
    ps=positions(db,owner); pos=next((x for x in ps if x.symbol==p.symbol),None)
    snap=portfolio(db,u)
    if snap['equity'] is None and not p.reduce_only: raise Rejected('Portfolio marks stale')
    recent=list(db.scalars(select(Order).where(Order.user_id==owner,Order.created>time.time()-60)))
    losses=list(db.scalars(select(Order).where(Order.user_id==owner,Order.side=='sell',Order.state=='filled').order_by(Order.created.desc()).limit(3)))
    limits=Limits.model_validate(u.limits)
    cooldown=losses[0].created+limits.cooldown_seconds if len(losses)==3 and all(o.realized-o.fee<0 for o in losses) else 0
    v=evaluate(p,q,limits,mode=u.mode,cash=u.cash,equity=Decimal(snap['equity'] or u.cash),
        high_water=u.high_water,daily_net=Decimal(snap['daily_net'])+min(Decimal(snap['unrealized'] or 0),Decimal(0)),exposure=Decimal(snap['exposure'] or 0),
        positions=len(ps),existing_quantity=pos.quantity if pos else Decimal(0),orders_last_minute=len(recent),cooldown_until=cooldown)
    record(db,owner,'risk_approval',{'proposal':p.model_dump(mode='json'),'verdict':v.model_dump(mode='json')})
    if not v.approved: raise Rejected('; '.join(v.reasons))
    if p.side=='buy':
        from backend.treasury import entry_guard
        entry_guard(db,owner,p.quantity*q.ask*(1+limits.max_slippage_bps/10000))
    if p.side=='buy' and pos: raise Rejected('Adding to an existing position requires aggregate stop-risk support')
    t0=time.perf_counter()
    price=q.ask*(1+limits.max_slippage_bps/10000) if p.side=='buy' else q.bid*(1-limits.max_slippage_bps/10000)
    fee=p.quantity*price*FEE
    realized=Decimal(0)
    closed_context=None
    if p.side=='buy':
        u.cash-=p.quantity*price+fee
        pos=Position(user_id=owner,symbol=p.symbol,quantity=p.quantity,entry=price,entry_fees=fee,stop=p.stop,take_profit=p.take_profit)
        db.add(pos)
    else:
        allocated=pos.entry_fees*p.quantity/pos.quantity
        realized=p.quantity*(price-pos.entry)
        pos.entry_fees-=allocated
        u.cash+=p.quantity*price-fee
        pos.quantity-=p.quantity
        if pos.quantity==0:
            context=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='paper_spot_context',Record.payload['position_id'].as_string()==pos.id).limit(1))
            if context:closed_context=(pos.id,context.payload)
            db.delete(pos)
        record(db,owner,'spot_realized',{'position_id':pos.id,'round_trip_net':str(realized-fee-allocated),'product':'spot','paper':True})
    if closed_context:
        from backend.learning import completed
        completed(db,owner,*closed_context)
    o=Order(user_id=owner,client_id=p.idempotency_key,fingerprint=fp,symbol=p.symbol,side=p.side,
            quantity=p.quantity,filled=p.quantity,price=price,fee=fee,realized=realized,state='filled')
    db.add(o); db.flush()
    record(db,owner,'paper_fill',{'symbol':p.symbol,'side':p.side,'order_id':o.id,'price':str(price),'quantity':str(p.quantity),'fee':str(fee),
                                'realized_gross':str(realized),'processing_ms':(time.perf_counter()-t0)*1000,
                                'latency_type':'local paper accounting; not exchange acknowledgment'})
    snap=portfolio(db,u)
    if snap['equity'] is not None: u.high_water=max(u.high_water,Decimal(snap['equity']))
    record(db,owner,'portfolio_snapshot',snap)
    return o

def serialize_order(o):
    return {k:str(getattr(o,k)) for k in ['id','symbol','side','quantity','filled','price','fee','realized','state','created']}
def serialize_positions(db,u):
    qs=quotes(db)
    rows=[]
    for p in positions(db,u.id):
        q=qs.get(p.symbol); fresh=q and time.time()-q.timestamp<=15
        rows.append({'id':p.id,'symbol':p.symbol,'side':'LONG','quantity':str(p.quantity),'entry':str(p.entry),
            'mark':str(q.bid) if fresh else None,'unrealized':str(p.quantity*(q.bid-p.entry)) if fresh else None,
            'notional':str(p.quantity*q.bid) if fresh else None,'leverage':'1','margin_mode':'spot',
            'liquidation_price':None,'stop':str(p.stop) if p.stop else None,'take_profit':str(p.take_profit) if p.take_profit else None,
            'entry_fees':str(p.entry_fees),'funding':'0','stale':not bool(fresh)})
    return rows
