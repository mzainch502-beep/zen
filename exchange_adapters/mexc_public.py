"""Public MEXC spot observations; never handles credentials or orders."""
import asyncio
import time
from decimal import Decimal
import httpx
from backend.domain import Quote

class MexcPublic:
    def __init__(self, transport=None):
        self.client = httpx.AsyncClient(base_url='https://api.mexc.com', timeout=8,
                                       transport=transport, follow_redirects=False)

    async def close(self):
        await self.client.aclose()

    async def read(self, path, symbol, **params):
        if symbol not in ('BTC/USDT', 'ETH/USDT', 'SOL/USDT'):
            raise ValueError('Unsupported spot symbol')
        response = await self.client.get('/api/v3/' + path,
            params={'symbol': symbol.replace('/', ''), **params})
        response.raise_for_status()
        return response.json()

    async def quote(self, symbol):
        started = time.monotonic()
        book, trades = await asyncio.gather(self.read('ticker/bookTicker', symbol),
                                           self.read('trades', symbol, limit=1))
        if book.get('symbol') != symbol.replace('/', '') or not trades:
            raise ValueError('Spot ticker identity mismatch or no recent trades')
        ts = int(trades[-1]['time']) / 1000
        if not -5 <= time.time() - ts <= 15 or time.monotonic() - started > 8:
            raise ValueError('Stale spot observation')
        bid, ask, last = (Decimal(str(v)) for v in
                         (book['bidPrice'], book['askPrice'], trades[-1]['price']))
        if not all(p.is_finite() and p > 0 for p in (bid, ask, last)) or ask < bid:
            raise ValueError('Invalid spot prices')
        # Timestamp belongs to the latest trade, not the untimestamped REST book.
        return Quote(symbol=symbol, bid=bid, ask=ask, last=last,
                     timestamp=ts, source='mexc', change_percent=None)

    async def candles(self, symbol, timeframe, limit=100):
        intervals = {'1m':'1m','5m':'5m','15m':'15m','30m':'30m',
                     '1h':'60m','4h':'4h','1d':'1d'}
        if timeframe not in intervals:
            raise ValueError('MEXC spot timeframe unsupported')
        rows = await self.read('klines', symbol, interval=intervals[timeframe],
                               limit=min(500, max(1, limit)))
        return sorted([[int(r[0]), *[float(v) for v in r[1:6]]] for r in rows], key=lambda r:r[0])

    async def depth(self, symbol):
        data = await self.read('depth', symbol, limit=20)
        return {'symbol':symbol, 'source':'mexc', 'timestamp':None,
                'received_at':time.time(), 'bids':data['bids'], 'asks':data['asks']}
