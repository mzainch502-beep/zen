import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.api import create_app
from backend.domain import Limits
from backend.security import password_hash, create_session
from backend.futures_paper import config
from database.models import Database, User, Record

@pytest.fixture
def world(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'automation.db'));db.create_dev()
    with db.sessions() as s:
        u=User(mode='Paper',email='automation@example.invalid',password=password_hash('test-password-long'),limits=Limits().model_dump(mode='json'))
        s.add(u);s.flush();uid=u.id;token=create_session(s,u);s.commit()
    c=TestClient(create_app(db));c.headers['Authorization']='Bearer '+token
    return db,c,uid

def test_default_off_persistent_disable_idempotent(world):
    db,c,uid=world
    assert c.get('/snapshot').json()['automation']['enabled'] is False
    assert c.put('/agent/automation',json={'enabled':True}).json()['enabled'] is True
    with db.sessions() as s:assert Limits.model_validate(s.get(User,uid).limits).automatic
    assert c.put('/agent/automation',json={'enabled':False}).json()['enabled'] is False
    assert c.put('/agent/automation',json={'enabled':False}).status_code==200
    with db.sessions() as s:assert len(list(s.scalars(select(Record).where(Record.kind=='automation_changed'))))==2

@pytest.mark.parametrize('mode',['Paused','Emergency Stop','Live'])
def test_cannot_enable_blocked_workspace_but_can_disable(world,mode):
    db,c,uid=world
    with db.sessions() as s:s.get(User,uid).mode=mode;s.commit()
    assert c.put('/agent/automation',json={'enabled':True}).status_code==409
    assert c.put('/agent/automation',json={'enabled':False}).status_code==200

def test_workspace_switch_disarms_and_active_futures_only(world):
    db,c,uid=world
    c.put('/agent/automation',json={'enabled':True})
    limits=c.get('/futures/settings').json()['limits'];limits['automatic']=True
    assert c.put('/futures/settings',json={'workspace':'futures','limits':limits}).status_code==200
    assert c.get('/agent/automation').json()['enabled'] is False
    assert c.put('/agent/automation',json={'enabled':True}).json()['product']=='futures'
    with db.sessions() as s:
        assert not Limits.model_validate(s.get(User,uid).limits).automatic
        assert config(s,uid).limits['automatic']

def test_session_and_body_validation(world):
    db,c,uid=world
    assert c.put('/agent/automation',json={'enabled':True,'extra':'invalid'}).status_code==422
    c.headers.clear()
    assert c.put('/agent/automation',json={'enabled':True}).status_code==401


def test_settings_cannot_secretly_arm_automation(world):
    db,c,uid=world
    limits=c.get('/snapshot').json()['limits'];limits['automatic']=True
    assert c.put('/risk',json=limits).status_code==200
    assert not c.get('/agent/automation').json()['requested']
    limits=c.get('/futures/settings').json()['limits'];limits['automatic']=True
    assert c.put('/futures/settings',json={'workspace':'spot','limits':limits}).status_code==200
    with db.sessions() as s:assert not config(s,uid).limits['automatic']
