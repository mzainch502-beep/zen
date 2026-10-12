import time
from decimal import Decimal
from fastapi import Depends,HTTPException
from pydantic import Field
from sqlalchemy import select
from backend.domain import Strict
from backend.futures_domain import FuturesLimits,FuturesProposal,Contract
from backend.futures_paper import config,book,account,execute_paper,close_paper
from backend.futures_live import enqueue,enqueue_close,serialize
from backend.security import Vault
from backend.service import Rejected
from database.models import User,Connection,FuturesAccount,FuturesIntent,FuturesPaperPosition,FuturesMarket,Record,record
from exchange_adapters.mexc_futures import MexcFutures,json_safe

class Settings(Strict):
    workspace:str=Field(pattern='^(spot|futures)$')
    limits:FuturesLimits
    exchange_max:bool=False
class Connect(Strict):
    api_key:str=Field(min_length=8,max_length=512)
    secret:str=Field(min_length=8,max_length=512)
    withdrawals_disabled:bool
    trading_permission_enabled:bool
    derivatives_permitted:bool
class Activation(Strict):
    connection_id:str
    confirmation:str
    acknowledge_experimental:bool
    derivatives_permitted:bool
class Close(Strict):
    fraction:Decimal=Field(default=Decimal(1),gt=0,le=1)
    idempotency_key:str=Field(min_length=16,max_length=64,pattern='^[a-zA-Z0-9_-]+$')
class Seed(Strict):
    equity:Decimal=Field(gt=0,le=100000)
    confirmation:str
class Exits(Strict):
    stop:Decimal=Field(gt=0)
    take_profit:Decimal=Field(gt=0)

def install(app,db_dep,owner):
    @app.get('/futures/public-contracts')
    def public_contracts(db=Depends(db_dep)):
        # Public exchange data only. Never contains owners, balances or credentials.
        return [{'symbol':m.symbol,'ticker':m.ticker,'contract':m.contract,'received':m.received,'source':'mexc-futures','stale':time.time()-m.received>15} for m in db.scalars(select(FuturesMarket))]
    @app.get('/futures/settings')
    def settings(u=Depends(owner),db=Depends(db_dep)):
        c=config(db,u.id)
        return {'workspace':c.workspace,'limits':FuturesLimits.model_validate(c.limits).model_dump(mode='json'),'exchange_max':c.exchange_max,
                'live_connection_id':c.live_connection_id,'activated':bool(c.activated),
                'live_validation':'Private exchange order acceptance not validated in this release'}
    @app.put('/futures/settings')
    def save(body:Settings,u=Depends(owner),db=Depends(db_dep)):
        db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True));c=config(db,u.id)
        if c.activated and body.workspace=='spot':raise HTTPException(409,'Close and reconcile live exposure, then return to paper before changing workspace')
        body.limits.automatic=FuturesLimits.model_validate(c.limits).automatic
        if c.activated and body.limits.automatic:
            raise HTTPException(409,'Autonomous live strategy promotion remains pending')
        if c.workspace!=body.workspace:
            spot=dict(u.limits);spot['automatic']=False;u.limits=spot
            body.limits.automatic=False
        c.workspace=body.workspace;c.limits=body.limits.model_dump(mode='json');c.exchange_max=body.exchange_max
        record(db,u.id,'futures_settings',body.model_dump(mode='json'));db.commit();return {'saved':True}
    @app.post('/futures/paper/seed')
    def seed(body:Seed,u=Depends(owner),db=Depends(db_dep)):
        db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        if u.mode=='Live' or body.confirmation!='RESET SIMULATED CAPITAL':raise HTTPException(409,'Explicit paper reset confirmation required')
        if db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==u.id)):raise HTTPException(409,'Close paper futures positions before resetting')
        b=book(db,u.id);b.cash=body.equity;b.initial_equity=body.equity;b.high_water=body.equity
        record(db,u.id,'paper_capital_reset',{'equity':str(body.equity),'product':'futures','paper':True});db.commit();return {'reset':True}
    @app.post('/futures/paper/orders')
    def paper(body:FuturesProposal,u=Depends(owner),db=Depends(db_dep)):
        try:result=execute_paper(db,u.id,body);db.commit();return result
        except Rejected as e:
            db.rollback();record(db,u.id,'risk_veto',{'reason':str(e),'product':'paper_futures'});db.commit();raise HTTPException(409,str(e))
    @app.post('/futures/positions/{position_id}/close')
    def close(position_id:str,body:Close,u=Depends(owner),db=Depends(db_dep)):
        try:
            # UUID position IDs identify only the simulated ledger; native numeric IDs only live.
            if db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.id==position_id,FuturesPaperPosition.user_id==u.id)) or db.scalar(select(Record).where(Record.user_id==u.id,Record.kind=='futures_paper_fill',Record.payload['client_id'].as_string()==body.idempotency_key)):
                result=close_paper(db,u.id,position_id,body.fraction,body.idempotency_key)
            else:result=serialize(enqueue_close(db,u.id,position_id,body.fraction,body.idempotency_key))
            db.commit();return result
        except Rejected as e:db.rollback();raise HTTPException(409,str(e))
    @app.put('/futures/positions/{position_id}/exits')
    def exits(position_id:str,body:Exits,u=Depends(owner),db=Depends(db_dep)):
        db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        p=db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==u.id,FuturesPaperPosition.id==position_id).with_for_update().execution_options(populate_existing=True))
        if not p:raise HTTPException(409,'Live TP/SL editing is not certified; use the exchange protective-order controls')
        d=dict(p.data);entry=Decimal(d['entry']);liq=Decimal(d['liquidation_estimate']);long=d['direction']=='LONG'
        if not (liq<body.stop<entry<body.take_profit if long else body.take_profit<entry<body.stop<liq):raise HTTPException(409,'Exit levels violate entry/liquidation envelope')
        cost=Decimal(d['contracts'])*Decimal(d['size'])*(abs(entry-body.stop)+entry*Decimal(d['taker_fee'])*2)
        if cost>FuturesLimits.model_validate(config(db,u.id).limits).max_loss_trade:raise HTTPException(409,'Exit change exceeds loss budget')
        d['stop']=str(body.stop);d['take_profit']=str(body.take_profit);p.data=d
        record(db,u.id,'futures_exits',{'position_id':position_id,**body.model_dump(mode='json')});db.commit();return {'saved':True}
    @app.post('/futures/connections')
    async def connect(body:Connect,u=Depends(owner),db=Depends(db_dep)):
        if not body.withdrawals_disabled or not body.trading_permission_enabled or not body.derivatives_permitted:
            raise HTTPException(422,'Confirm futures trading permission, no withdrawals, and lawful account eligibility')
        a=MexcFutures(body.api_key,body.secret)
        try:
            await a.sync_clock();assets=await a.assets();ps=await a.positions();mode=await a.position_mode()
            if mode!=2:raise HTTPException(409,'Set one-way position mode on MEXC first. ZEN does not change your account mode automatically.')
            asset=next((x for x in assets if x['currency']=='USDT'),None)
            if asset is None:raise HTTPException(409,'USDT futures account unavailable')
            ciphertext=Vault().encrypt(u.id,'mexc',{'apiKey':body.api_key,'secret':body.secret})
            caps={'product':'futures','native_adapter':'mexc-open-api-v1','private_reads_verified':True,
                  'trading_permission_owner_attested':True,'withdrawals_disabled_owner_attested':True,
                  'permissions_verified':False,'live_enabled':False,'position_mode':mode,'live_orders_tested':False}
            c=Connection(user_id=u.id,exchange='mexc',ciphertext=ciphertext,capabilities=caps);db.add(c);db.flush()
            data=json_safe({'asset':asset,'positions':ps,'position_mode':mode,'high_water':str(asset['equity']),
                            'day':int(time.time()//86400),'day_start_equity':str(asset['equity']),'markets':{},'contracts':{}})
            db.add(FuturesAccount(connection_id=c.id,user_id=u.id,data=data,received=time.time()));record(db,u.id,'connection_added',{'exchange':'mexc','product':'futures'});db.commit()
            return {'id':c.id,'capabilities':caps,'available_balance':str(asset['availableBalance'])}
        except HTTPException:raise
        except Exception:db.rollback();raise HTTPException(502,'MEXC private API test failed; verify account eligibility, credentials and one-way mode')
        finally:await a.close()
    @app.post('/futures/live/activate')
    def activate(body:Activation,u=Depends(owner),db=Depends(db_dep)):
        user=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True));c=config(db,u.id)
        connection=db.scalar(select(Connection).where(Connection.id==body.connection_id,Connection.user_id==u.id))
        if body.confirmation!='I AUTHORIZE LIVE FUTURES' or not body.acknowledge_experimental or not body.derivatives_permitted:
            raise HTTPException(409,'Explicit live futures authorization and eligibility acknowledgment required')
        if not connection or connection.capabilities.get('product')!='futures' or connection.capabilities.get('revoked'):
            raise HTTPException(409,'Owner futures connection required')
        state=db.get(FuturesAccount,connection.id)
        if not state or time.time()-state.received>30 or state.data['position_mode']!=2:
            raise HTTPException(409,'Fresh private one-way account reconciliation required')
        if db.scalar(select(FuturesPaperPosition).where(FuturesPaperPosition.user_id==u.id)):
            raise HTTPException(409,'Close simulated futures positions before live activation')
        if FuturesLimits.model_validate(c.limits).automatic:
            raise HTTPException(409,'Autonomous live strategy has not passed promotion gates. Disable automatic trials for manual live activation.')
        heartbeat=db.scalar(select(Record).where(Record.kind=='executor_heartbeat').order_by(Record.created.desc()).limit(1))
        if not heartbeat or time.time()-heartbeat.created>30:raise HTTPException(409,'Privileged executor offline')
        user.mode='Live';c.workspace='futures';c.live_connection_id=connection.id;c.activated=time.time()
        record(db,u.id,'live_futures_activation',{'connection_id':connection.id,'limits':c.limits,'private_order_acceptance':'untested; owner acknowledged experimental status'});db.commit()
        return {'mode':'Live','automatic_live':False,'notice':'Manual risk-approved native futures orders enabled; private order acceptance remains unverified'}
    @app.post('/futures/live/deactivate')
    def deactivate(u=Depends(owner),db=Depends(db_dep)):
        user=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True));c=config(db,u.id)
        state=db.get(FuturesAccount,c.live_connection_id) if c.live_connection_id else None
        unresolved=db.scalar(select(FuturesIntent).where(FuturesIntent.user_id==u.id,FuturesIntent.state.in_(['pending','submitting','unknown','acknowledged','partial','open'])))
        if unresolved or (c.activated and (not state or time.time()-state.received>30 or any(Decimal(str(p['holdVol']))>0 for p in state.data['positions']))):
            raise HTTPException(409,'Close and reconcile live exposure before returning to paper')
        c.activated=None;user.mode='Paper';record(db,u.id,'live_deactivated',{});db.commit();return {'mode':'Paper'}
    @app.post('/futures/live/orders')
    def live(body:FuturesProposal,u=Depends(owner),db=Depends(db_dep)):
        try:
            c=config(db,u.id)
            if not c.live_connection_id:raise Rejected('Activate a futures connection first')
            result=enqueue(db,u.id,body,c.live_connection_id);db.commit();return serialize(result)
        except Rejected as e:db.rollback();raise HTTPException(409,str(e))
    @app.get('/futures/orders')
    def orders(u=Depends(owner),db=Depends(db_dep)):
        return [serialize(i) for i in db.scalars(select(FuturesIntent).where(FuturesIntent.user_id==u.id).order_by(FuturesIntent.created.desc()).limit(30))]
