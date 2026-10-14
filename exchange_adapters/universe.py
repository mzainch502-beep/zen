"""Dynamic catalogue and fair, bounded candle scheduling."""
import time
from decimal import Decimal,DecimalException
from backend.futures_domain import Contract
from exchange_adapters.mexc_futures import valid_symbol

def catalogue(rows):
    result={}
    for row in rows:
        try:
            valid_symbol(row['symbol']);Contract.parse(row)
            if row.get('state')==0:result[row['symbol']]=row
        except (ValueError,KeyError,TypeError,DecimalException):continue
    return result

def rotation(markets,cursor,batch=12,held=(),blocked=()):
    blocked=set(blocked)
    eligible=[]
    for m in markets:
        if m.symbol in blocked:continue
        t=m.ticker;c=m.contract
        try:
            bid,ask,last=(Decimal(str(t[k])) for k in ['bid1','ask1','lastPrice'])
            if all(x.is_finite() and x>0 for x in [bid,ask,last]) and ask>=bid and time.time()-m.received<=15 and c.get('apiAllowed') is True and c.get('state')==0 and last>0 and (ask-bid)/last*10000<=30 and Decimal(str(t.get('amount24',0)))>=1000000:
                high=Decimal(str(t.get('high24Price',last)));low=Decimal(str(t.get('lower24Price',last)))
                movement=max(Decimal(0),(high-low)/last) if high.is_finite() and low.is_finite() else Decimal(0)
                eligible.append((m.symbol,Decimal(str(t['amount24'])),min(movement,Decimal('.5'))))
        except (ValueError,KeyError,TypeError,DecimalException):continue
    eligible.sort(key=lambda x:(-x[1],x[0]));symbols=[x[0] for x in eligible]
    if not symbols:return [],0
    # Prioritize volatility among already liquid/tight-spread markets, then fairly
    # rotate the full eligible catalogue. No forced trade count or target feedback.
    priority=list(dict.fromkeys(s for s in held if s not in blocked))
    if priority:priority=(priority[cursor%len(priority):]+priority[:cursor%len(priority)])[:batch//2]
    volatile=[x[0] for x in sorted(eligible,key=lambda x:(-x[2],-x[1],x[0]))[:max(1,batch//4)]]
    anchors=list(dict.fromkeys([*priority,*volatile,*symbols[:2]]))[:max(1,batch*2//3)]
    start=cursor%len(symbols);selected=list(anchors);consumed=0
    while len(selected)<batch and consumed<len(symbols):
        symbol=symbols[(start+consumed)%len(symbols)];consumed+=1
        if symbol not in selected:selected.append(symbol)
    return selected,(start+consumed)%len(symbols)

class CandleBackoff:
    """Process-local bounded retry schedule; successful reads clear failure state."""
    def __init__(self):self.failures={};self.until={}
    def failed(self,symbol,now):
        n=min(5,self.failures.get(symbol,0)+1);self.failures[symbol]=n
        self.until[symbol]=now+min(900,30*2**n)
    def succeeded(self,symbol):self.failures.pop(symbol,None);self.until.pop(symbol,None)
    def blocked(self,now):return {s for s,t in self.until.items() if t>now}
