"""Contextual multi-hypothesis PAPER execution, with independent risk approval."""
import hashlib,time
from decimal import Decimal
from sqlalchemy import select
from database.models import FuturesMarket,FuturesPaperPosition,Record,User,record
from backend.futures_domain import FuturesProposal,FuturesLimits,Contract
from backend.futures_paper import execute_paper,account,config
from backend.service import Rejected
from backend.learning import snapshot as learning_snapshot
from research.adaptive import evaluate,VERSION

def process(db,u,symbol,rows):
    u=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
    cfg=config(db,u.id)
    if cfg.workspace not in ['futures','combined']:return
    market=db.get(FuturesMarket,symbol)
    if not market:return
    limits=FuturesLimits.model_validate(cfg.limits);t=market.ticker
    if limits.auto_risk:
        from risk.adaptive import recommend
        equity=Decimal(account(db,u.id)['portfolio']['equity'] or 0)
        limits=FuturesLimits.model_validate(recommend(db,u.id,cfg.limits,equity,t)['effective_limits'])
    fee=max(float(market.contract.get('takerFeeRate',.0008)),.0008)
    d=evaluate(rows,t,limits.profile,learning_snapshot(db,u.id)['weights'],fee=fee,slippage_bps=float(limits.max_slippage_bps))
    key='fauto-'+hashlib.sha256(f'{u.id}:{symbol}:{VERSION}:{d.get("bar_timestamp",int(time.time()//60))}'.encode()).hexdigest()[:48]
    if db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='decision',Record.payload['decision_key'].as_string()==key)):return
    d.update(symbol=symbol,decision_key=key,profile=limits.profile,execution='not_requested')
    blocked='Live strategy promotion pending' if cfg.activated or u.mode=='Live' else 'Automatic trading is disabled' if not limits.automatic else 'Workspace paused' if u.mode!='Paper' else None
    if blocked:d.update(execution='blocked',execution_reason=blocked)
    if not blocked and d['action'] in ['LONG','SHORT']:
        snap=account(db,u.id);cash=Decimal(snap['portfolio']['cash'])
        exposure=Decimal(snap['portfolio']['exposure'] or 0)
        c=Contract.parse(market.contract);lev=min(limits.max_leverage,c.max_leverage)
        # Size down to available notional, exchange IMR and stop-loss budget.
        fraction=Decimal(str(d['stop_fraction']));fee_d=Decimal(str(fee));funding=abs(Decimal(str(t.get('fundingRate',0))))
        loss_fraction=fraction+fee_d*2+limits.max_slippage_bps*3/10000+funding
        notional=min(limits.max_notional-exposure,limits.max_margin*lev,cash*Decimal('.75')*lev,limits.max_loss_trade/loss_fraction)
        margin=min(notional/lev,limits.max_margin)
        if margin>0:
            long=d['action']=='LONG';entry=Decimal(str(t['ask1'] if long else t['bid1']))
            # Keep exits inside isolated liquidation envelope; governor independently checks them.
            p=FuturesProposal(symbol=symbol,direction=d['action'],margin=margin.quantize(Decimal('.000000000001')),
                leverage=lev,stop=(entry*(1-fraction if long else 1+fraction)).quantize(Decimal('.000000000001')),
                take_profit=(entry*(1+Decimal("2.2")*fraction if long else 1-Decimal("2.2")*fraction)).quantize(Decimal('.000000000001')),idempotency_key=key)
            try:
                with db.begin_nested():
                    result=execute_paper(db,u.id,p)
                    position=db.get(FuturesPaperPosition,result['position_id'])
                    context=dict(position.data);context.update(strategy=d['strategy'],regime=d['regime'],version=VERSION,
                        decision_key=key,initial_risk=str(Decimal(context['notional'])*loss_fraction))
                    position.data=context
                    d.update(execution='filled',position_id=position.id)
                    record(db,u.id,'autonomous_futures_entry',{'symbol':symbol,'direction':d['action'],'strategy':d['strategy'],'position_id':position.id,'decision_key':key,'paper':True})
            except (Rejected,ValueError) as e:
                d.update(execution='risk_veto',execution_reason=str(e));record(db,u.id,'risk_veto',{'reason':str(e),'decision_key':key,'product':'paper_futures'})
        else:d.update(execution='risk_veto',execution_reason='No available allocation within limits')
    record(db,u.id,'decision',d)
    return d
