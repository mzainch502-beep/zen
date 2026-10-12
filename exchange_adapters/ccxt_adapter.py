"""Read-only adapter. Live order placement is deliberately not exposed in this release."""
import asyncio, time, os
from decimal import Decimal
import ccxt.async_support as ccxt
from backend.domain import Quote
EXCHANGES={'binance':'binance','bybit':'bybit','okx':'okx','kraken':'kraken','coinbase':'coinbase',
           'bitget':'bitget','kucoin':'kucoin','gate':'gate','mexc':'mexc'}
class ReadAdapter:
    def __init__(self,exchange,credentials=None):
        if exchange not in EXCHANGES: raise ValueError('Unsupported exchange')
        self.name=exchange
        adapter_id=EXCHANGES[exchange]
        if exchange=='gate' and not hasattr(ccxt,'gate'): adapter_id='gateio'
        self.client=getattr(ccxt,adapter_id)({'enableRateLimit':True,'aiohttp_trust_env':True,'timeout':10000,
            **({'cafile':os.environ['SSL_CERT_FILE']} if os.getenv('SSL_CERT_FILE') else {}),
            'options':{'defaultType':'spot','adjustForTimeDifference':True},**(credentials or {})})
    async def close(self): await self.client.close()
    async def discover(self):
        markets=await self.client.load_markets()
        return {'exchange':self.name,'spot':any(m.get('spot') for m in markets.values()),
            'swap':any(m.get('swap') for m in markets.values()),'timeframes':list(self.client.timeframes or {}),
            'websocket':bool(self.client.has.get('watchTicker')),'live_enabled':False,
            'permissions_verified':False,'validation':'read-only; no private execution certification'}
    async def balance(self):
        b=await self.client.fetch_balance()
        return {k:str(v) for k,v in b.get('free',{}).items() if v is not None}
    async def quote(self,symbol):
        t=await self.client.fetch_ticker(symbol)
        if not t.get('bid') or not t.get('ask') or not t.get('last') or not t.get('timestamp'):
            raise ValueError('Ticker lacks timestamp or executable bid/ask')
        return Quote(symbol=symbol,bid=Decimal(str(t['bid'])),ask=Decimal(str(t['ask'])),last=Decimal(str(t['last'])),
            timestamp=t['timestamp']/1000,source=self.name,change_percent=t.get('percentage'))
    async def candles(self,symbol,timeframe,limit=200):
        await self.client.load_markets()
        if timeframe not in (self.client.timeframes or {}): raise ValueError('Timeframe unavailable')
        return await self.client.fetch_ohlcv(symbol,timeframe,limit=limit)

async def bounded_read(call,attempts=3):
    for attempt in range(attempts):
        try: return await call()
        except (ccxt.NetworkError,ccxt.RateLimitExceeded):
            if attempt+1==attempts: raise
            await asyncio.sleep(min(2**attempt,4))
