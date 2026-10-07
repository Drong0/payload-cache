import hashlib
import json
from itertools import chain


def interleave(first: list[str], second: list[str]) -> str:
    return ", ".join(chain.from_iterable(zip(first, second, strict=True)))


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def payload_fingerprint(list_1: list[str], list_2: list[str]) -> str:
    # JSON keeps item boundaries, so ["a b"] and ["a", "b"] get different keys.
    return fingerprint(json.dumps([list_1, list_2], ensure_ascii=False))
