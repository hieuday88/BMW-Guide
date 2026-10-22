"""Square live minimap embedded in the overlay: map around the player, points finished in the save are hidden."""
import json
import math
import re
import threading
import unicodedata
import time
import tkinter as tk

import bmw_live
import bmw_route

TICK_MS = 16
GRID_N = bmw_route.GRID
REROUTE_CELLS = 6
LOOKAHEAD = 1500
SMOOTH = 0.35
LEARN_RADIUS = 3500
CHEST_RADIUS = 700
ACTOR_SCAN_S = 2
NPC_PREFIXES = ('TAMER_', 'LSP_', 'Unit_', 'NPC')
NPC_RADIUS = 1200
NPC_NEAR = 3000
NPC_VISIT = 500
NPC_MISSES = 3
CHEST_CATS = {'baoxiang', 'cailiao'}
BOSS_LOOT_RADIUS = 3000
NEAR_LABEL = 1500
GENERIC_NAMES = {'ruong', 'diem thien', 'kim dan', 'ruong quan tai', 'nam ruong'}
PICKUP_CATS = CHEST_CATS |{'xiandan', 'luojia', 'sandongchong', 'zhenwan', 'hulu', 'jiushi', 'yaojin', 'bianhua'}
ICON_SUBSAMPLE = 10
HOVER_PX = 14
MAP_LEVELS = {10: 'HFS01_PersistentLevel', 11: 'HFS01_Old_GYCY_YKX_PersistentLevel', 20: 'HFM02_PersistentLevel',
              25: 'HFM_DuJiaoXian_Persist', 30: 'LYS_PersistentLevel', 40: 'PSD_PersistentLevel',
              80: 'ZYS01_persistentlevel', 50: 'HYS_PersistentLevel', 70: 'BSD02_persistentlevel', 98: 'BYS_persistentlevel'}
DOT_COLORS = {'renwu': '#f2e6c9', 'cailiao': '#8fb3c9'}
CATEGORY = {
    'vi': {'teleport': 'Miếu', 'baoxiang': 'Rương', 'luojia': 'Lạc Già', 'sandongchong': 'Tam Đông Trùng', 'jingpo': 'Tinh phách',
           'boss': 'Boss', 'toumu': 'Đầu mục', 'dazuo': 'Thiền', 'xiandan': 'Kim Đan', 'zhenwan': 'Bảo vật', 'hulu': 'Hồ lô',
           'jiushi': 'Rượu', 'bianhua': 'Phép', 'renwu': 'NPC', 'yaojin': 'Nhiệm vụ', 'cailiao': 'Nguyên liệu'},
    'en': {'teleport': 'Shrine', 'baoxiang': 'Chest', 'luojia': 'Luojia Vine', 'sandongchong': 'Wine Worm', 'jingpo': 'Spirit',
           'boss': 'Boss', 'toumu': 'Chief', 'dazuo': 'Meditation', 'xiandan': 'Celestial Pill', 'zhenwan': 'Curio', 'hulu': 'Gourd',
           'jiushi': 'Drink', 'bianhua': 'Spell', 'renwu': 'NPC', 'yaojin': 'Key item', 'cailiao': 'Material'},
}
CHAPTER_LEVELS = {0: ('HFS01_PersistentLevel', 'HFS01_Old_GYCY_YKX_PersistentLevel'), 1: ('HFM02_PersistentLevel', 'HFM_DuJiaoXian_Persist'),
                  2: ('LYS_PersistentLevel',), 3: ('PSD_PersistentLevel', 'ZYS01_persistentlevel'),
                  4: ('HYS_PersistentLevel', 'BSD02_persistentlevel'), 5: ('BYS_persistentlevel',)}
TURNS = {
    'vi': ['↑ phía trước', '↗ trước bên phải', '→ bên phải', '↘ sau bên phải', '↓ phía sau', '↙ sau bên trái', '← bên trái', '↖ trước bên trái'],
    'en': ['↑ ahead', '↗ ahead right', '→ right', '↘ behind right', '↓ behind', '↙ behind left', '← left', '↖ ahead left'],
}
LUOJIA, SANDONG = 1999, 1998
BG, GOLD, DIM, TEXT = '#121010', '#d9a441', '#857a6a', '#e6dccb'
PLAYER, ROUTE, TARGET = '#39ff6a', '#ffffff', '#3cc8ff'
KEY = '#010203'  # window transparent colour used for the corners outside the circle


def _norm(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    return re.sub(r'\s+', ' ', ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')).strip()


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
    """Circular minimap canvas that follows the player read live from game memory."""

    def __init__(self, parent, assets, state, save_state, texts, lang, width):
        self.state, self.save_state, self.texts, self.lang = state, save_state, texts, lang
        self.maps = json.loads((assets / 'maps' / 'maps.json').read_text(encoding='utf-8'))
        self.points = json.loads((assets / 'maps' / 'points.json').read_text(encoding='utf-8'))
        self.point_ids = json.loads((assets / 'maps' / 'point_ids.json').read_text(encoding='utf-8'))
        self.map_dir = assets / 'maps'
        self.icons = {f.stem: tk.PhotoImage(file=str(f)).subsample(ICON_SUBSAMPLE) for f in (assets / 'map_icons').glob('*.png')}
        self.images = {}
        self.hidden = set(state.setdefault('map_hidden', []))
        self.actors, self.opened = set(), set()
        self.owned = {'card': set(), 'item': set(), 'equip': set(), 'soul': set(), 'meditation': set()}
        self.chests = []
        self.npc_misses = {}
        self.map_id = 0
        self.prev = None
        self.pos = None
        self.view = None
        self.mouse = None
        self.target = None
        self.route_path = None
        self.route_key = None
        self.route_busy = False
        self.version = 0
        self.static_key = None
        self.shown = []
        self.live = bmw_live.LiveReader()
        self.zoom = state.get('map_zoom', 1)
        self.w = width
        self.h = width - 8
        self.r = self.h // 2 - 2
        self.canvas = tk.Canvas(parent, width=self.w, height=self.h, bg=KEY, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind('<Motion>', lambda e: setattr(self, 'mouse', (e.x, e.y)))
        self.canvas.bind('<Leave>', lambda e: setattr(self, 'mouse', None))
        self.on_pick = None
        self.canvas.bind('<Button-1>', self.click)
        threading.Thread(target=self.scan_chests, daemon=True).start()
        self.tick_job = None
        self.canvas.bind('<Destroy>', lambda e: self.tick_job and self.canvas.after_cancel(self.tick_job))
        self.tick()

    def click(self, e):
        """Guides to the clicked map point and shows its checklist line; clicking empty map stops guiding."""
        level = self.current_level() if self.pos else None
        hit = min(self.shown, key=lambda s: math.hypot(s[0] - e.x, s[1] - e.y)) if self.shown else None
        if level and hit and math.hypot(hit[0] - e.x, hit[1] - e.y) <= HOVER_PX:
            pt = next(p for p in self.points[level] if p[0] == hit[6])
            self.target = (level, pt)
            if self.on_pick:
                self.on_pick(level, pt)
        else:
            self.target = None
        self.bump()

    def zoom_by(self, step):
        self.zoom = min(4, max(1, self.zoom + step))
        self.bump()
        self.state['map_zoom'] = self.zoom
        self.save_state()

    def scan_chests(self):
        """Periodically lists loaded chests and NPC actors (background thread) and drops NPC points whose NPC has left."""
        while True:
            try:
                actors = self.live.loaded_actors('')
                if not actors or self.live.position() is None:
                    time.sleep(ACTOR_SCAN_S)
                    continue
                chests = [a for a in actors if 'TreasureBox' in a[0]]
                if [c[0] for c in chests] != [c[0] for c in self.chests]:
                    self.chests = chests
                    self.bump()
                npcs = [a for a in actors if a[0].startswith(NPC_PREFIXES) and not a[0].startswith('Unit_Player')]
                pickups = [a for a in actors if 'TreasureBox' in a[0] or 'SceneItem' in a[0]]
                rules = {cat: (pickups, CHEST_RADIUS) for cat in PICKUP_CATS}
                rules['renwu'] = (npcs, NPC_RADIUS)
                self.check_absent(rules)
            except Exception:
                pass
            time.sleep(ACTOR_SCAN_S)

    def check_absent(self, rules):
        """Hides NPC points the player walked up to, and NPC/chest/pickup points found empty over several close-by scans."""
        pos, level = self.pos, self.current_level()
        if not pos or not level or not (pos[0] or pos[1]):
            return
        for i, cat, wx, wy, wz, *_ in self.points.get(level, []):
            pid = f'{level}:{i}'
            if pid in self.hidden:
                continue
            if cat == 'renwu' and math.dist(pos[:2], (wx, wy)) <= NPC_VISIT:
                self.remember(pid)
                self.save_state()
                continue
            if cat not in rules or math.dist(pos[:2], (wx, wy)) > NPC_NEAR:
                continue
            actors, radius = rules[cat]
            present = any(math.dist((wx, wy), n[1:3]) <= radius for n in actors)
            self.npc_misses[pid] = 0 if present else self.npc_misses.get(pid, 0) + 1
            if self.npc_misses[pid] >= NPC_MISSES:
                self.remember(pid)
                self.save_state()

    def update_from_save(self, progress, save_id=''):
        """Refreshes finished objects from the save and learns which nearby map points the newest pickups came from."""
        restarted = self.prev is not None and len(progress['card']) < len(self.prev['card'])
        if save_id != self.state.get('map_save') or restarted:
            self.state['map_save'] = save_id
            self.hidden.clear()
            self.state['map_hidden'] = []
            self.save_state()
            self.prev = None
        self.actors, self.opened = progress['actors'], progress['opened']
        self.owned = {k: progress[k] for k in ('card', 'item', 'equip', 'soul', 'meditation')}
        self.map_id = progress.get('map_id', 0)
        self.bump()
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
        for item, num in progress['item_num'].items():
            if num > prev['item_num'].get(item, 0):
                cats |= _item_categories(item)
        for item in progress['equip'] - prev['equip']:
            cats |= _item_categories(item)
        if cats:
            self.learn(cats)

    def remember(self, pid):
        self.hidden.add(pid)
        self.bump()
        self.state['map_hidden'] = sorted(self.hidden)

    def learn(self, cats):
        """Hides the nearest visible point of the given categories around the player."""
        level = self.current_level()
        best = None
        for i, cat, px, py, pz, *_ in self.points.get(level, []):
            pid = f'{level}:{i}'
            if cat in cats and pid not in self.hidden:
                d = math.dist(self.pos[:3], (px, py, pz))
                if d <= LEARN_RADIUS and (best is None or d < best[0]):
                    best = (d, pid)
        if best:
            self.remember(best[1])
            self.save_state()

    def is_done(self, level, i, cat, wx, wy, wz, key):
        """Decides from the save whether a map point is finished; chest results are remembered."""
        pid = f'{level}:{i}'
        if pid in self.hidden or (key and key in self.actors and level == self.current_level()):
            return True
        ref = None if cat in CHEST_CATS else self.point_ids.get(pid)
        if ref:
            src, gid, unique = ref
            if src == 'item' and 8000 <= gid < 9000:
                return gid in self.owned['soul']
            if src in ('card', 'equip') or unique:
                return gid in self.owned[src]
        if cat in PICKUP_CATS and self.chests:
            near = min(self.chests, key=lambda c: math.dist((wx, wy, wz), c[1:4]))
            if math.dist((wx, wy, wz), near[1:4]) <= CHEST_RADIUS and self.chest_opened(near):
                self.remember(pid)
                return True
        if cat == 'cailiao':
            return any(p[1] in ('boss', 'toumu') and math.hypot(p[2] - wx, p[3] - wy) <= BOSS_LOOT_RADIUS
                       and self.is_done(level, *p[:6]) for p in self.points.get(level, []))
        return False

    def chest_opened(self, chest):
        """Matches a loaded chest to the save by its GUID; falls back to the actor name when the GUID is unreadable."""
        guid = chest[4]
        if guid:
            return guid in self.opened
        return any(o.endswith('-' + chest[0]) for o in self.opened)

    def current_level(self):
        level = MAP_LEVELS.get(self.map_id)
        if level and self.pos and self.pick_map(level, self.pos):
            return level
        for m in self.maps:
            if self.pos and self.in_range(m['range'], self.pos):
                return m['level']
        return level

    @staticmethod
    def in_range(rng, pos):
        (x0, y0), (x1, y1) = rng
        return x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1

    def pick_map(self, level, pos):
        """Chooses the map layer for the level at pos, honouring height-based sub-areas (pagodas, caves)."""
        plain = None
        for m in self.maps:
            if m['level'] != level or not self.in_range(m['range'], pos):
                continue
            if not m['areas']:
                plain = plain or m
                continue
            for (sx, sy, sz), (ex, ey, ez) in m['areas']:
                if sx <= pos[0] <= ex and sy <= pos[1] <= ey and sz <= pos[2] <= ez:
                    return m
        return plain

    def locate(self, chapter, tokens, text, shrine=False):
        """Finds map points for a checklist line by game id, then by name, within the chapter's levels."""
        wanted = set()
        for cat, gid in tokens:
            wanted.add(({'soul': 'item', 'equip': 'equip', 'card': 'card', 'meditation': 'meditation'}.get(cat, 'item'), gid))
            if cat in ('item', 'equip'):
                wanted.add(('item' if cat == 'equip' else 'equip', gid))
        name = _norm(re.split(r'\s+[—–]\s+|\s+\d+$', text)[0])
        found = []
        own = CHAPTER_LEVELS.get(chapter, ())
        for level in [*own, *(lv for lv in self.points if lv not in own)]:
            if found and level not in own:
                break
            for pt in self.points.get(level, []):
                ref = self.point_ids.get(f'{level}:{pt[0]}')
                by_id = ref is not None and (ref[0], ref[1]) in wanted
                by_name = bool(name) and _norm(pt[7]) == name and (pt[1] == 'teleport') == shrine
                if by_id or by_name:
                    found.append((level, pt))
        return found or self.mentioned(own, _norm(text), shrine)

    def mentioned(self, levels, text, shrine):
        """Falls back to map points of the chapter whose name appears in the line text, preferring the earliest mention."""
        hits = []
        for level in levels:
            for pt in self.points.get(level, []):
                name = _norm(re.sub(r'\s*×\d+$', '', pt[7]))
                if len(name) >= 4 and name not in GENERIC_NAMES and (pt[1] == 'teleport') == shrine:
                    at = text.find(name)
                    if at >= 0:
                        hits.append((at, -len(name), level, pt))
        if not hits:
            return []
        first = min(hits)[:2]
        return [(level, pt) for at, size, level, pt in hits if (at, size) == first]

    def focus(self, found):
        """Centres the map on the best candidate (nearest unfinished point) and draws a route line to it."""
        if not found:
            return False

        def rank(entry):
            level, pt = entry
            done = self.is_done(level, pt[0], pt[1], pt[2], pt[3], pt[4], pt[5])
            return done, math.dist(self.pos[:2], pt[2:4]) if self.pos else 0

        self.target = min(found, key=rank)
        self.bump()
        return True

    def image(self, name):
        if name not in self.images:
            self.images[name] = tk.PhotoImage(file=str(self.map_dir / name))
        return self.images[name]

    def smooth(self, raw):
        """Eases the drawn position/heading toward the live reading so movement looks continuous."""
        if self.pos is None or math.dist(self.pos[:3], raw[:3]) > 3000:
            return raw
        x, y, z, yaw = (a + (b - a) * SMOOTH for a, b in zip(self.pos[:3] + (0,), raw[:3] + (0,)))
        turn = (raw[3] - self.pos[3] + 180) % 360 - 180
        return x, y, z, self.pos[3] + turn * SMOOTH

    def tick(self):
        try:
            if self.canvas.winfo_ismapped():
                raw = self.live.position()
                if raw:
                    self.pos = self.smooth(raw)
                self.render()
        finally:
            if self.canvas.winfo_exists():
                self.tick_job = self.canvas.after(TICK_MS, self.tick)

    def bump(self):
        """Marks the static layer (map + points) as stale after the save or hidden set changes."""
        self.version += 1

    def draw_arrow(self, ax, ay, cx, cy, r, inside):
        """Draws a large player arrow, or an edge marker pointing at the player when they are outside the view."""
        c = self.canvas
        if inside(ax, ay, 4):
            a = math.radians(self.pos[3])
            shape = [(15, 0), (9, 2.45), (4, math.pi), (9, -2.45)]
            centre = (ax, ay)
        else:
            a = math.atan2(ay - cy, ax - cx)
            k = (r - 16) / max(abs(math.cos(a)), abs(math.sin(a)))
            centre = (cx + k * math.cos(a), cy + k * math.sin(a))
            shape = [(14, 0), (10, 2.4), (10, -2.4)]

        def poly(scale):
            return [v for d, t in shape for v in (centre[0] + d * scale * math.cos(a + t), centre[1] + d * scale * math.sin(a + t))]

        c.create_polygon(*poly(1.25), fill=BG, outline=BG, width=3, tags='dyn')
        c.create_polygon(*poly(1.0), fill=PLAYER, outline=ROUTE, width=2, tags='dyn')

    def request_route(self, m):
        """Recomputes the walking route in the background when the target changes or the player strays from it."""
        if self.route_busy or self.pos is None:
            return
        (x0, y0), (x1, y1) = m['range']
        to_cell = lambda wx, wy: (min(GRID_N - 1, max(0, int((wx - x0) / (x1 - x0) * GRID_N))),
                                  min(GRID_N - 1, max(0, int((wy - y0) / (y1 - y0) * GRID_N))))
        start, goal = to_cell(*self.pos[:2]), to_cell(*self.target[1][2:4])
        key = (m['image'], self.target[1][0], self.target[0])
        known = self.route_path if self.route_key == key else None
        if known and math.dist(start, known['start']) < REROUTE_CELLS and time.time() - known['at'] < 30:
            return
        self.route_busy = True

        def work():
            try:
                grid = bmw_route.load(self.map_dir, m['image'])
                cells = bmw_route.find(grid, start, goal) if grid else None
                if cells:
                    pts = [(x0 + (cx + 0.5) / GRID_N * (x1 - x0), y0 + (cy + 0.5) / GRID_N * (y1 - y0))
                           for cx, cy in bmw_route.simplify(cells)]
                    self.route_path, self.route_key = {'pts': pts, 'start': start, 'at': time.time()}, key
            finally:
                self.route_busy = False

        threading.Thread(target=work, daemon=True).start()

    def dashed_path(self, pts):
        """Draws a moving dashed polyline through screen points."""
        phase = (time.time() * 40) % 16
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            length = math.hypot(bx - ax, by - ay)
            if length < 0.5:
                continue
            ux, uy = (bx - ax) / length, (by - ay) / length
            d = -phase
            while d < length:
                a, b = max(d, 0), min(d + 10, length)
                if b > a:
                    seg = (ax + ux * a, ay + uy * a, ax + ux * b, ay + uy * b)
                    self.canvas.create_line(*seg, fill=BG, width=5, capstyle='round', tags='dyn')
                    self.canvas.create_line(*seg, fill=ROUTE, width=3, capstyle='round', tags='dyn')
                d += 16
            phase = (phase + length) % 16

    def guide(self, level, m, place, inside, ax, ay, here, cx, cy, r):
        """Guides the player along the walking route: dashed path, target ring or edge arrow, path distance and next turn."""
        c = self.canvas
        tlevel, tpt = self.target
        if not here or tlevel != level:
            self.label(cx - r + 8, cy - r + 6, f'{tpt[7]} · {self.texts("map_other")}', 'nw', 2 * r - 16)
            return
        self.request_route(m)
        route = self.route_path['pts'] if self.route_path and self.route_key and self.route_key[0] == m['image'] \
            and self.route_key[1] == tpt[0] else None
        if route:
            near = min(range(len(route)), key=lambda i: math.dist(route[i], self.pos[:2]))
            world = [tuple(self.pos[:2]), *route[near + 1:], tuple(tpt[2:4])]
        else:
            world = [tuple(self.pos[:2]), tuple(tpt[2:4])]
        dist = sum(math.dist(a, b) for a, b in zip(world, world[1:])) / 100
        ahead = next((p for p in world[1:] if math.dist(p, self.pos[:2]) > LOOKAHEAD), world[-1])
        hx, hy = place(*ahead)
        turn = (math.degrees(math.atan2(hy - ay, hx - ax)) - self.pos[3] + 180) % 360 - 180
        hint = TURNS[self.lang()][round(turn / 45) % 8]
        self.dashed_path([place(*p) for p in world])
        tx, ty = place(tpt[2], tpt[3])
        if inside(tx, ty):
            pulse = 9 + 3 * math.sin(time.time() * 5)
            c.create_oval(tx - pulse, ty - pulse, tx + pulse, ty + pulse, outline=TARGET, width=3, tags='dyn')
        else:
            bearing = math.atan2(ty - cy, tx - cx)
            k = (r - 16) / max(abs(math.cos(bearing)), abs(math.sin(bearing)))
            ex, ey = cx + k * math.cos(bearing), cy + k * math.sin(bearing)
            tip = [(ex + 16 * math.cos(bearing), ey + 16 * math.sin(bearing)),
                   (ex + 10 * math.cos(bearing + 2.4), ey + 10 * math.sin(bearing + 2.4)),
                   (ex + 10 * math.cos(bearing - 2.4), ey + 10 * math.sin(bearing - 2.4))]
            c.create_polygon(*[v for q in tip for v in q], fill=TARGET, outline=BG, width=2, tags='dyn')
        self.label(cx - r + 8, cy - r + 6, f'{tpt[7]} · {dist:.0f} m · {hint}', 'nw', 2 * r - 16)

    def label(self, x, y, text, anchor, width=0):
        c = self.canvas
        t = c.create_text(x, y, text=text, fill=TEXT, font=('Segoe UI', 9, 'bold'), anchor=anchor, width=width, tags='dyn')
        bx = c.bbox(t)
        c.create_rectangle(bx[0] - 5, bx[1] - 2, bx[2] + 5, bx[3] + 2, fill=BG, outline=GOLD, tags='dyn')
        c.tag_raise(t)

    def render(self):
        """Redraws the map/points layer only when the view moves; the player, route and labels are redrawn every frame."""
        c, cx, cy, r = self.canvas, self.w / 2, self.h / 2, self.r
        level = self.current_level() if self.pos else None
        m = self.pick_map(level, self.pos) if level else None
        centre = self.pos[:2] if self.pos else None
        c.delete('dyn')
        if m is None:
            if self.static_key != 'empty':
                c.delete('static')
                c.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill=BG, outline=GOLD, width=2, tags='static')
                self.static_key = 'empty'
            msg = self.texts('map_wait' if self.pos is None else 'map_none')
            c.create_text(cx, cy, text=msg, fill=DIM, width=r * 1.6, justify='center', font=('Segoe UI', 8), tags='dyn')
            return
        img = self.image(m['image'])
        size = img.width()
        (x0, y0), (x1, y1) = m['range']
        to_px = lambda wx, wy: ((wx - x0) / (x1 - x0) * size, (wy - y0) / (y1 - y0) * size)
        span = (2 * r) // self.zoom
        px, py = to_px(*centre)
        left = int(min(max(px - span / 2, 0), size - span))
        top = int(min(max(py - span / 2, 0), size - span))
        ox, oy = cx - span * self.zoom / 2, cy - span * self.zoom / 2

        def place(wx, wy):
            mx, my = to_px(wx, wy)
            return ox + (mx - left) * self.zoom, oy + (my - top) * self.zoom

        def inside(sx, sy, pad=8):
            return max(abs(sx - cx), abs(sy - cy)) <= r - pad

        key = (m['image'], left, top, self.zoom, self.version, level)
        if key != self.static_key:
            self.static_key = key
            c.delete('static')
            if self.view is None:
                self.view = tk.PhotoImage()
            self.view.blank()
            self.view.tk.call(self.view, 'copy', img, '-from', left, top, left + span, top + span, '-zoom', self.zoom)
            c.create_image(ox, oy, image=self.view, anchor='nw', tags='static')
            self.shown = []
            for i, cat, wx, wy, wz, pkey, cn, name in self.points.get(level, []):
                sx, sy = place(wx, wy)
                if not inside(sx, sy) or self.is_done(level, i, cat, wx, wy, wz, pkey):
                    continue
                icon = self.icons.get(cat)
                if icon:
                    c.create_image(sx, sy, image=icon, tags='static')
                else:
                    c.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill=DOT_COLORS.get(cat, DIM), outline=BG, width=2, tags='static')
                self.shown.append((sx, sy, cat, name, wx, wy, i))
            c.create_rectangle(cx - r, cy - r, cx + r, cy + r, outline=GOLD, width=2, tags='static')
        here = self.pos is not None and self.pick_map(level, self.pos) is m
        ax, ay = place(self.pos[0], self.pos[1]) if here else (0, 0)
        if self.target:
            self.guide(level, m, place, inside, ax, ay, here, cx, cy, r)
        if here:
            self.draw_arrow(ax, ay, cx, cy, r, inside)
            near = [(math.hypot(s[4] - self.pos[0], s[5] - self.pos[1]), s) for s in self.shown]
            near = [n for n in near if n[0] <= NEAR_LABEL]
            for _, (sx, sy, cat, *_rest) in near:
                if cat in self.icons:
                    c.create_image(sx, sy, image=self.icons[cat], tags='dyn')
            if near and not self.target:
                d, (_, _, _, name, *_rest) = min(near, key=lambda n: n[0])
                self.label(cx, cy + r - 8, f'📍 {name} · {d / 100:.0f} m', 's', width=2 * r - 40)
        c.create_text(cx + r - 6, cy + r - 4, anchor='se', text=f'x{self.zoom}', fill=GOLD, font=('Segoe UI', 8, 'bold'), tags='dyn')
        if self.mouse and self.shown:
            hx, hy, cat, name, *_rest = min(self.shown, key=lambda s: math.hypot(s[0] - self.mouse[0], s[1] - self.mouse[1]))
            if math.hypot(hx - self.mouse[0], hy - self.mouse[1]) <= HOVER_PX:
                labels = CATEGORY[self.lang()]
                self.label(hx, hy - 16, name if name in labels.values() else f'{labels.get(cat, "")}: {name}', 's')


class FullMap:
    """Large pan/zoom view of the whole current map, sharing points, progress and routes with the minimap."""

    STEPS = ((4, 1), (3, 1), (2, 1), (1, 1), (1, 2))
    REFRESH_MS = 100

    def __init__(self, root, minimap, on_close, on_pick):
        self.mini, self.on_close, self.on_pick = minimap, on_close, on_pick
        screen = min(root.winfo_screenwidth(), root.winfo_screenheight())
        self.size = size = int(screen * 0.8)
        self.win = tk.Toplevel(root, bg=BG)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.geometry(f'{size}x{size}+{(root.winfo_screenwidth() - size) // 2}+{(root.winfo_screenheight() - size) // 2}')
        self.canvas = tk.Canvas(self.win, width=size, height=size, bg=BG, highlightthickness=1, highlightbackground=GOLD)
        self.canvas.pack()
        self.map = None
        self.step = 1
        self.centre = None
        self.drag = None
        self.mouse = None
        self.shown = []
        self.scaled = {}
        self.static_key = None
        c = self.canvas
        c.bind('<ButtonPress-1>', self.press)
        c.bind('<B1-Motion>', self.motion_drag)
        c.bind('<ButtonRelease-1>', self.release)
        c.bind('<Motion>', lambda e: setattr(self, 'mouse', (e.x, e.y)))
        c.bind('<Leave>', lambda e: setattr(self, 'mouse', None))
        c.bind('<MouseWheel>', lambda e: self.zoom_at(1 if e.delta > 0 else -1, e.x, e.y))
        self.job = None
        self.refresh()

    def factor(self):
        sub, zoom = self.STEPS[self.step]
        return zoom / sub

    def map_px(self):
        return self.mini.image(self.map['image']).width()

    def to_px(self, wx, wy):
        (x0, y0), (x1, y1) = self.map['range']
        size = self.map_px()
        return (wx - x0) / (x1 - x0) * size, (wy - y0) / (y1 - y0) * size

    def to_screen(self, px, py):
        f = self.factor()
        return self.size / 2 + (px - self.centre[0]) * f, self.size / 2 + (py - self.centre[1]) * f

    def scaled_image(self):
        """Returns the map image scaled for the current step; zoomed-in steps only render the visible window."""
        sub, zoom = self.STEPS[self.step]
        img = self.mini.image(self.map['image'])
        if zoom == 1:
            key = (self.map['image'], sub)
            if key not in self.scaled:
                self.scaled = {k: v for k, v in self.scaled.items() if k[0] == self.map['image']}
                self.scaled[key] = img.subsample(sub) if sub > 1 else img
            return self.scaled[key], 0, 0
        size = self.map_px()
        half = self.size // (2 * zoom) + 2
        left = int(max(0, min(size - 2 * half, self.centre[0] - half)))
        top = int(max(0, min(size - 2 * half, self.centre[1] - half)))
        view = tk.PhotoImage()
        view.tk.call(view, 'copy', img, '-from', left, top, left + 2 * half, top + 2 * half, '-zoom', zoom)
        self.scaled['zoomed'] = view
        return view, left, top

    def draw_static(self):
        """Draws the map image and every unfinished point of the shown level."""
        c, m = self.canvas, self.map
        c.delete('static')
        image, left, top = self.scaled_image()
        x, y = self.to_screen(left, top)
        c.create_image(x, y, image=image, anchor='nw', tags='static')
        self.shown = []
        for i, cat, wx, wy, wz, pkey, cn, name in self.mini.points.get(m['level'], []):
            if not self.mini.in_range(m['range'], (wx, wy)) or self.mini.is_done(m['level'], i, cat, wx, wy, wz, pkey):
                continue
            sx, sy = self.to_screen(*self.to_px(wx, wy))
            if not (-20 < sx < self.size + 20 and -20 < sy < self.size + 20):
                continue
            icon = self.mini.icons.get(cat)
            if icon:
                c.create_image(sx, sy, image=icon, tags='static')
            else:
                c.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill=DOT_COLORS.get(cat, DIM), outline=BG, width=2, tags='static')
            self.shown.append((sx, sy, cat, name, i))

    def draw_dynamic(self):
        """Redraws the route, target ring, player arrow, close button and hover label."""
        c, mini = self.canvas, self.mini
        c.delete('dyn')
        if mini.target and mini.target[0] == self.map['level']:
            tx, ty = self.to_screen(*self.to_px(*mini.target[1][2:4]))
            route = mini.route_path['pts'] if mini.route_path and mini.route_key and mini.route_key[0] == self.map['image'] \
                and mini.route_key[1] == mini.target[1][0] else None
            if route:
                pts = [v for p in route for v in self.to_screen(*self.to_px(*p))]
                if len(pts) >= 4:
                    c.create_line(*pts, fill=ROUTE, width=3, dash=(8, 6), tags='dyn')
            c.create_oval(tx - 14, ty - 14, tx + 14, ty + 14, outline=TARGET, width=3, tags='dyn')
        if mini.pos and mini.pick_map(self.map['level'], mini.pos) is self.map:
            ax, ay = self.to_screen(*self.to_px(*mini.pos[:2]))
            a = math.radians(mini.pos[3])
            shape = [(18, 0), (11, 2.45), (5, math.pi), (11, -2.45)]
            pts = [v for d, t in shape for v in (ax + d * math.cos(a + t), ay + d * math.sin(a + t))]
            c.create_polygon(*pts, fill=PLAYER, outline=ROUTE, width=2, tags='dyn')
        c.create_text(self.size - 14, 10, text='✕', fill=GOLD, font=('Segoe UI', 16, 'bold'), anchor='ne', tags='dyn')
        c.create_text(12, self.size - 10, text=f'F12 · x{self.factor():.2g}', fill=GOLD, font=('Segoe UI', 9, 'bold'),
                      anchor='sw', tags='dyn')
        hit = self.hovered()
        if hit:
            hx, hy, cat, name, _ = hit
            labels = CATEGORY[mini.lang()]
            text = name if name in labels.values() else f'{labels.get(cat, "")}: {name}'
            t = c.create_text(hx, hy - 18, text=text, fill=TEXT, font=('Segoe UI', 10, 'bold'), anchor='s', tags='dyn')
            bx = c.bbox(t)
            c.create_rectangle(bx[0] - 6, bx[1] - 3, bx[2] + 6, bx[3] + 3, fill=BG, outline=GOLD, tags='dyn')
            c.tag_raise(t)

    def hovered(self):
        if not self.mouse or not self.shown:
            return None
        best = min(self.shown, key=lambda s: math.hypot(s[0] - self.mouse[0], s[1] - self.mouse[1]))
        return best if math.hypot(best[0] - self.mouse[0], best[1] - self.mouse[1]) <= HOVER_PX else None

    def refresh(self):
        """Follows the player's current map, redrawing points only when the view or progress changes."""
        try:
            mini = self.mini
            level = mini.current_level() if mini.pos else None
            current = mini.pick_map(level, mini.pos) if level else None
            if current is not None and current is not self.map:
                self.map = current
                self.centre = self.to_px(*mini.pos[:2])
                self.static_key = None
                fits = [i for i, (sub, zoom) in enumerate(self.STEPS) if self.map_px() * zoom / sub <= self.size]
                self.step = max(fits) if fits else 0
            if self.map is None:
                self.canvas.delete('all')
                self.canvas.create_text(self.size / 2, self.size / 2, text=mini.texts('map_wait'), fill=DIM,
                                        justify='center', font=('Segoe UI', 11))
            else:
                key = (self.map['image'], self.step, self.centre, mini.version)
                if key != self.static_key and self.drag is None:
                    self.static_key = key
                    self.draw_static()
                self.draw_dynamic()
        finally:
            if self.win.winfo_exists():
                self.job = self.win.after(self.REFRESH_MS, self.refresh)

    def zoom_at(self, step, x, y):
        new = max(0, min(len(self.STEPS) - 1, self.step + step))
        if new == self.step or self.map is None:
            return
        f = self.factor()
        px, py = self.centre[0] + (x - self.size / 2) / f, self.centre[1] + (y - self.size / 2) / f
        self.step = new
        f = self.factor()
        self.centre = (px - (x - self.size / 2) / f, py - (y - self.size / 2) / f)

    def press(self, e):
        if e.x > self.size - 40 and e.y < 40:
            self.close()
            return
        self.drag = (e.x, e.y, e.x, e.y)

    def motion_drag(self, e):
        if self.drag:
            self.canvas.move('static', e.x - self.drag[2], e.y - self.drag[3])
            self.drag = (self.drag[0], self.drag[1], e.x, e.y)

    def release(self, e):
        """Ends a drag by moving the view, or treats a click on a point as picking it as the route target."""
        if not self.drag or self.map is None:
            self.drag = None
            return
        x0, y0 = self.drag[:2]
        self.drag = None
        if math.hypot(e.x - x0, e.y - y0) < 5:
            self.static_key = None
            hit = self.hovered()
            if hit:
                pt = next(p for p in self.mini.points[self.map['level']] if p[0] == hit[4])
                self.mini.target = (self.map['level'], pt)
                self.mini.bump()
                self.on_pick(self.map['level'], pt)
            return
        f = self.factor()
        self.centre = (self.centre[0] - (e.x - x0) / f, self.centre[1] - (e.y - y0) / f)

    def close(self):
        if self.job:
            self.win.after_cancel(self.job)
        self.win.destroy()
        self.on_close()
