import sys, math
sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from bntx import textures
import texture2ddecoder as t2d
from PIL import Image

def gob_off(x, y, swap56):
    # x in bytes (0..63), y in rows (0..7) within one 512-byte GOB
    a = ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16)
    if swap56:
        b5, b6 = (a >> 5) & 1, (a >> 6) & 1
        a = (a & ~0x60) | (b5 << 6) | (b6 << 5)
    return a

def addr(x, y, wbytes, bh, swap56):
    gobs_w = math.ceil(wbytes / 64)
    return ((y // (8 * bh)) * 512 * bh * gobs_w + (x // 64) * 512 * bh
            + ((y % (8 * bh)) // 8) * 512 + gob_off(x, y, swap56))

def deswizzle(data, bw, bh_rows, bpb, bhl, swap56):
    """bw/bh_rows: size in blocks, bpb: bytes per block. Returns linear block data."""
    wbytes = bw * bpb
    out = bytearray(wbytes * bh_rows)
    bh = 1 << bhl
    for y in range(bh_rows):
        for x in range(wbytes):
            out[y * wbytes + x] = data[addr(x, y, wbytes, bh, swap56)]
    return bytes(out)

def swizzle(lin, bw, bh_rows, bpb, bhl, swap56, size):
    wbytes = bw * bpb
    out = bytearray(size)
    bh = 1 << bhl
    for y in range(bh_rows):
        for x in range(wbytes):
            out[addr(x, y, wbytes, bh, swap56)] = lin[y * wbytes + x]
    return bytes(out)

FMT = {0x1d: ("bc4", 4, 4, 8), 0x2d: ("astc", 4, 4, 16), 0x2e: ("astc", 5, 4, 16), 0x2f: ("astc", 5, 5, 16),
       0x30: ("astc", 6, 5, 16), 0x31: ("astc", 6, 6, 16), 0x32: ("astc", 8, 5, 16), 0x33: ("astc", 8, 6, 16), 0x34: ("astc", 8, 8, 16)}

def decode(b, t, swap56):
    kind, bx, by, bpb = FMT[t["fmt"] >> 8]
    bw, bhr = math.ceil(t["w"] / bx), math.ceil(t["h"] / by)
    raw = b[t["data"]:t["data"] + t["size"]]
    lin = deswizzle(raw, bw, bhr, bpb, t["bhl"], swap56)
    W, H = bw * bx, bhr * by
    if kind == "bc4":
        px = t2d.decode_bc4(lin, W, H)
    else:
        px = t2d.decode_astc(lin, W, H, bx, by)
    return Image.frombytes("RGBA", (W, H), px, "raw", "BGRA").crop((0, 0, t["w"], t["h"]))

if __name__ == "__main__":
    b = open(sys.argv[1], "rb").read()
    tx = textures(b)
    outdir = sys.argv[2]
    for name in sys.argv[3:]:
        for s in (0, 1):
            decode(b, tx[name], s).save(f"{outdir}/{name}_s{s}.png")
