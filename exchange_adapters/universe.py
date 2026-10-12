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

def rotation(markets,cursor,batch=12,held=()):
    eligible=[]
    for m in markets:
        t=m.ticker;c=m.contract
        try:
            bid,ask,last=(Decimal(str(t[k])) for k in ['bid1','ask1','lastPrice'])
            if all(x.is_finite() and x>0 for x in [bid,ask,last]) and ask>=bid and time.time()-m.received<=15 and c.get('apiAllowed') is True and c.get('state')==0 and last>0 and (ask-bid)/last*10000<=30 and Decimal(str(t.get('amount24',0)))>=1000000:
                eligible.append((m.symbol,Decimal(str(t['amount24']))))
        except (ValueError,KeyError,TypeError,DecimalException):continue
    eligible.sort(key=lambda x:(-x[1],x[0]));symbols=[s for s,_ in eligible]
    if not symbols:return [],0
    # Rotate all liquid symbols; reserve four slots for the most liquid pairs.
    anchor=symbols[:min(4,batch//2)];n=max(1,batch-len(anchor));start=cursor%len(symbols)
    rotated=[symbols[(start+i)%len(symbols)] for i in range(min(n,len(symbols)))]
    return list(dict.fromkeys([*held,*anchor,*rotated])),(start+n)%len(symbols)
