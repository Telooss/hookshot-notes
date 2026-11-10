import struct, zstandard, os
def sarc(buf):
    d0 = struct.unpack_from("<I", buf, 0xC)[0]; sf = struct.unpack_from("<H", buf, 4)[0]; n = struct.unpack_from("<H", buf, sf + 6)[0]; nm = sf + 12 + n * 16 + 8; o = {}
    for i in range(n):
        _, at, s, e = struct.unpack_from("<IIII", buf, sf + 12 + i * 16); p = nm + (at & 0xFFFF) * 4; o[buf[p:buf.index(b"\0", p)].decode()] = buf[d0 + s:d0 + e]
    return o
R = "C:/chemin/vers/Hookshot/romfs/"
_d = sarc(zstandard.ZstdDecompressor().decompress(open(R + "Pack/ZsDic.pack.zs", "rb").read()))
D = {k: zstandard.ZstdCompressionDict(v) for k, v in _d.items()}
def unzs(rel):
    if not rel.endswith(".zs"): return open(R + rel, "rb").read()
    raw = open(R + rel, "rb").read()
    did = zstandard.get_frame_parameters(raw).dict_id
    d = next((x for x in D.values() if x.dict_id() == did), None) if did else None
    return zstandard.ZstdDecompressor(dict_data=d).decompress(raw, max_output_size=1 << 31)
