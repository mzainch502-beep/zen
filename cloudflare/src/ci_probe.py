"""CI-only entry point with labelled fixtures. Never use as a deployment main."""
import time
from decimal import Decimal
from urllib.parse import urlparse
from workers import Response
from entry import Default, ZenEngine

class AppProbe(ZenEngine):
    async def fetch(self, request):
        if urlparse(request.url).path=='/fixturequotes':
            async def fixture():
                self.initialize()
                from sqlalchemy import select
                from database.models import User,FuturesMarket,Market
                from backend.futures_paper import config,book
                from backend.futures_domain import FuturesLimits
                with self.database.sessions() as s:
                    user=s.scalar(select(User))
                    cfg=config(s,user.id);cfg.workspace='futures';cfg.limits=FuturesLimits(max_leverage=10).model_dump(mode='json')
                    b=book(s,user.id);b.cash=b.initial_equity=b.high_water=Decimal('3')
                    meta={'symbol':'BTC_USDT','contractSize':'.01','volUnit':'1','minVol':'1','maxVol':'100000','priceUnit':'.001','maxLeverage':500,'minLeverage':1,'maintenanceMarginRate':'.001','takerFeeRate':'.0008','apiAllowed':True,'state':0,'countryConfigContractMaxLeverage':0}
                    tick={'symbol':'BTC_USDT','bid1':'100','ask1':'100.01','lastPrice':'100','fairPrice':'100','timestamp':int(time.time()*1000),'fundingRate':'0'}
                    s.merge(FuturesMarket(symbol='BTC_USDT',contract=meta,ticker=tick,received=time.time()));s.commit()
                return Response.json({'fixture':True})
            return await self.ctx.blockConcurrencyWhile(fixture)
        return await super().fetch(request)
