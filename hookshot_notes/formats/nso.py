from pathlib import Path


def build_id(main: Path) -> str:
    """Module ID of an NSO executable: 20 bytes at 0x40, as hex."""
    with open(main, "rb") as f:
        head = f.read(0x54)
    if head[:4] != b"NSO0":
        raise ValueError(f"{main}: not an NSO executable")
    return head[0x40:0x54].hex()
