"""Opt-in real public quote → simulated trade → simulated reduction → fee ledger smoke test."""
import asyncio, json, time, uuid
from decimal import Decimal
from pathlib import Path
from database.models import Database, User, Market
from backend.domain import Limits, Proposal
from backend.security import password_hash
from backend.service import execute, portfolio
from exchange_adapters.ccxt_adapter import ReadAdapter
async def main():
    a=ReadAdapter('bitget')
    try:q=await a.quote('BTC/USDT')
    finally:await a.close()
    db=Database('sqlite://');db.create_dev()
    with db.sessions() as s:
        u=User(email=str(uuid.uuid4())+'@test.invalid',password=password_hash(str(uuid.uuid4())),mode='Paper',limits=Limits().model_dump(mode='json'))
        s.add(u);s.merge(Market(symbol=q.symbol,payload=q.model_dump(mode='json'),received=time.time()));s.commit()
        quantity=(Decimal('10')/q.ask).quantize(Decimal('.00000001'))
        buy=execute(s,u.id,Proposal(symbol=q.symbol,side='buy',quantity=quantity,stop=q.ask*Decimal('.995'),idempotency_key=str(uuid.uuid4())));s.commit()
        sell=execute(s,u.id,Proposal(symbol=q.symbol,side='sell',quantity=quantity,reduce_only=True,idempotency_key=str(uuid.uuid4())));s.commit()
        result={'test':'real-quote-paper-ledger','exchange':'bitget','quote':q.model_dump(mode='json'),
                'buy':{'price':str(buy.price),'fee':str(buy.fee)},'sell':{'price':str(sell.price),'fee':str(sell.fee)},
                'portfolio':portfolio(s,u),'real_exchange_orders_sent':0}
        Path('docs/paper-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['portfolio'],indent=2))
if __name__=='__main__':asyncio.run(main())
