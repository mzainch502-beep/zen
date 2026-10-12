import os,subprocess
from sqlalchemy import text,inspect
from database.models import Database,Base

def test_upgrade_existing_0001_preserves_owner_tables(tmp_path):
    url='sqlite:///'+str(tmp_path/'upgrade.db');db=Database(url)
    legacy=[t for t in Base.metadata.sorted_tables if not t.name.startswith('futures_')]
    Base.metadata.create_all(db.engine,tables=legacy)
    with db.engine.begin() as c:
        c.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)'))
        c.execute(text("INSERT INTO alembic_version VALUES ('0001')"))
    run=subprocess.run(['python','-m','alembic','-c','database/alembic.ini','upgrade','head'],env={**os.environ,'DATABASE_URL':url},capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    names=set(inspect(db.engine).get_table_names())
    assert 'users' in names and 'orders' in names
    assert {'futures_config','futures_paper_books','futures_paper_positions','futures_order_intents','futures_account_states','futures_market_data'}<=names
