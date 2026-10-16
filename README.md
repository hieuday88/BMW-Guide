<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">An in-game checklist and live minimap overlay for <b>Black Myth: Wukong</b> that tracks your progress straight from the save file.<br>
<a href="README.vi.md">Tiếng Việt</a> · <b>English</b> · <a href="CHANGELOG.md">Changelog</a></p>

---

## Features

### Checklist
- **Always-on-top overlay that never steals the game's focus.** By default the mouse passes straight through it to the game (🔒); press **`** (backtick, left of 1) to use the overlay (🖱) and press it again to lock it. Run the game in *Borderless / Windowed* mode.
- **Follows game progression.** All 6 chapters, ordered by Keeper's Shrine, with bosses, spirits, items, spells, quests, secret areas, meditation spots and tips.
- **Ticks come only from your save, never by hand.** The app reads the game's save and marks Journal entries (bosses and enemies met), items, equipment, spirits, spells, meditation spots and activated shrines (⛩ next to the area name).
- Dimmed `·` lines are guidance the save does not record (story beats, quests, consumed items) and do not count toward progress.
- **Finds your save automatically** (Steam, Epic or standalone installs), or pick a save file under ⚙.
- **Vietnamese / English**, switch under ⚙ → Language.
- **Compact mode (F10)** shows only the next 3 steps and their tips.
- **Tray icon.** A BMW icon in the system tray (next to the clock) shows the app is running. Left-click to show / hide it; right-click for show / hide, mouse lock, minimap and Quit.

### Minimap (F11)
- A live map around your character, built into the overlay above the checklist, at 60 fps with a green facing arrow.
- Shows chests, Luojia Fragrant Vines, Awaken Wine Worms, bosses, chiefs, spirits, meditation spots, shrines and NPCs. Hover a point to see its name; scroll to zoom.
- **Finished points disappear**, judged from the save: activated shrines, defeated bosses and chiefs, owned spirits and unique items, and opened chests. Chest, pickup and NPC points also disappear once you stand nearby and nothing is there.
- **Directions along the paths:** click a checklist line or area title. A dashed route follows the valleys and roads painted on the map (not a straight line through mountains), with the walking distance and a turn hint for the next stretch (e.g. "→ right"). The route updates when you stray. Lines without their own point guide you to the area's shrine. Click the map to stop guiding.
- Your position is read from game memory **read-only**. Nothing is injected and nothing is written.

## Install

**Quick:** download `BMW_Guide.exe` from [Releases](https://github.com/hieuday88/BMW-Guide/releases) and double-click it. Nothing else to install. Windows SmartScreen may warn because the exe is unsigned.

**From source:**
1. Install [Python 3.10+](https://www.python.org/downloads/) and tick *Add to PATH*. No extra packages are needed.
2. Download this repo (**Code → Download ZIP**) and extract it.
3. Run the shortcut installer. It creates a **BMW Guide** shortcut on the Desktop and in the Start Menu, with the hotkey **Ctrl+Alt+B**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
   ```

Set the game to **Borderless / Windowed** while playing.

## Hotkeys

| Key | Action |
|---|---|
| `` ` `` (backtick, key left of 1) | Lock / unlock the mouse (🔒 passes through to the game, 🖱 lets you click the overlay) |
| `F9` | Show / hide the overlay |
| `F10` | Toggle compact / full mode |
| `F11` | Show / hide the minimap |
| `Ctrl+Alt+B` | Launch the app (Start Menu shortcut) |
| Mouse wheel | Scroll the list, or zoom when over the map |
| Drag the title bar | Move the window |

## Editing the checklist

The data lives in `data/checklist.en.md` and `data/checklist.vi.md`. Each line looks like this:

```
- [Boss] Bullguard — first boss, grants Immobilize @card:102004
```

The `@category:id` token at the end of a line is the in-game ID used for auto-ticking. Categories are `card` (Journal), `item`, `equip`, `soul` (spirit), `meditation` and `shrine` (on area headings). Lines without a token are shown as guidance. Both files must keep the same line order. The exe reads a `data/` folder next to it if present, so you can edit the checklist without rebuilding.

## Notes

- The app only **reads** your save file and game memory. It never writes to either.
- Vietnamese names follow the community Vietnamese translation. Sources include game8, PowerPyx, bmwukong.info, BWIKI and 3DM.
- Minimap images, icons and point data come from [jaskang/wukong-minimap](https://github.com/jaskang/wukong-minimap) (Apache-2.0), see `assets/maps/NOTICE.txt`.
- This is a personal fan project, not affiliated with Game Science.
