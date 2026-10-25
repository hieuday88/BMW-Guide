"""Safe editing of Black Myth: Wukong saves: bag quantities, Will and a fixed set of materials.

Every write keeps the original as a timestamped backup, refuses to run while the game is open, re-encrypts the
payload, recomputes the checksum and reads the result back to verify it before replacing the save.
"""
import hashlib
import os
import time
from pathlib import Path

import bmw_live

XOR_KEY = bytes.fromhex('7b5cda913efcda37')
SALT = b'lhx2tkh6lj1wj8jmrgs3k1xb2brusehx'
BAG_PATH = (1, 1, 2)
CURRENCY, ITEMS = 1, 2
WILL_ID = 1
MAX_WILL = 99_999_999
MAX_ITEM = 9_999
SAFE_MATERIALS = (3310, 3003, 3309, 3301, 3950, 3951, 3952, 3953, 3954, 3958, 3959, 3960, 3961, 3962)


class SaveFormatError(ValueError):
    pass


def _varint(b, p):
    value = shift = 0
    while True:
        if p >= len(b) or shift > 63:
            raise SaveFormatError('truncated integer')
        c = b[p]
        p += 1
        value |= (c & 0x7F) << shift
        if c < 0x80:
            return value, p
        shift += 7


def _enc(n):
    if n < 0:
        raise SaveFormatError('negative integer')
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def parse(b):
    """Splits a protobuf message into [(field, wire, value, raw_bytes)] without interpreting nested messages."""
    out, p = [], 0
    while p < len(b):
        start = p
        tag, p = _varint(b, p)
        f, w = tag >> 3, tag & 7
        if f < 1:
            raise SaveFormatError('invalid field')
        if w == 0:
            v, p = _varint(b, p)
        elif w in (1, 5):
            n = 8 if w == 1 else 4
            v, p = b[p:p + n], p + n
        elif w == 2:
            n, p = _varint(b, p)
            if n > len(b) - p:
                raise SaveFormatError('invalid length')
            v, p = b[p:p + n], p + n
        else:
            raise SaveFormatError('unsupported wire type')
        out.append((f, w, v, b[start:p]))
    return out


def field(f, w, v):
    if w == 2:
        return _enc(f * 8 + w) + _enc(len(v)) + v
    return _enc(f * 8 + w) + (_enc(v) if w == 0 else v)


def one(b, f, w):
    hits = [x for x in parse(b) if x[0] == f]
    if len(hits) != 1 or hits[0][1] != w:
        raise SaveFormatError(f'unsupported save layout (field {f})')
    return hits[0][2]


def replace(b, f, w, v):
    """Replaces the single field f (or appends it) and returns the re-encoded message."""
    fs = parse(b)
    hits = [x for x in fs if x[0] == f]
    if len(hits) > 1 or (hits and hits[0][1] != w):
        raise SaveFormatError(f'ambiguous field {f}')
    body = b''.join(field(f, w, v) if x[0] == f else x[3] for x in fs)
    return body if hits else body + field(f, w, v)


def get_path(b, path):
    for f in path:
        b = one(b, f, 2)
    return b


def set_path(b, path, v):
    if not path:
        return v
    return replace(b, path[0], 2, set_path(one(b, path[0], 2), path[1:], v))


def crypt(b):
    return bytes(c ^ XOR_KEY[i % 8] for i, c in enumerate(b))


def checksum(cipher):
    return hashlib.md5(cipher + SALT).hexdigest()


def read(raw):
    """Decodes a save into {'raw','header','payload','rows'}; rows are bag entries with their position."""
    header, cipher = one(raw, 1, 2), one(raw, 2, 2)
    if one(header, 1, 2).decode('ascii', 'replace') != checksum(cipher):
        raise SaveFormatError('checksum mismatch: the save is damaged or uses an unknown format')
    payload = crypt(cipher)
    rows = []
    for index, (f, w, v, _) in enumerate(parse(get_path(payload, BAG_PATH))):
        if w != 2 or f not in (CURRENCY, ITEMS):
            continue
        qty = [x for x in parse(v) if x[0] == 2]
        if len(qty) > 1 or (qty and qty[0][1] != 0):
            raise SaveFormatError('unsupported quantity field')
        rows.append({'index': index, 'group': f, 'id': one(v, 1, 0), 'qty': qty[0][2] if qty else 0})
    if sum(1 for r in rows if r['group'] == CURRENCY and r['id'] == WILL_ID) != 1:
        raise SaveFormatError('Will record missing')
    return {'raw': raw, 'header': header, 'payload': payload, 'rows': rows}


def limit_for(row):
    return MAX_WILL if row['group'] == CURRENCY and row['id'] == WILL_ID else MAX_ITEM


def build(save, quantities, additions):
    """Returns new save bytes with {row index: qty} and {material id: qty} applied, then verified."""
    by_index = {r['index']: r for r in save['rows']}
    bag = parse(get_path(save['payload'], BAG_PATH))
    parts = [x[3] for x in bag]
    for index, qty in quantities.items():
        row = by_index.get(index)
        if row is None or not 0 <= qty <= limit_for(row):
            raise SaveFormatError(f'invalid quantity for item {row and row["id"]}')
        f, w, v, _ = bag[index]
        parts[index] = field(f, 2, replace(v, 2, 0, qty))
    owned = {r['id'] for r in save['rows'] if r['group'] == ITEMS}
    for item_id, qty in additions.items():
        if item_id not in SAFE_MATERIALS or item_id in owned or not 1 <= qty <= MAX_ITEM:
            raise SaveFormatError(f'material {item_id} cannot be added')
        parts.append(field(ITEMS, 2, field(1, 0, item_id) + field(2, 0, qty)))
    payload = set_path(save['payload'], BAG_PATH, b''.join(parts))
    cipher = crypt(payload)
    header = replace(save['header'], 1, 2, checksum(cipher).encode('ascii'))
    out = replace(replace(save['raw'], 1, 2, header), 2, 2, cipher)
    verify(save, read(out), quantities, additions)
    return out


def verify(before, after, quantities, additions):
    """Checks that only the requested values changed."""
    old = {r['index']: r for r in before['rows']}
    for r in after['rows']:
        if r['index'] in old:
            want = quantities.get(r['index'], old[r['index']]['qty'])
            if r['id'] != old[r['index']]['id'] or r['qty'] != want:
                raise SaveFormatError('verification failed: bag changed unexpectedly')
    added = {r['id']: r['qty'] for r in after['rows'] if r['index'] not in old}
    if added != additions:
        raise SaveFormatError('verification failed: material additions differ')


def game_running():
    return bmw_live._find_pid() is not None


def write(path, save, quantities, additions):
    """Backs up the save, writes the edited copy atomically and returns the backup path."""
    if game_running():
        raise RuntimeError('game is running')
    path = Path(path)
    if path.read_bytes() != save['raw']:
        raise RuntimeError('save changed on disk since it was opened')
    out = build(save, quantities, additions)
    backup = path.with_name(f'{path.name}.bak-{time.strftime("%Y%m%d-%H%M%S")}')
    backup.write_bytes(save['raw'])
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(out)
    os.replace(tmp, path)
    read(path.read_bytes())
    return backup


TEXTS = {
    'vi': {'title': 'Sửa save', 'warn': 'Tắt hẳn game trước khi lưu. File cũ luôn được sao lưu thành .bak kèm giờ.',
           'will': 'Linh Uẩn', 'search': 'Tìm vật phẩm…', 'add': 'Thêm nguyên liệu chưa có',
           'save': 'Lưu vào save', 'close': 'Đóng', 'running': 'Game đang chạy. Tắt hẳn game rồi bấm Lưu lại.',
           'none': 'Chưa đổi gì.', 'confirm': 'Ghi {n} thay đổi vào save?\nFile cũ sẽ được sao lưu.',
           'bad': 'Số không hợp lệ: {name}', 'done': 'Đã lưu. Bản sao lưu:\n{backup}',
           'fail': 'Không lưu được, save giữ nguyên:\n{err}'},
    'en': {'title': 'Edit save', 'warn': 'Close the game completely before saving. The old file is always backed up as a timestamped .bak.',
           'will': 'Will', 'search': 'Search items…', 'add': 'Add materials you do not have',
           'save': 'Write to save', 'close': 'Close', 'running': 'The game is running. Close it completely, then press Write again.',
           'none': 'Nothing changed.', 'confirm': 'Write {n} change(s) to the save?\nThe old file will be backed up.',
           'bad': 'Invalid number: {name}', 'done': 'Saved. Backup:\n{backup}',
           'fail': 'Could not save, the save is untouched:\n{err}'},
}


class EditorWindow:
    """Window that lists the bag with editable quantities and writes them back through write()."""

    def __init__(self, root, path, names, lang, colors, on_saved):
        import tkinter as tk
        from tkinter import messagebox
        self.tk, self.messagebox = tk, messagebox
        self.path, self.names, self.on_saved = Path(path), names, on_saved
        self.t = TEXTS.get(lang, TEXTS['en'])
        self.c = colors
        self.save = read(self.path.read_bytes())
        self.entries = {}
        self.additions = {}
        self.win = tk.Toplevel(root, bg=colors['bg'])
        self.win.title(f"{self.t['title']} - {self.path.name}")
        self.win.attributes('-topmost', True)
        self.win.geometry('540x660')
        self.build_ui()

    def label(self, parent, text, size=9, **kw):
        kw.setdefault('fg', self.c['text'])
        return self.tk.Label(parent, text=text, bg=self.c['bg'], font=('Segoe UI', size), **kw)

    def entry(self, parent, value):
        e = self.tk.Entry(parent, width=10, bg=self.c['panel'], fg=self.c['text'], insertbackground=self.c['text'],
                          relief='flat', justify='right')
        e.insert(0, str(value))
        return e

    def item_row(self, name, item_id, value):
        line = self.tk.Frame(self.body, bg=self.c['bg'])
        self.label(line, name, anchor='w', width=34).pack(side='left')
        self.label(line, f'ID {item_id}', size=8, fg=self.c['dim'], width=8).pack(side='left')
        e = self.entry(line, value)
        e.pack(side='right', padx=(0, 6))
        self.rows.append((f'{name} {item_id}'.lower(), line))
        return e

    def build_ui(self):
        tk, c, t = self.tk, self.c, self.t
        self.label(self.win, t['warn'], fg=c['gold'], wraplength=510, justify='left').pack(fill='x', padx=10, pady=(10, 6))
        top = tk.Frame(self.win, bg=c['bg'])
        top.pack(fill='x', padx=10)
        will = next(r for r in self.save['rows'] if r['group'] == CURRENCY and r['id'] == WILL_ID)
        self.label(top, t['will'], size=10).pack(side='left')
        will_entry = self.entry(top, will['qty'])
        will_entry.pack(side='left', padx=8)
        self.entries[will['index']] = (will, will_entry)
        self.query = tk.StringVar()
        search = tk.Entry(top, textvariable=self.query, bg=c['panel'], fg=c['text'], insertbackground=c['text'], relief='flat')
        search.pack(side='right', fill='x', expand=True, padx=(12, 0))
        search.insert(0, t['search'])
        search.bind('<FocusIn>', lambda e: search.get() == t['search'] and search.delete(0, 'end'))
        box = tk.Frame(self.win, bg=c['bg'])
        box.pack(fill='both', expand=True, padx=10, pady=8)
        canvas = tk.Canvas(box, bg=c['bg'], highlightthickness=0)
        bar = tk.Scrollbar(box, command=canvas.yview)
        self.body = tk.Frame(canvas, bg=c['bg'])
        self.body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        holder = canvas.create_window((0, 0), window=self.body, anchor='nw')
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(holder, width=e.width))
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        self.win.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-e.delta // 120, 'units'))
        self.rows = []
        for row in sorted((r for r in self.save['rows'] if r['group'] == ITEMS), key=lambda r: r['id']):
            name = self.names.get(str(row['id']), f"#{row['id']}")
            self.entries[row['index']] = (row, self.item_row(name, row['id'], row['qty']))
        owned = {r['id'] for r in self.save['rows'] if r['group'] == ITEMS}
        missing = [m for m in SAFE_MATERIALS if m not in owned]
        if missing:
            head = tk.Frame(self.body, bg=c['bg'])
            self.label(head, t['add'], fg=c['gold']).pack(side='left', pady=(10, 2))
            self.rows.append(('', head))
            for item_id in missing:
                self.additions[item_id] = self.item_row(self.names.get(str(item_id), f'#{item_id}'), item_id, 0)
        self.query.trace_add('write', lambda *a: self.filter())
        self.filter()
        buttons = tk.Frame(self.win, bg=c['bg'])
        buttons.pack(fill='x', padx=10, pady=(0, 10))
        tk.Button(buttons, text=t['close'], command=self.win.destroy, bg=c['panel'], fg=c['text'], relief='flat',
                  padx=12).pack(side='right')
        tk.Button(buttons, text=t['save'], command=self.commit, bg=c['gold'], fg=c['bg'], relief='flat',
                  padx=12).pack(side='right', padx=8)

    def filter(self):
        q = self.query.get().strip().lower()
        q = '' if q == self.t['search'].lower() else q
        for _, line in self.rows:
            line.pack_forget()
        for text, line in self.rows:
            if (text and q in text) or (not text and not q):
                line.pack(fill='x', pady=1)

    def collect(self):
        """Reads the entry boxes into (quantity changes, material additions); raises ValueError naming a bad entry."""
        quantities, additions = {}, {}
        for index, (row, e) in self.entries.items():
            text = e.get().strip().replace(',', '').replace('.', '')
            if not text.isdigit() or int(text) > limit_for(row):
                raise ValueError(self.names.get(str(row['id']), row['id']))
            if int(text) != row['qty']:
                quantities[index] = int(text)
        for item_id, e in self.additions.items():
            text = e.get().strip()
            if not text.isdigit() or int(text) > MAX_ITEM:
                raise ValueError(self.names.get(str(item_id), item_id))
            if int(text):
                additions[item_id] = int(text)
        return quantities, additions

    def commit(self):
        t, mb = self.t, self.messagebox
        try:
            quantities, additions = self.collect()
        except ValueError as err:
            mb.showerror(t['title'], t['bad'].format(name=err), parent=self.win)
            return
        if not quantities and not additions:
            mb.showinfo(t['title'], t['none'], parent=self.win)
            return
        if game_running():
            mb.showwarning(t['title'], t['running'], parent=self.win)
            return
        if not mb.askyesno(t['title'], t['confirm'].format(n=len(quantities) + len(additions)), parent=self.win):
            return
        try:
            backup = write(self.path, self.save, quantities, additions)
        except (SaveFormatError, RuntimeError, OSError) as err:
            mb.showerror(t['title'], t['fail'].format(err=err), parent=self.win)
            return
        mb.showinfo(t['title'], t['done'].format(backup=backup), parent=self.win)
        self.win.destroy()
        self.on_saved()
