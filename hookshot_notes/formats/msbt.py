"""MSBT message files: label -> plain text (formatting tags dropped)."""
import struct


def read_msbt(buf: bytes) -> dict[str, str]:
    if buf[:8] != b"MsgStdBn":
        raise ValueError("not an MSBT file")
    utf16 = buf[0xC] == 1
    blocks, o = {}, 0x20
    while o + 16 <= len(buf):
        size = struct.unpack_from("<I", buf, o + 4)[0]
        blocks[buf[o:o + 4]] = (o + 16, size)
        o += 16 + size
        o += -o % 16
    lbl, _ = blocks[b"LBL1"]
    labels = {}
    for i in range(struct.unpack_from("<I", buf, lbl)[0]):
        count, off = struct.unpack_from("<II", buf, lbl + 4 + 8 * i)
        p = lbl + off
        for _ in range(count):
            n = buf[p]
            labels[struct.unpack_from("<I", buf, p + 1 + n)[0]] = buf[p + 1:p + 1 + n].decode()
            p += 1 + n + 4
    txt, size = blocks[b"TXT2"]
    count = struct.unpack_from("<I", buf, txt)[0]
    offs = list(struct.unpack_from(f"<{count}I", buf, txt + 4)) + [size]
    return {labels[i]: _text(buf[txt + offs[i]:txt + offs[i + 1]], utf16) for i in range(count) if i in labels}


def _text(raw: bytes, utf16: bool) -> str:
    unit = 2 if utf16 else 1
    out, i = bytearray(), 0
    while i < len(raw):
        c = int.from_bytes(raw[i:i + unit], "little")
        if c == 0:
            break
        if c == 0x0E:  # tag: group, type, parameter size, parameters
            size = struct.unpack_from("<H", raw, i + unit + 4)[0]
            i += unit + 6 + size
        elif c == 0x0F:  # closing tag: group, type
            i += unit + 4
        else:
            out += raw[i:i + unit]
            i += unit
    return out.decode("utf-16-le" if utf16 else "utf-8", "replace")
