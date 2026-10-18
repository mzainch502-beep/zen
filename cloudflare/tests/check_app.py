"""Actual HTTP calls to workerd; all market prices here are test fixtures."""
import json, urllib.request, urllib.error, uuid
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
call('/snapshot',expected=401,authenticated=False)
call('/auth/setup','POST',{'email':'runtime@test.invalid','password':'ci-password-long-enough','setup_token':'ci-bootstrap-fixture-not-a-production-secret'})
token=call('/auth/login','POST',{'email':'runtime@test.invalid','password':'ci-password-long-enough'})['token']
checks.append('owner login and authorization')
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
call('/auth/logout','POST',{})
call('/snapshot',expected=401)
checks.append('session revocation')
print(json.dumps({'runtime':'Cloudflare workerd','market_data':'test fixtures only','passed':checks},indent=2))
