import struct


def read_sarc(buf: bytes) -> dict[str, bytes]:
    """Files of a little-endian SARC archive, by name."""
    if buf[:4] != b"SARC":
        raise ValueError("not a SARC archive")
    header_len = struct.unpack_from("<H", buf, 4)[0]
    data_off = struct.unpack_from("<I", buf, 0xC)[0]
    sfat = header_len
    count = struct.unpack_from("<H", buf, sfat + 6)[0]
    names = sfat + 12 + count * 16 + 8  # after the SFAT nodes and the SFNT header
    out = {}
    for i in range(count):
        _, attrs, start, end = struct.unpack_from("<IIII", buf, sfat + 12 + i * 16)
        at = names + (attrs & 0xFFFF) * 4
        name = buf[at:buf.index(b"\0", at)].decode()
        out[name] = buf[data_off + start:data_off + end]
    return out
