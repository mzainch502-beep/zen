"""Risk recommendations tighten configured ceilings; never grant live permissions."""
from decimal import Decimal
from backend.futures_domain import FuturesLimits
from backend.learning import snapshot

def recommend(db,owner,base,equity,ticker=None):
    l=FuturesLimits.model_validate(base);learning=snapshot(db,owner)
    n=learning['samples'];positive=Decimal(learning['net'])>0
    stage='Evidence building' if n<30 or not positive else 'Paper expansion'
    fraction=Decimal('.005') if stage=='Evidence building' else Decimal('.01')
    loss=min(l.max_loss_trade,max(Decimal('.01'),equity*fraction))
    leverage=min(l.max_leverage,1 if stage=='Evidence building' else 3)
    reasons=['Ceilings are owner-configured; recommendations only tighten them',f'{n} completed learning exposures; net outcome {learning["net"]}',stage]
    if ticker:
        from decimal import InvalidOperation
        try:
            bid,ask,last=(Decimal(str(ticker[k])) for k in ['bid1','ask1','lastPrice'])
            if (ask-bid)/last*10000>10:loss*=Decimal('.5');leverage=1;reasons.append('Wide spread reduces risk allowance')
        except (KeyError,InvalidOperation,ZeroDivisionError):loss=Decimal('.01');leverage=1;reasons.append('Market context incomplete')
    from backend.context import snapshot as context_snapshot
    import time
    events=context_snapshot(db)['events']
    if any(e.get('review_flag') and e.get('published') and -300<=time.time()-e['published']<=3600 for e in events):
        loss*=Decimal('.5');leverage=1;reasons.append('Recent monitored headline requires caution; not a directional signal')
    effective=l.model_copy(update={'max_loss_trade':loss,'max_daily_loss':min(l.max_daily_loss,max(Decimal('.01'),equity*Decimal('.02'))),
        'max_margin':min(l.max_margin,max(Decimal('.01'),equity*Decimal('.05'))),'max_leverage':leverage})
    return {'stage':stage,'effective_limits':effective.model_dump(mode='json'),'outer_limits':l.model_dump(mode='json'),'reasons':reasons,
            'calibration':None,'automatic':l.auto_risk,'notice':'Recommendations are not a guarantee of loss prevention or returns'}
