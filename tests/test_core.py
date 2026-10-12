import time, base64, os, asyncio
from decimal import Decimal as D
from dataclasses import asdict
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.domain import Quote, Limits, Proposal, Rule
from risk.governor import evaluate, liquidation_distance
from backend.security import Vault, password_hash, authenticate
from database.models import Database, User, Market, Order, Record
from backend.api import create_app
from backend.service import execute, portfolio, Rejected
from exchange_adapters.state import OrderTracker, State
from exchange_adapters.ccxt_adapter import ReadAdapter, EXCHANGES, bounded_read
from research.evaluation import evaluate as backtest, walk_forward, promotion_gate
from agents.pipeline import DecisionAgent, Observation

def q(**kw):
    return Quote(**{'symbol':'BTC/USDT','bid':D('100'),'ask':D('100.01'),'last':D('100'),'timestamp':time.time(),'source':'test-fixture',**kw})
def p(**kw):
    return Proposal(**{'symbol':'BTC/USDT','side':'buy','quantity':D('.1'),'stop':D('98'),'idempotency_key':'test-000000000001',**kw})
def verdict(proposal=None,quote=None,**kw):
    args=dict(mode='Paper',cash=D('200'),equity=D('200'),high_water=D('200'),daily_net=D(0),exposure=D(0),positions=0,existing_quantity=D(0),orders_last_minute=0)
    args.update(kw)
    return evaluate(proposal or p(),quote or q(),Limits(),**args)
@pytest.mark.parametrize('kwargs,reason',[({'mode':'Paused'},'paused'),({'daily_net':D('-6')},'Daily'),({'exposure':D('40')},'Exposure'),({'cash':D('1')},'cash'),({'orders_last_minute':6},'rate'),({'high_water':D('230')},'Drawdown'),({'cooldown_until':time.time()+999},'cooldown')])
def test_risk_veto(kwargs,reason):
    v=verdict(**kwargs);assert not v.approved;assert any(reason in r for r in v.reasons)
def test_fresh_paper_approved(): assert verdict().approved
def test_stale_quote_veto(): assert not verdict(quote=q(timestamp=time.time()-30)).approved
def test_future_quote_veto(): assert not verdict(quote=q(timestamp=time.time()+30)).approved
def test_short_disabled(): assert not verdict(proposal=p(side='sell')).approved
def test_reduction_allowed_after_stop(): assert verdict(proposal=p(side='sell',reduce_only=True),mode='Emergency Stop',cash=D(0),daily_net=D('-99'),existing_quantity=D('.1')).approved
def test_over_reduction_blocked(): assert not verdict(proposal=p(side='sell',reduce_only=True),existing_quantity=D('.01')).approved
def test_loss_budget(): assert not verdict(proposal=p(quantity=D('1'),stop=D('1'))).approved
def test_precision():
    rule=Rule(step=D('.001'),min_qty=D('.001'),min_notional=D('5'))
    assert rule.quantity(D('.123456'),D('100'))==D('.123')
    with pytest.raises(ValueError):rule.quantity(D('.0001'),D('100'))
def test_liquidation():
    assert liquidation_distance(D('100'),D('80'))==D('.2')
    assert liquidation_distance(D('100'),None) is None
@pytest.mark.parametrize('exchange',list(EXCHANGES))
def test_adapter_constructs(exchange):
    a=ReadAdapter(exchange);assert a.client.id;asyncio.run(a.close())
def test_partial_unknown():
    t=OrderTracker(D('1'));assert t.update(D('.3'),'open')==State.PARTIAL
    assert t.update(D('.3'),'unknown')==State.UNKNOWN;assert not t.can_resubmit
    assert t.update(D('1'),'closed')==State.FILLED
    with pytest.raises(ValueError):t.update(D('.5'),'open')
def test_bounded_read():
    import ccxt
    count=0
    async def f():
        nonlocal count;count+=1
        if count<2:raise ccxt.NetworkError('fixture')
        return 7
    assert asyncio.run(bounded_read(f,attempts=2))==7;assert count==2
@pytest.fixture
def setup(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'test.db'));db.create_dev()
    with db.sessions() as s:
        u=User(email='owner@test.invalid',password=password_hash('long-test-password'),mode='Paper',limits=Limits().model_dump(mode='json'))
        s.add(u);s.add(Market(symbol='BTC/USDT',payload=q().model_dump(mode='json'),received=time.time()));s.commit();owner=u.id
    c=TestClient(create_app(db));r=c.post('/auth/login',json={'email':'owner@test.invalid','password':'long-test-password'});assert r.status_code==200
    h={'Authorization':'Bearer '+r.json()['token']}
    return db,owner,c,h

def test_api_auth_and_revoke(setup):
    db,u,c,h=setup
    assert c.get('/snapshot').status_code==401
    assert c.get('/snapshot',headers=h).status_code==200
    assert c.post('/auth/logout',headers=h).status_code==200
    assert c.get('/snapshot',headers=h).status_code==401

def test_live_never_enabled(setup):
    db,u,c,h=setup
    assert c.post('/live/activate',headers=h).status_code==409
    assert c.post('/agent/mode',headers=h,json={'mode':'Live'}).status_code==422
    assert c.put('/risk',headers=h,json={'max_leverage':'500'}).status_code==422

def test_paper_execution_idempotent_and_fees(setup):
    db,u,c,h=setup
    r=c.post('/paper/orders',headers=h,json=p().model_dump(mode='json'));assert r.status_code==200
    repeat=c.post('/paper/orders',headers=h,json=p().model_dump(mode='json'));assert repeat.json()['id']==r.json()['id']
    with db.sessions() as s:
        orders=list(s.scalars(select(Order)));assert len(orders)==1
        user=s.get(User,u);assert user.cash==D('200')-orders[0].price*D('.1')-orders[0].fee
    changed=p(quantity=D('.2'));assert c.post('/paper/orders',headers=h,json=changed.model_dump(mode='json')).status_code==409
    close=p(side='sell',reduce_only=True,idempotency_key='close-00000000001')
    assert c.post('/paper/orders',headers=h,json=close.model_dump(mode='json')).status_code==200
    snap=c.get('/snapshot',headers=h).json();assert snap['positions']==[]
    assert D(snap['portfolio']['net_pnl'])<0

def test_stop_and_reduction(setup):
    db,u,c,h=setup
    c.post('/agent/mode',headers=h,json={'mode':'Emergency Stop'})
    assert c.post('/paper/orders',headers=h,json=p().model_dump(mode='json')).status_code==409

def test_other_owner_cannot_edit_position(setup):
    db,u,c,h=setup
    c.post('/paper/orders',headers=h,json=p().model_dump(mode='json'))
    pos=c.get('/snapshot',headers=h).json()['positions'][0]['id']
    with db.sessions() as s:
        s.add(User(email='other@test.invalid',password=password_hash('another-long-password')));s.commit()
    token=c.post('/auth/login',json={'email':'other@test.invalid','password':'another-long-password'}).json()['token']
    assert c.put(f'/positions/{pos}/exits',headers={'Authorization':'Bearer '+token},json={'stop':'97'}).status_code==404

def test_validation_never_reflects_secret(setup):
    db,u,c,h=setup
    r=c.post('/connections',headers=h,json={'api_key':'DO-NOT-REFLECT-SECRET','bad':True})
    assert r.status_code==422;assert 'DO-NOT-REFLECT' not in r.text

def test_vault_aad_tamper():
    key=base64.b64encode(os.urandom(32)).decode();v=Vault(key);enc=v.encrypt('owner','bybit',{'secret':'fixture'})
    assert 'fixture' not in enc;assert v.decrypt('owner','bybit',enc)['secret']=='fixture'
    with pytest.raises(Exception):v.decrypt('other','bybit',enc)
    with pytest.raises(Exception):v.decrypt('owner','okx',enc)

def candles(n=400):
    return [[i*60000,100+i*.01,101+i*.01,99+i*.01,100.5+i*.01,1000] for i in range(n)]
def test_research_cost_and_leakage():
    rows=candles();a=backtest(rows,0,0);b=backtest(rows,10,10)
    assert b.net_return<a.net_return;assert b.status=='research_only'
    folds=walk_forward(rows);assert len(folds)==3
    assert not promotion_gate(folds,0,False)
    with pytest.raises(ValueError):backtest(list(reversed(rows)))
    with pytest.raises(ValueError):backtest(rows[:10])
def test_decision_wait_without_validation():
    d=DecisionAgent().decide(Observation('BTC/USDT',tuple(range(100,150)),1.),[])
    assert d['action']=='WAIT';assert d['confidence'] is None

def test_api_contract(setup):
    db,u,c,h=setup
    schema=c.get('/openapi.json').json()
    assert '/paper/orders' in schema['paths'];assert '/connections' in schema['paths']
    assert c.get('/health').json()['live_execution'] is False

def test_paper_minimum(): assert not verdict(proposal=p(quantity=D('.001'))).approved

def test_owner_setup_one_time(tmp_path,monkeypatch):
    db=Database('sqlite:///'+str(tmp_path/'setup.db'));db.create_dev()
    monkeypatch.setenv('BOOTSTRAP_TOKEN','fixture-setup-token-at-least32')
    c=TestClient(create_app(db))
    body={'email':'new@test.invalid','password':'new-long-test-password','setup_token':'fixture-setup-token-at-least32'}
    assert c.post('/auth/setup',json={**body,'setup_token':'incorrect-token-at-least16'}).status_code==403
    assert c.post('/auth/setup',json=body).status_code==200
    assert c.post('/auth/setup',json=body).status_code==409
    logged=c.post('/auth/login',json={'email':body['email'],'password':body['password']});assert logged.status_code==200
    state=c.get('/snapshot',headers={'Authorization':'Bearer '+logged.json()['token']}).json()
    assert state['portfolio']['mode']=='Paper'

def test_auth_rate_limit(setup):
    db,u,c,h=setup
    for _ in range(20): c.post('/auth/login',json={'email':'bad','password':'bad'})
    assert c.post('/auth/login',json={'email':'bad','password':'bad'}).status_code==429

def test_snapshot_readable_account_and_agent(setup):
    db,u,c,h=setup
    result=c.get('/snapshot',headers=h).json()
    assert result['account']['email']=='owner@test.invalid'
    assert result['agent']['action']=='WAIT'
    assert result['agent']['version']=='research-v1'

def test_depth_authenticated_and_market_allowlist(setup):
    db,u,c,h=setup
    assert c.get('/market-depth').status_code==401
    assert c.get('/market-depth?symbol=BAD',headers=h).status_code==422

def test_bootstrap_status_is_disabled_after_owner(setup):
    db,u,c,h=setup
    assert c.get('/bootstrap/status').json()['setup_available'] is False

def test_maintenance_refuses_real_account():
    from backend.maintenance import purge_deployment_fixture
    with pytest.raises(ValueError):purge_deployment_fixture('owner@real.example')
