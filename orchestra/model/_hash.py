import hashlib


def hash(to_hash: str) -> str:
    return hashlib.sha1(to_hash.encode("utf-8")).hexdigest()
