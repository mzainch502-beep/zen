import os
from alembic import context
from sqlalchemy import create_engine
from database.models import Base
config=context.config
url=os.environ['DATABASE_URL']
if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
elif url.startswith('postgresql://'): url=url.replace('postgresql://','postgresql+psycopg://',1)
if context.is_offline_mode():
    context.configure(url=url,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    with create_engine(url).connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata)
        with context.begin_transaction():context.run_migrations()
