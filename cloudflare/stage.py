"""Stage only application Python source, never local credentials or databases."""
from pathlib import Path
import shutil
root = Path(__file__).resolve().parent.parent
output = root / 'cloudflare' / 'src'
for name in ('backend', 'agents', 'database', 'exchange_adapters', 'risk', 'research'):
    target = output / name
    if target.exists(): shutil.rmtree(target)
    for source in (root / name).rglob('*.py'):
        relative = source.relative_to(root / name)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
