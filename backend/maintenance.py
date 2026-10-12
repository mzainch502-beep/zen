"""Hosting-admin maintenance for explicitly disposable deployment-verification accounts.

Not exposed over HTTP. The owner setup token cannot invoke this command.
"""
import argparse
from sqlalchemy import select, delete
from database.models import Database, User, Session, Connection, Order, Position, Record

def purge_deployment_fixture(email: str):
    if not email.endswith('@deployment-test.invalid') or not email.startswith('qa-'):
        raise ValueError('Refusing to remove a non-fixture account')
    db=Database()
    with db.sessions() as s:
        u=s.scalar(select(User).where(User.email==email).with_for_update())
        if not u: return False
        for model in [Session,Connection,Order,Position,Record]:
            s.execute(delete(model).where(model.user_id==u.id))
        s.delete(u);s.commit()
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['purge-deployment-fixture']);p.add_argument('--email',required=True)
    args=p.parse_args();print('Disposable fixture removed:',purge_deployment_fixture(args.email))
if __name__=='__main__':main()
