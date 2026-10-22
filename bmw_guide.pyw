"""BMW Guide: always-on-top Black Myth: Wukong progression checklist that auto-ticks from the save file."""
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import bmw_minimap
import bmw_save
import bmw_tray

HERE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
BUNDLE = Path(getattr(sys, '_MEIPASS', HERE))
DATA = HERE / 'data' if (HERE / 'data').is_dir() else BUNDLE / 'data'
ICON = BUNDLE / 'assets' / 'BMW.ico'
STATE_PATH = Path(os.environ.get('APPDATA', HERE)) / 'BMW-Guide' / 'state.json'
HOTKEYS = {1: 0x78, 2: 0x79, 3: 0x7A, 4: 0xC0, 5: 0x7B}  # F9 show/hide, F10 compact/full, F11 minimap, ` mouse lock, F12 full map
GWL_EXSTYLE, WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE = -20, 0x20, 0x80000, 0x08000000
MINI_COUNT = 3
SAVE_POLL_MS = 3000
ALPHA = 0.9
WIDTH, HEIGHT = 300, 520
FONT = 'Segoe UI'

BG, PANEL, HOVER, LINE = '#121010', '#1c1814', '#262019', '#2e2720'
TEXT, DIM, GOLD, DONE, NEXT_BG, AUTO = '#e6dccb', '#857a6a', '#d9a441', '#544c41', '#2a2217', '#4fae9b'
TAG_COLORS = {'Boss': '#e0664f', 'Tinh phách': '#a58be6', 'Spirit': '#a58be6', 'Vật phẩm': '#5fb3d9', 'Item': '#5fb3d9',
              'Phép': '#7fd17f', 'Spell': '#7fd17f', 'Nhiệm vụ': '#d9a441', 'Quest': '#d9a441', 'Ẩn': '#d97fb8',
              'Secret': '#d97fb8', 'NPC': '#c9c0ae', 'Thiền': '#6fc7b8', 'Meditation': '#6fc7b8',
              'Cốt truyện': '#f2e6c9', 'Story': '#f2e6c9'}
TIP_TAGS = {'Mẹo', 'Tip'}
STORY_TAGS = {'Cốt truyện', 'Story'}
TOKEN = re.compile(r'\s*@(\w+):(\d+)')

UI = {
    'vi': {'map': 'Bản đồ (F11)', 'map_wait': 'Đang chờ game…\nMở game ở chế độ Borderless', 'map_none': 'Chưa có bản đồ cho khu này', 'map_other': 'ở khu khác', 'tray_toggle': 'Ẩn / hiện (F9)', 'tray_mouse': 'Khoá / mở chuột (`)', 'tray_full': 'Toàn bản đồ (F12)', 'map_nopos': 'Mục này chưa có vị trí trên map',
           'title': '` chuột · F9 ẩn · F10 gọn · F11/F12 map', 'lang': 'Ngôn ngữ', 'pick': 'Chọn file save…', 'auto': 'Tự tìm save',
           'reload': 'Tải lại checklist', 'quit': 'Thoát', 'hide': 'Ẩn mục đã xong', 'nosave': 'Chưa tìm thấy save — ⚙ để chọn',
           'searching': 'Đang tìm save…', 'save': 'Save', 'manual': 'chọn tay', 'autolbl': 'tự động',
           'chapter_done': 'Xong chương này ✓', 'badsave': 'Không đọc được save', 'missing': 'Thiếu file checklist'},
    'en': {'map': 'Minimap (F11)', 'map_wait': 'Waiting for the game…\nRun it in Borderless mode', 'map_none': 'No map for this area', 'map_other': 'in another area', 'tray_toggle': 'Show / hide (F9)', 'tray_mouse': 'Lock / unlock mouse (`)', 'tray_full': 'Full map (F12)', 'map_nopos': 'No map location for this entry',
           'title': '` mouse · F9 hide · F10 compact · F11/F12 map', 'lang': 'Language', 'pick': 'Choose save file…', 'auto': 'Find save automatically',
           'reload': 'Reload checklist', 'quit': 'Quit', 'hide': 'Hide completed', 'nosave': 'No save found — use ⚙ to pick one',
           'searching': 'Searching for save…', 'save': 'Save', 'manual': 'manual', 'autolbl': 'auto',
           'chapter_done': 'Chapter complete ✓', 'badsave': 'Could not read save', 'missing': 'Checklist file missing'},
}


class Heading(str):
    """Section title that also carries its @shrine token."""

    def __new__(cls, text, tokens):
        obj = super().__new__(cls, text)
        obj.tokens = tokens
        return obj


def parse(md):
    """Parses a checklist into [(chapter, [(section, [(key, tag, text, tokens)])])] with language-independent keys."""
    chapters, sections, items = [], None, None
    for raw in md.splitlines():
        line = raw.strip()
        if line.startswith('## '):
            sections = []
            chapters.append((line[3:].strip(), sections))
            items = None
        elif line.startswith('### ') and sections is not None:
            items = []
            head = line[4:].strip()
            sections.append((Heading(TOKEN.sub('', head).strip(), {(c, int(i)) for c, i in TOKEN.findall(head)}), items))
        elif items is not None:
            m = re.match(r'^(?:\d+\.|-)\s+(.+)', line)
            if not m:
                continue
            text = m.group(1)
            tokens = {(c, int(i)) for c, i in TOKEN.findall(text)}
            text = TOKEN.sub('', text).replace('~~', '').replace('`', '').strip()
            tag = ''
            t = re.match(r'^\[([^\]]+)\]\s*(.*)', text)
            if t:
                tag, text = t.group(1), t.group(2)
            key = f'{len(chapters) - 1}.{len(sections) - 1}.{len(items)}'
            items.append((key, tag, text, tokens))
    return chapters


class Overlay:
    """Borderless topmost checklist window with global hotkeys and save-file auto-ticking."""

    def __init__(self):
        self.state = self.load_state()
        self.lang = self.state.get('lang', 'vi')
        self.auto = set()
        self.shrines = set()
        self.save_file = None
        self.save_mtime = None
        self.save_status = ''
        self.found_saves = None
        self.last_chapter = None
        self.root = tk.Tk()
        self.root.title('BMW Guide')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True, '-alpha', ALPHA)
        self.root.configure(bg=BG)
        self.root.attributes('-transparentcolor', bmw_minimap.KEY)
        if ICON.exists():
            self.root.iconbitmap(str(ICON))
        x, y = self.state.get('pos', (40, 80))
        self.root.geometry(f'{WIDTH}x{HEIGHT}+{x}+{y}')
        self.visible = True
        self.scroll_target = 0.0
        self.scroll_anim = None
        self.build_chrome()
        self.root.after(50, self.round_corners)
        self.root.after(60, self.apply_mouse_mode)
        self.reload()
        self.minimap = bmw_minimap.Minimap(self.map_frame, BUNDLE / 'assets', self.state, self.save_state, self.t,
                                           lambda: self.lang, WIDTH)
        self.apply_mode()
        self.start_hotkey_thread()
        self.tray = bmw_tray.Tray(ICON, 'BMW Guide', self.tray_menu())
        self.start_save_search()
        self.root.after(500, self.poll_save)
        self.root.after(2000, self.keep_on_top)

    def t(self, key):
        return UI[self.lang][key]

    def load_state(self):
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def save_state(self):
        self.state['pos'] = (self.root.winfo_x(), self.root.winfo_y())
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')

    def apply_mouse_mode(self):
        """Never lets the overlay take focus from the game; while locked, mouse input passes through to the game."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) | WS_EX_NOACTIVATE | WS_EX_LAYERED
            if self.state.get('mouse_locked', True):
                style |= WS_EX_TRANSPARENT
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
        except (AttributeError, OSError):
            pass
        icon = '🔒' if self.state.get('mouse_locked', True) else '🖱'
        self.title_lbl.configure(text=f"{icon} {self.t('title')}")

    def toggle_mouse(self):
        self.state['mouse_locked'] = not self.state.get('mouse_locked', True)
        self.save_state()
        self.apply_mouse_mode()
        if not self.state['mouse_locked']:
            self.move_cursor_here()

    def move_cursor_here(self):
        """Puts the mouse cursor in the middle of the overlay so it can be used right after unlocking."""
        try:
            user32 = ctypes.windll.user32
            rect = wt.RECT()
            user32.GetWindowRect(user32.GetParent(self.root.winfo_id()), ctypes.byref(rect))
            user32.SetCursorPos((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        except (AttributeError, OSError):
            pass

    def round_corners(self):
        """Asks Windows 11 DWM to round the borderless window's corners."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except (AttributeError, OSError):
            pass

    def flat_button(self, parent, text, command, fg=DIM, bg=PANEL, **kw):
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, 8), cursor='hand2', **kw)
        b.bind('<Button-1>', lambda e: command())
        b.bind('<Enter>', lambda e: b.configure(fg=TEXT))
        b.bind('<Leave>', lambda e: b.configure(fg=b.base_fg))
        b.base_fg = fg
        return b

    def build_chrome(self):
        """Creates the drag bar, settings menu, chapter tabs, progress bar, list body and save status."""
        self.bar_frame = bar = tk.Frame(self.root, bg=PANEL)
        bar.pack(fill='x')
        self.title_lbl = tk.Label(bar, bg=PANEL, fg=DIM, font=(FONT, 8))
        self.title_lbl.pack(side='left', padx=8, pady=3)
        for w in (bar, self.title_lbl):
            w.bind('<ButtonPress-1>', self.start_drag)
            w.bind('<B1-Motion>', self.drag)
            w.bind('<ButtonRelease-1>', lambda e: self.save_state())
        self.flat_button(bar, '✕', self.quit, padx=6).pack(side='right')
        self.flat_button(bar, '—', self.toggle, padx=4).pack(side='right')
        self.flat_button(bar, '▭', self.toggle_compact, padx=4).pack(side='right')
        self.hide_btn = self.flat_button(bar, '', self.toggle_hide_done, padx=4)
        self.hide_btn.pack(side='right')
        self.flat_button(bar, '⚙', self.open_menu, padx=4).pack(side='right')

        self.map_frame = tk.Frame(self.root, bg=bmw_minimap.KEY)
        if self.state.get('map_visible', True):
            self.map_frame.pack(fill='x', after=bar)
        self.mini = tk.Frame(self.root, bg=BG)
        self.full = tk.Frame(self.root, bg=BG)
        self.full.pack(fill='both', expand=True)
        self.tabs = tk.Frame(self.full, bg=BG)
        self.tabs.pack(fill='x', padx=6, pady=(6, 2))
        head = tk.Frame(self.full, bg=BG)
        head.pack(fill='x', padx=8)
        self.chapter_lbl = tk.Label(head, bg=BG, fg=TEXT, font=(FONT, 10, 'bold'), anchor='w')
        self.chapter_lbl.pack(side='left')
        self.stat = tk.Label(head, bg=BG, fg=GOLD, font=(FONT, 8, 'bold'))
        self.stat.pack(side='right')
        self.bar = tk.Canvas(self.full, height=3, bg=LINE, highlightthickness=0)
        self.bar.pack(fill='x', padx=8, pady=(2, 4))
        self.bar_fill = self.bar.create_rectangle(0, 0, 0, 3, fill=GOLD, width=0)
        self.save_lbl = tk.Label(self.full, bg=PANEL, fg=DIM, font=(FONT, 7), anchor='w', cursor='hand2')
        self.save_lbl.pack(side='bottom', fill='x')
        self.save_lbl.bind('<Button-1>', lambda e: self.open_menu())
        self.canvas = tk.Canvas(self.full, bg=BG, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.body_id, width=e.width))
        self.root.bind_all('<MouseWheel>', self.on_wheel)

    def open_menu(self):
        """Shows the settings popup: language, save file selection, reload, quit."""
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=TEXT, activebackground=GOLD, activeforeground=BG, bd=0)
        lang = tk.Menu(m, tearoff=0, bg=PANEL, fg=TEXT, activebackground=GOLD, activeforeground=BG)
        for code, label in (('vi', 'Tiếng Việt'), ('en', 'English')):
            lang.add_radiobutton(label=label, value=code, variable=tk.StringVar(value=self.lang),
                                 command=lambda c=code: self.set_lang(c))
        m.add_cascade(label=self.t('lang'), menu=lang)
        m.add_separator()
        m.add_command(label=self.t('map'), command=self.toggle_map)
        m.add_separator()
        m.add_command(label=self.t('pick'), command=self.pick_save)
        m.add_command(label=self.t('auto'), command=self.use_auto_save)
        m.add_command(label=self.t('reload'), command=self.reload)
        m.add_separator()
        m.add_command(label=self.t('quit'), command=self.quit)
        m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def set_lang(self, code):
        self.lang = self.state['lang'] = code
        self.save_state()
        self.reload()
        self.tray.set_menu(self.tray_menu())

    def pick_save(self):
        start = self.save_file.parent if self.save_file else Path.home()
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(start), title=self.t('pick'),
                                          filetypes=[('Black Myth save', 'ArchiveSaveFile.*.sav'), ('*.sav', '*.sav')])
        self.root.attributes('-topmost', True)
        if path:
            self.state['save_path'] = path
            self.save_state()
            self.save_mtime = None
            self.poll_save(reschedule=False)

    def use_auto_save(self):
        self.state.pop('save_path', None)
        self.save_state()
        self.save_mtime = None
        self.start_save_search()

    def start_save_search(self):
        """Searches drives for save files on a background thread."""
        self.found_saves = None
        self.save_status = self.t('searching')

        def work():
            try:
                self.found_saves = bmw_save.find_saves()
            except OSError:
                self.found_saves = []
        threading.Thread(target=work, daemon=True).start()

    def current_save(self):
        manual = self.state.get('save_path')
        if manual:
            return Path(manual), True
        if self.found_saves:
            newest = max(self.found_saves, key=lambda f: f.stat().st_mtime if f.exists() else 0)
            return newest, False
        return None, False

    def poll_save(self, reschedule=True):
        """Re-reads the save only when its modification time changes."""
        path, manual = self.current_save()
        if path is None:
            if self.found_saves is not None:
                self.save_status = self.t('nosave')
        else:
            try:
                mtime = path.stat().st_mtime
                if path != self.save_file or mtime != self.save_mtime:
                    progress = bmw_save.read_progress(path)
                    self.save_file, self.save_mtime = path, mtime
                    self.apply_progress(progress)
                stamp = time.strftime('%H:%M', time.localtime(self.save_mtime))
                mode = self.t('manual') if manual else self.t('autolbl')
                self.save_status = f'💾 {path.name} · {stamp} · {mode}'
            except (OSError, ValueError, IndexError):
                self.save_status = self.t('badsave')
        self.save_lbl.configure(text=f' {self.save_status}')
        if reschedule:
            self.root.after(SAVE_POLL_MS, self.poll_save)

    def apply_progress(self, progress):
        """Marks every checklist item whose @category:id token is present in the save."""
        if hasattr(self, 'minimap'):
            self.minimap.update_from_save(progress, str(self.save_file))
        owned = {(cat, i) for cat, ids in progress.items() if isinstance(ids, set) for i in ids}
        self.shrines = {i for cat, i in owned if cat == 'shrine'}
        loose = progress['item'] | progress['equip'] | progress['spell'] | progress['wine'] | progress['relic']
        owned |= {(cat, i) for cat in ('item', 'equip') for i in loose}
        owned |= self.remember_owned(owned, len(progress['card']))
        self.auto = {key for _, sections in self.chapters for _, items in sections
                     for key, _, _, tokens in items if tokens & owned}
        chapter = progress.get('chapter', 0) // 10 - 1
        if chapter != self.last_chapter and 0 <= chapter < len(self.chapters):
            self.last_chapter = chapter
            if self.state.get('follow_save', True):
                self.select(chapter)
                return
        self.refresh()

    def start_drag(self, e):
        self.drag_off = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag(self, e):
        self.root.geometry(f'+{e.x_root - self.drag_off[0]}+{e.y_root - self.drag_off[1]}')

    def toggle_map(self):
        """Shows or hides the round minimap above the checklist."""
        visible = not self.state.get('map_visible', True)
        self.state['map_visible'] = visible
        self.save_state()
        if visible:
            self.map_frame.pack(fill='x', after=self.bar_frame)
        else:
            self.map_frame.pack_forget()
        self.apply_mode()

    def map_height(self):
        return self.minimap.h if self.state.get('map_visible', True) and hasattr(self, 'minimap') else 0

    def on_wheel(self, e):
        if hasattr(self, 'minimap') and e.widget is self.minimap.canvas:
            self.minimap.zoom_by(1 if e.delta > 0 else -1)
            return
        """Eases the list toward the wheel target instead of jumping."""
        top, bottom = self.canvas.yview()
        span = bottom - top
        if span >= 1:
            return
        if self.scroll_anim is None:
            self.scroll_target = top
        self.scroll_target = min(max(self.scroll_target - e.delta / 120 * span * 0.25, 0), 1 - span)
        if self.scroll_anim is None:
            self.animate_scroll()

    def animate_scroll(self):
        top = self.canvas.yview()[0]
        step = (self.scroll_target - top) * 0.3
        if abs(step) < 0.0005:
            self.canvas.yview_moveto(self.scroll_target)
            self.scroll_anim = None
            return
        self.canvas.yview_moveto(top + step)
        self.scroll_anim = self.root.after(12, self.animate_scroll)

    def reload(self):
        """Re-reads the checklist for the current language and redraws everything."""
        self.title_lbl.configure(text=self.t('title'))
        self.root.after(10, self.apply_mouse_mode)
        path = DATA / f'checklist.{self.lang}.md'
        try:
            self.chapters = parse(path.read_text(encoding='utf-8'))
        except OSError:
            self.chapters = [(f"{self.t('missing')}: {path.name}", [])]
        for w in self.tabs.winfo_children():
            w.destroy()
        for i, (name, _) in enumerate(self.chapters):
            short = re.sub(r'^\D*?(\d+).*', r'\1', name)
            tab = tk.Label(self.tabs, text=short, font=(FONT, 9, 'bold'), width=3, pady=1, cursor='hand2')
            tab.bind('<Button-1>', lambda e, i=i: self.select(i))
            tab.pack(side='left', padx=1, expand=True, fill='x')
        if self.save_file:
            self.save_mtime = None
        self.select(min(self.state.get('ch', 0), len(self.chapters) - 1))
        self.apply_mode()

    def select(self, i):
        self.state['ch'] = i
        for j, tab in enumerate(self.tabs.winfo_children()):
            tab.configure(bg=GOLD if j == i else PANEL, fg=BG if j == i else DIM)
        self.render()
        self.canvas.yview_moveto(0)
        self.scroll_target = 0.0

    def remember_owned(self, owned, journal_size):
        """Keeps items ticked after they are used up or handed over; resets when the save restarts."""
        save_id = str(self.save_file)
        memory = self.state.setdefault('seen', {})
        record = memory.get(save_id, {'journal': 0, 'tokens': []})
        if journal_size < record['journal']:
            record = {'journal': 0, 'tokens': []}
        seen = {tuple(t) for t in record['tokens']} | {t for t in owned if t[0] in ('item', 'equip')}
        memory[save_id] = {'journal': journal_size, 'tokens': sorted(seen)}
        self.save_state()
        return seen

    def is_done(self, key):
        return key in self.auto

    def render(self):
        """Builds the active chapter's sections and rows once; later ticks update in place."""
        for w in self.body.winfo_children():
            w.destroy()
        hide = self.state.get('hide', False)
        self.hide_btn.configure(text='◐' if hide else '○')
        self.hide_btn.base_fg = GOLD if hide else DIM
        self.hide_btn.configure(fg=self.hide_btn.base_fg)
        name, sections = self.chapters[self.state['ch']]
        self.chapter_lbl.configure(text=re.sub(r'^\D*\d+\s*-?\s*', '', name) or name)
        self.rows, self.sections, self.order = {}, [], []
        self.row_frames, self.row_section = {}, {}
        for sec_name, items in sections:
            box = tk.Frame(self.body, bg=BG)
            box.pack(fill='x', padx=4, pady=(4, 0))
            head = tk.Frame(box, bg=BG, cursor='hand2')
            head.pack(fill='x')
            arrow = tk.Label(head, bg=BG, fg=DIM, font=(FONT, 7))
            arrow.pack(side='left', padx=(2, 4))
            smark = tk.Label(head, bg=BG, font=(FONT, 8))
            if sec_name.tokens:
                smark.pack(side='left')
            title = tk.Label(head, text=sec_name, bg=BG, fg=GOLD, font=(FONT, 9, 'bold'), cursor='hand2')
            title.pack(side='left')
            count = tk.Label(head, bg=BG, fg=DIM, font=(FONT, 7))
            count.pack(side='right', padx=4)
            rows_frame = tk.Frame(box, bg=BG)
            sec = {'items': [it for it in items if it[1] not in TIP_TAGS and it[3]], 'count': count, 'arrow': arrow,
                   'rows': rows_frame, 'head': head, 'open': None, 'smark': smark, 'shrine': sec_name.tokens}
            for w in (head, arrow, smark, count):
                w.bind('<Button-1>', lambda e, s=sec: self.set_open(s, not s['open']))
            title.bind('<Button-1>', lambda e, n=sec_name: self.focus_on(n.tokens, n, shrine=True))
            for item in items:
                self.add_row(rows_frame, item, hide, sec_name)
                self.order.append((sec_name, item))
                self.row_section[item[0]] = sec
            self.sections.append(sec)
            self.set_open(sec, any(not self.is_done(it[0]) for it in sec['items']) or not sec['items'])
        self.refresh()

    def set_open(self, sec, is_open):
        sec['open'] = is_open
        sec['arrow'].configure(text='▼' if is_open else '▶')
        if is_open:
            sec['rows'].pack(fill='x', after=sec['head'])
        else:
            sec['rows'].pack_forget()

    def add_row(self, parent, item, hide, area=None):
        key, tag, text, tokens = item
        row = tk.Frame(parent, bg=BG, cursor='hand2')
        row.pack(fill='x', pady=0)
        self.row_frames[key] = row
        if tag in TIP_TAGS:
            tk.Label(row, text=f'💡 {text}', bg=BG, fg=DIM, font=(FONT, 8, 'italic'), anchor='w', justify='left',
                     wraplength=WIDTH - 40).pack(side='left', fill='x', padx=(22, 4))
            row.configure(cursor='')
            return
        if not tokens:
            story = tag in STORY_TAGS
            parts = [tk.Label(row, text='➤' if story else '·', bg=BG, fg=GOLD if story else DIM, font=(FONT, 9), width=2)]
            if tag:
                parts.append(tk.Label(row, text=tag, bg=BG, fg=GOLD if story else DIM, font=(FONT, 7, 'bold' if story else 'normal')))
            parts.append(tk.Label(row, text=text, bg=BG, fg=TEXT if story else DIM, font=(FONT, 9, 'bold' if story else 'normal'),
                                  anchor='w', justify='left', wraplength=WIDTH - 110))
            for w in parts:
                w.pack(side='left', anchor='n', fill='x' if w is parts[-1] else None, pady=2 if w is parts[1] and tag else 0)
            for w in (row, *parts):
                w.bind('<Button-1>', lambda e, t=tokens, x=text: self.focus_on(t, x, area=area))
            return
        mark = tk.Label(row, bg=BG, font=(FONT, 9), width=2)
        mark.pack(side='left', anchor='n')
        tag_lbl = tk.Label(row, text=tag, bg=BG, font=(FONT, 7, 'bold')) if tag else None
        if tag_lbl:
            tag_lbl.pack(side='left', anchor='n', pady=2)
        lbl = tk.Label(row, text=text, bg=BG, anchor='w', justify='left', wraplength=WIDTH - 110)
        lbl.pack(side='left', fill='x', anchor='n')
        widgets = [w for w in (row, mark, tag_lbl, lbl) if w]
        self.rows[key] = {'row': row, 'mark': mark, 'tag_lbl': tag_lbl, 'tag': tag, 'lbl': lbl, 'widgets': widgets, 'hover': False}
        for w in widgets:
            w.bind('<Button-1>', lambda e, t=tokens, x=text: self.focus_on(t, x, area=area))
            w.bind('<Enter>', lambda e, k=key: self.hover(k, True))
            w.bind('<Leave>', lambda e, k=key: self.hover(k, False))
        if hide and self.is_done(key):
            row.pack_forget()

    def focus_on(self, tokens, text, shrine=False, area=None):
        """Jumps the minimap to where a checklist line can be found, falling back to its area's shrine."""
        found = self.minimap.locate(self.state['ch'], tokens, str(text), shrine)
        if not found and area is not None:
            found = self.minimap.locate(self.state['ch'], area.tokens, str(area), True)
        if self.minimap.focus(found):
            if not self.state.get('map_visible', True):
                self.toggle_map()
            return
        self.save_lbl.configure(text=f" {self.t('map_nopos')}")
        self.root.after(2500, lambda: self.save_lbl.configure(text=f' {self.save_status}'))

    def toggle_full_map(self):
        """Opens or closes the large full-map window; it unlocks the mouse so points can be clicked."""
        if getattr(self, 'full_map', None):
            self.full_map.close()
            return
        self.full_map = bmw_minimap.FullMap(self.root, self.minimap, self.full_map_closed, self.show_point_line)
        if self.state.get('mouse_locked', True):
            self.toggle_mouse()

    def full_map_closed(self):
        self.full_map = None

    def show_point_line(self, level, pt):
        """Scrolls the checklist to the line that matches a map point picked on the full map."""
        match = self.line_for_point(level, pt)
        if match is None:
            return
        chapter, key = match
        if chapter != self.state['ch']:
            self.select(chapter)
        sec = self.row_section.get(key)
        if sec and not sec['open']:
            self.set_open(sec, True)
        row = self.row_frames.get(key)
        if row is None:
            return
        self.root.update_idletasks()
        total = max(self.body.winfo_height(), 1)
        offset = row.winfo_rooty() - self.body.winfo_rooty()
        top = min(max((offset - 40) / total, 0), 1)
        self.canvas.yview_moveto(top)
        self.scroll_target = self.canvas.yview()[0]
        self.flash_row(row, 6)

    def flash_row(self, row, times):
        """Blinks a checklist row so the line picked from the map is easy to spot."""
        if not row.winfo_exists():
            return
        colour = NEXT_BG if times % 2 == 0 else BG
        for w in (row, *row.winfo_children()):
            w.configure(bg=colour)
        if times:
            self.root.after(250, lambda: self.flash_row(row, times - 1))
        else:
            self.refresh()

    def line_for_point(self, level, pt):
        """Finds (chapter, line key) for a map point by game id first, then by its name appearing in the line."""
        ref = self.minimap.point_ids.get(f'{level}:{pt[0]}')
        wanted = set()
        if ref:
            src, gid = ref[0], ref[1]
            wanted = {('soul', gid), ('item', gid)} if src == 'item' else {(src, gid)}
            if src in ('item', 'equip'):
                wanted |= {('item', gid), ('equip', gid)}
        name = bmw_minimap._norm(re.sub(r'\s*×\d+$', '', pt[7]))
        own = [ch for ch, levels in bmw_minimap.CHAPTER_LEVELS.items() if level in levels]
        order = own + [i for i in range(len(self.chapters)) if i not in own]
        for by_name in (False, True):
            for ci in order:
                for _, items in self.chapters[ci][1]:
                    for key, tag, text, tokens in items:
                        if tag in TIP_TAGS:
                            continue
                        if not by_name and tokens & wanted:
                            return ci, key
                        if by_name and len(name) >= 4 and name in bmw_minimap._norm(text) and \
                                (ci in own or not own) and name not in bmw_minimap.GENERIC_NAMES:
                            return ci, key
        return None

    def hover(self, key, on):
        self.rows[key]['hover'] = on
        self.style_row(key)

    def style_row(self, key):
        r = self.rows[key]
        is_done = self.is_done(key)
        bg = HOVER if r['hover'] else NEXT_BG if key == self.next_id else BG
        for w in r['widgets']:
            w.configure(bg=bg)
        r['mark'].configure(text='◆' if is_done else '◇', fg=AUTO if is_done else GOLD)
        if r['tag_lbl']:
            r['tag_lbl'].configure(fg=DONE if is_done else TAG_COLORS.get(r['tag'], DIM))
        r['lbl'].configure(fg=DONE if is_done else TEXT, font=(FONT, 9, 'overstrike') if is_done else (FONT, 9))

    def refresh(self):
        """Updates row styles, the next-step highlight, section counters and the progress bar."""
        if not hasattr(self, 'rows'):
            return
        self.next_id = next((k for k in self.rows if not self.is_done(k)), None)
        for key in self.rows:
            self.style_row(key)
        total = finished = 0
        for sec in self.sections:
            n = sum(1 for it in sec['items'] if self.is_done(it[0]))
            total += len(sec['items'])
            finished += n
            full = n == len(sec['items']) and n > 0
            sec['count'].configure(text=f'{n}/{len(sec["items"])}' if sec['items'] else '', fg=GOLD if full else DIM)
            if sec['shrine']:
                active = any(i in self.shrines for _, i in sec['shrine'])
                sec['smark'].configure(text='⛩' if active else '·', fg=AUTO if active else DIM)
        self.stat.configure(text=f'{finished}/{total}')
        self.root.update_idletasks()
        w = self.bar.winfo_width()
        self.bar.coords(self.bar_fill, 0, 0, w * finished / total if total else 0, 3)
        self.progress = f'{finished}/{total}'
        if self.state.get('compact'):
            self.render_mini()

    def render_mini(self):
        """Shows only the next few unticked steps, plus the tips that follow the first one."""
        for w in self.mini.winfo_children():
            w.destroy()
        name = self.chapters[self.state['ch']][0]
        top = tk.Frame(self.mini, bg=BG)
        top.pack(fill='x', padx=8, pady=(4, 0))
        tk.Label(top, text=re.sub(r'\s*-.*', '', name), bg=BG, fg=DIM, font=(FONT, 8)).pack(side='left')
        tk.Label(top, text=self.progress, bg=BG, fg=GOLD, font=(FONT, 8, 'bold')).pack(side='right')
        shown, last_sec, tips_for_first = 0, None, True
        for sec_name, (key, tag, text, tokens) in self.order:
            if tag in TIP_TAGS:
                if shown == 1 and tips_for_first:
                    tk.Label(self.mini, text=f'💡 {text}', bg=BG, fg=DIM, font=(FONT, 8, 'italic'), anchor='w',
                             justify='left', wraplength=WIDTH - 40).pack(fill='x', padx=(26, 6))
                continue
            if shown == 1:
                tips_for_first = False
            if self.is_done(key) or not tokens:
                continue
            if shown == MINI_COUNT:
                break
            if sec_name != last_sec:
                tk.Label(self.mini, text=sec_name, bg=BG, fg=GOLD, font=(FONT, 8, 'bold'), anchor='w').pack(fill='x', padx=8, pady=(3, 0))
                last_sec = sec_name
            row = tk.Frame(self.mini, bg=NEXT_BG if shown == 0 else BG)
            row.pack(fill='x', padx=4)
            parts = [tk.Label(row, text='◇', fg=GOLD, font=(FONT, 9), width=2)]
            if tag:
                parts.append(tk.Label(row, text=tag, fg=TAG_COLORS.get(tag, DIM), font=(FONT, 7, 'bold')))
            parts.append(tk.Label(row, text=text, fg=TEXT, font=(FONT, 9), anchor='w', justify='left', wraplength=WIDTH - 110))
            for w in parts:
                w.configure(bg=row['bg'])
                w.pack(side='left', anchor='n', pady=1 if w is parts[-1] else 0)
            shown += 1
        if not shown:
            tk.Label(self.mini, text=self.t('chapter_done'), bg=BG, fg=GOLD, font=(FONT, 9)).pack(pady=4)
        self.root.update_idletasks()
        h = self.bar_frame.winfo_reqheight() + self.map_height() + self.mini.winfo_reqheight() + 6
        self.root.geometry(f'{WIDTH}x{h}')

    def apply_mode(self):
        if self.state.get('compact'):
            self.full.pack_forget()
            self.mini.pack(fill='x')
            self.render_mini()
        else:
            self.mini.pack_forget()
            self.full.pack(fill='both', expand=True)
            self.root.geometry(f'{WIDTH}x{HEIGHT + self.map_height()}')

    def toggle_compact(self):
        self.state['compact'] = not self.state.get('compact', False)
        self.save_state()
        self.apply_mode()

    def toggle_hide_done(self):
        self.state['hide'] = not self.state.get('hide', False)
        self.save_state()
        y = self.canvas.yview()[0]
        self.render()
        self.canvas.yview_moveto(y)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.root.deiconify()
            self.root.attributes('-topmost', True)
            self.root.after(10, self.apply_mouse_mode)
        else:
            self.root.withdraw()

    def keep_on_top(self):
        """Re-asserts topmost because borderless-fullscreen games sometimes steal it."""
        if self.visible:
            self.root.attributes('-topmost', True)
        self.root.after(2000, self.keep_on_top)

    def start_hotkey_thread(self):
        """Registers global hotkeys on a background thread and forwards presses to Tk."""
        def loop():
            user32 = ctypes.windll.user32
            for hk_id, vk in HOTKEYS.items():
                user32.RegisterHotKey(None, hk_id, 0x4000, vk)  # MOD_NOREPEAT
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    self.hotkey_pressed[msg.wParam].set()
        self.hotkey_pressed = {hk_id: threading.Event() for hk_id in HOTKEYS}
        threading.Thread(target=loop, daemon=True).start()
        self.poll_hotkey()

    def poll_hotkey(self):
        """Handles hotkey presses on the Tk thread, since Tk is not thread-safe."""
        for hk_id, action in ((1, self.toggle), (2, self.toggle_compact), (3, self.toggle_map), (4, self.toggle_mouse),
                              (5, self.toggle_full_map)):
            if self.hotkey_pressed[hk_id].is_set():
                self.hotkey_pressed[hk_id].clear()
                action()
        actions = {'toggle': self.toggle, 'mouse': self.toggle_mouse, 'map': self.toggle_map, 'full': self.toggle_full_map,
                   'quit': self.quit}
        while hasattr(self, 'tray') and not self.tray.events.empty():
            actions[self.tray.events.get()]()
        self.root.after(50, self.poll_hotkey)

    def tray_menu(self):
        return [(self.t('tray_toggle'), 'toggle'), (self.t('tray_mouse'), 'mouse'), (self.t('map'), 'map'), (self.t('tray_full'), 'full'),
                (None, None), (self.t('quit'), 'quit')]

    def quit(self):
        self.save_state()
        if hasattr(self, 'tray'):
            self.tray.close()
        self.root.destroy()


def single_instance():
    """Returns False if another BMW Guide is already running."""
    ctypes.windll.kernel32.CreateMutexW(None, False, 'BMWGuideOverlayMutex')
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


if __name__ == '__main__':
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    if single_instance():
        Overlay().root.mainloop()
