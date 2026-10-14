import asyncio, os, time, uuid, secrets
from collections import deque
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select, delete
from pydantic import Field
from backend.domain import Strict, Limits, Proposal
from database.models import Database, User, Session, Connection, Order, Record, Market, Position, record
from backend.security import authenticate, create_session, verify, Vault, digest, password_hash
from backend.service import portfolio, serialize_positions, execute, serialize_order, Rejected
from exchange_adapters.ccxt_adapter import ReadAdapter, EXCHANGES

class Login(Strict):
    email: str=Field(max_length=254)
    password: str=Field(min_length=1,max_length=256)
class Setup(Login):
    setup_token: str=Field(min_length=16,max_length=256)
class AutomationCommand(Strict):
    enabled: bool

class Command(Strict):
    mode: str=Field(pattern='^(Paper|Paused|Emergency Stop)$')
class CredentialInput(Strict):
    exchange: str
    api_key: str=Field(min_length=8,max_length=512)
    secret: str=Field(min_length=8,max_length=512)
    passphrase: str | None=Field(default=None,max_length=512)
    read_only_attestation: bool
class Exits(Strict):
    stop: Decimal=Field(gt=0)
    take_profit: Decimal | None=Field(default=None,gt=0)

def create_app(database=None):
    database=database or Database()
    app=FastAPI(title='ZEN Paper API',version='0.8.0')
    app.state.database=database
    login_attempts=deque()
    def login_budget():
        now=time.monotonic()
        while login_attempts and login_attempts[0]<now-60: login_attempts.popleft()
        if len(login_attempts)>=20: raise HTTPException(429,"Authentication rate limit; wait one minute")
        login_attempts.append(now)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Do not reflect request bodies, which can contain credentials.
        return JSONResponse(status_code=422,content={'detail':'Invalid request fields'})
    @app.middleware('http')
    async def headers(request,call_next):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    def db_dep():
        with database.sessions() as db: yield db
    def owner(authorization: str=Header(default=''),db=Depends(db_dep)):
        token=authorization.removeprefix('Bearer ')
        u=authenticate(db,token)
        if not u: raise HTTPException(401,'Session expired or invalid')
        return u
    @app.get('/health')
    def health(db=Depends(db_dep)):
        db.execute(select(1))
        heartbeat=db.scalar(select(Record).where(Record.kind=='worker_heartbeat').order_by(Record.created.desc()).limit(1))
        scanner=db.scalar(select(Record).where(Record.kind=='research_scan_heartbeat').order_by(Record.created.desc()).limit(1))
        executor=db.scalar(select(Record).where(Record.kind=='executor_heartbeat').order_by(Record.created.desc()).limit(1))
        from database.models import FuturesMarket
        futures_markets=list(db.scalars(select(FuturesMarket)))
        public=[{'symbol':m.symbol,'max_leverage':m.contract.get('maxLeverage'),'api_allowed':m.contract.get('apiAllowed'),'fresh':time.time()-m.received<15} for m in futures_markets[:20]]
        return {'status':'ok','research_scanner_online':bool(scanner and time.time()-scanner.created<180),'research_market_reads':scanner.payload if scanner else None,'live_execution':bool(db.scalar(select(User).where(User.mode=='Live').limit(1))),'futures_executor_online':bool(executor and time.time()-executor.created<30),'futures_public_markets':public,'futures_catalogue_count':len(futures_markets),'autonomous_paper':True,'worker_version':heartbeat.payload.get('version') if heartbeat else None,'worker_online':bool(heartbeat and time.time()-heartbeat.created<30)}
    @app.post('/auth/setup')
    def setup(body: Setup,db=Depends(db_dep)):
        login_budget()
        expected=os.getenv('BOOTSTRAP_TOKEN','')
        if len(expected)<16 or not secrets.compare_digest(expected,body.setup_token): raise HTTPException(403,'Invalid or disabled setup token')
        if database.engine.dialect.name=='postgresql':
            from sqlalchemy import text
            db.execute(text('SELECT pg_advisory_xact_lock(937413)'))
        if db.scalar(select(User).limit(1)): raise HTTPException(409,'Owner already provisioned; setup disabled')
        try: encoded=password_hash(body.password)
        except ValueError as e: raise HTTPException(422,str(e))
        u=User(email=body.email.strip().lower(),password=encoded,mode='Paper',limits=Limits().model_dump(mode='json'))
        db.add(u);db.flush();record(db,u.id,'owner_provisioned',{});db.commit()
        return {'created':True,'notice':'Remove BOOTSTRAP_TOKEN from hosting variables now'}
    @app.post('/auth/login')
    def login(body: Login,db=Depends(db_dep)):
        login_budget()
        # Owner-installed accounts; no public signup or password reset surface.
        u=db.scalar(select(User).where(User.email==body.email.strip().lower()))
        if not u or not verify(u.password,body.password): raise HTTPException(401,'Invalid credentials')
        token=create_session(db,u); record(db,u.id,'login',{}); db.commit()
        return {'token':token,'expires_in':43200}
    @app.post('/auth/logout')
    def logout(u=Depends(owner),authorization: str=Header(),db=Depends(db_dep)):
        db.execute(delete(Session).where(Session.token_hash==digest(authorization.removeprefix('Bearer ')))); db.commit()
        return {'revoked':True}
    @app.get('/bootstrap/status')
    def bootstrap_status(db=Depends(db_dep)):
        return {'setup_available':bool(len(os.getenv('BOOTSTRAP_TOKEN',''))>=16 and not db.scalar(select(User).limit(1))), 'initial_mode':'Paper', 'live_execution':False}
    @app.get('/snapshot')
    def snapshot(u=Depends(owner),db=Depends(db_dep)):
        events=list(db.scalars(select(Record).where(Record.user_id==u.id).order_by(Record.created.desc()).limit(30)))
        decisions=[e for e in events if e.kind=='decision']
        latest=decisions[0].payload if decisions else {}
        from backend.futures_paper import config, account
        from backend.futures_live import live_snapshot
        from backend.futures_domain import FuturesLimits
        cfg=config(db,u.id)
        from backend.treasury import combined
        future=combined(db,u.id) if cfg.workspace=='combined' and not cfg.activated else live_snapshot(db,u.id) if cfg.live_connection_id and cfg.activated and cfg.workspace=='futures' else account(db,u.id) if cfg.workspace=='futures' else None
        from backend.research_status import status as research_status
        from backend.automation import status as automation_status
        return {'research':research_status(db,u.id),'automation':automation_status(db,u),'account':{'email':u.email},
            'agent':{'action':latest.get('action','WAIT'),'version':latest.get('version','research-v1'),
                     'automated_paper':automation_status(db,u)['enabled'],'research_trial':True,
                     'summary':'Continuous experimental paper scanner · unvalidated strategy',
                     'reason':latest.get('reason','Collecting evidence. Execution strategies remain gated by validation.')},
            'portfolio':future['portfolio'] if future else portfolio(db,u),'positions':future['positions'] if future else serialize_positions(db,u),
            'futures':{'workspace':cfg.workspace,'limits':FuturesLimits.model_validate(cfg.limits).model_dump(mode='json'),'exchange_max':cfg.exchange_max,'activated':bool(cfg.activated),'live_connection_id':cfg.live_connection_id},
            'limits':Limits.model_validate(u.limits).model_dump(mode='json'),
            'events':[{'id':e.id,'kind':e.kind,'created':e.created,'payload':e.payload} for e in events],
            'connections':[{'id':c.id,'exchange':c.exchange,'capabilities':c.capabilities} for c in db.scalars(select(Connection).where(Connection.user_id==u.id)) if not c.capabilities.get('revoked')]}
    @app.get('/markets')
    def markets(u=Depends(owner),db=Depends(db_dep)):
        from backend.futures_paper import config
        if config(db,u.id).workspace in ['futures','combined']:
            from database.models import FuturesMarket
            return [{'quote':{'symbol':m.symbol,'bid':m.ticker['bid1'],'ask':m.ticker['ask1'],'last':m.ticker['lastPrice'],'timestamp':int(m.ticker['timestamp'])/1000,'source':'mexc-futures','change_percent':str(Decimal(str(m.ticker.get('riseFallRate',0)))*100)},'stale':time.time()-m.received>15,'product':'futures','instrument':__import__('backend.instruments',fromlist=['classify']).classify(m.contract),'contract':{k:m.contract.get(k) for k in ['maxLeverage','minLeverage','contractSize','minVol','apiAllowed','state']},'ticker':{k:m.ticker.get(k) for k in ['fundingRate','holdVol','amount24','high24Price','lower24Price','fairPrice']}} for m in db.scalars(select(FuturesMarket).where(FuturesMarket.contract['state'].as_integer()==0).order_by(FuturesMarket.symbol))]
        return [{'quote':m.payload,'stale':time.time()-m.received>15} for m in db.scalars(select(Market))]
    @app.get('/candles')
    async def candles(symbol: str='BTC/USDT',timeframe: str='1m',u=Depends(owner),db=Depends(db_dep)):
        if __import__('re').fullmatch(r'[A-Z0-9]{2,20}_USDT',symbol):
            from database.models import FuturesMarket
            if not db.get(FuturesMarket,symbol):raise HTTPException(404,'Contract not discovered by observer')
            from exchange_adapters.mexc_futures import MexcFutures
            a=MexcFutures()
            try:return {'symbol':symbol,'timeframe':timeframe,'candles':await a.candles(symbol,timeframe,200)}
            except Exception:raise HTTPException(503,'Futures candles unavailable or timeframe unsupported')
            finally:await a.close()
        if symbol not in ['BTC/USDT','ETH/USDT','SOL/USDT'] or timeframe not in ['1m','3m','5m','15m','30m','1h','4h','1d']:
            raise HTTPException(422,'Unsupported market/timeframe')
        a=ReadAdapter(os.getenv('MARKET_EXCHANGE','bitget'))
        try: return {'symbol':symbol,'timeframe':timeframe,'candles':await a.candles(symbol,timeframe)}
        except Exception: raise HTTPException(503,'Exchange candles unavailable')
        finally: await a.close()
    @app.get('/market-depth')
    async def market_depth(symbol: str='BTC/USDT',u=Depends(owner),db=Depends(db_dep)):
        if __import__('re').fullmatch(r'[A-Z0-9]{2,20}_USDT',symbol):
            from database.models import FuturesMarket
            if not db.get(FuturesMarket,symbol):raise HTTPException(404,'Contract not discovered by observer')
            from exchange_adapters.mexc_futures import MexcFutures
            a=MexcFutures()
            try:return await a.depth(symbol)
            except Exception:raise HTTPException(503,'Futures depth unavailable')
            finally:await a.close()
        if symbol not in ['BTC/USDT','ETH/USDT','SOL/USDT']: raise HTTPException(422,'Unsupported market')
        a=ReadAdapter(os.getenv('MARKET_EXCHANGE','bitget'))
        try: return await a.depth(symbol)
        except Exception: raise HTTPException(503,'Order book currently unavailable')
        finally: await a.close()
    @app.get('/agent/automation')
    def automation_state(u=Depends(owner),db=Depends(db_dep)):
        from backend.automation import status
        return status(db,u)
    @app.put('/agent/automation')
    def automation_command(body:AutomationCommand,u=Depends(owner),db=Depends(db_dep)):
        from backend.automation import change
        locked=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        try: result=change(db,locked,body.enabled)
        except ValueError as e: raise HTTPException(409,str(e))
        db.commit()
        return result
    @app.post('/agent/mode')
    def mode(body: Command,u=Depends(owner),db=Depends(db_dep)):
        locked=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        locked.mode=body.mode; record(db,u.id,'mode',{'mode':body.mode}); db.commit()
        return {'mode':body.mode,'notice':'Emergency stop prevents new exposure. Existing positions require explicit close.'}
    @app.post('/live/activate')
    def live(u=Depends(owner)):
        raise HTTPException(409,'Live execution not implemented or certified. No order will be placed.')
    @app.put('/risk')
    def limits(body: Limits,u=Depends(owner),db=Depends(db_dep)):
        locked=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        from database.models import FuturesConfig
        cfg=db.get(FuturesConfig,u.id)
        if cfg and cfg.workspace in ['futures','combined']:raise HTTPException(409,'Use Settings → Trading controls to edit futures limits. This editor applies to spot only.')
        body.automatic=Limits.model_validate(locked.limits).automatic
        locked.limits=body.model_dump(mode='json')
        record(db,u.id,'risk_limits',locked.limits); db.commit(); return locked.limits
    @app.post('/paper/orders')
    def orders(body: Proposal,u=Depends(owner),db=Depends(db_dep)):
        try: o=execute(db,u.id,body); db.commit(); return serialize_order(o)
        except Rejected as e:
            db.rollback()
            record(db,u.id,'risk_veto',{'reason':str(e),'proposal':body.model_dump(mode='json')}); db.commit()
            raise HTTPException(409,str(e))
    @app.put('/positions/{position_id}/exits')
    def exits(position_id: str,body: Exits,u=Depends(owner),db=Depends(db_dep)):
        db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        p=db.scalar(select(Position).where(Position.id==position_id,Position.user_id==u.id).with_for_update().execution_options(populate_existing=True))
        if not p: raise HTTPException(404,'Position not found')
        if body.stop>=p.entry or (body.take_profit and body.take_profit<=p.entry): raise HTTPException(422,'Invalid exit levels')
        limits=Limits.model_validate(u.limits)
        if p.quantity*(p.entry-body.stop)+p.quantity*p.entry*Decimal('.002')>limits.max_loss_trade: raise HTTPException(409,'Exit change exceeds trade risk budget')
        p.stop=body.stop;p.take_profit=body.take_profit;record(db,u.id,'paper_exits',{'position':p.id,**body.model_dump(mode='json')});db.commit()
        return {'saved':True,'type':'Backend-monitored paper exits; not exchange-native'}
    @app.get('/exchanges')
    def directory(u=Depends(owner)):
        return [{'id':x,'live_enabled':False,'tested_private':False} for x in EXCHANGES]
    @app.post('/connections')
    async def connect(body: CredentialInput,u=Depends(owner),db=Depends(db_dep)):
        if not body.read_only_attestation: raise HTTPException(422,'Use a read-only key with trading and withdrawals disabled')
        try: vault=Vault()
        except Exception: raise HTTPException(503,'Credential vault not configured')
        creds={'apiKey':body.api_key,'secret':body.secret}
        if body.passphrase: creds['password']=body.passphrase
        try: a=ReadAdapter(body.exchange,creds)
        except ValueError: raise HTTPException(422,'Unknown exchange')
        try: caps=await a.discover(); balance=await a.balance()
        except Exception: raise HTTPException(502,'Connectivity or read permission test failed; verify key and account restrictions')
        finally: await a.close()
        c=Connection(user_id=u.id,exchange=body.exchange,ciphertext=vault.encrypt(u.id,body.exchange,creds),capabilities=caps)
        db.add(c);record(db,u.id,'connection_added',{'exchange':body.exchange});db.commit()
        return {'id':c.id,'capabilities':caps,'available_balances':balance,'notice':'Permission flags not verified; live trading remains disabled'}
    @app.delete('/connections/{connection_id}')
    def disconnect(connection_id: str,u=Depends(owner),db=Depends(db_dep)):
        locked=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
        c=db.scalar(select(Connection).where(Connection.id==connection_id,Connection.user_id==u.id))
        if not c: raise HTTPException(404,'Connection not found')
        if c.capabilities.get('product')=='futures':
            from database.models import FuturesAccount,FuturesIntent
            state=db.get(FuturesAccount,c.id)
            pending=db.scalar(select(FuturesIntent).where(FuturesIntent.connection_id==c.id,FuturesIntent.state.in_(['pending','submitting','unknown','acknowledged','partial','open'])))
            if pending or (state and any(Decimal(str(p['holdVol']))>0 for p in state.data['positions'])):raise HTTPException(409,'Close/reconcile live exposure before deleting this credential')
            c.ciphertext='revoked';c.capabilities={**c.capabilities,'revoked':True}
            from backend.futures_paper import config
            cfg=config(db,u.id)
            if cfg.live_connection_id==c.id:cfg.activated=None;cfg.live_connection_id=None;locked.mode='Paused'
        else:db.delete(c)
        record(db,u.id,'connection_removed',{'id':connection_id});db.commit()
        return {'removed':True,'notice':'Revoke the key on the exchange separately'}
    @app.get('/audit/export')
    def export(u=Depends(owner),db=Depends(db_dep)):
        return [{'kind':e.kind,'created':e.created,'payload':e.payload} for e in db.scalars(select(Record).where(Record.user_id==u.id).order_by(Record.created).limit(10000))]
    @app.websocket('/events')
    async def events(ws: WebSocket):
        await ws.accept()
        try:
            # Token in first frame, never query parameters or access logs.
            token=await asyncio.wait_for(ws.receive_text(),timeout=10)
            while True:
                with database.sessions() as db:
                    u=authenticate(db,token)
                    if not u: await ws.close(code=4401);return
                    await ws.send_json({'schema_version':1,'type':'snapshot','timestamp':time.time(),
                                        'portfolio':portfolio(db,u),'positions':serialize_positions(db,u)})
                await asyncio.sleep(3)
        except (WebSocketDisconnect,asyncio.TimeoutError): pass
    from backend.desk_api import install as install_desk
    install_desk(app,db_dep,owner)
    from backend.futures_api import install
    install(app,db_dep,owner)
    return app
app=create_app()
