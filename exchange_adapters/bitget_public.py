"""Small public-only Bitget V3 reader; no account discovery or private methods.

Schema: https://www.bitget.com/docs/catalog/market/market-data
"""
import time
from decimal import Decimal
import httpx
from backend.domain import Quote

class BitgetPublic:
    def __init__(self,transport=None):
        self.client=httpx.AsyncClient(base_url='https://api.bitget.com',timeout=8,transport=transport,follow_redirects=False)
    async def close(self): await self.client.aclose()
    async def read(self,path,symbol,**params):
        if symbol not in ('BTC/USDT','ETH/USDT','SOL/USDT'):raise ValueError('Unsupported spot symbol')
        response=await self.client.get('/api/v3/market/'+path,params={'category':'SPOT','symbol':symbol.replace('/',''),**params})
        response.raise_for_status()
        data=response.json()
        if data.get('code')!='00000':raise ValueError('Spot market read rejected')
        return data['data']
    async def quote(self,symbol):
        rows=await self.read('tickers',symbol)
        matches=[r for r in rows if r.get('symbol')==symbol.replace('/','') and r.get('category')=='SPOT']
        if len(matches)!=1:raise ValueError('Spot ticker identity mismatch')
        r=matches[0];ts=int(r['ts'])/1000
        if not -5<=time.time()-ts<=15:raise ValueError('Stale spot ticker')
        bid,ask,last=(Decimal(r[k]) for k in ('bid1Price','ask1Price','lastPrice'))
        if not all(p.is_finite() and p>0 for p in (bid,ask,last)) or ask<bid:raise ValueError('Invalid spot prices')
        return Quote(symbol=symbol,bid=bid,ask=ask,last=last,timestamp=ts,source='bitget',change_percent=Decimal(r['price24hPcnt'])*100 if r.get('price24hPcnt') is not None else None)
    async def candles(self,symbol,timeframe,limit=100):
        if timeframe!='1m':raise ValueError('Worker spot research uses closed 1m candles')
        rows=await self.read('candles',symbol,interval='1m',limit=str(min(100,max(1,limit))))
        return sorted([[int(r[0]),*[float(v) for v in r[1:6]]] for r in rows],key=lambda r:r[0])
