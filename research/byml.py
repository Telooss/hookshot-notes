"""Minimal little-endian BYML (v2-v7) reader: enough to inspect game data."""
import struct

class Byml:
    def __init__(self, b):
        assert b[:2] in (b"YB", b"BY"), b[:2]
        self.b = b
        self.e = "<" if b[:2] == b"YB" else ">"
        self.bo = "little" if self.e == "<" else "big"
        self.ver, kt, st, root = struct.unpack_from(self.e + "HIII", b, 2)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []
        self.root = self._node(b[root], root) if root else None

    def _strtab(self, o):
        assert self.b[o] == 0xC2
        n = int.from_bytes(self.b[o + 1:o + 4], self.bo)
        offs = struct.unpack_from(self.e + f"{n + 1}I", self.b, o + 4)
        return [self.b[o + offs[i]:o + offs[i + 1]].split(b"\0")[0].decode("utf-8", "replace") for i in range(n)]

    def _val(self, t, raw_at):
        b = self.b
        v = struct.unpack_from(self.e + "I", b, raw_at)[0]
        if t == 0xA0: return self.strs[v]
        if t == 0xD0: return bool(v)
        if t == 0xD1: return struct.unpack_from(self.e + "i", b, raw_at)[0]
        if t == 0xD2: return struct.unpack_from(self.e + "f", b, raw_at)[0]
        if t == 0xD3: return v
        if t == 0xD4: return struct.unpack_from(self.e + "q", b, v)[0]
        if t == 0xD5: return struct.unpack_from(self.e + "Q", b, v)[0]
        if t == 0xD6: return struct.unpack_from(self.e + "d", b, v)[0]
        if t == 0xA1:  # binary
            n = struct.unpack_from(self.e + "I", b, v)[0]; return b[v + 4:v + 4 + n]
        if t == 0xFF: return None
        if t in (0xC0, 0xC1, 0x20, 0x21): return self._node(t, v)
        return ("?", hex(t), v)

    def _node(self, t, o):
        b = self.b
        n = int.from_bytes(b[o + 1:o + 4], self.bo)
        if t == 0xC0:  # array
            types = b[o + 4:o + 4 + n]
            base = o + 4 + ((n + 3) & ~3)
            return [self._val(types[i], base + 4 * i) for i in range(n)]
        if t == 0xC1:  # dict
            out = {}
            for i in range(n):
                e = o + 4 + 8 * i
                k = int.from_bytes(b[e:e + 3], self.bo)
                out[self.keys[k]] = self._val(b[e + 3], e + 4)
            return out
        if t in (0x20, 0x21):  # hash32 / hash64 dicts (v7)
            ks = 4 if t == 0x20 else 8
            out = {}
            types = b[o + 4 + n * (ks + 4):]
            for i in range(n):
                e = o + 4 + i * (ks + 4)
                h = int.from_bytes(b[e:e + ks], self.bo)
                out[h] = self._val(types[i], e + ks)
            return out
        raise ValueError(hex(t))
