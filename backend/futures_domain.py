from decimal import Decimal, ROUND_DOWN
from typing import Literal
from pydantic import Field
from backend.domain import Strict

class FuturesLimits(Strict):
    max_leverage:int=Field(default=1,ge=1,le=500)
    max_margin:Decimal=Field(default=Decimal('3'),gt=0,le=10000)
    max_notional:Decimal=Field(default=Decimal('40'),gt=0,le=100000)
    max_loss_trade:Decimal=Field(default=Decimal('2'),gt=0,le=10000)
    max_daily_loss:Decimal=Field(default=Decimal('6'),gt=0,le=10000)
    max_drawdown:Decimal=Field(default=Decimal('20'),gt=0,le=10000)
    min_liquidation_distance:Decimal=Field(default=Decimal('.005'),gt=0,lt=1)
    max_spread_bps:Decimal=Field(default=Decimal('20'),gt=0,le=100)
    max_slippage_bps:Decimal=Field(default=Decimal('10'),gt=0,le=100)
    max_positions:int=Field(default=2,ge=1,le=10)
    max_order_rate:int=Field(default=6,ge=1,le=20)
    automatic:bool=False
    auto_risk:bool=False
    profile:Literal["balanced","aggressive"]="balanced"

class FuturesProposal(Strict):
    symbol:str=Field(pattern='^[A-Z0-9]{2,20}_USDT$')
    direction:Literal['LONG','SHORT']
    margin:Decimal=Field(gt=0,max_digits=28,decimal_places=12)
    leverage:int=Field(default=1,ge=1,le=500)
    use_exchange_max:bool=False
    stop:Decimal=Field(gt=0,max_digits=28,decimal_places=12)
    take_profit:Decimal=Field(gt=0,max_digits=28,decimal_places=12)
    idempotency_key:str=Field(min_length=16,max_length=64,pattern='^[a-zA-Z0-9_-]+$')

class Contract(Strict):
    symbol:str
    size:Decimal=Field(gt=0)
    step:Decimal=Field(gt=0)
    min_vol:Decimal=Field(gt=0)
    max_vol:Decimal=Field(gt=0)
    tick:Decimal=Field(gt=0)
    max_leverage:int=Field(ge=1)
    min_leverage:int=Field(ge=1)
    mmr:Decimal=Field(ge=0,lt=1)
    imr:Decimal=Field(default=Decimal(0),ge=0,lt=1)
    taker_fee:Decimal=Field(ge=0,lt=1)
    api_allowed:bool
    state:int
    tiers:list[dict]=[]
    @classmethod
    def parse(cls,d):
        if d.get('futureType',1)!=1 or d.get('settleCoin','USDT')!='USDT':raise ValueError('Only USDT-settled perpetual contracts supported')
        caps=[int(d['maxLeverage'])]
        if int(d.get('countryConfigContractMaxLeverage') or 0)>0:caps.append(int(d['countryConfigContractMaxLeverage']))
        return cls(symbol=d['symbol'],size=d['contractSize'],step=d['volUnit'],min_vol=d['minVol'],max_vol=d['maxVol'],tick=d['priceUnit'],
                   max_leverage=min(caps),min_leverage=d['minLeverage'],mmr=d['maintenanceMarginRate'],imr=d.get('initialMarginRate',0),taker_fee=d['takerFeeRate'],
                   api_allowed=d.get('apiAllowed') is True,state=d['state'],tiers=d.get('riskLimitCustom') or [])
    def round_price(self,p):return (p/self.tick).to_integral_value(rounding=ROUND_DOWN)*self.tick
    def round_vol(self,v):return (v/self.step).to_integral_value(rounding=ROUND_DOWN)*self.step

def liquidation_estimate(entry,leverage,mmr,direction):
    # Isolated, linear model only. Native exchange liquidation values supersede it.
    return entry*(1-Decimal(1)/leverage)/(1-mmr) if direction=='LONG' else entry*(1+Decimal(1)/leverage)/(1+mmr)

def plan(p,contract,ticker,limits,available,equity,exposure,position_count,daily_net,high_water,now):
    from backend.service import Rejected
    c=contract;d=lambda k:Decimal(str(ticker[k]));bid=d('bid1');ask=d('ask1');mark=d('fairPrice');last=d('lastPrice')
    reasons=[]
    if c.symbol!=p.symbol or ticker.get('symbol')!=p.symbol:raise Rejected('Futures contract/ticker symbol mismatch')
    lev=min(c.max_leverage,limits.max_leverage) if p.use_exchange_max else p.leverage
    if lev>min(c.max_leverage,limits.max_leverage) or lev<c.min_leverage:reasons.append('Leverage outside discovered/user ceiling')
    price=(ask*(1+limits.max_slippage_bps/10000) if p.direction=='LONG' else bid*(1-limits.max_slippage_bps/10000))
    vol=c.round_vol(p.margin*lev/(price*c.size));notional=vol*c.size*price
    mmr=c.mmr;imr=c.imr
    for tier in sorted(c.tiers,key=lambda t:Decimal(str(t['maxVol']))):
        if vol<=Decimal(str(tier['maxVol'])):
            if lev>int(tier['maxLeverage']):reasons.append('Risk-tier leverage exceeded')
            mmr=max(mmr,Decimal(str(tier['mmr'])));imr=max(imr,Decimal(str(tier.get('imr',0))));break
    else:
        if c.tiers:reasons.append('No supported risk tier for quantity')
    stop=c.round_price(p.stop);take=c.round_price(p.take_profit)
    fee=notional*c.taker_fee;reserve=fee*2+notional*abs(Decimal(str(ticker.get('fundingRate',0))))
    allocated=max(notional/lev,notional*imr)
    liq=liquidation_estimate(price,lev,mmr,p.direction)
    distance=abs(mark-liq)/mark
    if not c.api_allowed or c.state!=0:reasons.append('Contract not API tradable')
    if not -5<=now-int(ticker['timestamp'])/1000<=15:reasons.append('Stale/future futures ticker')
    if min(bid,ask,mark,last)<=0 or ask<bid:reasons.append('Invalid futures prices')
    if (ask-bid)/last*10000>limits.max_spread_bps:reasons.append('Spread exceeds limit')
    if vol<c.min_vol or vol>c.max_vol:reasons.append('Exchange contract minimum/maximum quantity')
    if allocated>p.margin:reasons.append('Requested margin below exchange initial margin requirement')
    if allocated>limits.max_margin:reasons.append('Margin allocation limit')
    if allocated+reserve>available:reasons.append('Insufficient cash for margin, both-side fees and funding reserve')
    if notional+exposure>limits.max_notional:reasons.append('Notional exposure limit')
    if position_count>=limits.max_positions:reasons.append('Position count limit')
    if (p.direction=='LONG' and mark<=liq) or (p.direction=='SHORT' and mark>=liq):reasons.append('Mark is beyond modeled liquidation')
    if distance<limits.min_liquidation_distance:reasons.append('Insufficient modeled liquidation buffer')
    if p.direction=='LONG':
        if not liq<stop<bid or take<=ask:reasons.append('LONG exits invalid or stop beyond modeled liquidation')
    else:
        if not ask<stop<liq or take>=bid:reasons.append('SHORT exits invalid or stop beyond modeled liquidation')
    worst_loss=vol*c.size*abs(price-stop)+reserve+notional*limits.max_slippage_bps/10000
    if worst_loss>limits.max_loss_trade:reasons.append('Trade loss budget')
    if daily_net<=-limits.max_daily_loss:reasons.append('Daily loss circuit breaker')
    if high_water-equity>=limits.max_drawdown:reasons.append('Drawdown circuit breaker')
    if reasons:raise Rejected('; '.join(reasons))
    return {'contracts':vol,'entry':price,'stop':stop,'take_profit':take,'leverage':lev,'notional':notional,
            'margin':allocated,'entry_fee':fee,'reserve':reserve,'liquidation_estimate':liq,'direction':p.direction,
            'mmr':mmr,'size':c.size,'taker_fee':c.taker_fee}
