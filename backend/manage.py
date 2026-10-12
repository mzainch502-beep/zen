import argparse, getpass
from database.models import Database, User, Base
from backend.security import password_hash
from backend.domain import Limits

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['init-dev','create-owner']);p.add_argument('--email');args=p.parse_args()
    db=Database()
    if args.command=='init-dev': db.create_dev();return
    if not args.email: p.error('--email required')
    password=getpass.getpass('Owner password (12+ characters): ')
    with db.sessions() as s:
        s.add(User(email=args.email.strip().lower(),password=password_hash(password),limits=Limits().model_dump(mode='json')));s.commit()
    print('Owner created; paper cash is simulated, not deposited money.')
if __name__=='__main__': main()
