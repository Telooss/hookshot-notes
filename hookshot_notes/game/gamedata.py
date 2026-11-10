import mmh3


def flag_hash(name: str) -> int:
    """GameData flag names are stored as unsigned 32-bit MurmurHash3 (seed 0)."""
    return mmh3.hash(name, 0, signed=False)
