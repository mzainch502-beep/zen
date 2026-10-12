import os, time, uuid
from decimal import Decimal
from sqlalchemy import create_engine, String, Numeric, Float, JSON, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def uid(): return str(uuid.uuid4())
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(254),unique=True)
    password: Mapped[str]=mapped_column(Text)
    mode: Mapped[str]=mapped_column(String(24),default='Paused')
    cash: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
    initial_equity: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
    high_water: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
    limits: Mapped[dict]=mapped_column(JSON,default=dict)
    created: Mapped[float]=mapped_column(Float,default=time.time)
class Session(Base):
    __tablename__='sessions'
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    expires: Mapped[float]=mapped_column(Float)
class Connection(Base):
    __tablename__='exchange_connections'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    exchange: Mapped[str]=mapped_column(String(32))
    ciphertext: Mapped[str]=mapped_column(Text)
    capabilities: Mapped[dict]=mapped_column(JSON)
    created: Mapped[float]=mapped_column(Float,default=time.time)
class Order(Base):
    __tablename__='orders'
    __table_args__=(UniqueConstraint('user_id','client_id'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    client_id: Mapped[str]=mapped_column(String(64))
    fingerprint: Mapped[str]=mapped_column(String(64))
    symbol: Mapped[str]=mapped_column(String(64))
    side: Mapped[str]=mapped_column(String(8))
    quantity: Mapped[Decimal]=mapped_column(Numeric(28,12))
    filled: Mapped[Decimal]=mapped_column(Numeric(28,12),default=0)
    price: Mapped[Decimal]=mapped_column(Numeric(28,12),default=0)
    fee: Mapped[Decimal]=mapped_column(Numeric(28,12),default=0)
    realized: Mapped[Decimal]=mapped_column(Numeric(28,12),default=0)
    state: Mapped[str]=mapped_column(String(24))
    created: Mapped[float]=mapped_column(Float,default=time.time)
class Position(Base):
    __tablename__='positions'
    __table_args__=(UniqueConstraint('user_id','symbol'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    symbol: Mapped[str]=mapped_column(String(64))
    quantity: Mapped[Decimal]=mapped_column(Numeric(28,12))
    entry: Mapped[Decimal]=mapped_column(Numeric(28,12))
    entry_fees: Mapped[Decimal]=mapped_column(Numeric(28,12),default=0)
    stop: Mapped[Decimal | None]=mapped_column(Numeric(28,12),nullable=True)
    take_profit: Mapped[Decimal | None]=mapped_column(Numeric(28,12),nullable=True)
class Record(Base):
    """Append-only paper ledger. Typed payloads are versioned; includes fills/fees/decisions."""
    __tablename__='audit_events'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str | None]=mapped_column(ForeignKey('users.id'),nullable=True,index=True)
    kind: Mapped[str]=mapped_column(String(48),index=True)
    payload: Mapped[dict]=mapped_column(JSON)
    created: Mapped[float]=mapped_column(Float,default=time.time,index=True)
class Market(Base):
    __tablename__='market_quotes'
    symbol: Mapped[str]=mapped_column(String(64),primary_key=True)
    payload: Mapped[dict]=mapped_column(JSON)
    received: Mapped[float]=mapped_column(Float)
class Strategy(Base):
    __tablename__='model_versions'
    version: Mapped[str]=mapped_column(String(64),primary_key=True)
    status: Mapped[str]=mapped_column(String(24),default='research')
    evidence: Mapped[dict]=mapped_column(JSON)

class Database:
    def __init__(self,url=None):
        url=url or os.getenv('DATABASE_URL','sqlite:///zen-dev.db')
        if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
        elif url.startswith('postgresql://'): url=url.replace('postgresql://','postgresql+psycopg://',1)
        kw={'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'pool_pre_ping':True}
        self.engine=create_engine(url,**kw)
        self.sessions=sessionmaker(self.engine,expire_on_commit=False)
    def create_dev(self): Base.metadata.create_all(self.engine)

def record(db,user_id,kind,payload):
    db.add(Record(user_id=user_id,kind=kind,payload={'schema_version':1,**payload}))

class FuturesConfig(Base):
    __tablename__='futures_config'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    workspace: Mapped[str]=mapped_column(String(12),default='spot')
    limits: Mapped[dict]=mapped_column(JSON,default=dict)
    exchange_max: Mapped[bool]=mapped_column(default=False)
    live_connection_id: Mapped[str | None]=mapped_column(String(36),nullable=True)
    activated: Mapped[float | None]=mapped_column(Float,nullable=True)
class FuturesPaperBook(Base):
    __tablename__='futures_paper_books'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    cash: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
    initial_equity: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
    high_water: Mapped[Decimal]=mapped_column(Numeric(28,12),default=Decimal('200'))
class FuturesPaperPosition(Base):
    __tablename__='futures_paper_positions'
    __table_args__=(UniqueConstraint('user_id','symbol'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    symbol: Mapped[str]=mapped_column(String(32))
    data: Mapped[dict]=mapped_column(JSON)
    created: Mapped[float]=mapped_column(Float,default=time.time)
class FuturesMarket(Base):
    __tablename__='futures_market_data'
    symbol: Mapped[str]=mapped_column(String(32),primary_key=True)
    ticker: Mapped[dict]=mapped_column(JSON)
    contract: Mapped[dict]=mapped_column(JSON)
    received: Mapped[float]=mapped_column(Float)
class FuturesIntent(Base):
    __tablename__='futures_order_intents'
    __table_args__=(UniqueConstraint('user_id','client_id'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    connection_id: Mapped[str]=mapped_column(ForeignKey('exchange_connections.id'))
    client_id: Mapped[str]=mapped_column(String(64))
    fingerprint: Mapped[str]=mapped_column(String(64))
    symbol: Mapped[str]=mapped_column(String(32))
    state: Mapped[str]=mapped_column(String(24),default='pending')
    payload: Mapped[dict]=mapped_column(JSON)
    receipt: Mapped[dict]=mapped_column(JSON,default=dict)
    created: Mapped[float]=mapped_column(Float,default=time.time)
    updated: Mapped[float]=mapped_column(Float,default=time.time)
class FuturesAccount(Base):
    __tablename__='futures_account_states'
    connection_id: Mapped[str]=mapped_column(ForeignKey('exchange_connections.id'),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    data: Mapped[dict]=mapped_column(JSON)
    received: Mapped[float]=mapped_column(Float)
