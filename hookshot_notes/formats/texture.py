"""Tegra block-linear layout as used by the Switch 2, and texture decoding."""
import math
from functools import lru_cache

import numpy as np
import texture2ddecoder
from PIL import Image

from .bntx import TexInfo

# format type (high byte) -> (kind, block width, block height, bytes per block)
FORMATS = {
    0x02: ("raw", 1, 1, 1), 0x09: ("raw", 1, 1, 2), 0x0B: ("raw", 1, 1, 4),
    0x1D: ("bc4", 4, 4, 8),
    0x2D: ("astc", 4, 4, 16), 0x2E: ("astc", 5, 4, 16), 0x2F: ("astc", 5, 5, 16), 0x30: ("astc", 6, 5, 16),
    0x31: ("astc", 6, 6, 16), 0x32: ("astc", 8, 5, 16), 0x33: ("astc", 8, 6, 16), 0x34: ("astc", 8, 8, 16),
}


def swizzled_size(bw: int, bh: int, bpb: int, bhl: int) -> int:
    gob_rows = 8 << bhl
    return math.ceil(bw * bpb / 64) * 64 * math.ceil(bh / gob_rows) * gob_rows


@lru_cache(maxsize=32)
def _addresses(bw: int, bh: int, bpb: int, bhl: int) -> np.ndarray:
    """Swizzled address of every byte of the linear image, row by row."""
    wbytes = bw * bpb
    blk = 1 << bhl
    gobs_w = math.ceil(wbytes / 64)
    x = np.arange(wbytes, dtype=np.int64)[None, :]
    y = np.arange(bh, dtype=np.int64)[:, None]
    gob = ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16)
    gob = (gob & ~0x60) | ((gob >> 5) & 1) << 6 | ((gob >> 6) & 1) << 5  # Switch 2: bits 5 and 6 swapped
    return ((y // (8 * blk)) * 512 * blk * gobs_w + (x // 64) * 512 * blk + ((y % (8 * blk)) // 8) * 512 + gob).ravel()


def deswizzle(raw: bytes, bw: int, bh: int, bpb: int, bhl: int) -> bytes:
    return np.frombuffer(raw, np.uint8)[_addresses(bw, bh, bpb, bhl)].tobytes()


def swizzle(linear: bytes, bw: int, bh: int, bpb: int, bhl: int, size: int) -> bytes:
    out = np.zeros(size, np.uint8)
    out[_addresses(bw, bh, bpb, bhl)] = np.frombuffer(linear, np.uint8)
    return out.tobytes()


def decode(buf: bytes, info: TexInfo) -> Image.Image:
    """RGBA image of a texture's first mip, with the texture's channel selectors applied
    (so a BC4 mask with selectors 1,1,1,R becomes white with the mask as alpha)."""
    kind, bx, by, bpb = FORMATS[info.fmt >> 8]
    bw, bh = math.ceil(info.width / bx), math.ceil(info.height / by)
    raw = buf[info.data_offset:info.data_offset + info.data_size]
    lin = deswizzle(raw, bw, bh, bpb, info.block_height_log2)
    w, h = bw * bx, bh * by
    if kind == "raw":
        src = np.zeros((h, w, 4), np.uint8)
        src[:, :, :bpb] = np.frombuffer(lin, np.uint8).reshape(h, w, bpb)
    else:
        px = texture2ddecoder.decode_bc4(lin, w, h) if kind == "bc4" else texture2ddecoder.decode_astc(lin, w, h, bx, by)
        src = np.asarray(Image.frombytes("RGBA", (w, h), px, "raw", "BGRA"))
    # selector values: 0 = zero, 1 = one, 2..5 = source R, G, B, A
    planes = [np.zeros((h, w), np.uint8), np.full((h, w), 255, np.uint8)] + [src[:, :, i] for i in range(4)]
    out = np.stack([planes[s] for s in info.comp_sel], axis=2)
    return Image.fromarray(out, "RGBA").crop((0, 0, info.width, info.height))
