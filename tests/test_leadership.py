import asyncio
from types import SimpleNamespace
import pytest
from backend.leadership import acquire

class Lock:
    dialect=SimpleNamespace(name='postgresql')
    def __init__(self,sequence):self.sequence=iter(sequence);self.commits=0
    def scalar(self,statement,params):return next(self.sequence,False)
    def commit(self):self.commits+=1

def test_rolling_handover_waits_without_claiming_two_leaders():
    connection=Lock([False,False,True])
    asyncio.run(acquire(connection,937414,wait_seconds=1,pause_seconds=0))
    assert connection.commits==3

def test_handover_wait_is_bounded():
    connection=Lock([])
    with pytest.raises(RuntimeError,match='bounded'):asyncio.run(acquire(connection,937414,wait_seconds=0,pause_seconds=0))
    assert connection.commits==1
