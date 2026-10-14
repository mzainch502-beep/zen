"""Versioned paper-only contextual strategy ranking, not a validated return model.

Uses completed candles and realized net outcomes. Updates bounded preferences;
never mutates code, increases leverage, or claims calibrated probabilities.
"""
import math,time
from statistics import mean,pstdev
VERSION='contextual-paper-v3'
STRATEGIES=('momentum','pullback','range_reversion')

def outcomes(rows):
    """Decay recent *completed* position outcomes; one sample per position."""
    weights={};counts={};losses={}
    for r in sorted(rows,key=lambda x:(x.get('closed_at',0),x.get('position_id',''))):
        if not r.get('completed') or r.get('strategy') not in STRATEGIES:continue
        risk=float(r.get('initial_risk',0));net=float(r.get('net',0))
        if risk<=0 or not math.isfinite(risk+net):continue
        key=r['strategy']+':'+r.get('regime','unknown')
        reward=max(-1,min(1,net/risk))
        weights[key]=round(.85*weights.get(key,0)+.15*reward,6)
        counts[key]=counts.get(key,0)+1
        losses[key]=losses.get(key,0)+1 if reward<0 else 0
    return {k:{'weight':max(-.25,min(.25,v)), 'samples':counts[k], 'consecutive_losses':losses[k],
               'suspended':counts[k]>=5 and losses[k]>=4} for k,v in weights.items()}

def evaluate(rows,ticker,profile='balanced',learning=None,now=None,fee=.0008,slippage_bps=10):
    now=time.time() if now is None else now
    result={'version':VERSION,'action':'WAIT','strategy':None,'confidence':None,'research_trial':True,
            'reason':'Awaiting complete market context','evidence':[],'contradictions':['Paper research; predictive value unvalidated'],
            'opportunities':[],'regime':'unknown'}
    if len(rows)<40:return result
    try:
        values=[[float(v) for v in row[:6]] for row in rows]
        if any(len(r)!=6 or not all(math.isfinite(v) for v in r) or r[5]<0 or min(r[1:5])<=0 or r[2]<max(r[1],r[4]) or r[3]>min(r[1],r[4]) for r in values):raise ValueError()
        if any(b[0]-a[0]!=60000 for a,b in zip(values,values[1:])):raise ValueError()
        if values[-1][0]/1000+60>now or now-(values[-1][0]/1000+60)>120:raise ValueError()
        bid,ask,mark,last=(float(ticker[k]) for k in ('bid1','ask1','fairPrice','lastPrice'))
        if not all(math.isfinite(v) and v>0 for v in [bid,ask,mark,last]) or ask<bid or not -5<=now-int(ticker['timestamp'])/1000<=15:raise ValueError()
    except (ValueError,KeyError,TypeError,IndexError,OverflowError):
        result['reason']='Stale, malformed or incomplete observation';return result
    result['bar_timestamp']=int(values[-1][0])
    closes=[r[4] for r in values];returns=[b/a-1 for a,b in zip(closes,closes[1:])]
    vol=pstdev(returns[-20:]);base=pstdev(returns[-40:-20]);drift=closes[-1]/closes[-20]-1
    atr=mean([(r[2]-r[3])/r[4] for r in values[-14:]])
    spread=(ask-bid)/last*10000
    regime='liquidity_stress' if spread>30 else 'expansion' if base and vol>base*2 else 'trend' if abs(drift)>max(vol*2,.001) else 'range'
    result['regime']=regime
    try:
        funding=abs(float(ticker.get('fundingRate',0)))
        if not all(math.isfinite(x) and x>=0 for x in (funding,fee,slippage_bps)):raise ValueError()
    except (TypeError,ValueError):
        result['reason']='Invalid execution cost inputs';return result
    cost=fee*2+slippage_bps*2/10000+spread/10000+funding
    result['estimated_cost_bps']=round(cost*10000,3)
    result['stop_fraction']=min(.025,max(.0025,atr*1.5))
    result['evidence']=[f'20-bar movement {drift*100:.3f}%',f'Regime {regime}',f'Round-trip cost estimate {cost*10000:.2f} bps']
    if regime=='liquidity_stress' or atr>.04 or abs(mark/last-1)>.01 or abs(last/closes[-1]-1)>.02:
        result['reason']='Liquidity, volatility or mark deviation outside research envelope';return result
    short_move=closes[-1]/closes[-6]-1
    center=mean(closes[-20:]);sd=pstdev(closes[-20:]);z=(closes[-1]-center)/sd if sd else 0
    direction='LONG' if short_move>0 else 'SHORT'
    # Scores describe relative hypotheses, not probabilities of profit.
    trend_strength=min(1,abs(drift)/max(vol*4,.001))
    score=min(1,abs(short_move)/max(cost,.0001))*.55+trend_strength*.35
    if short_move*drift<0:score*=.4
    candidates=[('momentum',direction,score,max(abs(drift),atr*2.5),'Recent momentum with multi-bar structure')]
    pull_dir='LONG' if drift>0 else 'SHORT'
    pull_score=trend_strength*.65+(.25 if short_move*drift<0 and abs(short_move)<abs(drift)*.6 else 0)
    candidates.append(('pullback',pull_dir,pull_score,max(abs(drift)*.8,atr*2),'Pullback within observed trend'))
    rev_dir='SHORT' if z>0 else 'LONG'
    rev_score=min(1,abs(z)/3)*(.85 if regime=='range' else .25)
    candidates.append(('range_reversion',rev_dir,rev_score,abs(closes[-1]-center)/closes[-1],'Deviation from local range center'))
    threshold=.35 if profile=='aggressive' else .65
    for strategy,side,score,move,evidence in candidates:
        learned=(learning or {}).get(strategy+':'+regime,{})
        adjustment=learned.get('weight',0) if learned.get('samples',0)>=5 else 0
        score=max(0,min(1,score+adjustment))
        suspended=learned.get('suspended',False)
        eligible=score>=threshold and move>cost*1.2 and not suspended
        reason='Recent loss streak suspends this strategy/regime' if suspended else 'Movement estimate below costs' if move<=cost*1.2 else 'Evidence score below profile threshold' if score<threshold else 'Eligible paper hypothesis'
        result['opportunities'].append({'strategy':strategy,'direction':side,'score':round(score,4),'estimated_move_bps':round(move*10000,3),
            'estimated_net_move_bps':round((move-cost)*10000,3),'cost_bps':round(cost*10000,3),'eligible':eligible,'research_eligible':score>=threshold and move>cost*1.2,'reason':reason,
            'learning_samples':learned.get('samples',0),'learning_adjustment':adjustment,'evidence':evidence})
    result['opportunities'].sort(key=lambda x:x['score'],reverse=True)
    chosen=next((x for x in result['opportunities'] if x['eligible']),None)
    if chosen:
        result.update(action=chosen['direction'],strategy=chosen['strategy'],reason=chosen['evidence']+' · paper experiment',evidence=result['evidence']+[chosen['evidence']])
    else:result['reason']='No eligible cost-aware hypothesis; '+result['opportunities'][0]['reason']
    return result
