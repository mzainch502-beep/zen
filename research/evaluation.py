"""Cost-aware next-bar research baseline. Does not promote models automatically."""
import hashlib, json, math
from dataclasses import dataclass, asdict
@dataclass(frozen=True)
class Evaluation:
    version: str
    samples: int
    trades: int
    net_return: float
    max_drawdown: float
    status: str
    data_sha256: str

def validate_candles(rows):
    if len(rows)<50: raise ValueError('At least 50 historical candles required')
    times=[r[0] for r in rows]
    if times!=sorted(set(times)): raise ValueError('Timestamps must be unique and chronological')
    for r in rows:
        if len(r)!=6 or not all(math.isfinite(float(x)) for x in r): raise ValueError('Invalid OHLCV')
        if min(r[1:5])<=0 or r[2]<max(r[1],r[3],r[4]) or r[3]>min(r[1],r[2],r[4]) or r[5]<0:
            raise ValueError('Invalid candle geometry')

def evaluate(rows,fee_bps=10,slippage_bps=10):
    validate_candles(rows)
    cash=1.; qty=0.; peak=1.; drawdown=0.; trades=0
    cost=(fee_bps+slippage_bps)/10000
    # Prior completed candles only. Orders fill at next bar open, never signal bar close.
    for i in range(21,len(rows)):
        history=[r[4] for r in rows[i-20:i]]
        long=history[-1]>sum(history)/len(history) and history[-1]>history[-5]
        price=rows[i][1]
        if long and qty==0: qty=cash/(price*(1+cost)); cash=0.; trades+=1
        if not long and qty>0: cash=qty*price*(1-cost); qty=0.; trades+=1
        equity=cash+qty*rows[i][4]; peak=max(peak,equity); drawdown=max(drawdown,1-equity/peak)
    if qty>0: cash=qty*rows[-1][4]*(1-cost)
    sha=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    return Evaluation('momentum-research-v1',len(rows),trades,cash-1,drawdown,'research_only',sha)

def walk_forward(rows):
    validate_candles(rows)
    if len(rows)<300: raise ValueError('At least 300 samples required for three out-of-sample folds')
    size=len(rows)//5
    return [asdict(evaluate(rows[start:start+size])) for start in range(2*size,5*size,size) if len(rows[start:start+size])>=50]

def promotion_gate(folds,shadow_days,security_review):
    return bool(len(folds)>=3 and all(f['trades']>=30 and f['net_return']>0 and f['max_drawdown']<.1 for f in folds)
                and shadow_days>=30 and security_review)
