"""Native MEXC Futures Open-API. No WEB tokens, API bypass or withdrawals.

Private order acceptance is NOT certified without owner account validation.
"""
import hashlib,hmac,json,time,re
from decimal import Decimal
from urllib.parse import urlencode
import httpx

class ExchangeFailure(RuntimeError): pass
class UnknownSubmission(ExchangeFailure): pass

def decimal_json(value):
    if isinstance(value,Decimal):
        if not value.is_finite():raise ValueError('Nonfinite decimal')
        return format(value,'f')
    if isinstance(value,dict):return '{'+','.join(json.dumps(k)+':'+decimal_json(v) for k,v in value.items())+'}'
    if isinstance(value,list):return '['+','.join(decimal_json(v) for v in value)+']'
    return json.dumps(value,separators=(',',':'),allow_nan=False)

def signature(key,secret,timestamp,params):
    return hmac.new(secret.encode(),(key+str(timestamp)+params).encode(),hashlib.sha256).hexdigest()

def valid_symbol(symbol):
    if not re.fullmatch(r'[A-Z0-9]{2,20}_USDT',symbol):raise ValueError('Only linear USDT perpetual symbols supported')
    return symbol

class MexcFutures:
    def __init__(self,key='',secret='',transport=None):
        self.key=key;self.secret=secret;self.offset=0;self.synced=0
        self.client=httpx.AsyncClient(base_url='https://api.mexc.com',timeout=10,transport=transport,follow_redirects=False)
    async def close(self):await self.client.aclose()
    async def request(self,method,path,params=None,private=False):
        params={k:v for k,v in (params or {}).items() if v is not None}
        query=urlencode(sorted(params.items())) if method=='GET' else ''
        body=decimal_json(params) if method!='GET' else ''
        headers={'Language':'English'}
        if private:
            if not self.key or not self.secret:raise ExchangeFailure('Futures credentials required')
            if time.time()-self.synced>60:await self.sync_clock()
            ts=int(time.time()*1000+self.offset)
            headers.update({'ApiKey':self.key,'Request-Time':str(ts),'Recv-Window':'10',
                            'Signature':signature(self.key,self.secret,ts,query if method=='GET' else body)})
        if body:headers['Content-Type']='application/json'
        try:
            response=await self.client.request(method,path+('?' + query if query else ''),content=body or None,headers=headers)
            if response.status_code>=500 and method!='GET':raise UnknownSubmission('Exchange response ambiguous; reconcile by client ID')
            response.raise_for_status()
            data=json.loads(response.text,parse_float=Decimal)
        except (httpx.TransportError,httpx.HTTPStatusError,ValueError) as e:
            if method!='GET':raise UnknownSubmission('Submission status unknown; no automatic resubmit') from e
            raise ExchangeFailure('Exchange read unavailable') from e
        if not data.get('success') or data.get('code')!=0:raise ExchangeFailure('Exchange rejected request; code '+str(data.get('code')))
        return data['data']
    async def sync_clock(self):
        start=time.time()*1000
        remote=await self.request('GET','/api/v1/contract/ping')
        self.offset=int(remote)-(start+time.time()*1000)/2
        self.synced=time.time()
        if abs(self.offset)>30000:raise ExchangeFailure('Clock offset outside operational envelope')
    async def contracts(self,symbol=None):
        data=await self.request('GET','/api/v1/contract/detail/country',{'symbol':valid_symbol(symbol)} if symbol else {})
        rows=data if isinstance(data,list) else [data]
        if symbol:
            rows=[row for row in rows if row.get("symbol")==symbol]
            if not rows:raise ExchangeFailure("Requested contract missing from metadata")
        return rows
    async def ticker(self,symbol):
        data=await self.request('GET','/api/v1/contract/ticker',{'symbol':valid_symbol(symbol)})
        if isinstance(data,list):
            matches=[row for row in data if row.get('symbol')==symbol]
            if not matches:raise ExchangeFailure('Requested ticker missing')
            data=matches[0]
        if data.get('symbol')!=symbol:raise ExchangeFailure('Ticker symbol mismatch')
        if min(Decimal(str(data[k])) for k in ['bid1','ask1','fairPrice','lastPrice'])<=0 or Decimal(str(data['ask1']))<Decimal(str(data['bid1'])):raise ExchangeFailure('Invalid futures ticker prices')
        if not -5<=time.time()-int(data['timestamp'])/1000<=15:raise ExchangeFailure('Stale/future futures ticker')
        return data
    async def depth(self,symbol):
        data=await self.request('GET','/api/v1/contract/depth/'+valid_symbol(symbol),{'limit':20})
        return json_safe({'symbol':symbol,'source':'mexc-futures','received_at':time.time(),'bids':data['bids'],'asks':data['asks'],'timestamp':data.get('timestamp')})
    async def candles(self,symbol,timeframe='1m',limit=100):
        intervals={'1m':'Min1','5m':'Min5','15m':'Min15','30m':'Min30','1h':'Min60','4h':'Hour4','1d':'Day1'}
        if timeframe not in intervals:raise ValueError('Timeframe unsupported by MEXC futures')
        data=await self.request('GET','/api/v1/contract/kline/'+valid_symbol(symbol),{'interval':intervals[timeframe]})
        keys=['time','open','high','low','close','vol']
        if len({len(data[k]) for k in keys})!=1:raise ExchangeFailure('Malformed OHLCV arrays')
        return [[int(data['time'][i])*1000,*[float(data[k][i]) for k in keys[1:]]] for i in range(max(0,len(data['time'])-limit),len(data['time']))]
    async def assets(self):return await self.request('GET','/api/v1/private/account/assets',private=True)
    async def positions(self):return await self.request('GET','/api/v1/private/position/open_positions',private=True)
    async def position_mode(self):
        data=await self.request('GET','/api/v1/private/position/position_mode',private=True)
        mode=data.get('positionMode') if isinstance(data,dict) else data if isinstance(data,int) else None
        if mode not in [1,2]:raise ExchangeFailure('Unrecognized account position mode')
        return mode
    async def fees(self,symbol):return await self.request('GET','/api/v1/private/account/tiered_fee_rate/v2',{'symbol':valid_symbol(symbol)},private=True)
    async def risk_limits(self,symbol):return await self.request('GET','/api/v1/private/account/risk_limit',{'symbol':valid_symbol(symbol)},private=True)
    async def submit(self,payload):return await self.request('POST','/api/v1/private/order/create',payload,private=True)
    async def order(self,symbol,client_id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{16,64}',client_id):raise ValueError('Invalid client ID')
        return await self.request('GET','/api/v1/private/order/external/'+valid_symbol(symbol)+'/'+client_id,private=True)
    async def cancel(self,symbol,client_id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{16,64}',client_id):raise ValueError('Invalid client ID')
        return await self.request('POST','/api/v1/private/order/cancel_with_external',{'symbol':valid_symbol(symbol),'externalOid':client_id},private=True)

def json_safe(value):
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [json_safe(v) for v in value]
    return value
