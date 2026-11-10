"""Synthetic game-format files for tests (no game data)."""
import struct


def build_byml(root, big_endian=False) -> bytes:
    """BYML v7 with dict (str keys), dict (int keys -> 0x20), list, str, int, bool."""
    e = ">" if big_endian else "<"
    bo = "big" if big_endian else "little"
    keys, strs = set(), set()

    def collect(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(k, str):
                    keys.add(k)
                collect(x)
        elif isinstance(v, list):
            for x in v:
                collect(x)
        elif isinstance(v, str):
            strs.add(v)
    collect(root)
    keys, strs = sorted(keys), sorted(strs)

    def strtab(items):
        n = len(items)
        head = bytes([0xC2]) + n.to_bytes(3, bo)
        body = b"".join(s.encode() + b"\0" for s in items)
        offs, o = [], 4 + 4 * (n + 1)
        for s in items:
            offs.append(o)
            o += len(s.encode()) + 1
        offs.append(o)
        raw = head + struct.pack(e + f"{n + 1}I", *offs) + body
        return raw + b"\0" * (-len(raw) % 4)

    out = bytearray(16)
    kt = len(out); out += strtab(keys) if keys else b""
    st = len(out); out += strtab(strs) if strs else b""

    def scalar(v):
        if isinstance(v, bool): return 0xD0, int(v)
        if isinstance(v, int): return 0xD1, v & 0xFFFFFFFF
        if isinstance(v, str): return 0xA0, strs.index(v)
        raise TypeError(v)

    def node(v) -> int:
        items = list(v.items()) if isinstance(v, dict) else list(enumerate(v))
        vals = []
        for _, x in items:
            if isinstance(x, (dict, list)):
                vals.append(((0xC1 if isinstance(x, dict) and all(isinstance(k, str) for k in x) else 0x20 if isinstance(x, dict) else 0xC0), node(x)))
            else:
                vals.append(scalar(x))
        at = len(out)
        n = len(items)
        if isinstance(v, list):
            out.extend(bytes([0xC0]) + n.to_bytes(3, bo) + bytes(t for t, _ in vals) + b"\0" * (-n % 4))
            for _, x in vals: out.extend(struct.pack(e + "I", x))
        elif all(isinstance(k, str) for k in v):
            out.extend(bytes([0xC1]) + n.to_bytes(3, bo))
            for (k, _), (t, x) in sorted(zip(items, vals), key=lambda p: p[0][0]):
                out.extend(keys.index(k).to_bytes(3, bo) + bytes([t]) + struct.pack(e + "I", x))
        else:
            out.extend(bytes([0x20]) + n.to_bytes(3, bo))
            for (k, _), (t, x) in zip(items, vals):
                out.extend(struct.pack(e + "II", k, x))
            out.extend(bytes(t for t, _ in vals) + b"\0" * (-n % 4))
        return at

    # children are written before parents, so the root goes last
    def build(v):
        return node(v)
    root_off = build(root)
    struct.pack_into(e + "2sHIII", out, 0, b"BY" if big_endian else b"YB", 7, kt if keys else 0, st if strs else 0, root_off)
    return bytes(out)


def build_msbt(messages: dict[str, bytes]) -> bytes:
    """UTF-8 MSBT with LBL1 (one label per bucket) and TXT2; message values are raw UTF-8 bytes (tags allowed)."""
    labels = list(messages)
    lbl = bytearray(struct.pack("<I", len(labels)))
    table_end = 4 + 8 * len(labels)
    entries = bytearray()
    for i, name in enumerate(labels):
        lbl += struct.pack("<II", 1, table_end + len(entries))
        entries += bytes([len(name)]) + name.encode() + struct.pack("<I", i)
    lbl += entries
    txt = bytearray(struct.pack("<I", len(labels)))
    body = bytearray(); offs = []
    for name in labels:
        offs.append(4 + 4 * len(labels) + len(body)); body += messages[name] + b"\0"
    txt += struct.pack(f"<{len(offs)}I", *offs) + body

    def block(tag, data):
        b = tag + struct.pack("<I", len(data)) + bytes(8) + bytes(data)
        return b + b"\xab" * (-len(b) % 16)
    blocks = block(b"LBL1", lbl) + block(b"TXT2", txt)
    head = b"MsgStdBn" + b"\xff\xfe" + bytes(2) + bytes([0, 3]) + struct.pack("<H", 2) + bytes(2) + struct.pack("<I", 0x20 + len(blocks)) + bytes(10)
    return head + blocks


def build_sarc(files: dict[str, bytes]) -> bytes:
    names = sorted(files)
    sfnt = bytearray()
    name_off = []
    for n in names:
        name_off.append(len(sfnt))
        sfnt += n.encode() + b"\0"
        sfnt += b"\0" * (-len(sfnt) % 4)
    data = bytearray(); spans = []
    for n in names:
        start = len(data); data += files[n]; spans.append((start, len(data)))
        data += b"\0" * (-len(data) % 4)
    sfat = b"SFAT" + struct.pack("<HHI", 0xC, len(names), 0x65)
    for n, o, (s, t) in zip(names, name_off, spans):
        sfat += struct.pack("<IIII", 0, 0x01000000 | (o // 4), s, t)
    head_len = 0x14 + len(sfat) + 8 + len(sfnt)
    data_off = head_len + (-head_len % 0x100)
    total = data_off + len(data)
    hdr = b"SARC" + struct.pack("<HHIIHH", 0x14, 0xFEFF, total, data_off, 0x100, 0)
    body = hdr + sfat + b"SFNT" + struct.pack("<HH", 8, 0) + sfnt
    return body + b"\0" * (data_off - len(body)) + bytes(data)
