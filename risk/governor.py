import time
from decimal import Decimal
from backend.domain import Limits, Proposal, Quote, Verdict
FEE=Decimal('.001')

def liquidation_distance(mark: Decimal, liquidation: Decimal | None):
    if not liquidation or mark<=0: return None
    return abs(mark-liquidation)/mark

def evaluate(p: Proposal,q: Quote,limits: Limits,*,mode: str,cash: Decimal,equity: Decimal,
             high_water: Decimal,daily_net: Decimal,exposure: Decimal,positions: int,
             existing_quantity: Decimal,orders_last_minute: int,cooldown_until: float=0):
    reasons=[]
    if time.time()-q.timestamp>15 or q.timestamp>time.time()+5: reasons.append('Stale or future market timestamp')
    if q.ask<q.bid: reasons.append('Crossed book')
    if p.symbol!=q.symbol: reasons.append('Quote symbol mismatch')
    if p.reduce_only:
        if p.side!='sell' or p.quantity>existing_quantity: reasons.append('Invalid reduction')
        return Verdict(approved=not reasons,reasons=reasons,estimated_cost=p.quantity*q.bid*FEE)
    if mode!='Paper': reasons.append('New exposure is paused')
    if p.side!='buy': reasons.append('Spot-only paper release; short positions disabled')
    if p.stop is None or p.stop>=q.ask: reasons.append('Valid stop required')
    if p.take_profit is not None and p.take_profit<=q.ask: reasons.append('Take profit must exceed entry')
    fill=q.ask*(1+limits.max_slippage_bps/10000)
    notional=p.quantity*fill
    if notional<Decimal('5'): reasons.append('Paper minimum notional is $5; exchange-specific minimum may be higher')
    costs=notional*FEE*2+p.quantity*(fill-q.bid)
    if p.stop and p.quantity*(fill-p.stop)+costs>limits.max_loss_trade: reasons.append('Trade loss budget exceeded')
    if notional*(1+FEE)>cash: reasons.append('Insufficient paper cash')
    if exposure+notional>min(limits.max_notional,limits.max_correlated_notional): reasons.append('Exposure limit')
    if positions>=limits.max_positions and existing_quantity==0: reasons.append('Position limit')
    if daily_net<=-limits.max_daily_loss: reasons.append('Daily loss circuit breaker')
    if high_water-equity>=limits.max_drawdown: reasons.append('Drawdown circuit breaker')
    if q.spread_bps>limits.max_spread_bps: reasons.append('Spread too wide')
    if orders_last_minute>=limits.max_order_rate: reasons.append('Order rate limit')
    if time.time()<cooldown_until: reasons.append('Loss cooldown active')
    return Verdict(approved=not reasons,reasons=reasons,estimated_cost=costs)
