from __future__ import annotations

import hashlib


def derive_seed(
    base_seed: int, *, day: int, action_seq: int, stream: str, purpose: str
) -> int:
    payload = f"{base_seed}|{day}|{action_seq}|{stream}|{purpose}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big")
