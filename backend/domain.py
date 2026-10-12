from decimal import Decimal, ROUND_DOWN
from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Mode(StrEnum):
    PAPER = 'Paper'
    PAUSED = 'Paused'
    EMERGENCY = 'Emergency Stop'

class Limits(Strict):
    max_loss_trade: Decimal = Field(default=Decimal('2'), gt=0, le=20)
    max_daily_loss: Decimal = Field(default=Decimal('6'), gt=0, le=50)
    max_drawdown: Decimal = Field(default=Decimal('20'), gt=0, le=100)
    max_notional: Decimal = Field(default=Decimal('40'), gt=0, le=200)
    max_leverage: Decimal = Field(default=Decimal('1'), ge=1, le=1)
    max_positions: int = Field(default=2, ge=1, le=10)
    max_spread_bps: Decimal = Field(default=Decimal('20'), gt=0, le=100)
    max_slippage_bps: Decimal = Field(default=Decimal('10'), gt=0, le=100)
    max_order_rate: int = Field(default=6, ge=1, le=20)
    cooldown_seconds: int = Field(default=300, ge=0, le=3600)
    min_liquidation_buffer: Decimal = Field(default=Decimal('.2'), gt=0, lt=1)
    max_correlated_notional: Decimal = Field(default=Decimal('40'), gt=0, le=200)

class Quote(Strict):
    symbol: str
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)
    last: Decimal = Field(gt=0)
    timestamp: float
    source: str
    change_percent: Decimal | None = None
    @property
    def spread_bps(self):
        return (self.ask-self.bid)/self.last*10000

class Proposal(Strict):
    symbol: str
    side: str = Field(pattern='^(buy|sell)$')
    quantity: Decimal = Field(gt=0, max_digits=28, decimal_places=12)
    stop: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    reduce_only: bool = False
    idempotency_key: str = Field(min_length=16, max_length=64, pattern='^[a-zA-Z0-9_-]+$')

class Verdict(Strict):
    approved: bool
    reasons: list[str]
    estimated_cost: Decimal = Decimal(0)

class Rule(Strict):
    step: Decimal = Field(gt=0)
    min_qty: Decimal = Field(gt=0)
    min_notional: Decimal = Field(gt=0)
    def quantity(self, amount: Decimal, price: Decimal) -> Decimal:
        qty = (amount/self.step).to_integral_value(rounding=ROUND_DOWN)*self.step
        if qty < self.min_qty or qty*price < self.min_notional:
            raise ValueError('Quantity below exchange minimum')
        return qty
