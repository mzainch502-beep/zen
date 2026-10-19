import assert from 'node:assert/strict';
import feed from '../market-feed.js';
const original=globalThis.fetch;
try {
  globalThis.fetch=async()=>Response.json({success:true,code:0,data:[{symbol:'BTC_USDT',contractSize:'.001',maxLeverage:500,apiAllowed:true,unneeded:'large metadata'},{symbol:'BTC_USDC'}]});
  let response=await feed.fetch(new Request('https://service/contracts'));
  let body=await response.json();
  assert.deepEqual(body.data,[{symbol:'BTC_USDT',contractSize:'.001',maxLeverage:500,apiAllowed:true}]);
  assert.equal((await feed.fetch(new Request('https://service/private'))).status,404);
  assert.equal((await feed.fetch(new Request('https://service/contracts',{method:'POST'}))).status,404);
  globalThis.fetch=async()=>Response.json({success:false,code:500});
  assert.equal((await feed.fetch(new Request('https://service/tickers'))).status,502);
  console.log('PASS: compact public feed filters metadata, rejects private/mutating paths and exchange errors');
} finally {globalThis.fetch=original;}
