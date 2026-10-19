import asyncio,time
import httpx,pytest
from decimal import Decimal
from exchange_adapters.bitget_public import BitgetPublic

def run(row):
    async def check():
        adapter=BitgetPublic(httpx.MockTransport(lambda req:httpx.Response(200,json={'code':'00000','data':[row]})))
        try:return await adapter.quote('BTC/USDT')
        finally:await adapter.close()
    return asyncio.run(check())
def tick(**changes):
    return {'category':'SPOT','symbol':'BTCUSDT','bid1Price':'100','ask1Price':'100.01','lastPrice':'100','price24hPcnt':'.01','ts':str(int(time.time()*1000)),**changes}
def test_native_public_quote():
    q=run(tick());assert q.ask==Decimal('100.01') and q.change_percent==1
@pytest.mark.parametrize('changes',[{'symbol':'ETHUSDT'},{'ts':'1'},{'ask1Price':'99'},{'lastPrice':'NaN'}])
def test_native_public_rejects_invalid(changes):
    with pytest.raises(ValueError):run(tick(**changes))
