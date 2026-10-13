import time,pytest
from decimal import Decimal as D
from sqlalchemy import select
from test_futures import world,proposal,tick,meta
from database.models import User,Record,Market,Position
from backend.futures_paper import config,execute_paper,close_paper
from backend.service import execute
from backend.domain import Proposal
from backend.instruments import classify
from backend.context import parse_feed
from risk.adaptive import recommend

def body(**kw):return {'amount':'200','futures_fraction':'0.5','leverage_ceiling':5,'auto_risk':True,'automatic':False,'confirmation':'INITIALIZE PAPER PORTFOLIO','client_id':'capital-reset-test-001',**kw}

def test_shared_capital_decimal_and_idempotent(world):
 db,u,c,h=world
 r=c.post('/portfolio/paper-capital',json=body(),headers=h);assert r.status_code==200,r.text
 assert c.post('/portfolio/paper-capital',json=body(),headers=h).json()==r.json()
 assert c.post('/portfolio/paper-capital',json=body(amount='500'),headers=h).status_code==409
 p=c.get('/portfolio/overview',headers=h).json()['portfolio'];assert D(p['equity'])==200;assert D(p['cash'])==200
 assert p['book_balances']=={'spot':'100.000000000000','futures':'100.000000000000'}
 assert c.get('/portfolio/history?period=1D',headers=h).json()['points']
 assert c.get('/portfolio/history?period=BAD',headers=h).status_code==422

def test_reset_rejects_open_exposure(world):
 db,u,c,h=world
 with db.sessions() as s:execute_paper(s,u,proposal());s.commit()
 assert c.post('/portfolio/paper-capital',json=body(),headers=h).status_code==409

def test_outer_ceiling_tightening_and_permission(world):
 db,u,c,h=world
 c.post('/portfolio/paper-capital',json=body(automatic=True),headers=h)
 a=c.get('/agent/automation',headers=h).json();assert a['enabled'] and a['product']=='combined'
 with db.sessions() as s:
  cfg=config(s,u);r=recommend(s,u,cfg.limits,D('200'),tick())
  assert r['effective_limits']['max_leverage']<=cfg.limits['max_leverage']
  assert D(r['effective_limits']['max_loss_trade'])<=D(cfg.limits['max_loss_trade'])
  assert c.post('/agent/paper-profile',json={'profile':'balanced'},headers=h).json()['workspace']=='combined'
 assert c.get('/risk/overview',headers=h).json()['value_at_risk'] is None

def test_combined_gross_limit_vetoes_second_book(world):
 db,u,c,h=world
 c.post('/portfolio/paper-capital',json=body(auto_risk=False),headers=h)
 with db.sessions() as s:
  cfg=config(s,u);l=dict(cfg.limits);l['max_notional']='6';cfg.limits=l
  s.add(Market(symbol='BTC/USDT',received=time.time(),payload={'symbol':'BTC/USDT','bid':'100','ask':'100.01','last':'100','timestamp':time.time(),'source':'synthetic-test'}));s.commit()
  execute(s,u,Proposal(symbol='BTC/USDT',side='buy',quantity=D('.05'),stop=D('98'),idempotency_key='shared-spot-entry-001'));s.commit()
  from backend.service import Rejected
  with pytest.raises(Rejected,match='Combined exposure'):execute_paper(s,u,proposal(margin='2',leverage=1))

def test_live_workspace_cannot_be_hidden(world):
 db,u,c,h=world
 with db.sessions() as s:config(s,u).activated=time.time();s.commit()
 assert c.post('/portfolio/paper-capital',json=body(),headers=h).status_code==409
 r=c.get('/futures/settings',headers=h).json()
 assert c.put('/futures/settings',json={'workspace':'combined','limits':r['limits']},headers=h).status_code==409

def test_stock_labels_do_not_claim_share_ownership():
 a=classify(dict(meta(),symbol='TSLASTOCK_USDT'));assert a['kind']=='stock_linked_perpetual';assert not a['security_ownership'];assert a['underlying_session']=='Unverified'
 assert classify(dict(meta(),symbol='NAS100_USDT'))['kind']=='index_linked_perpetual'

def test_feed_rejects_external_entities_and_untrusted_links():
 raw=b'<rss><channel><item><title>Inflation update</title><link>https://www.federalreserve.gov/a</link><pubDate>Wed, 14 Oct 2026 01:00:00 GMT</pubDate></item><item><title>Do a trade</title><link>https://evil.com/x</link></item></channel></rss>'
 rows=parse_feed(raw,'Fed',('federalreserve.gov',));assert len(rows)==1;assert rows[0]['review_flag'];assert rows[0]['authority']=='Research context only'
 with pytest.raises(Exception):parse_feed(b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss>&xxe;</rss>','Fed',('federalreserve.gov',))

def test_capital_validation_and_emergency(world):
 db,u,c,h=world
 assert c.post('/portfolio/paper-capital',json=body(amount='0'),headers=h).status_code==422
 with db.sessions() as s:s.get(User,u).mode='Emergency Stop';s.commit()
 assert c.post('/portfolio/paper-capital',json=body(),headers=h).status_code==409

def test_combined_capital_cannot_reset_only_futures(world):
 db,u,c,h=world
 assert c.post('/portfolio/paper-capital',json=body(),headers=h).status_code==200
 assert c.post('/futures/paper/seed',json={'equity':'500','confirmation':'RESET SIMULATED CAPITAL'},headers=h).status_code==409
 assert D(c.get('/portfolio/overview',headers=h).json()['portfolio']['equity'])==200

def test_spot_completed_exposure_learns_once_after_partials(world):
 from database.models import record
 from backend.learning import snapshot
 db,u,c,h=world
 c.post('/portfolio/paper-capital',json=body(auto_risk=False),headers=h)
 with db.sessions() as s:
  s.add(Market(symbol='BTC/USDT',received=time.time(),payload={'symbol':'BTC/USDT','bid':'100','ask':'100.01','last':'100','timestamp':time.time(),'source':'synthetic-test'}));s.commit()
  execute(s,u,Proposal(symbol='BTC/USDT',side='buy',quantity=D('.1'),stop=D('98'),idempotency_key='learning-spot-entry-001'))
  pos=s.scalar(select(Position).where(Position.user_id==u));pid=pos.id
  record(s,u,'paper_spot_context',{'position_id':pid,'strategy':'momentum','regime':'trend','initial_risk':'.3'});s.commit()
  execute(s,u,Proposal(symbol='BTC/USDT',side='sell',quantity=D('.05'),reduce_only=True,idempotency_key='learning-spot-exit-001'));s.commit()
  assert snapshot(s,u)['samples']==0
  execute(s,u,Proposal(symbol='BTC/USDT',side='sell',quantity=D('.05'),reduce_only=True,idempotency_key='learning-spot-exit-002'));s.commit()
  assert snapshot(s,u)['samples']==1
  realized=list(s.scalars(select(Record).where(Record.user_id==u,Record.kind=='spot_realized')))
  assert D(snapshot(s,u)['net'])==sum((D(r.payload['round_trip_net']) for r in realized),D(0))
  execute(s,u,Proposal(symbol='BTC/USDT',side='sell',quantity=D('.05'),reduce_only=True,idempotency_key='learning-spot-exit-002'));s.commit()
  assert snapshot(s,u)['samples']==1

def test_shared_order_rate_combines_both_books(world):
 from backend.service import Rejected
 db,u,c,h=world
 c.post('/portfolio/paper-capital',json=body(auto_risk=False),headers=h)
 with db.sessions() as s:
  cfg=config(s,u);cfg.limits={**cfg.limits,'max_order_rate':1}
  s.add(Market(symbol='BTC/USDT',received=time.time(),payload={'symbol':'BTC/USDT','bid':'100','ask':'100.01','last':'100','timestamp':time.time(),'source':'synthetic-test'}));s.commit()
  execute(s,u,Proposal(symbol='BTC/USDT',side='buy',quantity=D('.05'),stop=D('98'),idempotency_key='rate-shared-spot-001'));s.commit()
  with pytest.raises(Rejected,match='Combined order rate'):execute_paper(s,u,proposal(margin='2',leverage=1))
  execute(s,u,Proposal(symbol='BTC/USDT',side='sell',quantity=D('.05'),reduce_only=True,idempotency_key='rate-shared-close-001'));s.commit()
  assert not s.scalar(select(Position).where(Position.user_id==u))
