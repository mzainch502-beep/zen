"""Experimental DB-API bridge for SQLite Durable Objects.

Every transaction is a real storage.transaction callback. In particular,
commit/rollback are never emulated as successful no-ops. Runtime verification
is required before using this bridge with any account data.
"""
import asyncio
import re

apilevel = '2.0'
threadsafety = 0
paramstyle = 'qmark'
sqlite_version_info = (3, 46, 0)
sqlite_version = '3.46.0'
PARSE_DECLTYPES = 1
PARSE_COLNAMES = 2

class Error(Exception): pass
class Warning(Exception): pass
class InterfaceError(Error): pass
class DatabaseError(Error): pass
class DataError(DatabaseError): pass
class OperationalError(DatabaseError): pass
class IntegrityError(DatabaseError): pass
class InternalError(DatabaseError): pass
class ProgrammingError(DatabaseError): pass
class NotSupportedError(DatabaseError): pass

class Connection:
    def __init__(self, storage):
        self.storage = storage
        self.transactions = []
        self.isolation_level = ''
        self.closed = False

    async def _begin(self, name=None):
        from pyodide.ffi import create_proxy
        ready = asyncio.Event()
        done = asyncio.get_running_loop().create_future()
        tx = {'name': name, 'done': done, 'rolled_back': False}
        async def callback(handle):
            tx['handle'] = handle
            ready.set()
            await done
        proxy = create_proxy(callback)
        tx['proxy'] = proxy
        tx['promise'] = self.storage.transaction(proxy)
        # A rejected transaction must not leave begin waiting forever.
        async def monitor():
            try:
                await tx['promise']
            finally:
                ready.set()
        tx['task'] = asyncio.create_task(monitor())
        await ready.wait()
        if 'handle' not in tx:
            await tx['task']
            raise OperationalError('Storage transaction did not start')
        self.transactions.append(tx)

    def begin(self, name=None):
        from pyodide.ffi import run_sync
        run_sync(self._begin(name))

    async def _finish(self, rollback=False):
        tx = self.transactions.pop()
        try:
            if rollback and not tx['rolled_back']:
                tx['handle'].rollback()
            tx['done'].set_result(None)
            await tx['task']
        finally:
            tx['proxy'].destroy()

    def finish(self, rollback=False):
        from pyodide.ffi import run_sync
        if self.transactions:
            run_sync(self._finish(rollback))

    def commit(self):
        while self.transactions:
            self.finish(False)

    def rollback(self):
        while self.transactions:
            self.finish(True)

    def cursor(self):
        if self.closed: raise ProgrammingError('Connection closed')
        return Cursor(self)

    def execute(self, statement, parameters=()):
        return self.cursor().execute(statement, parameters)

    def close(self):
        self.rollback()
        self.closed = True

    def create_function(self, *args, **kwargs):
        # SQLAlchemy registers regexp/floor on connect. Native SQLite floor is
        # available; unsupported regexp queries still fail at SQL execution.
        if args[0] not in ('regexp', 'floor'):
            raise NotSupportedError('Custom SQLite functions unavailable')

class Cursor:
    arraysize = 1
    lastrowid = None
    description = None
    rowcount = -1
    def __init__(self, connection):
        self.connection = connection
        self.rows = []
        self.offset = 0
    def execute(self, statement, parameters=()):
        sql = statement.strip()
        upper = sql.upper()
        conn = self.connection
        if upper.startswith('SAVEPOINT '):
            conn.begin(sql.split(None, 1)[1]); return self
        if upper.startswith('ROLLBACK TO SAVEPOINT '):
            name = sql.split(None, 3)[3]
            if not conn.transactions or conn.transactions[-1]['name'] != name:
                raise ProgrammingError('Savepoint mismatch')
            # SQLAlchemy issues RELEASE after ROLLBACK TO. Keep the name until
            # release while completing the real nested transaction rollback.
            conn.finish(True)
            conn.begin(name)
            return self
        if upper.startswith('RELEASE SAVEPOINT '):
            name = sql.split(None, 2)[2]
            if not conn.transactions or conn.transactions[-1]['name'] != name:
                raise ProgrammingError('Savepoint mismatch')
            conn.finish(); return self
        if not conn.transactions:
            conn.begin()
        try:
            result = conn.storage.sql.exec(sql, *parameters)
            names = list(result.columnNames)
            self.description = [(x, None, None, None, None, None, None) for x in names]
            self.rows = [tuple(row) for row in result.raw().toArray()]
            self.rowcount = int(conn.storage.sql.exec('SELECT changes() AS affected').one().affected) if upper.startswith(('INSERT', 'UPDATE', 'DELETE')) else -1
            self.offset = 0
            return self
        except Exception as error:
            msg = str(error)
            if 'constraint' in msg.lower(): raise IntegrityError(msg) from error
            raise OperationalError(msg) from error
    def executemany(self, statement, parameters):
        count = 0
        for row in parameters:
            self.execute(statement, row); count += self.rowcount
        self.rowcount = count
        return self
    def fetchone(self):
        if self.offset >= len(self.rows): return None
        row = self.rows[self.offset]; self.offset += 1
        return row
    def fetchmany(self, size=None):
        size = size or self.arraysize
        rows = self.rows[self.offset:self.offset+size]; self.offset += len(rows)
        return rows
    def fetchall(self):
        rows = self.rows[self.offset:]; self.offset = len(self.rows)
        return rows
    def close(self): pass
    def __iter__(self): return iter(self.fetchall())
