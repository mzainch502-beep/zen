"""Forward-only, unleveraged OHLC shadow trials. Never an order authority."""
import math,time,hashlib
from sqlalchemy import select
from database.models import Record,record

VERSION='shadow-recovery-v1'
MIN_SAMPLES=8

def settle(trial,rows,now):
    """Enter at the next complete candle open; stop-first for ambiguous OHLC bars."""
    start=(int(trial['opened_at']//60)+1)*60000
    bars=[r for r in rows if r[0]>=start and r[0]/1000+60<=now]
    if not bars or bars[0][0]!=start:return None
    if any(b[0]-a[0]!=60000 for a,b in zip(bars,bars[1:])):return None
    if any(len(r)<6 or not all(math.isfinite(float(x)) for x in r[:6]) for r in bars):return None
    entry=float(bars[0][1]);fraction=trial['stop_fraction'];sign=1 if trial['direction']=='LONG' else -1
    stop=entry*(1-sign*fraction);take=entry*(1+sign*2.2*fraction)
    for i,r in enumerate(bars[:30]):
        opened,high,low,close=map(float,r[1:5]);exit_price=None;reason=None
        if (sign==1 and low<=stop) or (sign==-1 and high>=stop):
            exit_price=min(opened,stop) if sign==1 else max(opened,stop);reason='stop'
        elif (sign==1 and high>=take) or (sign==-1 and low<=take):exit_price=take;reason='take_profit'
        elif i==29:exit_price=close;reason='time_exit'
        if exit_price is not None:
            net=sign*(exit_price/entry-1)-trial['cost_fraction']
            return {'net_fraction':net,'closed_at':r[0]/1000+60,'entry_at':start/1000,'cause':reason}
    return None

def apply_recovery(weights,actual,shadow):
    for key,w in weights.items():
        if not w['suspended']:continue
        cutoff=max((r.get('closed_at',0) for r in actual if r.get('strategy','')+':'+r.get('regime','unknown')==key),default=0)
        rows=sorted([r for r in shadow if r.get('group')==key and r.get('opened_at',0)>cutoff and r.get('version')==VERSION and r.get('state')=='closed'],key=lambda r:r['closed_at'])[-MIN_SAMPLES:]
        net=sum(r['net_fraction'] for r in rows);gains=sum(max(0,r['net_fraction']) for r in rows);loss=-sum(min(0,r['net_fraction']) for r in rows)
        passed=len(rows)>=MIN_SAMPLES and net>0 and gains>1.25*loss and sum(r['net_fraction']>0 for r in rows)>=5 and rows[-1]['closed_at']-rows[0]['opened_at']>=3600
        w.update(recovery_samples=len(rows),recovery_required=MIN_SAMPLES,recovery_net_fraction=net,recovery_status='paper probation' if passed else 'forward shadow evaluation',suspended=not passed)
    return weights

def trials(db,owner):
    return list(db.scalars(select(Record).where(Record.user_id==owner,Record.kind=='shadow_trial').order_by(Record.created.desc()).limit(500)))

def advance(db,owner,symbol,rows,decision,weights,now=None):
    now=time.time() if now is None else now
    active=trials(db,owner)
    for r in active:
        t=r.payload
        if t['symbol']!=symbol or t['state']!='open':continue
        result=settle(t,rows,now)
        if result:
            r.payload={**t,**result,'state':'closed'}
            record(db,owner,'shadow_outcome',{**r.payload,'shadow_only':True})
        elif now-t['opened_at']>3600:r.payload={**t,'state':'expired','reason':'Missing complete forward candles'}
    db.flush()
    for op in decision['opportunities']:
        key=op['strategy']+':'+decision['regime']
        if not weights.get(key,{}).get('suspended') or not op.get('research_eligible'):continue
        # One sequential trial per group, no simultaneous correlated pseudo-samples.
        if any(r.payload['group']==key and (r.payload['state']=='open' or now-r.payload['opened_at']<1800) for r in active):continue
        trial_id=hashlib.sha256(f'{owner}:{key}:{symbol}:{decision["bar_timestamp"]}'.encode()).hexdigest()
        if any(r.payload.get('trial_id')==trial_id for r in active):continue
        record(db,owner,'shadow_trial',{'version':VERSION,'trial_id':trial_id,'group':key,'symbol':symbol,'direction':op['direction'],'opened_at':now,'state':'open','stop_fraction':decision['stop_fraction'],'cost_fraction':decision['estimated_cost_bps']/10000,'shadow_only':True})
        db.flush()

def pending_symbols(db):
    return list(dict.fromkeys(r.payload['symbol'] for r in db.scalars(select(Record).where(Record.kind=='shadow_trial',Record.created>time.time()-3600)).all() if r.payload.get('state')=='open'))
