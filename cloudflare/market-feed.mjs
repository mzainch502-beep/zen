// Public data only. Private, service-bound Worker; no keys or order methods.
const fields = {
  '/contracts': ['symbol','contractSize','volUnit','minVol','maxVol','priceUnit','maxLeverage','minLeverage','maintenanceMarginRate','initialMarginRate','takerFeeRate','makerFeeRate','apiAllowed','state','countryConfigContractMaxLeverage','riskLimitCustom','futureType','settleCoin'],
  '/tickers': ['symbol','bid1','ask1','fairPrice','lastPrice','timestamp','fundingRate','amount24','high24Price','lower24Price','riseFallRate','holdVol','volume24','indexPrice'],
};
const decimalFields = new Set(['contractSize','volUnit','minVol','maxVol','priceUnit','maintenanceMarginRate','initialMarginRate','takerFeeRate','makerFeeRate','bid1','ask1','fairPrice','lastPrice','fundingRate','amount24','high24Price','lower24Price','riseFallRate','holdVol','volume24','indexPrice','mmr','imr']);
export default {
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (request.method !== 'GET' || !fields[path]) return new Response('Not found', {status:404});
    const endpoint = path === '/contracts' ? '/api/v1/contract/detail/country' : '/api/v1/contract/ticker';
    let stage='fetch';
    try {
      const response = await fetch('https://api.mexc.com'+endpoint, {headers:{Language:'English'},signal:AbortSignal.timeout(6000),redirect:'manual'});
      if (!response.ok) {
        console.log(JSON.stringify({event:'mexc_public_rejected',endpoint,status:response.status}));
        return Response.json({error:'Public exchange request rejected',upstream_status:response.status}, {status:response.status});
      }
      stage='parse';
      const body = JSON.parse(await response.text(), (key,value,context) => {
        if (decimalFields.has(key) && typeof value === 'number') {
          if (!context?.source) throw new Error('Exact numeric parsing unavailable');
          return context.source;
        }
        return value;
      });
      if (!body.success || body.code !== 0 || !Array.isArray(body.data)) throw new Error('Exchange schema failure');
      stage='filter';
      const rows = body.data.filter(r => /^[A-Z0-9]{2,20}_USDT$/.test(r.symbol)).map(r => Object.fromEntries(fields[path].filter(k=>Object.hasOwn(r,k)).map(k=>[k,r[k]])));
      return Response.json({data:rows}, {headers:{'Cache-Control':'no-store'}});
    } catch (error) {
      console.log(JSON.stringify({event:'mexc_public_failed',endpoint,error_type:error?.name || 'Error',stage,detail:String(error?.message || '').slice(0,180)}));
      return Response.json({error:'Public exchange data unavailable'}, {status:502});
    }
  }
};
