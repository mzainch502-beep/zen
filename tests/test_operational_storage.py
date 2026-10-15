from sqlalchemy import select,func
from database.models import Database,Record,record

def test_heartbeats_bounded_but_financial_history_preserved(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'state.db'));db.create_dev()
    with db.sessions() as s:
        for n in range(100):
            record(s,None,'worker_heartbeat',{'cycle':n})
            record(s,None,'futures_paper_fill',{'sequence':n})
        s.commit()
        assert s.scalar(select(func.count()).select_from(Record).where(Record.kind=='worker_heartbeat'))==1
        assert s.scalar(select(Record).where(Record.kind=='worker_heartbeat')).payload['cycle']==99
        assert s.scalar(select(func.count()).select_from(Record).where(Record.kind=='futures_paper_fill'))==100

def test_status_update_rolls_back_with_transaction(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'state.db'));db.create_dev()
    with db.sessions() as s:
        record(s,None,'research_scan_heartbeat',{'batch':24});s.commit()
        record(s,None,'research_scan_heartbeat',{'batch':0});s.rollback()
        assert s.scalar(select(Record).where(Record.kind=='research_scan_heartbeat')).payload['batch']==24

def test_database_outage_retry_is_bounded_and_cancellation_propagates():
    import asyncio
    from sqlalchemy.exc import OperationalError
    from backend.supervisor import supervise
    waits=[]
    async def failing():raise OperationalError('secret-query',{},Exception('secret'))
    async def pause(delay):
        waits.append(delay)
        if len(waits)==7:raise asyncio.CancelledError()
    import pytest
    with pytest.raises(asyncio.CancelledError):asyncio.run(supervise(failing,sleep=pause))
    assert waits==[5,10,20,40,60,60,60]
