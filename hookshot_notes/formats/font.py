KEY = bytes.fromhex("a6018502")


def decrypt(buf: bytes) -> bytes:
    """Plain OpenType font from a .bfotf/.bfttf: 8-byte header, then data XORed with a 4-byte key."""
    data = buf[8:]
    key = (KEY * (len(data) // 4 + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, key))
