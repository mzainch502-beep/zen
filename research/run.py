import argparse, asyncio, json, time
from dataclasses import asdict
from pathlib import Path
from exchange_adapters.ccxt_adapter import ReadAdapter, EXCHANGES
from research.evaluation import evaluate, walk_forward
async def probe(output):
    async def one(exchange):
        a=ReadAdapter(exchange)
        try:
            q=await asyncio.wait_for(a.quote('BTC/USD' if exchange=='coinbase' else 'BTC/USDT'),timeout=35)
            return {'exchange':exchange,'status':'public_quote_received','quote':q.model_dump(mode='json'),'private_execution_validated':False}
        except Exception as e: return {'exchange':exchange,'status':'unavailable','error_type':type(e).__name__,'private_execution_validated':False}
        finally: await a.close()
    rows=await asyncio.gather(*(one(x) for x in EXCHANGES))
    Path(output).write_text(json.dumps({'collected_at':time.time(),'results':rows},indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!='quote'} for r in rows],indent=2))
async def historical(exchange,symbol,output):
    a=ReadAdapter(exchange)
    try:
        rows=await asyncio.wait_for(a.candles(symbol,'5m',720),timeout=45)
        rows=[r for r in rows if r[0]/1000+300<time.time()]
        result={'source':exchange,'symbol':symbol,'timeframe':'5m','downloaded_at':time.time(),'candles':rows,
                'evaluation':asdict(evaluate(rows)),'out_of_sample_folds':walk_forward(rows),
                'interpretation':'Unoptimized research baseline; not a profitability or promotion claim'}
        Path(output).write_text(json.dumps(result,indent=2));print(json.dumps(result['evaluation'],indent=2))
    finally:await a.close()
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['probe','history']);p.add_argument('--exchange',default='kraken');p.add_argument('--symbol',default='BTC/USDT');p.add_argument('--output',required=True);args=p.parse_args()
    asyncio.run(probe(args.output) if args.command=='probe' else historical(args.exchange,args.symbol,args.output))
if __name__=='__main__':main()
