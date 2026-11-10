"""Read-only access to the running game's guest memory (Windows).
Guest address g is mapped at HOST_BASE + g inside the game process."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

HOST_BASE = 0x100000000000
PROCESS_VM_READ, PROCESS_QUERY_INFORMATION, PROCESS_QUERY_LIMITED = 0x10, 0x400, 0x1000
MEM_COMMIT, PAGE_GUARD, READABLE = 0x1000, 0x100, 0x02 | 0x04 | 0x08 | 0x20 | 0x40 | 0x80


class Memory(Protocol):
    def read(self, guest: int, n: int) -> bytes | None: ...
    def regions(self, lo: int, hi: int) -> Iterator[tuple[int, int]]: ...


class _MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_uint64), ("AllocationBase", ctypes.c_uint64), ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_uint64), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.POINTER(_MBI), ctypes.c_size_t]
    k.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t,
                                    ctypes.POINTER(ctypes.c_size_t)]
    k.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    return k


class ProcessMemory:
    def __init__(self, pid: int):
        self.k = _k32()
        self.h = self.k.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)  # read-only rights
        if not self.h:
            raise OSError(ctypes.get_last_error(), f"cannot open process {pid}")

    def read(self, guest: int, n: int) -> bytes | None:
        buf, got = ctypes.create_string_buffer(n), ctypes.c_size_t()
        if not self.k.ReadProcessMemory(self.h, HOST_BASE + guest, buf, n, ctypes.byref(got)) or got.value != n:
            return None
        return buf.raw

    def regions(self, lo: int, hi: int) -> Iterator[tuple[int, int]]:
        addr, m = HOST_BASE + lo, _MBI()
        while addr < HOST_BASE + hi and self.k.VirtualQueryEx(self.h, addr, ctypes.byref(m), ctypes.sizeof(m)):
            if m.State == MEM_COMMIT and m.Protect & READABLE and not m.Protect & PAGE_GUARD:
                yield m.BaseAddress - HOST_BASE, m.RegionSize
            addr = m.BaseAddress + m.RegionSize

    def close(self) -> None:
        if self.h:
            self.k.CloseHandle(self.h)
            self.h = None


def find_game_pid() -> int | None:
    """The recompiled game: a hookshot.exe living in a `bin` folder (the root hookshot.exe is the launcher)."""
    k, psapi = _k32(), ctypes.WinDLL("psapi")
    pids = (wt.DWORD * 4096)()
    used = wt.DWORD()
    if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(used)):
        return None
    for pid in pids[:used.value // ctypes.sizeof(wt.DWORD)]:
        h = k.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if not h:
            continue
        try:
            buf, size = ctypes.create_unicode_buffer(1024), wt.DWORD(1024)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                p = Path(buf.value)
                if p.name.lower() == "hookshot.exe" and p.parent.name.lower() == "bin":
                    return pid
        finally:
            k.CloseHandle(h)
    return None


def open_game_memory() -> ProcessMemory | None:
    pid = find_game_pid()
    if pid is None:
        return None
    try:
        return ProcessMemory(pid)
    except OSError:
        return None
