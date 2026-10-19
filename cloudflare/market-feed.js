// Public data only. Private, service-bound Worker; no keys or order methods.
const fields = {
  '/contracts': ['symbol','contractSize','volUnit','minVol','maxVol','priceUnit','maxLeverage','minLeverage','maintenanceMarginRate','initialMarginRate','takerFeeRate','makerFeeRate','apiAllowed','state','countryConfigContractMaxLeverage','riskLimitCustom','futureType','settleCoin'],
  '/tickers': ['symbol','bid1','ask1','fairPrice','lastPrice','timestamp','fundingRate','amount24','high24Price','lower24Price','riseFallRate','holdVol','volume24','indexPrice'],
};
export default {
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (request.method !== 'GET' || !fields[path]) return new Response('Not found', {status:404});
    const endpoint = path === '/contracts' ? '/api/v1/contract/detail/country' : '/api/v1/contract/ticker';
    try {
      const response = await fetch('https://api.mexc.com'+endpoint, {headers:{Language:'English'},signal:AbortSignal.timeout(6000),redirect:'error'});
      if (!response.ok) throw new Error('Exchange HTTP failure');
      const body = await response.json();
      if (!body.success || body.code !== 0 || !Array.isArray(body.data)) throw new Error('Exchange schema failure');
      const rows = body.data.filter(r => /^[A-Z0-9]{2,20}_USDT$/.test(r.symbol)).map(r => Object.fromEntries(fields[path].filter(k=>Object.hasOwn(r,k)).map(k=>[k,r[k]])));
      return Response.json({data:rows}, {headers:{'Cache-Control':'no-store'}});
    } catch {
      return Response.json({error:'Public exchange data unavailable'}, {status:502});
    }
  }
};
