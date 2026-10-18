"""Cloudflare database wiring; financial data durable, replaceable quotes in RAM."""
from decimal import Decimal
from sqlalchemy import create_engine, Numeric, String
from sqlalchemy.types import TypeDecorator
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import do_dbapi

class ExactDecimal(TypeDecorator):
    impl = String
    cache_ok = True
    def process_bind_param(self, value, dialect):
        return None if value is None else format(Decimal(value), 'f')
    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)

class CloudDatabase:
    def __init__(self, storage):
        from database.models import Base, Market, FuturesMarket
        # SQLite NUMERIC affinity converts decimal strings to IEEE floats.
        # Monetary columns therefore use TEXT with explicit Decimal conversion.
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, Numeric): column.type = ExactDecimal()
        self.engine = create_engine('sqlite://', module=do_dbapi,
            creator=lambda: do_dbapi.Connection(storage), poolclass=StaticPool)
        # Durable Objects use serializable transactions; SQLite's optional
        # PRAGMA read_uncommitted is not exposed by the storage API.
        self.engine.dialect.get_isolation_level = lambda connection: 'SERIALIZABLE'
        self.engine.dialect.has_table = lambda connection, name, schema=None, **kwargs: connection.exec_driver_sql("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).first() is not None
        self.quotes = create_engine('sqlite://', poolclass=StaticPool)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False,
                                    binds={Market: self.quotes, FuturesMarket: self.quotes})
        self.cache_tables = (Market.__table__, FuturesMarket.__table__)

    def create_dev(self):
        from database.models import Base
        Base.metadata.create_all(self.engine, tables=[t for t in Base.metadata.sorted_tables if t not in self.cache_tables])
        Base.metadata.create_all(self.quotes, tables=list(self.cache_tables))
