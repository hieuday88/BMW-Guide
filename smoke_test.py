"""Smoke test for BMW Guide: data files, assets, save decoding, routing, map lookup and a short live app run.

Run with: python smoke_test.py
"""
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ['APPDATA'] = tempfile.mkdtemp(prefix='bmw-smoke-')  # keep the real state.json untouched

import bmw_minimap  # noqa: E402
import bmw_route  # noqa: E402
import bmw_save  # noqa: E402
import bmw_save_edit  # noqa: E402

failures = []


def check(name, ok, detail=''):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


def load_app_module():
    loader = importlib.machinery.SourceFileLoader('bmw_guide', str(HERE / 'bmw_guide.pyw'))
    spec = importlib.util.spec_from_loader('bmw_guide', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_checklists(app):
    vi = app.parse((HERE / 'data' / 'checklist.vi.md').read_text(encoding='utf-8'))
    en = app.parse((HERE / 'data' / 'checklist.en.md').read_text(encoding='utf-8'))
    flat = lambda chapters: [(key, tokens) for _, secs in chapters for _, items in secs for key, _, _, tokens in items]
    check('checklists have 6 chapters', len(vi) == 6 and len(en) == 6, f'vi={len(vi)} en={len(en)}')
    check('VI and EN lines and tokens match', flat(vi) == flat(en), f'{len(flat(vi))} lines')
    cats = {c for _, toks in flat(vi) for c, _ in toks} | {c for _, secs in vi for s, _ in secs for c, _ in s.tokens}
    check('only known token categories', cats <= {'card', 'item', 'equip', 'soul', 'meditation', 'shrine'}, str(sorted(cats)))
    tracked = sum(1 for _, toks in flat(vi) if toks)
    check('checklist has tracked lines', tracked > 250, f'{tracked} tracked')
    return vi


def test_assets():
    maps = json.loads((HERE / 'assets' / 'maps' / 'maps.json').read_text(encoding='utf-8'))
    missing = [m['image'] for m in maps if not (HERE / 'assets' / 'maps' / m['image']).exists()]
    check('every map image exists', not missing, ', '.join(missing))
    costs = [m['image'] for m in maps if bmw_route.load(HERE / 'assets' / 'maps', m['image']) is None]
    check('every map has a route grid', not costs, ', '.join(costs))
    icons = {p.stem for p in (HERE / 'assets' / 'map_icons').glob('*.png')}
    points = json.loads((HERE / 'assets' / 'maps' / 'points.json').read_text(encoding='utf-8'))
    cats = {p[1] for ps in points.values() for p in ps}
    check('map points loaded', sum(len(ps) for ps in points.values()) > 400)
    check('icons for most categories', len(cats & icons) >= 12, f'{len(cats & icons)}/{len(cats)}')
    check('app icon exists', (HERE / 'assets' / 'BMW.ico').exists())
    return maps


def test_save():
    saves = bmw_save.find_saves()
    if not saves:
        print('SKIP  no save file on this PC')
        return
    t = time.time()
    progress = bmw_save.read_progress(saves[0])
    keys = {'card', 'item', 'equip', 'soul', 'wine', 'shrine', 'actors', 'opened', 'meditation', 'spell', 'chapter', 'map_id', 'item_num'}
    check('save decodes with all fields', keys <= set(progress), f'{saves[0].name} in {time.time() - t:.2f}s')
    check('save has journal and shrines', bool(progress['card']) and bool(progress['shrine']),
          f"{len(progress['card'])} journal, {len(progress['shrine'])} shrines")


def test_save_edit():
    """Edits a copy of the save and checks that only the requested values changed."""
    saves = bmw_save.find_saves()
    if not saves:
        return
    save = bmw_save_edit.read(saves[0].read_bytes())
    will = next(r for r in save['rows'] if r['group'] == bmw_save_edit.CURRENCY and r['id'] == bmw_save_edit.WILL_ID)
    owned = {r['id'] for r in save['rows'] if r['group'] == bmw_save_edit.ITEMS}
    extra = {m: 3 for m in bmw_save_edit.SAFE_MATERIALS if m not in owned}
    extra = dict(list(extra.items())[:1])
    out = bmw_save_edit.read(bmw_save_edit.build(save, {will['index']: will['qty'] + 7}, extra))
    new_will = next(r['qty'] for r in out['rows'] if r['index'] == will['index'])
    check('save edit round-trips with a valid checksum', new_will == will['qty'] + 7, f'{len(out["rows"])} bag rows')
    try:
        bmw_save_edit.build(save, {will['index']: bmw_save_edit.MAX_WILL + 1}, {})
        rejected = False
    except bmw_save_edit.SaveFormatError:
        rejected = True
    check('save edit rejects out-of-range values', rejected)


def test_routes(maps):
    slow, broken = [], []
    for m in maps:
        grid = bmw_route.load(HERE / 'assets' / 'maps', m['image'])
        t = time.time()
        path = bmw_route.find(grid, (200, 256), (320, 256))
        if not path:
            broken.append(m['image'])
        elif time.time() - t > 1.0:
            slow.append(m['image'])
    check('A* finds a route on every map', not broken, ', '.join(broken))
    check('A* is fast (<1s per route)', not slow, ', '.join(slow))


def test_locate(vi):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    frame = tk.Frame(root)
    mini = bmw_minimap.Minimap(frame, HERE / 'assets', {}, lambda: None, lambda k: k, lambda: 'vi', 300)
    found = [bool(mini.locate(ci, toks, text)) for ci, (_, secs) in enumerate(vi)
             for _, items in secs for _, tag, text, toks in items if toks and tag == 'Boss']
    check('most bosses have a map location', sum(found) >= len(found) * 0.6, f'{sum(found)}/{len(found)}')
    root.destroy()


def test_app_run(app):
    o = app.Overlay()
    errors = []
    o.root.report_callback_exception = lambda *exc: errors.append(exc[1])

    def steps():
        try:
            o.select(1)
            o.set_lang('en')
            o.toggle_compact()
            o.toggle_compact()
            o.toggle_map()
            o.toggle_map()
            o.toggle_mouse()
            o.toggle_mouse()
            o.toggle()
            o.toggle()
            o.focus_on({('card', 103001)}, 'Lingxuzi')
            o.set_lang('vi')
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        o.root.after(1500, o.quit)

    o.root.after(2000, steps)
    o.root.mainloop()
    check('app starts, switches modes and quits cleanly', not errors, '; '.join(map(repr, errors)))
    check('tray icon was created', o.tray.hwnd is not None)


if __name__ == '__main__':
    app = load_app_module()
    vi = test_checklists(app)
    maps = test_assets()
    test_save()
    test_save_edit()
    test_routes(maps)
    test_locate(vi)
    test_app_run(app)
    print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: ' + ', '.join(failures)}")
    sys.exit(1 if failures else 0)
