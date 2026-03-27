import hashlib


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.sha256(password.encode() + salt).hexdigest()
