"""Actual HTTP calls to workerd; all market prices here are test fixtures."""
import json, time, urllib.request, urllib.error, uuid
from decimal import Decimal
base='http://127.0.0.1:8800'
token=''
checks=[]
def call(path,method='GET',body=None,expected=200,authenticated=True):
    headers={'Content-Type':'application/json'}
    if token and authenticated: headers['Authorization']='Bearer '+token
    request=urllib.request.Request(base+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(request,timeout=90) as response: status=response.status;raw=response.read()
    except urllib.error.HTTPError as error:status=error.code;raw=error.read()
    assert status==expected,(path,status,raw.decode()[:1500])
    return json.loads(raw)

assert call('/health')['status']=='ok'
with urllib.request.urlopen(base+'/cdn-cgi/local/scheduled',timeout=90) as response:
    assert response.status==200
for _ in range(20):
    if call('/fixturemanifest').get('alarm_ran'): break
    time.sleep(.5)
else: raise AssertionError('Fresh activation did not start production alarm handler')
checks.append('production scheduled handler, fresh activation and alarm invocation')
call('/snapshot',expected=401,authenticated=False)
call('/auth/setup','POST',{'email':'runtime@test.invalid','password':'ci-password-long-enough','setup_token':'ci-bootstrap-fixture-not-a-production-secret'})
token=call('/auth/login','POST',{'email':'runtime@test.invalid','password':'ci-password-long-enough'})['token']
checks.append('owner login and authorization')
assert Decimal(call('/snapshot')['portfolio']['equity'])==Decimal('200')
settings=call('/futures/settings')
assert settings['workspace']=='combined' and settings['limits']['automatic']
assert settings['limits']['max_leverage']==5 and not settings['activated']
checks.append('fresh combined paper capital is 200 total, aggressive automatic preset, live disabled')
call('/fixturequotes','POST',{})
assert Decimal(call('/snapshot')['portfolio']['equity'])==Decimal('3')
proposal={'symbol':'BTC_USDT','direction':'SHORT','margin':'1','leverage':10,'stop':'102','take_profit':'96','idempotency_key':uuid.uuid4().hex}
position=call('/futures/paper/orders','POST',proposal)['position_id']
assert call('/futures/paper/orders','POST',proposal)['position_id']==position
call('/futures/paper/orders','POST',{**proposal,'margin':'2'},expected=409)
checks.append('paper SHORT and duplicate prevention')
call('/agent/mode','POST',{'mode':'Emergency Stop'})
call('/futures/paper/orders','POST',{**proposal,'idempotency_key':uuid.uuid4().hex},expected=409)
call('/futures/positions/'+position+'/close','POST',{'fraction':'1','idempotency_key':uuid.uuid4().hex})
assert call('/snapshot')['positions']==[]
checks.append('emergency stop with reducing exits permitted')
# Repeated mobile snapshot polling must retain auth and ledger consistency.
for _ in range(30):
    assert call('/snapshot')['positions']==[]
    assert isinstance(call('/markets'),list)
    assert call('/health')['futures_catalogue_count']>=1
checks.append('30 repeated snapshot/markets/health refresh cycles')
call('/auth/logout','POST',{})
call('/snapshot',expected=401)
checks.append('session revocation')
print(json.dumps({'runtime':'Cloudflare workerd','market_data':'test fixtures only','passed':checks},indent=2))

# Separate Durable Object: verify authenticated ledger import and replay checks.
import hashlib
base += '/importcheck'
token=''
manifest=call('/fixturemanifest')
counts={name:0 for name in manifest['tables']};counts['users']=1
mid=uuid.uuid4().hex
call('/migration/begin','POST',{'id':mid,'tables':counts},expected=401)
token='ci-migration-fixture-not-a-production-secret'
call('/migration/begin','POST',{'id':mid,'tables':counts})
call('/migration/activate','POST',{'id':mid,'source_execution_stopped':True},expected=409)
rows=[{'id':str(uuid.uuid4()),'email':'import@test.invalid','password':'not-a-login-hash',
       'cash':'123.123456789123','initial_equity':'200','high_water':'200','mode':'Paused','limits':{},'created':1.0}]
batch={'id':mid,'batch':0,'table':'users','rows':rows}
reply=call('/migration/chunk','POST',batch)
assert call('/migration/chunk','POST',batch)['replayed']
call('/migration/chunk','POST',{**batch,'table':'audit_events'},expected=409)
call('/migration/finish','POST',{'id':mid,'chain':'wrong'},expected=409)
assert call('/migration/finish','POST',{'id':mid,'chain':reply['chain']})['verified']
assert call('/fixturemanifest')['cash']=='123.123456789123'
call('/migration/activate','POST',{'id':mid,'source_execution_stopped':False},expected=409)
print('PASS: authenticated import, exact decimals, replay conflict, hash verification and activation guard')
