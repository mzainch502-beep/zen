from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
class State(StrEnum):
    PENDING='pending'
    OPEN='open'
    PARTIAL='partial'
    FILLED='filled'
    CANCELLED='cancelled'
    UNKNOWN='unknown'
@dataclass
class OrderTracker:
    quantity: Decimal
    filled: Decimal=Decimal(0)
    state: State=State.PENDING
    def update(self,cumulative: Decimal,status: str):
        if cumulative<self.filled or cumulative>self.quantity: raise ValueError('Invalid cumulative fill')
        if self.state in {State.FILLED,State.CANCELLED} and cumulative!=self.filled:
            raise ValueError('Terminal order requires exchange reconciliation')
        self.filled=cumulative
        if cumulative==self.quantity: self.state=State.FILLED
        elif status=='cancelled': self.state=State.CANCELLED
        elif status=='unknown': self.state=State.UNKNOWN
        elif cumulative>0: self.state=State.PARTIAL
        else: self.state=State.OPEN
        return self.state
    @property
    def can_resubmit(self): return False # unknown acknowledgment must never create a second order
