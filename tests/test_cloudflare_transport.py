import asyncio
import importlib.util
import sys
import types
from pathlib import Path
import httpx


def test_fetch_decoded_body_is_not_decompressed_twice(monkeypatch):
    class Response:
        status=200
        headers={'Content-Encoding':'gzip','Content-Length':'123','Content-Type':'application/json'}
        async def bytes(self):return b'{"price":"0.00000001"}'
    async def fetch(url,**kwargs):
        assert 'accept-encoding' not in kwargs['headers']
        assert kwargs['redirect']=='manual'
        return Response()
    monkeypatch.setitem(sys.modules,'workers',types.SimpleNamespace(fetch=fetch))
    spec=importlib.util.spec_from_file_location('tested_fetch_transport',Path(__file__).parents[1]/'cloudflare/src/transport_runtime.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    async def check():
        async with httpx.AsyncClient(transport=module.FetchTransport()) as client:
            response=await client.get('https://example.test/public')
            assert response.json()=={'price':'0.00000001'}
            assert 'content-encoding' not in response.headers
            assert int(response.headers['content-length'])==len(response.content)
    asyncio.run(check())
