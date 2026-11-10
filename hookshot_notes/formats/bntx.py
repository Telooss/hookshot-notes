import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class TexInfo:
    name: str
    fmt: int
    width: int
    height: int
    block_height_log2: int
    data_offset: int
    data_size: int
    comp_sel: bytes


def list_textures(buf: bytes) -> dict[str, TexInfo]:
    """Textures of a BNTX file (Switch 'NX  ' or Switch 2 'Ounc' platform), by name."""
    if buf[:4] != b"BNTX":
        raise ValueError("not a BNTX file")
    count = struct.unpack_from("<I", buf, 0x24)[0]
    table = struct.unpack_from("<Q", buf, 0x28)[0]
    out = {}
    for i in range(count):
        o = struct.unpack_from("<Q", buf, table + 8 * i)[0]
        if buf[o:o + 4] != b"BRTI":
            raise ValueError(f"texture {i}: bad BRTI header")
        fmt, _, w, h, _, _, bhl = struct.unpack_from("<IIiiiiI", buf, o + 0x1C)
        size = struct.unpack_from("<I", buf, o + 0x50)[0]
        name_at = struct.unpack_from("<Q", buf, o + 0x60)[0]
        name = buf[name_at + 2:name_at + 2 + struct.unpack_from("<H", buf, name_at)[0]].decode()
        mips = struct.unpack_from("<Q", buf, o + 0x70)[0]
        out[name] = TexInfo(name, fmt, w, h, bhl, struct.unpack_from("<Q", buf, mips)[0], size, bytes(buf[o + 0x58:o + 0x5C]))
    return out
