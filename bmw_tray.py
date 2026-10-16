"""System tray icon for BMW Guide, built on raw Win32 calls so no extra packages are needed."""
import ctypes
import ctypes.wintypes as wt
import queue
import threading

WM_DESTROY, WM_COMMAND, WM_USER, WM_CLOSE = 0x0002, 0x0111, 0x0400, 0x0010
WM_TRAY = WM_USER + 20
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
MF_STRING, MF_SEPARATOR = 0, 0x800
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100
IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x10, 0x40

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32 = ctypes.WinDLL('user32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.CreateWindowExW.restype = wt.HWND
user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
user32.LoadImageW.restype = wt.HANDLE
user32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.CreatePopupMenu.restype = wt.HMENU
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.LPVOID]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [('style', wt.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
                ('hInstance', wt.HINSTANCE), ('hIcon', wt.HICON), ('hCursor', wt.HANDLE), ('hbrBackground', wt.HBRUSH),
                ('lpszMenuName', wt.LPCWSTR), ('lpszClassName', wt.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('hWnd', wt.HWND), ('uID', wt.UINT), ('uFlags', wt.UINT),
                ('uCallbackMessage', wt.UINT), ('hIcon', wt.HICON), ('szTip', wt.WCHAR * 128)]


class Tray:
    """Runs a tray icon on its own thread; menu picks are queued as action names for the Tk thread to handle."""

    def __init__(self, icon_path, tooltip, menu):
        self.icon_path, self.tooltip = str(icon_path), tooltip
        self.menu = menu
        self.events = queue.Queue()
        self.hwnd = None
        self._proc = WNDPROC(self._wndproc)
        threading.Thread(target=self._run, daemon=True).start()

    def set_menu(self, menu):
        self.menu = menu

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam == WM_LBUTTONUP:
                self.events.put('toggle')
            elif lparam == WM_RBUTTONUP:
                self._popup(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _popup(self, hwnd):
        menu = user32.CreatePopupMenu()
        for i, (label, _) in enumerate(self.menu):
            if label is None:
                user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            else:
                user32.AppendMenuW(menu, MF_STRING, i + 1, label)
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        pick = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD, pt.x, pt.y, 0, hwnd, None)
        user32.DestroyMenu(menu)
        if pick:
            self.events.put(self.menu[pick - 1][1])

    def _run(self):
        hinst = kernel32.GetModuleHandleW(None)
        cls = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName='BMWGuideTray')
        user32.RegisterClassW(ctypes.byref(cls))
        self.hwnd = user32.CreateWindowExW(0, 'BMWGuideTray', 'BMW Guide tray', 0, 0, 0, 0, 0, None, None, hinst, None)
        icon = user32.LoadImageW(None, self.icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        self.data = NOTIFYICONDATAW(cbSize=ctypes.sizeof(NOTIFYICONDATAW), hWnd=self.hwnd, uID=1,
                                    uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP, uCallbackMessage=WM_TRAY, hIcon=icon,
                                    szTip=self.tooltip)
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.data))
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.data))

    def close(self):
        """Removes the icon so it does not linger in the tray after the app exits."""
        if self.hwnd:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.data))
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
