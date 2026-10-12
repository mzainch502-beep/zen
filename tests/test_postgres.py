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
