import os, hashlib, secrets, time, json
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
from database.models import Session, User
ph=PasswordHasher()
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def password_hash(value):
    if len(value)<12: raise ValueError('Password must have at least 12 characters')
    return ph.hash(value)
def verify(encoded,value):
    try: return ph.verify(encoded,value)
    except VerificationError: return False

def create_session(db,user):
    token=secrets.token_urlsafe(32)
    db.add(Session(token_hash=digest(token),user_id=user.id,expires=time.time()+3600*12))
    return token

def authenticate(db,token):
    s=db.get(Session,digest(token))
    if not s or s.expires<time.time(): return None
    return db.get(User,s.user_id)

class Vault:
    def __init__(self,key=None):
        raw=base64.b64decode(key or os.environ['CREDENTIAL_MASTER_KEY'],validate=True)
        if len(raw)!=32: raise ValueError('Master key must be 32 bytes')
        self.aes=AESGCM(raw)
    def encrypt(self,owner,exchange,payload):
        nonce=os.urandom(12)
        aad=f'{owner}:{exchange}:v1'.encode()
        return base64.b64encode(nonce+self.aes.encrypt(nonce,json.dumps(payload).encode(),aad)).decode()
    def decrypt(self,owner,exchange,ciphertext):
        raw=base64.b64decode(ciphertext)
        return json.loads(self.aes.decrypt(raw[:12],raw[12:],f'{owner}:{exchange}:v1'.encode()))
