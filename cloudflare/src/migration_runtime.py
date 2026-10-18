"""Authenticated, resumable import into a new, inactive Cloudflare database."""
import hashlib, json, secrets, time
from decimal import Decimal
from sqlalchemy import select, func
from workers import Response
from database.models import Base, User

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

class Migration:
    def __init__(self, database, storage, env):
        self.database, self.storage, self.env = database, storage, env
        self.tables = {t.name:t for t in Base.metadata.sorted_tables if t not in database.cache_tables}
    async def handle(self, request, path):
        key = getattr(self.env, 'MIGRATION_TOKEN', '')
        authorization = request.headers.get('authorization') or ''
        if len(key)<32 or not secrets.compare_digest(authorization, 'Bearer '+key):
            return Response.json({'detail':'Unauthorized'},status=401)
        if request.method != 'POST': return Response.json({'detail':'POST required'},status=405)
        raw = await request.bytes()
        if len(raw)>500000: return Response.json({'detail':'Migration batch too large'},status=413)
        body=json.loads(raw)
        state=await self.storage.get('migration_state')
        if path=='/migration/begin':
            if state:
                if state['id']!=body['id']: return Response.json({'detail':'Different migration already exists'},status=409)
                return Response.json(state)
            with self.database.sessions() as s:
                if s.scalar(select(func.count()).select_from(User)):
                    return Response.json({'detail':'Target account database is not empty'},status=409)
            if set(body['tables']) != set(self.tables):
                return Response.json({'detail':'Schema table mismatch'},status=409)
            state={'id':body['id'],'next_batch':0,'chain':'0'*64,'tables':body['tables'],'complete':False,'created':time.time()}
            await self.storage.put('migration_state',state)
            return Response.json(state)
        if not state or body.get('id')!=state['id']:
            return Response.json({'detail':'Migration not initialized'},status=409)
        if path=='/migration/chunk':
            index=body['batch']; digest=hashlib.sha256(canonical(body['rows'])).hexdigest()
            prior=await self.storage.get('migration_batch:'+str(index))
            if prior:
                if prior!=digest: return Response.json({'detail':'Batch content conflict'},status=409)
                return Response.json({'accepted':True,'replayed':True})
            if state['complete'] or index!=state['next_batch'] or body['table'] not in self.tables:
                return Response.json({'detail':'Unexpected migration batch'},status=409)
            table=self.tables[body['table']]
            rows=body['rows']
            if len(rows)>1000: return Response.json({'detail':'Too many rows'},status=413)
            # Data insert and replay marker share one real storage transaction.
            async def commit_batch(txn):
                with self.database.engine.begin() as conn:
                    if rows: conn.execute(table.insert(), rows)
                await self.storage.put('migration_batch:'+str(index),digest)
                state['chain']=hashlib.sha256((state['chain']+body['table']+digest).encode()).hexdigest()
                state['next_batch']+=1
                await self.storage.put('migration_state',state)
            await self.storage.transaction(commit_batch)
            return Response.json({'accepted':True,'next_batch':state['next_batch'],'chain':state['chain']})
        if path=='/migration/finish':
            counts={}
            with self.database.engine.connect() as conn:
                for name,table in self.tables.items(): counts[name]=conn.scalar(select(func.count()).select_from(table))
            if counts!=state['tables'] or body['chain']!=state['chain']:
                return Response.json({'detail':'Migration verification mismatch','counts':counts},status=409)
            state['complete']=True
            await self.storage.put('migration_state',state)
            return Response.json({'verified':True,'counts':counts,'chain':state['chain'],'active':False})
        if path=='/migration/activate':
            if not state['complete'] or body.get('source_execution_stopped') is not True:
                return Response.json({'detail':'Verified import and stopped source execution required'},status=409)
            # Source must be stopped before this administrative cutover command.
            await self.storage.put('active',True)
            await self.storage.setAlarm(int(time.time()*1000)+1000)
            return Response.json({'activated':True})
        return Response.json({'detail':'Unknown migration operation'},status=404)
