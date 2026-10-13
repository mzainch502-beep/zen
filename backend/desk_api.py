import time
from decimal import Decimal as D
from fastapi import Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,delete
from backend.domain import Strict,Limits
from backend.futures_domain import FuturesLimits
from backend.futures_paper import config,book
from backend.treasury import combined,capture
from backend.instruments import classify
from backend.security import digest
from database.models import User,Position,FuturesPaperPosition,Record,FuturesMarket,Market,record

class Capital(Strict):
    amount:D=Field(ge=1,le=1000000000,max_digits=28,decimal_places=12)
    futures_fraction:D=Field(default=D('.5'),ge=D('.05'),le=D('.95'))
    leverage_ceiling:int=Field(default=5,ge=1,le=500)
    auto_risk:bool=True
    automatic:bool=False
    confirmation:str
    client_id:str=Field(min_length=16,max_length=64,pattern='^[a-zA-Z0-9_-]+$')

def install(app,db_dep,owner):
    @app.get('/portfolio/overview')
    def overview(u=Depends(owner),db=Depends(db_dep)):
        cfg=config(db,u.id)
        if cfg.activated:raise HTTPException(409,'Combined view currently supports simulated books only; use native exchange workspace for live balances')
        return combined(db,u.id)
    @app.post('/portfolio/paper-capital')
    def capital(body:Capital,u=Depends(owner),db=Depends(db_dep)):
        u=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True));cfg=config(db,u.id)
        fp=digest(body.model_dump_json())
        prior=db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='portfolio_capital_reset',Record.payload['client_id'].as_string()==body.client_id))
        if prior:
            if prior.payload['fingerprint']!=fp:raise HTTPException(409,'Capital command ID reused with different request')
            return prior.payload
        if cfg.activated or u.mode in ['Live','Emergency Stop'] or body.confirmation!='INITIALIZE PAPER PORTFOLIO':raise HTTPException(409,'Explicit simulated portfolio confirmation required; live account must be deactivated')
        if db.scalar(select(Position).where(Position.user_id==u.id)) or db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==u.id)):
            raise HTTPException(409,'Close simulated positions before changing paper capital')
        f=(body.amount*body.futures_fraction).quantize(D('.000000000001'));s=body.amount-f
        u.cash=u.initial_equity=u.high_water=s;u.mode='Paper'
        b=book(db,u.id);b.cash=b.initial_equity=b.high_water=f
        limits=FuturesLimits(max_leverage=body.leverage_ceiling,max_margin=min(D('10'),f),max_notional=min(body.amount,D('100')),
            max_loss_trade=min(D('2'),body.amount*D('.01')),max_daily_loss=min(D('6'),body.amount*D('.03')),
            max_drawdown=min(D('20'),body.amount*D('.1')),max_positions=3,profile='aggressive',automatic=body.automatic,auto_risk=body.auto_risk)
        cfg.workspace='combined';cfg.limits=limits.model_dump(mode='json');cfg.exchange_max=False
        spot=Limits(automatic=body.automatic,max_loss_trade=min(D('2'),body.amount*D('.01')),max_daily_loss=min(D('6'),body.amount*D('.03')),
            max_drawdown=min(D('20'),body.amount*D('.1')),max_notional=min(D('40'),s),max_correlated_notional=min(D('40'),s))
        u.limits=spot.model_dump(mode='json')
        payload={'schema_version':1,'client_id':body.client_id,'fingerprint':fp,'total':str(body.amount),'spot':str(s),'futures':str(f),'paper':True,'automatic':body.automatic}
        record(db,u.id,'portfolio_capital_reset',payload);record(db,u.id,'treasury_peak',{'equity':str(body.amount)});db.flush();capture(db,u.id);db.commit();return payload
    @app.get('/portfolio/history')
    def history(period:str='1D',u=Depends(owner),db=Depends(db_dep)):
        days={'1D':1,'7D':7,'30D':30,'90D':90,'1Y':365,'ALL':None}
        if period not in days:raise HTTPException(422,'Unsupported period')
        reset=db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='portfolio_capital_reset').order_by(Record.created.desc()).limit(1))
        start=max(reset.created if reset else 0,time.time()-days[period]*86400 if days[period] else 0)
        rows=list(db.scalars(select(Record).where(Record.user_id==u.id,Record.kind=='unified_snapshot',Record.created>=start).order_by(Record.created.desc()).limit(5000)))
        return {'period':period,'paper':True,'source':'Recorded consolidated portfolio snapshots','limit':5000,
            'points':[{'timestamp':r.created,'equity':r.payload['equity']} for r in reversed(rows)]}
    @app.get('/risk/overview')
    def risk(u=Depends(owner),db=Depends(db_dep)):
        from risk.adaptive import recommend
        cfg=config(db,u.id)
        if cfg.activated:raise HTTPException(409,'Combined risk analytics pending live native reconciliation; native controls remain available')
        snap=combined(db,u.id)['portfolio'];equity=D(snap['equity'] or 0)
        rec=recommend(db,u.id,cfg.limits,equity)
        ps=combined(db,u.id)['positions']
        scenarios=[]
        for shock in [D('-.2'),D('-.05'),D('.05'),D('.2')]:
            pnl=sum((D(p['notional'] or 0)*shock*(-1 if p['side']=='SHORT' else 1) for p in ps),D(0))
            scenarios.append({'price_shock':str(shock),'linear_pnl':None if snap['stale'] else str(pnl),'notice':'Static exposure estimate; exits, funding, gaps and liquidation are not modeled'})
        return {'portfolio':snap,'recommendation':rec,'scenarios':scenarios,'value_at_risk':None,'correlation':None,
            'unavailable':['Statistical VaR: insufficient validated return history','Correlation: synchronized history not available'],
            'live_authorized':False}
    @app.get('/instruments')
    def instruments(u=Depends(owner),db=Depends(db_dep)):
        return [{'symbol':m.symbol,**classify(m.contract),'api_allowed':m.contract.get('apiAllowed') is True,'fresh':time.time()-m.received<=15} for m in db.scalars(select(FuturesMarket))]
    @app.get('/context/events')
    def context(u=Depends(owner),db=Depends(db_dep)):
        from backend.context import snapshot
        return snapshot(db)
    @app.get('/platform/capabilities')
    def capabilities(u=Depends(owner)):
        return {'native_android':True,'desktop_web':False,'ios':False,'direct_stock_brokers':False,'stock_linked_perpetuals':'Discovered from venue contract labels; underlying rules require verification',
            'automatic_live':False,'private_order_certification':False,'multi_factor_auth':False,'password_recovery':False,
            'llm_research':'Provider not configured','context_news':'Public source metadata; not an order authority'}
