import assert from 'node:assert/strict';
import feed from '../market-feed.mjs';
const original=globalThis.fetch;
try {
  globalThis.fetch=async(url,options)=>{assert.equal(options.redirect,'manual');return Response.json({success:true,code:0,data:[{symbol:'BTC_USDT',contractSize:'.001',maxLeverage:500,apiAllowed:true,unneeded:'large metadata'},{symbol:'BTC_USDC'}]});};
  let response=await feed.fetch(new Request('https://service/contracts'));
  let body=await response.json();
  assert.deepEqual(body.data,[{symbol:'BTC_USDT',contractSize:'.001',maxLeverage:500,apiAllowed:true}]);
  globalThis.fetch=async()=>new Response('{"success":true,"code":0,"data":[{"symbol":"BTC_USDT","bid1":123.123456789123456789}]}');
  body=await (await feed.fetch(new Request('https://service/tickers'))).json();
  assert.equal(body.data[0].bid1,'123.123456789123456789');
  assert.equal((await feed.fetch(new Request('https://service/private'))).status,404);
  assert.equal((await feed.fetch(new Request('https://service/contracts',{method:'POST'}))).status,404);
  globalThis.fetch=async()=>new Response('Forbidden',{status:403});
  const denied=await feed.fetch(new Request('https://service/contracts'));
  assert.equal(denied.status,403);
  assert.equal((await denied.json()).upstream_status,403);
  globalThis.fetch=async()=>Response.json({success:false,code:500});
  assert.equal((await feed.fetch(new Request('https://service/tickers'))).status,502);
  console.log('PASS: compact public feed filters metadata, rejects private/mutating paths and exchange errors');
} finally {globalThis.fetch=original;}
