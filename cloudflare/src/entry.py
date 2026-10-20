"""Cloudflare entry point. Fresh paper backend with an isolated compact public market feed."""
import asyncio, gc, os, time
from urllib.parse import urlparse
from workers import WorkerEntrypoint, DurableObject, Response, Request, asgi

class ZenEngine(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.ready=False
        self.app=None
        self.database=None
        self.observer=None
        self.migration=None

    def initialize(self):
        if self.ready:return
        from transport_runtime import install
        install()
        os.environ['ZEN_CLOUDFLARE']='true'
        from database_runtime import CloudDatabase
        self.database=CloudDatabase(self.ctx.storage)
        self.database.create_dev()
        for key in ('CREDENTIAL_MASTER_KEY','BOOTSTRAP_TOKEN','ZEN_PAPER_PROFILE'):
            value=getattr(self.env,key,None)
            if value:os.environ[key]=value
        from backend.api import create_app
        from inline_asgi import adapt
        self.app=adapt(create_app(self.database))
        from alarm_worker import AlarmWorker
        self.observer=AlarmWorker(self.database,self.env)
        from migration_runtime import Migration
        self.migration=Migration(self.database,self.ctx.storage,self.env)
        self.ready=True

    async def fetch(self, request):
        async def operation():
            self.initialize()
            path=urlparse(request.url).path
            if path.startswith('/migration/'):
                return await self.migration.handle(request,path)
            active=bool(await self.ctx.storage.get('active'))
            if not active and getattr(self.env,'FRESH_WORKSPACE','false')=='true':
                await self.ctx.storage.put('active',True)
                active=True
            if path=='/_wake':
                if active and await self.ctx.storage.getAlarm() is None:
                    await self.ctx.storage.setAlarm(int(time.time()*1000)+1000)
                return Response.json({'active':active})
            if not active and getattr(self.env,'LOCAL_COMPATIBILITY_TEST','false')!='true':
                return Response.json({'status':'migration_pending','migration_complete':False},status=503)
            if path=='/events':
                return Response.json({'detail':'Use authenticated snapshot polling on this runtime'},status=503)
            response=Response(await asgi.fetch(self.app,request,self.env))
            # Consume the HTTP body inside the serialized operation so no ASGI
            # task retains a database transaction beyond the request boundary.
            body=await response.bytes()
            return Response(body,status=response.status,headers=dict(response.headers.items()))
        gc.collect()
        try:
            return await self.ctx.blockConcurrencyWhile(operation)
        finally:
            gc.collect()

    async def alarm(self):
        # Re-arm first: an exception or process eviction must not silently end
        # observation. Duplicate alarms are handled by existing decision IDs.
        if not await self.ctx.storage.get('active'):return
        await self.ctx.storage.setAlarm(int(time.time()*1000)+10000)
        async def operation():
            self.initialize()
            self.observer.cursor=int(await self.ctx.storage.get('scan_cursor') or 0)
            result=await asyncio.wait_for(self.observer.tick(),timeout=22)
            if result.get('scanned'):
                await self.ctx.storage.put('scan_cursor',self.observer.cursor)
                print({'event':'market_scan',**result})
        try:
            await self.ctx.blockConcurrencyWhile(operation)
        except Exception as error:
            # No exception bodies, exchange credentials, or SQL parameters.
            print({'event':'alarm_failed','error_type':type(error).__name__})
            raise
        finally:
            gc.collect()

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if urlparse(request.url).path.startswith('/_'):
            return Response.json({'detail':'Not found'},status=404)
        try:
            return await self.env.ENGINE.getByName('zen-primary').fetch(request)
        except Exception as error:
            if 'Exceeded allowed rows' in str(error):
                return Response.json({'detail':'Backend database allowance exhausted. Paper trading is unavailable until service recovers; repeated retries will not help.'},status=503)
            raise

    async def scheduled(self, controller, env, ctx):
        response=await self.env.ENGINE.getByName('zen-primary').fetch(Request('https://internal/_wake',method='POST'))
        if response.status != 200:
            raise RuntimeError('Scheduler wake failed')
        state=await response.json()
        print({'event':'scheduler_wake','active':bool(state.get('active'))})
