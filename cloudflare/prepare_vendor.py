"""Retain CCXT's nine configured adapters and license; omit unused exchanges.

Workers uses Fetch for DNS and HTTP, so pycares/aiodns are intentionally
excluded for emscripten in pyproject.toml. No signing or parser code is changed.
"""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parent/'python_modules'/'ccxt'
names=['binance','bybit','okx','kraken','coinbase','bitget','kucoin','gateio','mexc']
if (root/'async_support'/'gate.py').exists():names.append('gate')
license_text=(root/'__init__.py').read_text().split('__version__')[0]
core="__version__ = '4.4.100'\nfrom ccxt.base.errors import *\nfrom ccxt.base.precise import Precise\nfrom ccxt.base.decimal_to_precision import *\n"
(root/'__init__.py').write_text(license_text+core+'from ccxt.base.exchange import Exchange\n')
(root/'async_support'/'__init__.py').write_text(license_text+core+'from ccxt.async_support.base.exchange import Exchange\n'+''.join(f'from ccxt.async_support.{n} import {n}\n' for n in names)+f'exchanges = {names!r}\n')
for folder in (root, root/'async_support', root/'abstract'):
    for file in folder.glob('*.py'):
        if file.name=='__init__.py':continue
        if folder!=root and file.stem in names:continue
        file.unlink()
if (root/'pro').exists():shutil.rmtree(root/'pro')
