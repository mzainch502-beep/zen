import time
from types import SimpleNamespace
from decimal import Decimal
from sqlalchemy import select
from backend.shadow import settle,apply_recovery,advance,VERSION
from research.adaptive import outcomes
from exchange_adapters.universe import rotation
from test_futures import world,tick,meta
from test_adaptive import bars
from database.models import Record,User,FuturesMarket
from agents.futures_pipeline import process
from backend.futures_paper import config

def trial(**kw):return {'opened_at':60,'direction':'LONG','stop_fraction':.01,'cost_fraction':.002,**kw}
def test_shadow_forward_only_conservative_costs():
    assert settle(trial(),[[60000,100,200,1,101,1]],180) is None
    r=settle(trial(),[[120000,100,103,98,102,1]],180)
    assert abs(r['net_fraction']+.012)<1e-9 and r['cause']=='stop'
    assert settle(trial(),[[120000,100,103,100,102,1]],179) is None
    assert settle(trial(),[[180000,100,103,100,102,1]],240) is None
    short=settle(trial(direction='SHORT'),[[120000,100,100,97,98,1]],180)
    assert short['net_fraction']>0

def test_recovery_requires_forward_cost_positive_diverse_time_samples():
    actual=[{'position_id':str(i),'closed_at':i,'completed':True,'strategy':'momentum','regime':'trend','initial_risk':1,'net':-1} for i in range(5)]
    shadows=[dict(group='momentum:trend',opened_at=100+i*1800,closed_at=200+i*1800,state='closed',version=VERSION,net_fraction=.01 if i<5 else -.005) for i in range(8)]
    assert apply_recovery(outcomes(actual),actual,shadows[:7])['momentum:trend']['suspended']
    assert not apply_recovery(outcomes(actual),actual,shadows)['momentum:trend']['suspended']
    assert apply_recovery(outcomes(actual),actual,[dict(r,net_fraction=-.01) for r in shadows])['momentum:trend']['suspended']
    actual.append(dict(actual[-1],closed_at=999999))
    assert apply_recovery(outcomes(actual),actual,shadows)['momentum:trend']['suspended']

def test_shadow_idempotence_and_no_account_order(world):
    db,u,c,h=world
    decision={'bar_timestamp':0,'regime':'trend','stop_fraction':.01,'estimated_cost_bps':20,'opportunities':[{'strategy':'momentum','direction':'LONG','research_eligible':True}]}
    weights={'momentum:trend':{'suspended':True}}
    with db.sessions() as s:
        advance(s,u,'BTC_USDT',[],decision,weights,now=60);s.commit()
        advance(s,u,'BTC_USDT',[],decision,weights,now=61);s.commit()
        assert len(list(s.scalars(select(Record).where(Record.kind=='shadow_trial'))))==1
        advance(s,u,'BTC_USDT',[[120000,100,103,100,102,1]],decision,weights,now=180);s.commit()
        assert len(list(s.scalars(select(Record).where(Record.kind=='shadow_outcome'))))==1
        assert not s.scalar(select(Record).where(Record.kind=='futures_paper_fill'))
        advance(s,u,'BTC_USDT',[[120000,100,103,100,102,1]],decision,weights,now=181);s.commit()
        assert len(list(s.scalars(select(Record).where(Record.kind=='shadow_outcome'))))==1

def test_volatile_liquid_priority_with_full_rotation():
    markets=[SimpleNamespace(symbol=f'C{i}_USDT',contract=meta(),ticker={**tick(),'amount24':str(10000000-i),'high24Price':110 if i==29 else 101,'lower24Price':99},received=time.time()) for i in range(30)]
    selected,cursor=rotation(markets,0,12);assert 'C29_USDT' in selected
    seen=set(selected)
    for _ in range(12):
        selected,cursor=rotation(markets,cursor,12);seen.update(selected);assert len(selected)<=12
    assert len(seen)==30

def test_500_ceiling_uses_feasible_stop_leverage(world):
    db,u,c,h=world
    c.post('/agent/paper-profile',json={'profile':'aggressive'},headers=h)
    rows=bars();last=rows[-1][4]
    with db.sessions() as s:
        cfg=config(s,u);cfg.limits={**cfg.limits,'max_leverage':500}
        m=s.get(FuturesMarket,'BTC_USDT');m.ticker={**tick(),'bid1':str(last-.005),'ask1':str(last+.005),'lastPrice':str(last),'fairPrice':str(last)};s.commit()
        d=process(s,s.get(User,u),'BTC_USDT',rows);s.commit()
        assert d['execution']=='filled',d
        assert 1<=d['effective_leverage']<500


def test_candle_backoff_is_bounded_and_does_not_starve_other_markets():
    from exchange_adapters.universe import CandleBackoff
    b=CandleBackoff();b.failed('BAD_USDT',0)
    assert b.blocked(59)=={'BAD_USDT'} and not b.blocked(60)
    for _ in range(50):b.failed('BAD_USDT',100)
    assert b.until['BAD_USDT']==1000
    market=SimpleNamespace(symbol='GOOD_USDT',contract=meta(),ticker={**tick(),'amount24':'10000000'},received=time.time())
    selected,_=rotation([market],0,24,['BAD_USDT'],b.blocked(101))
    assert selected==['GOOD_USDT']
    b.succeeded('BAD_USDT');assert not b.failures and not b.until


def test_public_scanner_health_contains_no_owner_decisions(world):
    from database.models import record
    db,u,c,h=world
    with db.sessions() as s:
        record(s,None,'research_scan_heartbeat',{'batch':24,'candle_reads':23,'data_errors':1,'backoff':1});s.commit()
    health=c.get('/health').json()
    assert health['research_scanner_online']
    assert health['research_market_reads']=={'batch':24,'candle_reads':23,'data_errors':1,'backoff':1}
    assert 'decisions' not in health and 'positions' not in health
