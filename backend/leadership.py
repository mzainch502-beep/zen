"""Rolling deploys wait for the session-scoped advisory lock; never steal it."""
import asyncio,time
from sqlalchemy import text

async def acquire(connection,key,wait_seconds=120,pause_seconds=1):
    if connection.dialect.name!='postgresql':return
    deadline=time.monotonic()+wait_seconds
    while True:
        obtained=connection.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':key})
        # The session lock survives commit. Do not leave a long idle transaction.
        connection.commit()
        if obtained:return
        if time.monotonic()>=deadline:raise RuntimeError('Leadership unavailable after bounded handover wait')
        await asyncio.sleep(pause_seconds)
