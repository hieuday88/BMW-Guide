"""Reads Black Myth: Wukong save files (ArchiveSaveFile.N.sav) and extracts progress IDs."""
import os
import string
import winreg
from pathlib import Path

XOR_KEY = bytes.fromhex('7b5cda913efcda37')
SAVE_GLOB = 'ArchiveSaveFile.*.sav'
DIR_HINTS = ('black', 'wukong', 'steam', 'epic', 'game', 'b1')

# Protobuf field paths inside FUStBEDArchivesData -> RoleData(1) -> RoleCs(1).
BAG, ACTOR, COLLECTION, CHAPTER = 2, 3, 8, 11
ECS = 6  # PersistentECSData -> BPCData(2) -> BPCRebirthPointData(3) -> ActivedRebirthPointList(2)


def _varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def _fields(b):
    """Yields (field, wire_type, value) for a protobuf message."""
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 2:
            ln, i = _varint(b, i)
            v = b[i:i + ln]
            i += ln
        elif wt == 5:
            v = b[i:i + 4]
            i += 4
        elif wt == 1:
            v = b[i:i + 8]
            i += 8
        else:
            raise ValueError(f'bad wire type {wt}')
        yield f, wt, v


def _subs(b, field):
    return [v for f, wt, v in _fields(b) if f == field and wt == 2]


def _first(b, *path):
    for field in path:
        found = _subs(b, field)
        if not found:
            return b''
        b = found[0]
    return b


def _ints(b, field):
    """Returns all int values of a field, accepting packed or unpacked encoding."""
    out = []
    for f, wt, v in _fields(b):
        if f != field:
            continue
        if wt == 0:
            out.append(v)
        elif wt == 2:
            i = 0
            while i < len(v):
                x, i = _varint(v, i)
                out.append(x)
    return out


def _ids(msgs, field=1):
    return {x for m in msgs for x in _ints(m, field)}


def _actor(guid):
    """Strips the editor GUID prefix from a persistent actor id, keeping e.g. 'BPO_TreasureBox_01_C_1'."""
    return guid.rsplit('-', 1)[-1]


def _actors(ecs):
    """Returns actor names of map symbols the player has activated (shrines, banners)."""
    names = set()
    for entry in _subs(_first(ecs, 2, 4), 1):
        key = _first(entry, 1)
        if key:
            names.add(_actor(key.decode('utf-8', 'replace')))
    return names


def _opened(ecs):
    """Returns actor names whose persistent interaction state is set (opened chests, activated objects)."""
    names = set()
    for level in _subs(ecs, 3):
        for buc in _subs(level, 2):
            for interact in _subs(buc, 5):
                if (_ints(interact, 1) or [0])[0] >= 1:
                    names.add(_actor(_first(buc, 1).decode('utf-8', 'replace')))
    return names


def decrypt_payload(raw):
    """Unwraps the ArchiveFile container and removes the repeating XOR layer."""
    payload = _first(raw, 2)
    return bytes(c ^ XOR_KEY[i % 8] for i, c in enumerate(payload))


def read_progress(path):
    """Returns {'card','item','equip','soul','wine','shrine','meditation','spell': set[int], 'chapter': int}."""
    data = decrypt_payload(Path(path).read_bytes())
    role = _first(data, 1, 1)
    bag = _first(role, BAG)
    progress = _first(role, ACTOR, 2)
    equips = _subs(bag, 3)
    return {
        'card': _ids(_subs(_first(role, COLLECTION), 1)),
        'item': _ids(_subs(bag, 2)),
        'item_num': {(_ints(m, 1) or [0])[0]: (_ints(m, 2) or [0])[0] for m in _subs(bag, 2)},
        'equip': _ids(equips) | {x for m in equips for x in _ints(m, 5)},
        'soul': _ids(_subs(bag, 7)),
        'wine': _ids(_subs(bag, 5)),
        'shrine': _ids(_subs(_first(data, ECS, 2, 3), 2)),
        'actors': _actors(_first(data, ECS)),
        'opened': _opened(_first(data, ECS)),
        'map_id': (_ints(_first(data, ECS, 2, 2), 6) or [0])[0],
        'meditation': _ids(_subs(progress, 11)),
        'spell': set(_ints(progress, 3)),
        'chapter': (_ints(_first(role, CHAPTER), 1) or [0])[0],
    }


def _steam_roots():
    roots = []
    for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                      (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')):
        try:
            with winreg.OpenKey(hive, key) as k:
                for name in ('SteamPath', 'InstallPath'):
                    try:
                        roots.append(Path(winreg.QueryValueEx(k, name)[0]))
                    except OSError:
                        pass
        except OSError:
            pass
    return roots


def _candidate_dirs():
    for steam in _steam_roots():
        yield from steam.glob('userdata/*/2358720/remote/win64_save')
        yield steam / 'steamapps/common/BlackMythWukong/b1/Saved/SaveGames'
    local = os.environ.get('LOCALAPPDATA')
    if local:
        yield Path(local) / 'b1/Saved/SaveGames'
    for letter in string.ascii_uppercase:
        drive = Path(f'{letter}:/')
        if not drive.exists():
            continue
        try:
            tops = [d for d in drive.iterdir() if d.is_dir() and any(h in d.name.lower() for h in DIR_HINTS)]
        except OSError:
            continue
        for top in tops:
            for depth in ('', '*/', '*/*/', '*/*/*/'):
                yield from top.glob(f'{depth}b1/Saved/SaveGames')


def find_saves():
    """Returns save files found on this PC, newest first."""
    seen, found = set(), []
    for d in _candidate_dirs():
        try:
            files = list(d.glob(SAVE_GLOB)) + list(d.glob(f'*/{SAVE_GLOB}'))
        except OSError:
            continue
        for f in files:
            key = str(f).lower()
            if key not in seen:
                seen.add(key)
                found.append(f)
    return sorted(found, key=lambda f: f.stat().st_mtime, reverse=True)


if __name__ == '__main__':
    import sys
    saves = [Path(sys.argv[1])] if len(sys.argv) > 1 else find_saves()
    assert saves, 'no save found'
    p = read_progress(saves[0])
    print(saves[0])
    for k, v in p.items():
        print(k, sorted(v)[:12] if isinstance(v, set) else v, len(v) if isinstance(v, set) else '')
    assert p['card'] and p['item'], 'decode failed'
