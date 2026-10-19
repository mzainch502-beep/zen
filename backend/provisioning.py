"""Explicit fresh-install paper preset; never alters an existing workspace."""
from decimal import Decimal
from backend.futures_domain import FuturesLimits
from database.models import FuturesConfig, FuturesPaperBook, record

def fresh_paper_workspace(db, user):
    if db.get(FuturesConfig,user.id) or db.get(FuturesPaperBook,user.id):
        raise ValueError('Fresh provisioning cannot overwrite existing books')
    user.cash=user.initial_equity=user.high_water=Decimal('50')
    user.mode='Paper'
    user.limits={**user.limits,'automatic':True}
    limits=FuturesLimits(profile='aggressive',max_leverage=5,max_margin=3,
        max_notional=80,max_positions=3,max_slippage_bps=5,
        max_loss_trade=2,max_daily_loss=6,max_drawdown=20,automatic=True)
    db.add(FuturesConfig(user_id=user.id,workspace='combined',limits=limits.model_dump(mode='json'),exchange_max=False))
    db.add(FuturesPaperBook(user_id=user.id,cash=Decimal('150'),initial_equity=Decimal('150'),high_water=Decimal('150')))
    record(db,user.id,'fresh_paper_workspace',{'simulated_capital':'200','spot':'50','futures':'150','profile':'aggressive','live':False})
