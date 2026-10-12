"""Chronological cost-aware replay; retrospective results never authorize live orders."""
import argparse,asyncio,json,hashlib
from pathlib import Path
from research.adaptive import evaluate,outcomes,VERSION
from exchange_adapters.mexc_futures import MexcFutures

def replay(rows,profile='aggressive',adaptive=True):
    split=int(len(rows)*.6);history=[];weights={};position=None;equity=200.;peak=equity;max_dd=0.;trades=[];decisions=0;waits=0
    fee=.0008;slip=.0005;spread=.0005
    for i in range(40,len(rows)):
        bar=rows[i];ts=bar[0]/1000;open_price=float(bar[1])
        if position:
            p=position;long=p['direction']=='LONG'
            stopped=float(bar[3])<=p['stop'] if long else float(bar[2])>=p['stop']
            taken=float(bar[2])>=p['take'] if long else float(bar[3])<=p['take']
            if stopped or taken or i-p['bar']>=15:
                # Stop first if both touched; gap-through stops use worse open.
                raw=(min(open_price,p['stop']) if long else max(open_price,p['stop'])) if stopped else p['take'] if taken else float(bar[4])
                price=raw*(1-spread/2-slip if long else 1+spread/2+slip)
                net=p['qty']*(price-p['entry'])*(1 if long else -1)-fee*p['qty']*(price+p['entry'])
                equity+=net;peak=max(peak,equity);max_dd=max(max_dd,peak-equity)
                outcome={'position_id':str(p['bar']),'completed':True,'strategy':p['strategy'],'regime':p['regime'],'initial_risk':p['risk'],'net':net,'closed_at':ts,'oos':i>=split}
                history.append(outcome);trades.append(outcome);weights=outcomes(history[-250:]) if adaptive else {};position=None
        if position:continue
        closed=rows[max(0,i-100):i]
        ticker={'symbol':'REPLAY_USDT','bid1':open_price*(1-spread/2),'ask1':open_price*(1+spread/2),'lastPrice':open_price,'fairPrice':open_price,'timestamp':int(ts*1000),'fundingRate':0}
        d=evaluate(closed,ticker,profile,weights,now=ts,slippage_bps=slip*10000)
        decisions+=1
        if d['action']=='WAIT':waits+=1;continue
        long=d['action']=='LONG';entry=open_price*(1+spread/2+slip if long else 1-spread/2-slip);stop_fraction=d['stop_fraction']
        position={'bar':i,'direction':d['action'],'strategy':d['strategy'],'regime':d['regime'],'entry':entry,'qty':10/entry,'risk':10*(stop_fraction+fee*2+slip*2+spread),
                  'stop':entry*(1-stop_fraction if long else 1+stop_fraction),'take':entry*(1+2.2*stop_fraction if long else 1-2.2*stop_fraction)}
    oos=[r for r in trades if r['oos']]
    return {'version':VERSION,'bars':len(rows),'train_bars':split,'oos_bars':len(rows)-split,'completed_trades':len(trades),'oos_trades':len(oos),
            'realized_net':round(equity-200,8),'oos_realized_net':round(sum(t['net'] for t in oos),8),'max_realized_drawdown':round(max_dd,8),
            'decisions':decisions,'waits':waits,'open_exposure_excluded':bool(position),'adaptive':adaptive,'promoted':False,
            'assumptions':{'round_trip_fee_bps':fee*20000,'one_way_slippage_bps':slip*10000,'modeled_spread_bps':spread*10000,'funding_settlement':'not modeled','stop_precedes_take_on_ambiguous_bar':True},
            'limitations':['Retrospective simulated fills','Short single-window split; not production validation','Funding settlement not modeled','Open unrealized exposure excluded from realized results','No guaranteed improvement']}

async def main(args):
    a=MexcFutures();reports=[]
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    try:
        for symbol in args.symbols:
            try:
                rows=[r for r in await a.candles(symbol,limit=1000) if r[0]/1000+60<__import__('time').time()]
                raw=json.dumps(rows,separators=(',',':')).encode()
                Path(args.output).with_name(symbol+'-candles.json').write_bytes(raw)
                reports.append({'symbol':symbol,'source':'MEXC public completed 1m candles','data_sha256':hashlib.sha256(raw).hexdigest(),'adaptive':replay(rows),'frozen_baseline':replay(rows,adaptive=False)})
            except Exception as e:reports.append({'symbol':symbol,'status':'unavailable','error_type':type(e).__name__})
    finally:await a.close()
    Path(args.output).write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--symbols',nargs='+',default=['BTC_USDT','SOL_USDT','DOGE_USDT']);p.add_argument('--output',default='adaptive-replay.json');asyncio.run(main(p.parse_args()))
