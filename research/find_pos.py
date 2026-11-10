"""Spike step 1: find copies of each save slot's SavePos in guest memory."""
import glob, os, struct, sys, time, mmh3
from mem import Game

SAVE = "C:/chemin/vers/Hookshot/user/save"
H = struct.pack("<I", mmh3.hash("PlayerStatus.SavePos", signed=False))

def savepos(path):
    b = open(path, "rb").read(); i = b.find(H)
    if i < 0 or i % 8: return None
    off = struct.unpack_from("<I", b, i + 4)[0]
    return struct.unpack_from("<3f", b, off)

g = Game()
print("pid", g.pid)
total = sum(s for _, s in g.regions())
print(f"committed guest memory: {total / 2**30:.2f} GiB")
t = time.time()
for p in sorted(glob.glob(SAVE + "/*/slot_*/progress.sav")):
    v = savepos(p)
    if not v: continue
    hits = g.find(struct.pack("<3f", *v))
    print(os.path.basename(os.path.dirname(p)), [round(x, 3) for x in v], "->", [hex(h) for h in hits][:20], len(hits))
print(f"{time.time() - t:.1f}s")
