import asyncio,time,json,hmac,hashlib
from decimal import Decimal as D
import httpx,pytest
from sqlalchemy import select,func
from backend.futures_domain import Contract,FuturesLimits,FuturesProposal,plan,liquidation_estimate
from backend.futures_paper import execute_paper,close_paper,book,config,account,manage
from backend.futures_live import enqueue
from backend.futures_executor import process,reconcile
from database.models import Database,User,FuturesMarket,FuturesPaperPosition,Record,Connection,FuturesAccount,FuturesIntent
from backend.domain import Limits
from backend.security import password_hash
from backend.service import Rejected
from exchange_adapters.mexc_futures import MexcFutures,signature,decimal_json,UnknownSubmission
from fastapi.testclient import TestClient
from backend.api import create_app

def meta():return {'symbol':'BTC_USDT','contractSize':'.01','volUnit':'1','minVol':'1','maxVol':'100000','priceUnit':'.001','maxLeverage':500,'minLeverage':1,'maintenanceMarginRate':'.001','takerFeeRate':'.0008','apiAllowed':True,'state':0,'countryConfigContractMaxLeverage':0}
def tick():return {'symbol':'BTC_USDT','bid1':'100','ask1':'100.01','lastPrice':'100','fairPrice':'100','timestamp':int(time.time()*1000),'fundingRate':'0'}
def proposal(**kw):return FuturesProposal(**{'symbol':'BTC_USDT','direction':'LONG','margin':'1','leverage':10,'stop':'98','take_profit':'104','idempotency_key':'future-test-000001',**kw})
def make_plan(p=None,c=None,l=None,**kw):
 args={'available':D('3'),'equity':D('3'),'exposure':D(0),'position_count':0,'daily_net':D(0),'high_water':D('3'),'now':time.time()};args.update(kw)
 return plan(p or proposal(),c or Contract.parse(meta()),tick(),l or FuturesLimits(max_leverage=10),**args)

@pytest.fixture
def world(tmp_path):
 db=Database('sqlite:///'+str(tmp_path/'futures.db'));db.create_dev()
 with db.sessions() as s:
  u=User(email='futures@test.invalid',password=password_hash('futures-test-password'),mode='Paper',limits=Limits().model_dump(mode='json'));s.add(u);s.flush()
  cfg=config(s,u.id);cfg.workspace='futures';cfg.limits=FuturesLimits(max_leverage=10).model_dump(mode='json')
  b=book(s,u.id);b.cash=b.initial_equity=b.high_water=D('3')
  s.add(FuturesMarket(symbol='BTC_USDT',contract=meta(),ticker=tick(),received=time.time()));s.commit();owner=u.id
 c=TestClient(create_app(db));r=c.post('/auth/login',json={'email':'futures@test.invalid','password':'futures-test-password'});headers={'Authorization':'Bearer '+r.json()['token']}
 return db,owner,c,headers

def test_contract_precision_and_country_cap():
 c=Contract.parse({**meta(),'countryConfigContractMaxLeverage':50})
 assert c.max_leverage==50;assert c.round_vol(D('12.95'))==12
 assert c.round_price(D('100.0019'))==D('100.001')

def test_small_balance_long_and_short_plans():
 a=make_plan();assert a['margin']+a['reserve']<=3
 b=make_plan(proposal(direction='SHORT',stop='102',take_profit='96'))
 assert b['direction']=='SHORT';assert b['liquidation_estimate']>b['entry']
 assert a['liquidation_estimate']<a['entry']

def test_500x_requires_explicit_ceiling_and_buffer():
 p=proposal(margin='.5',leverage=500,stop='99.95',take_profit='100.2')
 with pytest.raises(Rejected):make_plan(p)
 d=make_plan(p,l=FuturesLimits(max_leverage=500,max_notional=1000,max_slippage_bps=1,min_liquidation_distance='.0001'))
 assert d['leverage']==500;assert d['margin']+d['reserve']<3

def test_full_balance_does_not_ignore_fees():
 with pytest.raises(Rejected,match='fees'):make_plan(proposal(margin='3',leverage=500,stop='99.99',take_profit='101'),l=FuturesLimits(max_leverage=500,max_notional=2000,min_liquidation_distance='.0001'))

@pytest.mark.parametrize('kwargs,reason',[({'daily_net':D('-6')},'Daily'),({'high_water':D('25')},'Drawdown'),({'position_count':2},'Position'),({'exposure':D('40')},'Notional'),({'available':D('.01')},'cash')])
def test_futures_risk_veto(kwargs,reason):
 with pytest.raises(Rejected,match=reason):make_plan(**kwargs)

def test_paper_short_roundtrip_and_idempotency(world):
 db,u,c,h=world;p=proposal(direction='SHORT',stop='102',take_profit='96')
 result=c.post('/futures/paper/orders',headers=h,json=p.model_dump(mode='json'));assert result.status_code==200,result.text
 same=c.post('/futures/paper/orders',headers=h,json=p.model_dump(mode='json'));assert same.json()['position_id']==result.json()['position_id']
 assert c.post('/futures/paper/orders',headers=h,json=p.model_copy(update={'margin':D('2')}).model_dump(mode='json')).status_code==409
 with db.sessions() as s:
  m=s.get(FuturesMarket,'BTC_USDT');m.ticker={**tick(),'bid1':'95.99','ask1':'96','lastPrice':'96','fairPrice':'96'};s.commit()
 close={'fraction':'1','idempotency_key':'future-close-00001'};pid=result.json()['position_id']
 r=c.post('/futures/positions/'+pid+'/close',headers=h,json=close);assert r.status_code==200,r.text
 assert D(r.json()['round_trip_net'])>0
 assert c.post('/futures/positions/'+pid+'/close',headers=h,json=close).json()==r.json()
 assert c.get('/snapshot',headers=h).json()['positions']==[]

def test_stop_when_paused_and_account_math(world):
 db,u,c,h=world
 with db.sessions() as s:
  result=execute_paper(s,u,proposal());s.commit();s.get(User,u).mode='Emergency Stop'
  m=s.get(FuturesMarket,'BTC_USDT');m.ticker={**tick(),'bid1':'97.98','ask1':'97.99','lastPrice':'97.98','fairPrice':'97.98'};s.commit()
  manage(s,u);s.commit()
  assert not s.scalar(select(FuturesPaperPosition))
  snap=account(s,u)['portfolio'];assert D(snap['equity'])<3;assert D(snap['fees'])>0

def test_live_activation_requires_fresh_owner_connection(world):
 db,u,c,h=world
 body={'connection_id':'other-owner','confirmation':'I AUTHORIZE LIVE FUTURES','acknowledge_experimental':True,'derivatives_permitted':True}
 assert c.post('/futures/live/activate',headers=h,json=body).status_code==409
 assert c.post('/futures/live/orders',headers=h,json=proposal().model_dump(mode='json')).status_code==409
 assert c.put('/futures/settings',json={'workspace':'futures','limits':{}},headers={}).status_code==401

def test_signing_matches_exact_wire_and_no_retry():
 body={'vol':D('1.2300'),'symbol':'BTC_USDT'};encoded=decimal_json(body)
 assert json.loads(encoded)['vol']==1.23
 expected=hmac.new(b'secret',('key123'+encoded).encode(),hashlib.sha256).hexdigest()
 assert signature('key','secret',123,encoded)==expected
 attempts=[]
 async def handler(request):
  if request.url.path.endswith('/ping'):return httpx.Response(200,json={'success':True,'code':0,'data':int(time.time()*1000)})
  attempts.append(request)
  raise httpx.ReadTimeout('synthetic uncertain acknowledgment')
 async def run():
  a=MexcFutures('fixture-key','fixture-secret',httpx.MockTransport(handler))
  try:
   with pytest.raises(UnknownSubmission):await a.submit({'symbol':'BTC_USDT','vol':D('1')})
  finally:await a.close()
 asyncio.run(run());assert len(attempts)==1

def test_unknown_intent_not_resubmitted_and_partial_reconciled(world):
 db,u,c,h=world
 with db.sessions() as s:
  conn=Connection(user_id=u,exchange='mexc',ciphertext='test-not-used',capabilities={'product':'futures'});s.add(conn);s.flush()
  intent=FuturesIntent(user_id=u,connection_id=conn.id,client_id='unknown-future-0001',fingerprint='fixture',symbol='BTC_USDT',state='unknown',payload={'reduce_only':False},receipt={});s.add(intent);s.commit();iid=intent.id
 class Adapter:
  async def submit(self,payload):raise AssertionError('Unknown intents must not resubmit')
  async def order(self,symbol,client_id):return {'state':2,'vol':'10','dealVol':'4','takerFee':'.02','makerFee':'0','profit':'0'}
 asyncio.run(process(db,conn,Adapter(),iid));asyncio.run(reconcile(db,Adapter(),iid))
 with db.sessions() as s:assert s.get(FuturesIntent,iid).state=='partial'

def live_fixture(db,owner):
 with db.sessions() as s:
  user=s.get(User,owner);user.mode='Live';cfg=config(s,owner);cfg.activated=time.time()
  conn=Connection(user_id=owner,exchange='mexc',ciphertext='fixture-not-decrypted',capabilities={'product':'futures'});s.add(conn);s.flush();cfg.live_connection_id=conn.id
  s.add(FuturesAccount(connection_id=conn.id,user_id=owner,data={'asset':{'availableBalance':'3','equity':'3'},'positions':[],'position_mode':2,'high_water':'3','day_start_equity':'3'},received=time.time()))
  s.commit();return conn

def test_live_long_short_wire_protection_and_acknowledgment(world):
 db,u,c,h=world;conn=live_fixture(db,u)
 class Adapter:
  def __init__(self):self.writes=[]
  async def contracts(self,symbol):return [meta()]
  async def ticker(self,symbol):return tick()
  async def fees(self,symbol):return {'feeRateMode':'NORMAL','realTakerFee':'.0008','maxLeverage':500}
  async def risk_limits(self,symbol):return {symbol:[{'maxLeverage':500,'mmr':'.001','maxVol':'100000'}]}
  async def submit(self,payload):self.writes.append(payload);return {'orderId':'synthetic-order','ts':int(time.time()*1000)}
 for direction,side in [('LONG',1),('SHORT',3)]:
  adapter=Adapter();p=proposal(direction=direction,stop='98' if direction=='LONG' else '102',take_profit='104' if direction=='LONG' else '96',idempotency_key='live-'+direction.lower()+'-test-00001')
  with db.sessions() as s:i=enqueue(s,u,p,conn.id);s.commit();iid=i.id
  asyncio.run(process(db,conn,adapter,iid));asyncio.run(process(db,conn,adapter,iid))
  assert len(adapter.writes)==1;wire=adapter.writes[0]
  assert wire['side']==side and wire['positionMode']==2 and wire['openType']==1 and wire['price']>0
  assert wire['stopLossPrice']>0 and wire['takeProfitPrice']>0 and wire['externalOid']==p.idempotency_key
  with db.sessions() as s:
   assert s.get(FuturesIntent,iid).state=='acknowledged'
   # Mark terminal only in this synthetic fixture before testing the second plan.
   s.get(FuturesIntent,iid).state='filled';s.commit()

def test_live_close_is_reduce_only_even_after_pause(world):
 from backend.futures_live import enqueue_close
 db,u,c,h=world;conn=live_fixture(db,u)
 with db.sessions() as s:
  state=s.get(FuturesAccount,conn.id);state.data={**state.data,'positions':[{'positionId':123,'symbol':'BTC_USDT','positionType':2,'holdVol':'8','openType':1}]};s.get(User,u).mode='Paused';s.commit()
  intent=enqueue_close(s,u,'123',D('.5'),'reduce-live-test-0001');s.commit();iid=intent.id
 class Adapter:
  def __init__(self):self.wire=None
  async def contracts(self,symbol):return [meta()]
  async def ticker(self,symbol):return tick()
  async def submit(self,payload):self.wire=payload;return {'orderId':'synthetic-close','ts':int(time.time()*1000)}
 a=Adapter();asyncio.run(process(db,conn,a,iid))
 assert a.wire['reduceOnly'] is True and a.wire['side']==2 and a.wire['vol']==4

def test_cached_owner_cannot_bypass_pause(world):
 db,u,c,h=world
 with db.sessions() as stale:
  assert stale.get(User,u).mode=='Paper'
  with db.sessions() as fresh:fresh.get(User,u).mode='Paused';fresh.commit()
  with pytest.raises(Rejected,match='paused'):execute_paper(stale,u,proposal())


def test_public_contract_data_does_not_expose_accounts(world):
 db,u,c,h=world
 r=c.get('/futures/public-contracts');assert r.status_code==200
 assert len(r.json())==1 and r.json()[0]['source']=='mexc-futures'
 assert 'futures@test.invalid' not in r.text and 'password' not in r.text
 assert c.get('/futures/settings').status_code==401


def test_initial_margin_and_product_symbol_fail_closed():
 with pytest.raises(Rejected,match='initial margin'):make_plan(c=Contract.parse({**meta(),'initialMarginRate':'.3'}))
 with pytest.raises(Rejected,match='symbol'):make_plan(c=Contract.parse({**meta(),'symbol':'SOL_USDT'}))
 with pytest.raises(ValueError):Contract.parse({**meta(),'futureType':2})


def test_revoked_futures_connection_cannot_queue(world):
 db,u,c,h=world;conn=live_fixture(db,u)
 with db.sessions() as s:
  s.get(Connection,conn.id).capabilities={'product':'futures','revoked':True};s.commit()
  with pytest.raises(Rejected,match='connection'):enqueue(s,u,proposal(),conn.id)
