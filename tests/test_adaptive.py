"""Synthetic tests prove behavior and math, not trading profitability."""
import time,math,asyncio
from decimal import Decimal as D
from types import SimpleNamespace
import pytest,httpx
from sqlalchemy import select
from research.adaptive import evaluate,outcomes
from exchange_adapters.universe import catalogue,rotation
from exchange_adapters.mexc_futures import MexcFutures
from backend.futures_paper import config,close_paper
from database.models import User,Record,FuturesPaperPosition,FuturesMarket
from agents.futures_pipeline import process
from test_futures import world,meta,tick

def bars(now=None,short=False,kind='trend'):
    now=time.time() if now is None else now
    result=[]
    for i in range(100):
        p=100-i*.15 if short else 100+i*.15
        if kind=='range':p=100+2*math.sin(i*.22)
        result.append([(int(now//60)-100+i)*60000,p-.03,p+.06,p-.06,p,100])
    return result

def test_long_and_short_without_narrow_breakout():
    for short in [False,True]:
        rows=bars(short=short);t={**tick(),'bid1':str(rows[-1][4]-.005),'ask1':str(rows[-1][4]+.005),'fairPrice':str(rows[-1][4]),'lastPrice':str(rows[-1][4])}
        d=evaluate(rows,t,'aggressive',slippage_bps=5)
        assert d['action']==('SHORT' if short else 'LONG')
        assert len(d['opportunities'])==3;assert d['confidence'] is None

@pytest.mark.parametrize('bad',['future','gap','nan','negative_volume'])
def test_corrupt_data_never_trades(bad):
    rows=bars()
    if bad=='future':rows[-1][0]=int(time.time()*1000)
    if bad=='gap':rows[-2][0]-=60000
    if bad=='nan':rows[-1][4]=float('nan')
    if bad=='negative_volume':rows[-1][5]=-1
    assert evaluate(rows,tick(),'aggressive')['action']=='WAIT'

def test_learning_chronological_bounded_suspension():
    history=[{'position_id':str(i),'closed_at':i,'completed':True,'strategy':'momentum','regime':'trend','initial_risk':'1','net':'-1'} for i in range(8)]
    a=outcomes(history);assert a==outcomes(list(reversed(history)))
    assert -.25<=a['momentum:trend']['weight']<=.25
    assert a['momentum:trend']['suspended']
    assert outcomes([dict(history[0],completed=False)])=={}

def test_all_markets_discovery_and_rotation():
    rows=[dict(meta(),symbol=f'COIN{i}_USDT') for i in range(40)]
    found=catalogue(rows+[dict(meta(),symbol='BAD_USDC')]);assert len(found)==40
    markets=[SimpleNamespace(symbol=s,contract=c,ticker={**tick(),'amount24':str(1000000+i)},received=time.time()) for i,(s,c) in enumerate(found.items())]
    cursor=0;seen=set()
    for _ in range(20):
        selected,cursor=rotation(markets,cursor);seen.update(selected)
        assert len(selected)<=12
    assert seen==set(found)
    markets[0].received=time.time()-100
    assert markets[0].symbol not in rotation(markets,0)[0]

def test_pipeline_executes_once_and_learns_only_after_full_exposure(world):
    db,owner,c,headers=world
    assert c.post('/agent/paper-profile',json={'profile':'aggressive'},headers=headers).status_code==200
    rows=bars();last=rows[-1][4]
    with db.sessions() as s:
        market=s.get(FuturesMarket,'BTC_USDT');market.ticker={**tick(),'bid1':str(last-.005),'ask1':str(last+.005),'lastPrice':str(last),'fairPrice':str(last)};s.commit()
        d=process(s,s.get(User,owner),'BTC_USDT',rows);s.commit()
        assert d['execution']=='filled',d
        pid=d['position_id']
        assert process(s,s.get(User,owner),'BTC_USDT',rows) is None
        close_paper(s,owner,pid,D('.5'),'adaptive-close-half-001');s.commit()
        assert not s.scalar(select(Record).where(Record.kind=='paper_learning_outcome'))
        close_paper(s,owner,pid,D(1),'adaptive-close-final-001');s.commit()
        samples=list(s.scalars(select(Record).where(Record.kind=='paper_learning_outcome')))
        assert len(samples)==1
        assert samples[0].payload['completed'] and D(samples[0].payload['initial_risk'])>0
        assert c.get('/agent/research',headers=headers).json()['learning']['samples']==1

def test_profile_live_cannot_bypass(world):
    db,owner,c,headers=world
    with db.sessions() as s:config(s,owner).activated=time.time();s.commit()
    assert c.post('/agent/paper-profile',json={'profile':'aggressive'},headers=headers).status_code==409

def test_bulk_tickers_filter_corrupt_rows():
    data=[tick(),dict(tick(),symbol='DOGE_USDT'),dict(tick(),symbol='INVALID'),dict(tick(),symbol='BAD_USDT',bid1='NaN')]
    async def run():
        a=MexcFutures(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'success':True,'code':0,'data':data})))
        rows=await a.tickers();await a.close();return rows
    assert len(asyncio.run(run()))==2

def test_replay_reproducible_and_no_promotion():
    from research.replay import replay
    r=bars(kind='range')
    assert replay(r)==replay(r)
    assert not replay(r)['promoted']
    assert replay(r)['train_bars']<len(r)

def test_unknown_contract_candles_rejected_without_network(world):
    db,owner,c,h=world
    assert c.get('/candles?symbol=NEWCOIN_USDT',headers=h).status_code==404
