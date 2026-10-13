"""Paper spot alternatives evaluated on their own venue's completed candles."""
import hashlib,time
from decimal import Decimal as D,ROUND_DOWN
from sqlalchemy import select
from database.models import User,Market,Record,Position,record
from backend.domain import Limits,Proposal
from backend.futures_paper import config
from backend.service import execute,portfolio,Rejected
from backend.learning import snapshot
from research.adaptive import evaluate,VERSION

def process_spot(db,owner,symbol,rows):
    u=db.scalar(select(User).where(User.id==owner).with_for_update().execution_options(populate_existing=True));cfg=config(db,owner)
    if cfg.workspace!='combined':return
    m=db.get(Market,symbol)
    if not m:return
    q=m.payload;l=Limits.model_validate(u.limits)
    t={'bid1':q['bid'],'ask1':q['ask'],'lastPrice':q['last'],'fairPrice':q['last'],'timestamp':int(q['timestamp']*1000),'fundingRate':0}
    d=evaluate(rows,t,cfg.limits.get('profile','balanced'),snapshot(db,owner)['weights'],fee=.001,slippage_bps=float(l.max_slippage_bps))
    key='spot-'+hashlib.sha256(f'{owner}:{symbol}:{VERSION}:{d.get("bar_timestamp",int(time.time()//60))}'.encode()).hexdigest()[:48]
    if db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='decision',Record.payload['decision_key'].as_string()==key)):return
    d.update(symbol=symbol,product='spot',decision_key=key,execution='not_requested')
    if d['action']=='SHORT':d.update(action='WAIT',execution_reason='Spot cannot open a naked SHORT; derivatives alternatives evaluated separately')
    if not l.automatic or u.mode!='Paper' or cfg.activated:d.update(execution='blocked',execution_reason='Spot automatic entry unavailable in current mode')
    elif d['action']=='LONG':
        snap=portfolio(db,u);notional=min(D('10'),u.cash/D('1.002'),l.max_notional-D(snap['exposure'] or 0))
        f=D(str(d['stop_fraction']));cost=f+D('.002')+l.max_slippage_bps*3/10000
        notional=min(notional,l.max_loss_trade/cost)
        if notional>=5:
            entry=D(q['ask']);qty=(notional/(entry*(1+l.max_slippage_bps/10000))).quantize(D('.000000000001'),rounding=ROUND_DOWN)
            p=Proposal(symbol=symbol,side='buy',quantity=qty,stop=entry*(1-f),take_profit=entry*(1+2*f),idempotency_key=key)
            try:
                with db.begin_nested():
                    o=execute(db,owner,p);pos=db.scalar(select(Position).where(Position.user_id==owner,Position.symbol==symbol))
                    record(db,owner,'paper_spot_context',{'position_id':pos.id,'strategy':d['strategy'],'regime':d['regime'],'initial_risk':str(notional*cost),'version':VERSION,'product':'spot'})
                    d.update(execution='filled',order_id=o.id)
            except Rejected as e:d.update(execution='risk_veto',execution_reason=str(e))
        else:d.update(execution='risk_veto',execution_reason='Spot allocation below minimum research notional')
    record(db,owner,'decision',d)
    return d
