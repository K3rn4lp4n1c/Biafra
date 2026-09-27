from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import secrets
import string
import json
import time
import hmac

def enc_req(key: str|None, req:dict[str, str],) -> str:
    if not key:
        raise ValueError("Encryption key is required")
    payload = json.dumps(req).encode('utf-8')
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    ciphertext = cipher.encrypt(pad(payload, AES.block_size))
    return base64.b64encode(ciphertext).decode('utf-8')

def dec_req(key: str|None, payload:str, ) -> dict[str, str]|None:
    if not key:
        raise ValueError("Decryption key is required")
    ciphertext = base64.b64decode(payload)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return json.loads(decrypted.decode('utf-8'))
        
def gen_enc_path(length=16) -> str:
    alphabet = string.ascii_letters
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def verify_credentials(file:str, username:str, password:str) -> bool|None:
    with open(file, "r") as f:
        for line in f:
            creds = line.strip().split(",")
            if len(creds) == 2 and creds[0] == username:
                if creds[1] == password:
                    return True
                return False
    return None

SHOP_TOKEN_TTL = 300  # 5 minutes

def issue_shop_token(session, shop_id: str, product_id: str) -> str:
    token = secrets.token_urlsafe(18)
    shop_tokens = session.get("shop_tokens", {})
    shop_tokens[f"{shop_id}:{product_id}"] = {
        "token": token,
        "issued_at": int(time.time()),
    }
    session["shop_tokens"] = shop_tokens
    session.modified = True
    return token

def validate_shop_token(session, shop_id: str, product_id: str, supplied: str) -> bool:
    if not supplied or not isinstance(supplied, str):
        return False
    shop_tokens = session.get("shop_tokens", {})
    record = shop_tokens.get(f"{shop_id}:{product_id}")
    if not record:
        return False
    expected = record.get("token", "")
    issued_at = int(record.get("issued_at", 0))
    if int(time.time()) - issued_at > SHOP_TOKEN_TTL:
        return False
    return hmac.compare_digest(expected, supplied)

def clear_shop_token(session, shop_id: str, product_id: str) -> None:
    shop_tokens = session.get("shop_tokens", {})
    shop_tokens.pop(f"{shop_id}:{product_id}", None)
    session["shop_tokens"] = shop_tokens
    session.modified = True