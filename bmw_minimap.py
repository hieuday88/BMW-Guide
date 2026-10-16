"""Live minimap window: map image around the player, with points already done in the save hidden."""
import json
import math
import tkinter as tk

import bmw_live

SIZE = 240
TICK_MS = 120
LEARN_RADIUS = 3500
ICON_SUBSAMPLE = 14
MAP_PX = 1024
MAP_LEVELS = {10: 'HFS01_PersistentLevel', 11: 'HFS01_Old_GYCY_YKX_PersistentLevel', 20: 'HFM02_PersistentLevel',
              25: 'HFM_DuJiaoXian_Persist', 30: 'LYS_PersistentLevel', 40: 'PSD_PersistentLevel',
              80: 'ZYS01_persistentlevel', 50: 'HYS_PersistentLevel', 70: 'BSD02_persistentlevel', 98: 'BYS_persistentlevel'}
DOT_COLORS = {'renwu': '#f2e6c9', 'yaojin': '#d9a441', 'cailiao': '#8fb3c9'}
LUOJIA, SANDONG = 1999, 1998
BG, GOLD, DIM = '#121010', '#d9a441', '#857a6a'


def _item_categories(item_id):
    """Maps a newly obtained item id to the minimap point categories it can come from."""
    if item_id == LUOJIA:
        return {'luojia'}
    if item_id == SANDONG:
        return {'sandongchong'}
    if 1000 <= item_id < 1200:
        return {'xiandan', 'baoxiang'}
    if 16000 <= item_id < 17000:
        return {'zhenwan', 'baoxiang'}
    if 18000 <= item_id < 19000:
        return {'hulu', 'baoxiang'}
    if 2000 <= item_id < 2400:
        return {'jiushi', 'baoxiang'}
    if 5000 <= item_id < 6000:
        return {'bianhua'}
    return set()


class Minimap:
    """Borderless topmost minimap that follows the player read live from game memory."""

    def __init__(self, root, assets, state, save_state, texts):
        self.root, self.state, self.save_state, self.texts = root, state, save_state, texts
        self.maps = json.loads((assets / 'maps' / 'maps.json').read_text(encoding='utf-8'))
        self.points = json.loads((assets / 'maps' / 'points.json').read_text(encoding='utf-8'))
        self.map_dir = assets / 'maps'
        self.icons = {}
        for f in (assets / 'map_icons').glob('*.png'):
            self.icons[f.stem] = tk.PhotoImage(file=str(f)).subsample(ICON_SUBSAMPLE)
        self.images = {}
        self.hidden = set(state.setdefault('map_hidden', []))
        self.actors = set()
        self.map_id = 0
        self.prev = None
        self.pos = None
        self.view = None
        self.live = bmw_live.LiveReader()
        self.zoom = state.get('map_zoom', 2)
        self.visible = state.get('map_visible', True)

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True, '-alpha', 0.92)
        x, y = state.get('map_pos', (root.winfo_screenwidth() - SIZE - 40, 80))
        self.win.geometry(f'{SIZE}x{SIZE}+{x}+{y}')
        self.canvas = tk.Canvas(self.win, width=SIZE, height=SIZE, bg=BG, highlightthickness=1, highlightbackground=GOLD)
        self.canvas.pack()
        self.canvas.bind('<ButtonPress-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', lambda e: self.remember_pos())
        self.canvas.bind('<MouseWheel>', self.on_wheel)
        if not self.visible:
            self.win.withdraw()
        self.tick()

    def start_drag(self, e):
        self.drag_off = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def drag(self, e):
        self.win.geometry(f'+{e.x_root - self.drag_off[0]}+{e.y_root - self.drag_off[1]}')

    def remember_pos(self):
        self.state['map_pos'] = (self.win.winfo_x(), self.win.winfo_y())
        self.save_state()

    def on_wheel(self, e):
        self.zoom = min(4, max(1, self.zoom + (1 if e.delta > 0 else -1)))
        self.state['map_zoom'] = self.zoom
        self.save_state()

    def toggle(self):
        self.visible = not self.visible
        self.state['map_visible'] = self.visible
        self.save_state()
        if self.visible:
            self.win.deiconify()
            self.win.attributes('-topmost', True)
        else:
            self.win.withdraw()

    def keep_on_top(self):
        if self.visible:
            self.win.attributes('-topmost', True)

    def update_from_save(self, progress):
        """Refreshes done world objects and learns which map points the newest pickups came from."""
        self.actors = progress['actors']
        self.map_id = progress.get('map_id', 0)
        prev, self.prev = self.prev, progress
        if prev is None or self.pos is None:
            return
        cats = set()
        if progress['card'] - prev['card']:
            cats |= {'boss', 'toumu'}
        if progress['soul'] - prev['soul']:
            cats.add('jingpo')
        if progress['meditation'] - prev['meditation']:
            cats.add('dazuo')
        if any('TreasureBox' in a for a in progress['actors'] - prev['actors']):
            cats |= {'baoxiang', 'cailiao'}
        for item, num in progress['item_num'].items():
            if num > prev['item_num'].get(item, 0):
                cats |= _item_categories(item)
        for item in progress['equip'] - prev['equip']:
            cats |= _item_categories(item)
        if cats:
            self.learn(cats)

    def learn(self, cats):
        """Hides the nearest visible point of the given categories around the player."""
        level = self.current_level()
        x, y, z, _ = self.pos
        best = None
        for i, cat, px, py, pz, key, name in self.points.get(level, []):
            pid = f'{level}:{i}'
            if cat not in cats or pid in self.hidden:
                continue
            d = math.dist((x, y, z), (px, py, pz))
            if d <= LEARN_RADIUS and (best is None or d < best[0]):
                best = (d, pid)
        if best:
            self.hidden.add(best[1])
            self.state['map_hidden'] = sorted(self.hidden)
            self.save_state()

    def current_level(self):
        level = MAP_LEVELS.get(self.map_id)
        if level and self.pos and self.pick_map(level):
            return level
        for m in self.maps:
            if self.pos and self.in_range(m['range'], self.pos):
                return m['level']
        return level

    @staticmethod
    def in_range(rng, pos):
        (x0, y0), (x1, y1) = rng
        return x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1

    def pick_map(self, level):
        """Chooses the map layer for the level, honouring height-based sub-areas (pagodas, caves)."""
        plain = None
        for m in self.maps:
            if m['level'] != level or not self.in_range(m['range'], self.pos):
                continue
            if not m['areas']:
                plain = plain or m
                continue
            for (sx, sy, sz), (ex, ey, ez) in m['areas']:
                if sx <= self.pos[0] <= ex and sy <= self.pos[1] <= ey and sz <= self.pos[2] <= ez:
                    return m
        return plain

    def image(self, name):
        if name not in self.images:
            self.images[name] = tk.PhotoImage(file=str(self.map_dir / name))
        return self.images[name]

    def tick(self):
        try:
            if self.visible:
                self.pos = self.live.position() or self.pos
                self.render()
        finally:
            self.win.after(TICK_MS, self.tick)

    def render(self):
        """Draws the cropped map around the player, undone points and the facing arrow."""
        c = self.canvas
        c.delete('all')
        if self.pos is None:
            c.create_text(SIZE / 2, SIZE / 2, text=self.texts('map_wait'), fill=DIM, width=SIZE - 30, justify='center')
            return
        level = self.current_level()
        m = self.pick_map(level) if level else None
        if not m:
            c.create_text(SIZE / 2, SIZE / 2, text=self.texts('map_none'), fill=DIM, width=SIZE - 30, justify='center')
            return
        (x0, y0), (x1, y1) = m['range']
        to_px = lambda wx, wy: ((wx - x0) / (x1 - x0) * MAP_PX, (wy - y0) / (y1 - y0) * MAP_PX)
        span = SIZE // self.zoom
        px, py = to_px(self.pos[0], self.pos[1])
        left = int(min(max(px - span / 2, 0), MAP_PX - span))
        top = int(min(max(py - span / 2, 0), MAP_PX - span))
        frame = tk.PhotoImage()
        frame.tk.call(frame, 'copy', self.image(m['image']), '-from', left, top, left + span, top + span, '-zoom', self.zoom)
        self.view = frame
        c.create_image(0, 0, image=frame, anchor='nw')
        for i, cat, wx, wy, wz, key, name in self.points.get(level, []):
            if f'{level}:{i}' in self.hidden or (key and key in self.actors):
                continue
            sx, sy = to_px(wx, wy)
            sx, sy = (sx - left) * self.zoom, (sy - top) * self.zoom
            if not (0 <= sx <= SIZE and 0 <= sy <= SIZE):
                continue
            icon = self.icons.get(cat)
            if icon:
                c.create_image(sx, sy, image=icon)
            else:
                c.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill=DOT_COLORS.get(cat, DIM), outline=BG)
        cx, cy = (px - left) * self.zoom, (py - top) * self.zoom
        a = math.radians(self.pos[3])
        tip = (cx + 11 * math.cos(a), cy + 11 * math.sin(a))
        l = (cx + 7 * math.cos(a + 2.5), cy + 7 * math.sin(a + 2.5))
        r = (cx + 7 * math.cos(a - 2.5), cy + 7 * math.sin(a - 2.5))
        c.create_polygon(*tip, *l, cx, cy, *r, fill=GOLD, outline=BG)
        c.create_text(SIZE - 6, SIZE - 6, text=f'x{self.zoom}', fill=DIM, anchor='se', font=('Segoe UI', 7))
