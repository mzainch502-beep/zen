"""Compact bulk data from the independent public-data isolate."""
from workers import Request
from exchange_adapters.mexc_futures import MexcFutures, ExchangeFailure

class PublicFutures(MexcFutures):
    def __init__(self,env):
        super().__init__()
        self.feed=getattr(env,'MARKET_FEED',None)
    async def bulk(self,path):
        response=await self.feed.fetch(Request('https://market.internal/'+path))
        if response.status!=200:raise ExchangeFailure('Public data service unavailable')
        payload=await response.json()
        return payload['data']
    async def contracts(self,symbol=None):
        if self.feed is None or symbol:return await super().contracts(symbol)
        return await self.bulk('contracts')
    async def tickers(self):
        if self.feed is None:return await super().tickers()
        rows=await self.bulk('tickers')
        valid=[]
        for row in rows:
            try:valid.append(self.validate_ticker(row))
            except (ExchangeFailure,ValueError,KeyError,TypeError):continue
        return valid
