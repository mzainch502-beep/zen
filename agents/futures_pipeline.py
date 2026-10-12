"""Experimental paper LONG/SHORT trial; never automatically promoted to live."""
import hashlib,time
from decimal import Decimal
from sqlalchemy import select
from database.models import FuturesConfig,FuturesMarket,Record,User,record
from backend.domain import Quote
from backend.futures_domain import FuturesProposal,FuturesLimits,Contract
from backend.futures_paper import execute_paper,account
from backend.service import Rejected
from agents.autonomous import assess
VERSION='futures-breakout-paper-trial-v1'

def process(db,u,symbol,rows):
    u=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
    cfg=db.get(FuturesConfig,u.id)
    if not cfg or cfg.workspace!='futures':return
    market=db.get(FuturesMarket,symbol)
    if not market:return
    t=market.ticker
    quote=Quote(symbol=symbol,bid=t['bid1'],ask=t['ask1'],last=t['lastPrice'],timestamp=int(t['timestamp'])/1000,source='mexc-futures')
    d=assess(rows,quote);d['version']=VERSION
    if d['hypothesis']=='SHORT' and 'bar_timestamp' in d:
        drift=abs(float(rows[-1][4])/float(rows[-20][4])-1)
        if drift>d.get('expected_cost_bps',10000)/10000*2:d.update(action='SHORT',reason='Bearish breakout qualifies for simulated SHORT experiment')
    if u.mode=='Live':d['action']='WAIT';d['reason']='Autonomous live strategy promotion not validated; manual orders only'
    key='fauto-'+hashlib.sha256(f'{u.id}:{symbol}:{VERSION}:{d.get("bar_timestamp",0)}'.encode()).hexdigest()[:48]
    if db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='decision',Record.payload['decision_key'].as_string()==key)):return
    d.update(symbol=symbol,decision_key=key);record(db,u.id,'decision',d)
    limits=FuturesLimits.model_validate(cfg.limits)
    if not limits.automatic or d['action'] not in ['LONG','SHORT'] or u.mode!='Paper':return
    snap=account(db,u.id);cash=Decimal(snap['portfolio']['cash'])
    margin=min(limits.max_margin,cash*Decimal('.8'))
    if margin<=0:return
    long=d['action']=='LONG';entry=Decimal(t['ask1'] if long else t['bid1']);fraction=Decimal(str(d['stop_fraction']))
    p=FuturesProposal(symbol=symbol,direction=d['action'],margin=margin,leverage=limits.max_leverage,use_exchange_max=cfg.exchange_max,
                      stop=entry*(1-fraction if long else 1+fraction),take_profit=entry*(1+3*fraction if long else 1-3*fraction),idempotency_key=key)
    try:
        with db.begin_nested():execute_paper(db,u.id,p)
    except Rejected as e:record(db,u.id,'risk_veto',{'reason':str(e),'decision_key':key,'product':'paper_futures'})
