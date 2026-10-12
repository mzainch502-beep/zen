"""Separate privileged executor: REST reconciliation, exactly-once submission attempt.

Ambiguous/submitting intents are only queried by external ID, never automatically
resubmitted. No credential is required by the public observer process.
"""
import asyncio,time
from decimal import Decimal
from sqlalchemy import select,text
from database.models import Database,Connection,User,FuturesAccount,FuturesIntent,record
from backend.security import Vault
from backend.leadership import acquire
from backend.futures_paper import config
from backend.futures_domain import FuturesProposal,FuturesLimits,Contract,plan
from backend.service import Rejected
from exchange_adapters.mexc_futures import MexcFutures,ExchangeFailure,UnknownSubmission,json_safe
D=lambda x:Decimal(str(x))

async def refresh(db,connection,a):
    assets=await a.assets();positions=await a.positions();mode=await a.position_mode()
    asset=next((x for x in assets if x['currency']=='USDT'),None)
    if not asset:raise ExchangeFailure('USDT futures account not available')
    with db.sessions() as s:
        previous=s.get(FuturesAccount,connection.id);old=previous.data if previous else {}
        eq=D(asset['equity']);day=int(time.time()//86400)
        data=json_safe({'asset':asset,'positions':positions,'position_mode':mode,
                        'high_water':str(max(eq,D(old.get('high_water',eq)))),
                        'day':day,'day_start_equity':old['day_start_equity'] if old.get('day')==day else str(eq),
                        'markets':old.get('markets',{}),'contracts':old.get('contracts',{})})
        if previous:previous.data=data;previous.received=time.time()
        else:s.add(FuturesAccount(connection_id=connection.id,user_id=connection.user_id,data=data,received=time.time()))
        s.commit()
    return data

async def process(db,connection,a,intent_id):
    with db.sessions() as s:
        i=s.scalar(select(FuturesIntent).where(FuturesIntent.id==intent_id).with_for_update().execution_options(populate_existing=True))
        if i.state!='pending':return
        owner=s.scalar(select(User).where(User.id==i.user_id).with_for_update().execution_options(populate_existing=True));cfg=config(s,owner.id)
        state=s.get(FuturesAccount,connection.id)
        if not state or time.time()-state.received>30:
            i.state='rejected';i.receipt={'reason':'Stale private account'};s.commit();return
        account=state.data;reduction=i.payload.get('reduce_only',False)
        if account['position_mode']!=2:
            i.state='rejected';i.receipt={'reason':'Only verified one-way execution supported'};s.commit();return
        if not reduction and (owner.mode!='Live' or cfg.live_connection_id!=connection.id or not cfg.activated):
            i.state='rejected';i.receipt={'reason':'Live activation revoked or paused'};s.commit();return
        symbol=i.symbol;client_id=i.client_id;source=dict(i.payload);limits=FuturesLimits.model_validate(cfg.limits);baseline_limits=dict(cfg.limits)
        # Mark as submitting BEFORE network I/O, so restart cannot repeat a write.
        i.state='submitting';i.updated=time.time();s.commit()
    try:
        raw=(await a.contracts(symbol))[0];ticker=await a.ticker(symbol);contract=Contract.parse(raw)
        payload=None
        if reduction:
            position=next((p for p in account['positions'] if str(p['positionId'])==source['position_id']),None)
            if not position:raise Rejected('Position no longer open')
            vol=contract.round_vol(D(position['holdVol'])*D(source['fraction']))
            if vol<=0 or vol>D(position['holdVol']):raise Rejected('Reduction quantity invalid')
            payload={'symbol':symbol,'price':contract.round_price(D(ticker['bid1'] if position['positionType']==1 else ticker['ask1'])),'vol':vol,'side':4 if position['positionType']==1 else 2,
                     'type':5,'openType':int(position['openType']),'positionId':int(position['positionId']),
                     'positionMode':2,'reduceOnly':True,'externalOid':client_id}
        else:
            if any(p['symbol']==symbol and D(p['holdVol'])>0 for p in account['positions']):raise Rejected('Existing live symbol exposure')
            fees=await a.fees(symbol);risk=await a.risk_limits(symbol)
            if fees.get('feeRateMode')=='LEVERAGE':raise Rejected('Leverage-dependent fee schedule not certified')
            fee=D(fees['realTakerFee']);cap=int(fees['maxLeverage'])
            risks=risk.get(symbol,[]) if isinstance(risk,dict) else []
            if not risks:raise Rejected('Account-specific risk tier missing')
            cap=min(cap,*[int(r['maxLeverage']) for r in risks])
            contract=contract.model_copy(update={'max_leverage':min(contract.max_leverage,cap),
                'taker_fee':max(contract.taker_fee,fee),
                'mmr':max(contract.mmr,*[D(r['mmr']) for r in risks]),
                'imr':max(contract.imr,*[D(r.get('imr',0)) for r in risks]),
                'max_vol':min(contract.max_vol,*[D(r['maxVol']) for r in risks])})
            if any(D(p['holdVol'])>0 for p in account['positions']):
                # Until multi-symbol mark reconciliation is complete, fail closed.
                raise Rejected('Only one live symbol at a time in this release')
            asset=account['asset'];eq=D(asset['equity']);daily=min(Decimal(0),eq-D(account['day_start_equity']))
            d=plan(FuturesProposal.model_validate(source['proposal']),contract,ticker,limits,D(asset['availableBalance']),eq,Decimal(0),0,daily,D(account['high_water']),time.time())
            payload={'symbol':symbol,'price':contract.round_price(D(ticker['ask1'] if d['direction']=='LONG' else ticker['bid1'])),'vol':d['contracts'],'leverage':d['leverage'],
                     'side':1 if d['direction']=='LONG' else 3,'type':5,'openType':1,'positionMode':2,
                     'externalOid':client_id,'stopLossPrice':d['stop'],'takeProfitPrice':d['take_profit'],'lossTrend':2,'profitTrend':2}
        with db.sessions() as s:
            i=s.get(FuturesIntent,intent_id);i.payload={**source,'wire':json_safe(payload)}
            record(s,i.user_id,'risk_approval',{'intent_id':i.id,'product':'live_futures','reduce_only':reduction,'approved':True});s.commit()
        # Re-read mode immediately before external write; reductions bypass entry pause.
        with db.sessions() as s:
            current=s.get(User,connection.user_id)
            latest_cfg=config(s,connection.user_id)
            if not reduction and (current.mode!='Live' or latest_cfg.live_connection_id!=connection.id or not latest_cfg.activated):raise Rejected('Execution paused/revoked before submission')
            if not reduction and latest_cfg.limits!=baseline_limits:raise Rejected('Risk limits changed during planning; submit a new proposal')
        response=await a.submit(payload)
        if not isinstance(response,dict) or not response.get('orderId'):raise UnknownSubmission('Acknowledgment cannot be identified safely')
        with db.sessions() as s:
            i=s.get(FuturesIntent,intent_id);i.state='acknowledged';i.updated=time.time();i.receipt=json_safe(response)
            record(s,i.user_id,'live_acknowledgment',{'intent_id':i.id,'order_id':str(response['orderId']),
                                                     'decision_to_ack_ms':(time.time()-i.created)*1000});s.commit()
    except UnknownSubmission:
        with db.sessions() as s:i=s.get(FuturesIntent,intent_id);i.state='unknown';i.receipt={'reason':'Ambiguous submission; external ID reconciliation only'};s.commit()
    except (ExchangeFailure,Rejected,ValueError,KeyError) as e:
        with db.sessions() as s:
            i=s.get(FuturesIntent,intent_id);i.state='rejected';i.receipt={'reason':str(e) if isinstance(e,(Rejected,ExchangeFailure)) else 'Malformed exchange capabilities'}
            record(s,i.user_id,'risk_veto',{'intent_id':i.id,'reason':i.receipt['reason']});s.commit()

async def reconcile(db,a,intent_id):
    with db.sessions() as s:
        i=s.get(FuturesIntent,intent_id);symbol=i.symbol;client_id=i.client_id
    try:remote=await a.order(symbol,client_id)
    except ExchangeFailure:return  # Never infer absent/failed from a read error.
    with db.sessions() as s:
        i=s.scalar(select(FuturesIntent).where(FuturesIntent.id==intent_id).with_for_update().execution_options(populate_existing=True))
        old=D(i.receipt.get('dealVol',0));filled=D(remote['dealVol']);total=D(remote['vol'])
        if filled<old or filled>total or total<=0:raise ExchangeFailure('Invalid cumulative fill state')
        state=int(remote['state'])
        mapped='filled' if state==3 and filled==total else 'cancelled' if state==4 else 'rejected' if state==5 else 'partial' if filled>0 else 'open'
        if i.state in ['filled','cancelled','rejected'] and i.state!=mapped:return
        changed=i.state!=mapped or filled!=old
        i.state=mapped;i.receipt=json_safe(remote);i.updated=time.time()
        if changed:record(s,i.user_id,'live_order_state',{'intent_id':i.id,'state':mapped,'filled':str(filled),
                                                     'decision_to_fill_observation_ms':(time.time()-i.created)*1000 if filled>old else None})
        s.commit()

async def run():
    db=Database();vault=Vault()
    with db.engine.connect() as leader:
        await acquire(leader,937414)
        while True:
            with db.sessions() as s:
                connections=[c for c in s.scalars(select(Connection)) if c.capabilities.get('product')=='futures' and not c.capabilities.get('revoked')]
            for c in connections:
                creds=vault.decrypt(c.user_id,c.exchange,c.ciphertext);a=MexcFutures(creds['apiKey'],creds['secret'])
                try:
                    await refresh(db,c,a)
                    with db.sessions() as s:
                        ids=[i.id for i in s.scalars(select(FuturesIntent).where(FuturesIntent.connection_id==c.id,FuturesIntent.state.in_(['pending','submitting','acknowledged','unknown','partial','open'])))]
                    for i in ids:
                        await process(db,c,a,i);await reconcile(db,a,i)
                except Exception as e:
                    with db.sessions() as s:record(s,c.user_id,'futures_connectivity_error',{'error_type':type(e).__name__});s.commit()
                finally:await a.close()
            with db.sessions() as s:record(s,None,'executor_heartbeat',{'live_connections':len(connections)});s.commit()
            await asyncio.sleep(5)
if __name__=='__main__':asyncio.run(run())
