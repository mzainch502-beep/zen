import os
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from database.models import Database, Base, User, Market, Order
from backend.domain import Limits
from backend.security import password_hash
from backend.service import execute
from test_core import q,p
@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'),reason='PostgreSQL service not configured')
def test_concurrent_duplicate_execution():
    db=Database(os.environ['TEST_POSTGRES_URL']);db.create_dev()
    with db.sessions() as s:
        u=User(email='concurrency@test.invalid',password=password_hash('long-test-password'),mode='Paper',limits=Limits().model_dump(mode='json'))
        s.add(u);s.merge(Market(symbol='BTC/USDT',payload=q().model_dump(mode='json'),received=q().timestamp));s.commit();owner=u.id
    def place():
        with db.sessions() as s:
            order=execute(s,owner,p());s.commit();return order.id
    with ThreadPoolExecutor(max_workers=4) as pool: ids=list(pool.map(lambda _:place(),range(4)))
    assert len(set(ids))==1
    with db.sessions() as s: assert len(list(s.scalars(select(Order).where(Order.user_id==owner))))==1

@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'),reason='PostgreSQL service not configured')
def test_concurrent_autonomous_bar_once():
    import time
    from sqlalchemy import func
    from agents.autonomous import process_observation
    from database.models import Record
    db=Database(os.environ['TEST_POSTGRES_URL']);db.create_dev()
    now=time.time()
    rows=[]
    for i in range(100):
        price=100+i*.1
        rows.append([(int(now//60)-100+i)*60000,price-.01,price+.02,price-.02,price,20])
    with db.sessions() as s:
        u=User(email='auto-concurrency@test.invalid',password=password_hash('long-test-password'),mode='Paper',limits=Limits(automatic=True).model_dump(mode='json'))
        s.add(u);s.merge(Market(symbol='BTC/USDT',payload=q(bid=Decimal('109.89'),ask=Decimal('109.9'),last=Decimal('109.9')).model_dump(mode='json'),received=now));s.commit();owner=u.id
    def scan():
        with db.sessions() as s:
            d=process_observation(s,owner,'BTC/USDT',rows);s.commit();return d
    with ThreadPoolExecutor(max_workers=4) as pool: decisions=list(pool.map(lambda _:scan(),range(4)))
    assert sum(d is not None for d in decisions)==1
    with db.sessions() as s:
        assert s.scalar(select(func.count()).select_from(Order).where(Order.user_id==owner))==1
        assert s.scalar(select(func.count()).select_from(Record).where(Record.user_id==owner,Record.kind=='decision'))==1

@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'),reason='PostgreSQL service not configured')
def test_concurrent_futures_paper_client_id_once():
    import time
    from test_futures import meta,tick,proposal
    from backend.futures_paper import config,book,execute_paper
    from backend.futures_domain import FuturesLimits
    from database.models import FuturesMarket,FuturesPaperPosition,Record
    from sqlalchemy import func
    db=Database(os.environ['TEST_POSTGRES_URL']);db.create_dev()
    with db.sessions() as s:
        u=User(email='futures-concurrency@test.invalid',password=password_hash('long-test-password'),mode='Paper',limits=Limits().model_dump(mode='json'))
        s.add(u);s.flush();cfg=config(s,u.id);cfg.workspace='futures';cfg.limits=FuturesLimits(max_leverage=10).model_dump(mode='json')
        b=book(s,u.id);b.cash=b.high_water=b.initial_equity=Decimal('3')
        s.merge(FuturesMarket(symbol='BTC_USDT',contract=meta(),ticker=tick(),received=time.time()));s.commit();owner=u.id
    def place():
        with db.sessions() as s:r=execute_paper(s,owner,proposal());s.commit();return r['position_id']
    with ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(lambda _:place(),range(4)))
    assert len(set(ids))==1
    with db.sessions() as s:
        assert s.scalar(select(func.count()).select_from(FuturesPaperPosition).where(FuturesPaperPosition.user_id==owner))==1
        assert s.scalar(select(func.count()).select_from(Record).where(Record.user_id==owner,Record.kind=='futures_paper_fill'))==1
