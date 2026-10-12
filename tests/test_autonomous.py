"""Synthetic fixtures verify control flow; never presented as trading performance."""
import time
from decimal import Decimal as D
import pytest
from sqlalchemy import select, func
from agents.autonomous import assess, process_observation, manage_exits, MAX_HOLD_SECONDS
from backend.domain import Quote, Limits
from backend.security import password_hash
from database.models import Database, User, Market, Order, Record, Position

@pytest.fixture
def world(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'auto.db'));db.create_dev()
    now=time.time()
    rows=[]
    for i in range(100):
        price=100+i*.1
        rows.append([(int(now//60)-100+i)*60000,price-.01,price+.02,price-.02,price,20])
    q=Quote(symbol='BTC/USDT',bid=D('109.89'),ask=D('109.9'),last=D('109.9'),timestamp=time.time(),source='synthetic-test')
    with db.sessions() as s:
        u=User(email='test@auto.invalid',password=password_hash('test-password-long'),mode='Paper',limits=Limits().model_dump(mode='json'))
        s.add(u);s.add(Market(symbol=q.symbol,payload=q.model_dump(mode='json'),received=time.time()));s.commit()
        owner=u.id
    return db,owner,rows,now,q

def test_assessment_and_invalid_data(world):
    db,owner,rows,now,q=world
    d=assess(rows,q,now);assert d['action']=='LONG';assert d['confidence'] is None;assert d['research_trial']
    assert assess(rows[:10],q,now)['action']=='WAIT'
    assert assess(list(reversed(rows)),q,now)['action']=='WAIT'
    assert assess(rows,q,now+200)['action']=='WAIT'
    assert assess(rows[:-5]+rows[-4:],q,now)['action']=='WAIT'
    assert assess(rows,q,now-90)['action']=='WAIT'

def test_full_loop_and_restart_duplicate(world):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        process_observation(s,owner,q.symbol,rows,now);s.commit()
    with db.sessions() as s:
        assert process_observation(s,owner,q.symbol,rows,now) is None;s.commit()
        assert s.scalar(select(func.count()).select_from(Order))==1
        p=s.scalar(select(Position));assert p.stop and p.take_profit
        q=q.model_copy(update={'bid':p.take_profit+D('.01'),'ask':p.take_profit+D('.02'),'last':p.take_profit})
        s.get(Market,q.symbol).payload=q.model_dump(mode='json');s.commit()
    with db.sessions() as s:
        results=manage_exits(s,owner);s.commit()
        assert results[0]['cause']=='take_profit';assert D(results[0]['net_pnl'])>0
        assert s.scalar(select(func.count()).select_from(Position))==0
        assert s.scalar(select(func.count()).select_from(Order))==2
        assert manage_exits(s,owner)==[]
        assert s.scalar(select(func.count()).select_from(Record).where(Record.kind=='trade_evaluation'))==1

@pytest.mark.parametrize('mode',['Paused','Emergency Stop'])
def test_scans_continue_but_entries_vetoed(world,mode):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        s.get(User,owner).mode=mode
        assert process_observation(s,owner,q.symbol,rows,now)['action']=='LONG';s.commit()
        assert s.scalar(select(func.count()).select_from(Order))==0
        assert s.scalar(select(Record).where(Record.kind=='risk_veto')) is not None

def test_time_exit_still_works_when_emergency_stopped(world):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        process_observation(s,owner,q.symbol,rows,now);s.commit()
        s.scalar(select(Order)).created=time.time()-MAX_HOLD_SECONDS-1
        s.get(User,owner).mode='Emergency Stop';s.commit()
        result=manage_exits(s,owner);s.commit()
        assert result[0]['cause']=='maximum_hold';assert D(result[0]['net_pnl'])<0

def test_target_does_not_affect_size_or_signal(world):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        process_observation(s,owner,q.symbol,rows,now);s.commit()
        order=s.scalar(select(Order));assert order.quantity*order.price<=D('10.000001')
        assert 'target' not in assess(rows,q,now)

def test_stale_exit_does_not_fabricate_fill(world):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        process_observation(s,owner,q.symbol,rows,now);s.commit()
        old=q.model_copy(update={'timestamp':time.time()-100,'bid':D('1')})
        s.get(Market,q.symbol).payload=old.model_dump(mode='json');s.commit()
        assert manage_exits(s,owner)==[]
        assert s.scalar(select(func.count()).select_from(Order))==1

def test_historical_replay_chronology_and_costs(world):
    from research.trial import replay
    db,owner,rows,now,q=world
    free=replay(rows,0,0,0);costed=replay(rows,10,10,2)
    assert free['closed_trades']>0
    assert costed['net_pnl']<free['net_pnl']
    assert costed['promoted'] is False
    with pytest.raises(ValueError):replay(list(reversed(rows)))
    with pytest.raises(ValueError):replay(rows[:-5]+rows[-4:])

def test_bearish_observation_does_not_send_spot_short(world):
    db,owner,rows,now,q=world
    down=[]
    for i,row in enumerate(rows):
        price=110-i*.1
        down.append([row[0],price+.01,price+.02,price-.02,price,20])
    d=assess(down,q,now)
    assert d['hypothesis']=='SHORT';assert d['action']=='WAIT'
    with db.sessions() as s:
        process_observation(s,owner,q.symbol,down,now);s.commit()
        assert s.scalar(select(func.count()).select_from(Order))==0

def test_autonomous_drawdown_veto_persists_audit(world):
    db,owner,rows,now,q=world
    with db.sessions() as s:
        s.get(User,owner).high_water=D('230')
        process_observation(s,owner,q.symbol,rows,now);s.commit()
        assert s.scalar(select(func.count()).select_from(Order))==0
        veto=s.scalar(select(Record).where(Record.kind=='risk_veto'))
        assert 'Drawdown' in veto.payload['reason']
        assert s.scalar(select(Record).where(Record.kind=='decision')) is not None
