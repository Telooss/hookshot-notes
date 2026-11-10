"""BYML v2-v7 reader, little-endian ("YB") and big-endian ("BY")."""
import struct
from typing import Any


def parse_byml(buf: bytes) -> Any:
    return _Reader(buf).root


class _Reader:
    def __init__(self, b: bytes):
        if b[:2] not in (b"YB", b"BY"):
            raise ValueError("not a BYML file")
        self.b = b
        self.e = "<" if b[:2] == b"YB" else ">"
        self.bo = "little" if self.e == "<" else "big"
        _, keys, strs, root = struct.unpack_from(self.e + "HIII", b, 2)
        self.keys = self._strings(keys) if keys else []
        self.strs = self._strings(strs) if strs else []
        self.root = self._node(b[root], root) if root else None

    def _u24(self, at: int) -> int:
        return int.from_bytes(self.b[at:at + 3], self.bo)

    def _strings(self, at: int) -> list[str]:
        n = self._u24(at + 1)
        offs = struct.unpack_from(self.e + f"{n + 1}I", self.b, at + 4)
        return [self.b[at + offs[i]:at + offs[i + 1]].split(b"\0")[0].decode("utf-8", "replace") for i in range(n)]

    def _value(self, t: int, at: int) -> Any:
        b, e = self.b, self.e
        v = struct.unpack_from(e + "I", b, at)[0]
        if t == 0xA0: return self.strs[v]
        if t == 0xD0: return bool(v)
        if t == 0xD1: return struct.unpack_from(e + "i", b, at)[0]
        if t == 0xD2: return struct.unpack_from(e + "f", b, at)[0]
        if t == 0xD3: return v
        if t == 0xD4: return struct.unpack_from(e + "q", b, v)[0]
        if t == 0xD5: return struct.unpack_from(e + "Q", b, v)[0]
        if t == 0xD6: return struct.unpack_from(e + "d", b, v)[0]
        if t == 0xA1: return b[v + 4:v + 4 + struct.unpack_from(e + "I", b, v)[0]]
        if t == 0xFF: return None
        if t in (0xC0, 0xC1, 0x20, 0x21): return self._node(t, v)
        raise ValueError(f"unsupported BYML node type {t:#x}")

    def _node(self, t: int, at: int) -> Any:
        n = self._u24(at + 1)
        if t == 0xC0:
            types = self.b[at + 4:at + 4 + n]
            base = at + 4 + ((n + 3) & ~3)
            return [self._value(types[i], base + 4 * i) for i in range(n)]
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = at + 4 + 8 * i
                out[self.keys[self._u24(e)]] = self._value(self.b[e + 3], e + 4)
            return out
        if t in (0x20, 0x21):  # v7 hash-keyed dicts: (key, value) pairs then one type byte per entry
            ks = 4 if t == 0x20 else 8
            types = at + 4 + n * (ks + 4)
            out = {}
            for i in range(n):
                e = at + 4 + i * (ks + 4)
                out[int.from_bytes(self.b[e:e + ks], self.bo)] = self._value(self.b[types + i], e + ks)
            return out
        raise ValueError(f"unsupported BYML container {t:#x}")
