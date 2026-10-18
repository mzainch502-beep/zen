"""Run inside the source backend after stopping mutations/execution.

Streams a consistent PostgreSQL snapshot to the inactive Cloudflare importer.
No credentials, session tokens, row payloads or URLs are written to logs.
Use environment variables for the HTTPS destination and one-use import token.
The source database is never deleted or modified by this command.
"""
import hashlib, json, os, time, uuid
from decimal import Decimal
from urllib.parse import urlparse
import httpx
from sqlalchemy import create_engine, select, func
from database.models import Base, Market, FuturesMarket, Connection, FuturesConfig, FuturesIntent, User
from backend.security import Vault

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def serializable(row):
    return {k:format(v,'f') if isinstance(v,Decimal) else v for k,v in row.items()}

def run():
    url=os.environ['DATABASE_URL'].replace('postgres://','postgresql+psycopg://',1)
    if url.startswith('postgresql://'):url=url.replace('postgresql://','postgresql+psycopg://',1)
    endpoint=os.environ['ZEN_MIGRATION_ENDPOINT'].rstrip('/')
    if urlparse(endpoint).scheme!='https':raise ValueError('Migration requires HTTPS')
    token=os.environ['ZEN_MIGRATION_TOKEN']
    if len(token)<32:raise ValueError('Migration token too short')
    migration_id=os.environ['ZEN_MIGRATION_ID']
    source=Vault()
    destination=Vault(os.environ['ZEN_TARGET_VAULT_KEY'])
    engine=create_engine(url,pool_pre_ping=True)
    tables=[t for t in Base.metadata.sorted_tables if t not in (Market.__table__,FuturesMarket.__table__)]
    with httpx.Client(timeout=60,follow_redirects=False,headers={'Authorization':'Bearer '+token}) as client:
        def send(path,body):
            # Only import requests are retried. The receiver authenticates and
            # identifies every batch; this never retries an exchange order.
            for attempt in range(4):
                try:
                    response=client.post(endpoint+path,json=body)
                    if response.status_code>=500:raise RuntimeError('Migration service unavailable')
                    if response.status_code!=200:raise ValueError('Migration rejected; status '+str(response.status_code))
                    return response.json()
                except (httpx.TransportError,RuntimeError):
                    if attempt==3:raise
                    time.sleep(2**attempt)
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            with conn.begin():
                if conn.scalar(select(func.count()).select_from(FuturesConfig).where(FuturesConfig.activated.is_not(None))):
                    raise ValueError('Reconcile and deactivate live execution before migration')
                unresolved=('pending','submitting','unknown','acknowledged','partial','open')
                if conn.scalar(select(func.count()).select_from(FuturesIntent).where(FuturesIntent.state.in_(unresolved))):
                    raise ValueError('Unresolved live order intents block migration')
                counts={t.name:conn.scalar(select(func.count()).select_from(t)) for t in tables}
                start=send('/migration/begin',{'id':migration_id,'tables':counts})
                batch=0;chain='0'*64
                def write(table,rows):
                    nonlocal batch,chain
                    digest=hashlib.sha256(canonical(rows)).hexdigest()
                    send('/migration/chunk',{'id':migration_id,'batch':batch,'table':table,'rows':rows})
                    chain=hashlib.sha256((chain+table+digest).encode()).hexdigest()
                    batch+=1
                for table in tables:
                    rows=[];size=0
                    result=conn.execute(select(table).order_by(*table.primary_key.columns)).mappings()
                    for original in result:
                        row=serializable(original)
                        if table.name==Connection.__tablename__ and row['ciphertext']!='revoked':
                            clear=source.decrypt(row['user_id'],row['exchange'],row['ciphertext'])
                            row['ciphertext']=destination.encrypt(row['user_id'],row['exchange'],clear)
                        item_size=len(canonical(row))
                        if rows and (len(rows)>=250 or size+item_size>350000):write(table.name,rows);rows=[];size=0
                        rows.append(row);size+=item_size
                    if rows:write(table.name,rows)
                result=send('/migration/finish',{'id':migration_id,'chain':chain})
                if not result.get('verified'):raise ValueError('Target snapshot verification failed')
                print(json.dumps({'migration_verified':True,'tables':counts,'batches':batch,'chain':chain,'execution_active':False}),flush=True)
    # Activation is intentionally a separate final cutover action.

if __name__=='__main__':run()
