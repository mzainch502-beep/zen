from typing import Protocol
from dataclasses import dataclass
from statistics import pstdev
@dataclass(frozen=True)
class Observation:
    symbol: str
    closes: tuple[float,...]
    spread_bps: float
@dataclass(frozen=True)
class Hypothesis:
    direction: str
    evidence: tuple[str,...]
    contradictions: tuple[str,...]
    calibrated_probability: float | None
    eligible: bool
class Observer(Protocol):
    async def observe(self,symbol: str)->Observation: ...
class ResearchModule(Protocol):
    def evaluate(self,observation: Observation)->Hypothesis: ...
class RegimeClassifier:
    def classify(self,o: Observation):
        if o.spread_bps>20: return 'liquidity deterioration'
        if len(o.closes)<30: return 'insufficient data'
        returns=[o.closes[i]/o.closes[i-1]-1 for i in range(1,len(o.closes))]
        recent=pstdev(returns[-10:]); previous=pstdev(returns[:-10])
        if previous and recent>previous*2: return 'volatility expansion'
        if previous and recent<previous*.5: return 'compression'
        drift=o.closes[-1]/o.closes[-20]-1
        return 'trend' if abs(drift)>recent*3 else 'range'
class TrendResearcher:
    def evaluate(self,o):
        regime=RegimeClassifier().classify(o)
        if len(o.closes)<30: return Hypothesis('WAIT',(),('Insufficient completed candles',),None,False)
        drift=o.closes[-1]/o.closes[-20]-1
        return Hypothesis('LONG' if drift>0 else 'SHORT',(f'Observed 20-bar change {drift:.5f}',f'Regime: {regime}'),
                          ('Predictive value not established','No calibrated probability'),None,False)
class StrategySelector:
    def select(self,versions): return next((v for v in versions if v.status=='paper_approved'),None)
class DecisionAgent:
    def decide(self,o,versions):
        h=TrendResearcher().evaluate(o)
        selected=StrategySelector().select(versions)
        return {'action':'WAIT','hypothesis':h.direction,'evidence':list(h.evidence),
                'contradictions':list(h.contradictions),'confidence':None,'selected_strategy':getattr(selected,'version',None),
                'reason':'No executable validated strategy in this release','version':'research-v1'}
