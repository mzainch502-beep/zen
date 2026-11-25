// Deterministic research-only evaluator. Signals use completed candles; fills use next open.
export function replay(candles,lookback,threshold,cost=0.0015){
 if(!Number.isInteger(lookback)||lookback<2||lookback>100||!Number.isFinite(threshold)||threshold<0||!Number.isFinite(cost)||cost<0)throw Error("Invalid parameters");
 if(candles.length<lookback+3||candles.some((c,i)=>!Number.isFinite(c.open)||!Number.isFinite(c.close)||c.open<=0||c.close<=0||!Number.isFinite(c.ts)||(i&&c.ts<=candles[i-1].ts)))throw Error("Invalid candles");
 let equity=1,peak=1,drawdown=0,returns=[],wins=0,gain=0,loss=0;
 for(let i=lookback;i<candles.length-2;i++){
 const momentum=candles[i].close/candles[i-lookback].close-1;
 const side=momentum>threshold?1:momentum< -threshold?-1:0;
 if(!side)continue;
 const r=side*(candles[i+2].open/candles[i+1].open-1)-2*cost;
 equity*=Math.max(0,1+r);peak=Math.max(peak,equity);drawdown=Math.max(drawdown,1-equity/peak);
 returns.push(r);if(r>0){wins++;gain+=r}else loss-=r;
 }
 const n=returns.length,mean=n?returns.reduce((a,b)=>a+b,0)/n:0;
 const variance=n>1?returns.reduce((a,b)=>a+(b-mean)**2,0)/(n-1):0;
 return {trades:n,netReturn:equity-1,maxDrawdown:drawdown,winRate:n?wins/n:null,profitFactor:loss?gain/loss:null,expectancy:mean,unannualizedSharpe:variance?mean/Math.sqrt(variance):null};
}
export function validate(candles,parameters){
 const cut=Math.floor(candles.length*.6),mid=Math.floor(candles.length*.8);
 const slices=[candles.slice(0,cut),candles.slice(cut,mid),candles.slice(mid)];
 const metrics=slices.map(c=>replay(c,parameters.lookback,parameters.threshold));
 const stress=slices.slice(1).map(c=>replay(c,parameters.lookback,parameters.threshold,.003));
 const passes=m=>m.trades>=30&&m.netReturn>0&&m.maxDrawdown<=.1;
 return {metrics,stress,verdict:metrics.every(passes)&&stress.every(passes)?"eligible_for_review":"rejected",executionAuthorized:false};
}