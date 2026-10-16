"""Reads the player's live position from a running Black Myth: Wukong process (read-only)."""
import array
import ctypes
import ctypes.wintypes as wt
import math
import struct
import threading

EXE = 'b1-Win64-Shipping.exe'
KNOWN_GWORLD_RVAS = (0x1D5DDCA0, 492713840)  # repack build, Steam build (Dumper-7 dump from jaskang/wukong-minimap)
UWORLD_GAME_INSTANCE = 400
GAME_INSTANCE_LOCAL_PLAYERS = 56
PLAYER_CONTROLLER = 48
CONTROLLER_PAWN = 808
CONTROLLER_ROTATION = 768
ACTOR_ROOT = 416
SCENE_LOCATION = 328

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS, TH32CS_SNAPMODULE = 0x2, 0x8

k32 = ctypes.WinDLL('kernel32', use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD), ('th32ProcessID', wt.DWORD),
                ('th32DefaultHeapID', ctypes.c_void_p), ('th32ModuleID', wt.DWORD), ('cntThreads', wt.DWORD),
                ('th32ParentProcessID', wt.DWORD), ('pcPriClassBase', ctypes.c_long), ('dwFlags', wt.DWORD),
                ('szExeFile', wt.WCHAR * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('th32ModuleID', wt.DWORD), ('th32ProcessID', wt.DWORD),
                ('GlblcntUsage', wt.DWORD), ('ProccntUsage', wt.DWORD), ('modBaseAddr', ctypes.c_void_p),
                ('modBaseSize', wt.DWORD), ('hModule', wt.HMODULE), ('szModule', wt.WCHAR * 256),
                ('szExePath', wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]


def _find_pid():
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32W(dwSize=ctypes.sizeof(PROCESSENTRY32W))
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == EXE.lower():
                return entry.th32ProcessID
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return None


def _module_base(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    entry = MODULEENTRY32W(dwSize=ctypes.sizeof(MODULEENTRY32W))
    try:
        ok = k32.Module32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szModule.lower() == EXE.lower():
                return entry.modBaseAddr
            ok = k32.Module32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return None


class LiveReader:
    """Attaches to the game on demand and returns (x, y, z, yaw_degrees) or None."""

    def __init__(self):
        self.handle = None
        self.base = None
        self.gworld = None
        self.scanning = False

    def _attach(self):
        pid = _find_pid()
        if not pid:
            return False
        base = _module_base(pid)
        handle = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not base or not handle:
            return False
        self.handle, self.base = handle, base
        self.gworld = next((self.base + rva for rva in KNOWN_GWORLD_RVAS if self._chain(self.base + rva)), None)
        if self.gworld is None and not self.scanning:
            self.scanning = True
            threading.Thread(target=self._scan_gworld, daemon=True).start()
        return True

    def _heap(self, v):
        return 0x10000 < v < 0x7FFFFFFFFFFF and not (self.base <= v < self.base + 0x40000000) and not v & 7

    def _chain(self, gworld_addr):
        """Returns (controller, root) if the address holds a UWorld* leading to a spawned player, else None."""
        try:
            world = self._ptr(gworld_addr)
            if not self._heap(world):
                return None
            game = self._ptr(world + UWORLD_GAME_INSTANCE)
            if not self._heap(game):
                return None
            players, count = struct.unpack('<Qi', self._read(game + GAME_INSTANCE_LOCAL_PLAYERS, 12))
            if count != 1 or not self._heap(players):
                return None
            controller = self._ptr(self._ptr(players) + PLAYER_CONTROLLER)
            root = self._ptr(self._ptr(controller + CONTROLLER_PAWN) + ACTOR_ROOT)
            x, y, z = struct.unpack('<3d', self._read(root + SCENE_LOCATION, 24))
        except OSError:
            return None
        if all(math.isfinite(v) and abs(v) < 2e6 for v in (x, y, z)) and (x or y):
            return controller, root
        return None

    def _sections(self):
        """Yields (rva, size) of writable PE sections where engine globals live."""
        head = self._read(self.base, 0x1000)
        pe = struct.unpack_from('<I', head, 0x3C)[0]
        count = struct.unpack_from('<H', head, pe + 6)[0]
        table = pe + 24 + struct.unpack_from('<H', head, pe + 20)[0]
        for i in range(count):
            vsize, rva = struct.unpack_from('<II', head, table + 40 * i + 8)
            flags = struct.unpack_from('<I', head, table + 40 * i + 36)[0]
            if flags & 0x80000000 and not flags & 0x20000000 and vsize < 0x2000000:
                yield rva, vsize

    def _scan_gworld(self):
        """Finds GWorld for unknown game builds by testing every pointer stored in writable sections (~2 s)."""
        try:
            seen = set()
            for rva, size in self._sections():
                for off in range(0, size, 0x100000):
                    try:
                        chunk = self._read(self.base + rva + off, min(0x100000, size - off))
                    except OSError:
                        continue
                    values = array.array('Q', chunk[:len(chunk) // 8 * 8])
                    for i, v in enumerate(values):
                        if v in seen or not self._heap(v):
                            continue
                        seen.add(v)
                        addr = self.base + rva + off + i * 8
                        if self._chain(addr):
                            self.gworld = addr
                            return
        except OSError:
            pass
        finally:
            self.scanning = False

    def _read(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not addr or not k32.ReadProcessMemory(self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
            raise OSError('read failed')
        return buf.raw

    def _ptr(self, addr):
        return struct.unpack('<Q', self._read(addr, 8))[0]

    def position(self):
        if self.handle is None and not self._attach():
            return None
        if self.gworld is None:
            if not self.scanning:
                self.handle = None
            return None
        try:
            found = self._chain(self.gworld)
            if not found:
                return None
            controller, root = found
            x, y, z = struct.unpack('<3d', self._read(root + SCENE_LOCATION, 24))
            _, yaw, _ = struct.unpack('<3d', self._read(controller + CONTROLLER_ROTATION, 24))
        except OSError:
            k32.CloseHandle(self.handle)
            self.handle = None
            return None
        if not all(math.isfinite(v) and abs(v) < 1e7 for v in (x, y, z)):
            return None
        return x, y, z, yaw


if __name__ == '__main__':
    import time
    r = LiveReader()
    for _ in range(5):
        print(r.position())
        time.sleep(0.5)
