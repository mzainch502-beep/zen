"""Contract identity is distinct from ownership of an underlying security."""
def classify(meta):
    symbol=meta.get('symbol','');base=symbol.split('_')[0]
    text=' '.join(str(meta.get(k,'')) for k in ['displayNameEn','baseCoinName'])
    stock=base.endswith('STOCK') or 'STOCK FUTURE' in text.upper()
    index=base in {'NAS100','SP500','US30'}
    return {'kind':'index_linked_perpetual' if index else 'stock_linked_perpetual' if stock else 'crypto_perpetual',
            'name':meta.get('displayNameEn') or symbol,'basis':'exchange symbol/display metadata',
            'security_ownership':False,'underlying_session':'Unverified' if stock or index else 'Crypto market',
            'corporate_action_rules':'Unverified' if stock or index else 'Not applicable',
            'notice':'Derivative exposure; no direct shares, voting or dividend ownership. Verify venue contract terms.' if stock or index else 'USDT-settled perpetual derivative'}
