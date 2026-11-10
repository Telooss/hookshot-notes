"""Find the live 'current map + position' GameData record by its shape (works after the heap moves)."""
import struct, time
from mem import Game
from zs import unzs; from byml import Byml

BANCS = set(Byml(unzs("Banc/BancBasedResource/MapParam.byml.zs")).root)
# also the other area names (indoor maps etc. are not in MapParam): accept any *_Child / *_Adult / known names
def plausible(name): return name in BANCS or name.endswith(("_Child", "_Adult"))

def locate(g):
    found = []
    for base, size in g.regions(0x1000000000, 0x1200000000):
        off = 0
        while off < size:
            n = min(64 << 20, size - off); data = g.read(base + off, n) or b""
            i = data.find(b"\x40\x00\x00\x00")
            while i >= 0:
                if i >= 8 and i + 4 + 64 + 8 + 12 <= len(data):
                    ptr = struct.unpack_from("<Q", data, i - 8)[0]
                    here = base + off + i + 4          # guest address of the chars
                    if ptr == here:
                        name = data[i + 4:i + 68].split(b"\0")[0]
                        try: s = name.decode("ascii")
                        except UnicodeDecodeError: s = ""
                        if s and plausible(s) and data[i + 68:i + 76] == bytes(8):
                            x, y, z = struct.unpack_from("<3f", data, i + 76)
                            found.append((here + 72, s, (x, y, z)))
                i = data.find(b"\x40\x00\x00\x00", i + 4)
            off += n
    return found

if __name__ == "__main__":
    t = time.time(); g = Game()
    for a, s, p in locate(g): print(hex(a), s, [round(v, 2) for v in p])
    print(f"{time.time() - t:.1f}s")
