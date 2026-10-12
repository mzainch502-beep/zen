"""Reproducible next-bar replay of the experimental 1m paper breakout rule.

Historical bid/ask is unavailable: spread is modeled, explicitly not measured.
Worst-case stop first if both exits are touched in one bar; fees on both sides.
"""
from decimal import Decimal
from backend.domain import Quote
from agents.autonomous import assess, VERSION
from research.evaluation import validate_candles

def replay(rows, fee_bps=10, slippage_bps=10, spread_bps=2):
    validate_candles(rows)
    if any(b[0]-a[0]!=60000 for a,b in zip(rows,rows[1:])):
        raise ValueError('Replay requires contiguous 1m candles')
    cash=200.; position=None; trades=[]; peak=200.; drawdown=0.
    fee=fee_bps/10000; slip=slippage_bps/10000; half=spread_bps/20000
    for i in range(50,len(rows)):
        bar=rows[i]; now=bar[0]/1000
        if position:
            entry,qty,stop,tp,start,entry_fee=position
            exit_price=None;cause=None
            if bar[3]<=stop: exit_price=min(bar[1],stop);cause='stop_loss'
            elif bar[2]>=tp: exit_price=max(bar[1],tp);cause='take_profit'
            elif now-start>=900: exit_price=bar[1];cause='maximum_hold'
            if exit_price is not None:
                fill=exit_price*(1-half)*(1-slip)
                exit_fee=qty*fill*fee;cash+=qty*fill-exit_fee
                trades.append({'net_pnl':qty*(fill-entry)-entry_fee-exit_fee,'cause':cause})
                position=None
        if position is None:
            price=bar[1]
            q=Quote(symbol='BTC/USDT',bid=Decimal(str(price*(1-half))),ask=Decimal(str(price*(1+half))),
                    last=Decimal(str(price)),timestamp=now,source='historical-modeled-spread')
            d=assess(rows[max(0,i-100):i],q,now)
            if d['action']=='LONG':
                entry=float(q.ask)*(1+slip);qty=10/entry;entry_fee=10*fee
                stop=float(q.ask)*(1-d['stop_fraction']);tp=float(q.ask)*(1+3*d['stop_fraction'])
                cash-=10+entry_fee;position=(entry,qty,stop,tp,now,entry_fee)
                # Entry at next open, and same entry bar can hit the stop.
                if bar[3]<=stop:
                    fill=min(bar[1],stop)*(1-half)*(1-slip);exit_fee=qty*fill*fee
                    cash+=qty*fill-exit_fee
                    trades.append({'net_pnl':qty*(fill-entry)-entry_fee-exit_fee,'cause':'stop_loss'})
                    position=None
        equity=cash+(position[1]*bar[4]*(1-half) if position else 0)
        peak=max(peak,equity);drawdown=max(drawdown,1-equity/peak)
    if position:
        entry,qty,_,_,_,entry_fee=position
        fill=rows[-1][4]*(1-half)*(1-slip);exit_fee=qty*fill*fee
        cash+=qty*fill-exit_fee
        trades.append({'net_pnl':qty*(fill-entry)-entry_fee-exit_fee,'cause':'end_of_sample'})
    return {'version':VERSION,'samples':len(rows),'closed_trades':len(trades),'net_pnl':cash-200,
            'max_drawdown_fraction':drawdown,'trades':trades,'promoted':False,
            'fee_bps':fee_bps,'slippage_bps':slippage_bps,'modeled_spread_bps':spread_bps,
            'limitation':'Short sample; modeled OHLC execution, not measured fills; no profitability claim'}

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',help='JSON file containing a candles array')
    args=parser.parse_args()
    print(json.dumps(replay(json.loads(Path(args.dataset).read_text())['candles']),indent=2))
