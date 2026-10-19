"""Fetch transport for existing exchange signing/parsing code. No order retries."""
import asyncio, json, httpx
from workers import fetch

class FetchTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        headers = dict(request.headers)
        headers.pop('host', None)
        try:
            response = await asyncio.wait_for(fetch(str(request.url), method=request.method,
                headers=headers, body=await request.aread() if request.method not in ('GET','HEAD') else None,
                redirect='manual'), timeout=10)
            data = await response.bytes()
            return httpx.Response(response.status, headers=dict(response.headers.items()),
                                  content=data, request=request)
        except asyncio.TimeoutError as error:
            raise httpx.ReadTimeout('Exchange request timed out', request=request) from error
        except Exception as error:
            raise httpx.TransportError('Exchange fetch unavailable', request=request) from error

def install():
    if getattr(httpx.AsyncClient, "_zen_fetch", False): return
    original = httpx.AsyncClient
    class FetchClient(original):
        _zen_fetch = True
        def __init__(self, *args, **kwargs):
            if kwargs.get('transport') is None: kwargs['transport'] = FetchTransport()
            kwargs['trust_env'] = False
            super().__init__(*args, **kwargs)
    httpx.AsyncClient = FetchClient

def install_ccxt():
    import ccxt.async_support as ccxt
    if getattr(ccxt.Exchange, "_zen_fetch", False):return
    async def exchange_fetch(self, url, method='GET', headers=None, body=None):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=headers, content=body)
            raw = response.text
            try: parsed = json.loads(raw)
            except ValueError: parsed = None
            self.handle_errors(response.status_code, response.reason_phrase, url, method,
                               dict(response.headers), raw, parsed, headers, body)
            if response.status_code == 429: raise ccxt.RateLimitExceeded('Exchange rate limit')
            if response.status_code >= 400: raise ccxt.ExchangeNotAvailable('Exchange request rejected')
            return parsed if parsed is not None else raw
        except httpx.TransportError as error:
            raise ccxt.NetworkError('Exchange fetch unavailable') from error
    ccxt.Exchange.fetch = exchange_fetch
    ccxt.Exchange._zen_fetch = True
