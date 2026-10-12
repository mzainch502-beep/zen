"""Continuous, experimental SPOT paper orchestration. Never imports a live order API.

Research trials are not strategy promotion or evidence of predictive performance.
The independent governor remains the sole authorization boundary for every fill.
"""
import hashlib
import math
import time
from decimal import Decimal, ROUND_DOWN
from statistics import mean
from sqlalchemy import select
from backend.domain import Limits, Proposal, Quote
from backend.service import execute, positions, portfolio, Rejected
from database.models import User, Market, Order, Record, record
from research.evaluation import validate_candles

VERSION = 'paper-breakout-trial-v1'
MAX_HOLD_SECONDS = 900


def assess(rows, quote, now=None):
    """Completed 1m OHLCV only; describes movement, never a calibrated prediction."""
    now = time.time() if now is None else now
    d = {'action': 'WAIT', 'hypothesis': 'WAIT', 'version': VERSION,
         'selected_strategy': VERSION, 'confidence': None,
         'evidence': [], 'contradictions': ['Experimental paper trial; predictive value unvalidated'],
         'reason': 'Collecting completed candles', 'research_trial': True}
    try:
        validate_candles(rows)
    except (ValueError, TypeError, IndexError):
        d['reason'] = 'Invalid or insufficient chronological OHLCV'
        return d
    if any(r[0] / 1000 + 60 > now for r in rows):
        d['reason'] = 'Incomplete candle rejected'
        return d
    if now - (rows[-1][0] / 1000 + 60) > 120 or now - quote.timestamp > 15 or quote.timestamp > now + 5:
        d['reason'] = 'Stale market observation'
        return d
    if any(b[0] - a[0] != 60000 for a, b in zip(rows, rows[1:])):
        d['reason'] = 'Missing 1m candles'
        return d
    closes = [float(r[4]) for r in rows]
    fast, slow = mean(closes[-10:]), mean(closes[-30:])
    last = closes[-1]
    ranges = [max(float(rows[i][2]) - float(rows[i][3]),
                  abs(float(rows[i][2]) - closes[i-1]), abs(float(rows[i][3]) - closes[i-1]))
              for i in range(len(rows)-14, len(rows))]
    atr_fraction = mean(ranges) / last
    drift = last / closes[-20] - 1
    costs = float(quote.spread_bps) / 10000 + .002 + .002  # fees + two-sided slippage
    stop_fraction = max(.005, 2 * atr_fraction)
    d.update(bar_timestamp=int(rows[-1][0]), stop_fraction=stop_fraction,
             expected_cost_bps=costs * 10000,
             evidence=[f'Observed 20-bar return {drift:.5f}', f'14-bar range fraction {atr_fraction:.5f}',
                       f'Modeled round-trip cost {costs*10000:.2f} bps'])
    if quote.ask < quote.bid or quote.spread_bps > 20 or not math.isfinite(stop_fraction) or stop_fraction > .03:
        d['reason'] = 'Liquidity or volatility outside trial envelope'
    elif fast < slow and last < min(float(r[3]) for r in rows[-21:-1]):
        d.update(hypothesis='SHORT', reason='Bearish breakout observed; spot trial cannot open SHORT')
    elif fast > slow and last > max(float(r[2]) for r in rows[-21:-1]) and drift > costs * 2:
        d.update(action='LONG', hypothesis='LONG', reason='Completed bullish breakout qualifies for paper experiment')
    else:
        d['reason'] = 'No cost-filtered breakout; WAIT'
    return d


def process_observation(db, owner, symbol, rows, now=None):
    now = time.time() if now is None else now
    u = db.scalar(select(User).where(User.id == owner).with_for_update().execution_options(populate_existing=True))
    market = db.get(Market, symbol)
    if not market:
        return None
    q = Quote.model_validate(market.payload)
    d = assess(rows, q, now)
    # A bar is processed at most once per owner/symbol/version, including WAIT/veto.
    bar = int(rows[-1][0]) if rows and len(rows[-1]) else 0
    key = 'auto-' + hashlib.sha256(f'{owner}:{symbol}:{VERSION}:{bar}'.encode()).hexdigest()[:48]
    existing = db.scalar(select(Record).where(Record.user_id == owner, Record.kind == 'decision',
                                               Record.payload['decision_key'].as_string() == key).limit(1))
    if existing:
        return None
    d.update(symbol=symbol, decision_key=key)
    record(db, owner, 'decision', d)
    if d['action'] != 'LONG':
        return d
    ps = positions(db, owner)
    if any(p.symbol == symbol for p in ps):
        record(db, owner, 'risk_veto', {'decision_key': key, 'reason': 'Existing symbol exposure'})
        return d
    limits = Limits.model_validate(u.limits)
    snap = portfolio(db, u)
    remaining = min(limits.max_notional, limits.max_correlated_notional) - Decimal(snap['exposure'] or '0')
    stop_fraction = Decimal(str(d['stop_fraction']))
    # Fixed upper size, never sized to aspirational target or increased after losses.
    notional = min(Decimal('10'), remaining, u.cash / Decimal('1.002'),
                   limits.max_loss_trade / (stop_fraction + Decimal('.006')))
    if notional < 5:
        record(db, owner, 'risk_veto', {'decision_key': key, 'reason': 'Insufficient experiment allocation'})
        return d
    qty = (notional / (q.ask * Decimal('1.001'))).quantize(Decimal('.000000000001'), rounding=ROUND_DOWN)
    p = Proposal(symbol=symbol, side='buy', quantity=qty, stop=q.ask * (1-stop_fraction),
                 take_profit=q.ask * (1+3*stop_fraction), idempotency_key=key)
    # SAVEPOINT retains the decision and risk audit on veto, without partial fills.
    try:
        with db.begin_nested():
            order = execute(db, owner, p)
            record(db, owner, 'autonomous_entry', {'decision_key': key, 'order_id': order.id,
                                                 'version': VERSION, 'symbol': symbol,
                                                 'maximum_hold_seconds': MAX_HOLD_SECONDS})
    except Rejected as e:
        record(db, owner, 'risk_veto', {'decision_key': key, 'reason': str(e)})
    return d


def manage_exits(db, owner, now=None):
    now = time.time() if now is None else now
    db.scalar(select(User).where(User.id == owner).with_for_update().execution_options(populate_existing=True))
    entries = list(db.scalars(select(Record).where(Record.user_id == owner, Record.kind == 'autonomous_entry')))
    entry_by_order = {e.payload['order_id']: e for e in entries}
    results = []
    for p in positions(db, owner):
        m = db.get(Market, p.symbol)
        if not m:
            continue
        q = Quote.model_validate(m.payload)
        if now-q.timestamp > 15 or q.timestamp > now+5:
            continue
        entry = db.scalar(select(Order).where(Order.user_id == owner, Order.symbol == p.symbol,
                                              Order.side == 'buy').order_by(Order.created.desc()))
        auto = entry and entry_by_order.get(entry.id)
        cause = 'stop_loss' if p.stop and q.bid <= p.stop else 'take_profit' if p.take_profit and q.bid >= p.take_profit else None
        if not cause and auto and now-entry.created >= MAX_HOLD_SECONDS:
            cause = 'maximum_hold'
        if not cause:
            continue
        allocated_entry_fee = p.entry_fees
        try:
            with db.begin_nested():
                order = execute(db, owner, Proposal(symbol=p.symbol, side='sell', quantity=p.quantity,
                                                     reduce_only=True, idempotency_key='exit-'+p.id))
                result = {'symbol': p.symbol, 'entry_order_id': entry.id if entry else None,
                          'exit_order_id': order.id, 'cause': cause,
                          'net_pnl': str(order.realized-order.fee-allocated_entry_fee),
                          'exit_fee': str(order.fee), 'entry_fee_allocated': str(allocated_entry_fee),
                          'holding_seconds': now-entry.created if entry else None,
                          'version': VERSION if auto else 'manual', 'paper': True}
                record(db, owner, 'trade_evaluation', result)
                results.append(result)
        except Rejected as e:
            record(db, owner, 'exit_error', {'reason': str(e), 'position_id': p.id})
    return results
