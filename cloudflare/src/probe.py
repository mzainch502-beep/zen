"""Compatibility checks only; never submits exchange orders."""
import json
from workers import WorkerEntrypoint, Response, DurableObject
import sqlalchemy
import argon2
import cryptography
import pydantic

class Probe(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY, n INTEGER NOT NULL)')

    async def fetch(self, request):
        checks = {}
        def increment():
            self.ctx.storage.sql.exec('INSERT INTO checks VALUES(1,1) ON CONFLICT(id) DO UPDATE SET n=n+1')
        self.ctx.storage.transactionSync(increment)
        before = self.ctx.storage.sql.exec('SELECT n FROM checks WHERE id=1').one().n
        def rejected():
            self.ctx.storage.sql.exec('UPDATE checks SET n=n+100 WHERE id=1')
            raise ValueError('intentional rollback test')
        try:
            self.ctx.storage.transactionSync(rejected)
        except Exception:
            pass
        after = self.ctx.storage.sql.exec('SELECT n FROM checks WHERE id=1').one().n
        checks['transaction_rollback'] = before == after
        checks['persistent_counter'] = after
        try:
            h = argon2.PasswordHasher()
            encoded = h.hash('compatibility-test-only-not-an-account')
            checks['argon2'] = h.verify(encoded, 'compatibility-test-only-not-an-account')
        except Exception as error:
            checks['argon2'] = False
            checks['argon2_error_type'] = type(error).__name__
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = AESGCM.generate_key(bit_length=256)
        cipher = AESGCM(key)
        ciphertext = cipher.encrypt(b'012345678901', b'test', b'owner:exchange:v1')
        checks['vault'] = cipher.decrypt(b'012345678901', ciphertext, b'owner:exchange:v1') == b'test'
        return Response.json({'compatibility_probe': True, 'migration_complete': False,
                              'sqlalchemy': sqlalchemy.__version__, 'checks': checks})

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await self.env.PROBE.getByName('compatibility').fetch(request)
