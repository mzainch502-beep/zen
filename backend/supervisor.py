"""Bounded restart frequency after database outages; never replay orders here."""
import asyncio
import logging
import time
from sqlalchemy.exc import OperationalError, InterfaceError

async def supervise(run, *, sleep=asyncio.sleep, clock=time.monotonic):
    delay=5
    while True:
        started=clock()
        try:
            await run()
            return
        except (OperationalError, InterfaceError) as exc:
            # SQL exception strings can contain account values. Log only the type.
            logging.error('database_unavailable component=%s retry_seconds=%s',type(exc).__name__,delay)
            if clock()-started>300:delay=5
            await sleep(delay)
            delay=min(delay*2,60)
