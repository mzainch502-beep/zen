"""Futures control and ledger tables; frozen column definitions for upgrade."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    # 0001's legacy create_all may already create these on a fresh installation.
    existing=set(sa.inspect(op.get_bind()).get_table_names())
    definitions={
      'futures_config':[sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),sa.Column('workspace',sa.String(12),nullable=False),sa.Column('limits',sa.JSON(),nullable=False),sa.Column('exchange_max',sa.Boolean(),nullable=False),sa.Column('live_connection_id',sa.String(36)),sa.Column('activated',sa.Float())],
      'futures_paper_books':[sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),sa.Column('cash',sa.Numeric(28,12),nullable=False),sa.Column('initial_equity',sa.Numeric(28,12),nullable=False),sa.Column('high_water',sa.Numeric(28,12),nullable=False)],
      'futures_paper_positions':[sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('symbol',sa.String(32),nullable=False),sa.Column('data',sa.JSON(),nullable=False),sa.Column('created',sa.Float(),nullable=False),sa.UniqueConstraint('user_id','symbol')],
      'futures_market_data':[sa.Column('symbol',sa.String(32),primary_key=True),sa.Column('ticker',sa.JSON(),nullable=False),sa.Column('contract',sa.JSON(),nullable=False),sa.Column('received',sa.Float(),nullable=False)],
      'futures_order_intents':[sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('connection_id',sa.String(36),sa.ForeignKey('exchange_connections.id'),nullable=False),sa.Column('client_id',sa.String(64),nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('symbol',sa.String(32),nullable=False),sa.Column('state',sa.String(24),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('receipt',sa.JSON(),nullable=False),sa.Column('created',sa.Float(),nullable=False),sa.Column('updated',sa.Float(),nullable=False),sa.UniqueConstraint('user_id','client_id')],
      'futures_account_states':[sa.Column('connection_id',sa.String(36),sa.ForeignKey('exchange_connections.id'),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('data',sa.JSON(),nullable=False),sa.Column('received',sa.Float(),nullable=False)]}
    for name,columns in definitions.items():
        if name not in existing:op.create_table(name,*columns)
def downgrade():
    for name in ['futures_account_states','futures_order_intents','futures_market_data','futures_paper_positions','futures_paper_books','futures_config']:op.drop_table(name)
