"""Read-only access to the running game's guest memory (spike).
Guest address g lives at host address HOST_BASE + g in hookshot.exe (seen in a crash log)."""
import ctypes, ctypes.wintypes as wt, struct, subprocess

HOST_BASE = 0x100000000000
PROCESS_VM_READ, PROCESS_QUERY_INFORMATION = 0x10, 0x400
MEM_COMMIT = 0x1000
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_uint64), ("AllocationBase", ctypes.c_uint64), ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_uint64), ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]

k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

def find_pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq hookshot.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    pids = [int(l.split('","')[1]) for l in out.splitlines() if l.startswith('"hookshot.exe"')]
    return max(pids, key=lambda p: p) if pids else None

class Game:
    def __init__(self, pid=None):
        self.pid = pid or find_pid()
        if not self.pid: raise SystemExit("hookshot.exe is not running")
        self.h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.h: raise OSError(ctypes.get_last_error())

    def read(self, guest, n):
        buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.h, HOST_BASE + guest, buf, n, ctypes.byref(got)): return None
        return buf.raw[:got.value]

    def regions(self, lo=0, hi=0x2000000000):
        """Committed readable regions within guest [lo, hi)."""
        a = HOST_BASE + lo; m = MBI()
        while a < HOST_BASE + hi and k32.VirtualQueryEx(self.h, a, ctypes.byref(m), ctypes.sizeof(m)):
            if m.State == MEM_COMMIT and m.Protect & 0xEE and not m.Protect & 0x100:  # readable, not guard
                yield m.BaseAddress - HOST_BASE, m.RegionSize
            a = m.BaseAddress + m.RegionSize

    def find(self, pat, lo=0, hi=0x2000000000, align=4, chunk=64 << 20):
        hits = []
        for base, size in self.regions(lo, hi):
            off = 0
            while off < size:
                n = min(chunk, size - off); data = self.read(base + off, n + len(pat) - 1) or b""
                i = data.find(pat)
                while i >= 0:
                    if (base + off + i) % align == 0: hits.append(base + off + i)
                    i = data.find(pat, i + 1)
                off += n
        return hits

    def vec3(self, guest):
        b = self.read(guest, 12); return struct.unpack("<3f", b) if b and len(b) == 12 else None
