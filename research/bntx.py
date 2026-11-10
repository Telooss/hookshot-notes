import struct

def textures(b):
    n = struct.unpack_from("<I", b, 0x24)[0]
    ptrs = struct.unpack_from("<Q", b, 0x28)[0]
    out = {}
    for i in range(n):
        o = struct.unpack_from("<Q", b, ptrs + 8 * i)[0]
        assert b[o:o + 4] == b"BRTI"
        mips = struct.unpack_from("<H", b, o + 0x16)[0]
        fmt, _acc, w, h, _d, _arr, bhl = struct.unpack_from("<IIiiiiI", b, o + 0x1C)
        size = struct.unpack_from("<I", b, o + 0x50)[0]
        comp = b[o + 0x58:o + 0x5C]
        name_at = struct.unpack_from("<Q", b, o + 0x60)[0]
        ln = struct.unpack_from("<H", b, name_at)[0]
        name = b[name_at + 2:name_at + 2 + ln].decode()
        mip_ptr = struct.unpack_from("<Q", b, o + 0x70)[0]
        data = struct.unpack_from("<Q", b, mip_ptr)[0]
        out[name] = dict(brti=o, fmt=fmt, w=w, h=h, bhl=bhl, mips=mips, size=size, data=data, comp=comp.hex())
    return out

if __name__ == "__main__":
    import sys
    b = open(sys.argv[1], "rb").read()
    for k, v in textures(b).items():
        if any(s in k for s in sys.argv[2:]):
            print(k, {x: (hex(y) if isinstance(y, int) else y) for x, y in v.items()})
