import asyncio
import time
from decimal import Decimal
import httpx
import pytest
from exchange_adapters.mexc_public import MexcPublic


def quote(book_changes=None, trade_changes=None):
    book={'symbol':'BTCUSDT','bidPrice':'100.00000001','askPrice':'100.00000002',**(book_changes or {})}
    trade={'price':'100.00000001','time':int(time.time()*1000),**(trade_changes or {})}
    async def check():
        def respond(req):
            assert req.url.params['symbol']=='BTCUSDT'
            return httpx.Response(200,json=book if req.url.path.endswith('bookTicker') else [trade])
        adapter=MexcPublic(httpx.MockTransport(respond))
        try:return await adapter.quote('BTC/USDT')
        finally:await adapter.close()
    return asyncio.run(check())


def test_quote_preserves_precision_and_source():
    q=quote()
    assert q.ask==Decimal('100.00000002') and q.source=='mexc'
    assert q.change_percent is None


@pytest.mark.parametrize('book,trade',[
    ({'symbol':'ETHUSDT'},{}), ({'askPrice':'99'},{}),
    ({'bidPrice':'NaN'},{}), ({},{'time':1}),
    ({},{'time':int((time.time()+120)*1000)}), ({},{'price':'0'}),
])
def test_invalid_quote_rejected(book,trade):
    with pytest.raises(ValueError):quote(book,trade)


def test_candles_and_depth():
    async def check():
        def respond(req):
            if req.url.path.endswith('klines'):
                assert req.url.params['interval']=='60m'
                return httpx.Response(200,json=[[1000,'1','2','0.5','1.5','10',2000]])
            return httpx.Response(200,json={'bids':[['1','2']],'asks':[['2','3']]})
        adapter=MexcPublic(httpx.MockTransport(respond))
        try:
            assert await adapter.candles('BTC/USDT','1h')==[[1000,1.,2.,.5,1.5,10.]]
            depth=await adapter.depth('BTC/USDT')
            assert depth['timestamp'] is None and depth['source']=='mexc'
            with pytest.raises(ValueError):await adapter.candles('BTC/USDT','3m')
        finally:await adapter.close()
    asyncio.run(check())
