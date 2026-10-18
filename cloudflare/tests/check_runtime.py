"""Verify the real workerd response; fabricated/missing checks fail the gate."""
import json, sys, urllib.request

def read():
    with urllib.request.urlopen('http://127.0.0.1:8799/', timeout=90) as response:
        return json.load(response)

first, second = read(), read()
print(json.dumps({'first': first, 'second': second}, indent=2))
for result in (first, second):
    assert result['migration_complete'] is False
    for name in ('transaction_rollback', 'argon2', 'vault', 'orm_rollback', 'orm_savepoint'):
        assert result['checks'][name] is True, f'Compatibility failed: {name}'
assert second['checks']['persistent_counter'] == first['checks']['persistent_counter'] + 1
