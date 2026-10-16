<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">An in-game checklist overlay for <b>Black Myth: Wukong</b> that ticks itself from your save file.<br>
<a href="README.md">Tiếng Việt</a> · <b>English</b></p>

---

## Features

- **Always-on-top overlay.** The window is translucent, has rounded corners and can be dragged around. The game must run in *Borderless / Windowed* mode.
- **Follows game progression.** All 6 chapters are ordered by Keeper's Shrine and cover bosses, spirits, items, spells, quests, secret areas, meditation spots and tips.
- **Ticks come only from your save, never by hand.** The app reads the game's save file and marks:
  - Journal entries (bosses and enemies met), items, equipment, spirits, spells and meditation spots;
  - activated Keeper's Shrines (⛩ next to the area name).
  - The save is re-read only when it changes, so CPU cost is near zero.
  - Dimmed `·` lines are guidance the save doesn't record (story beats, quests, consumed items…) and don't count toward progress.
- **Finds your save automatically** (Steam, Epic or standalone installs). You can also pick a save file manually from ⚙.
- **Vietnamese / English:** switch under ⚙ → Language.
- **Compact mode (F10):** shows only the next 3 steps and their tips, taking up very little screen space.

## Install

**Quick:** download `BMW_Guide.exe` from [Releases](https://github.com/hieuday88/BMW-Guide/releases) and double-click it. Nothing else to install.

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
| `F9` | Show / hide the overlay |
| `F10` | Toggle compact / full mode |
| `Ctrl+Alt+B` | Launch the app (Start Menu shortcut) |
| Mouse wheel | Scroll the list |
| Drag the title bar | Move the window |

## Editing the checklist

The data lives in `data/checklist.en.md` and `data/checklist.vi.md`. Each line looks like this:

```
- [Boss] Bullguard — first boss, grants Immobilize @card:102004
```

The `@category:id` token at the end of a line is the in-game ID used for auto-ticking. Categories are `card` (Journal), `item`, `equip`, `soul` (spirit), `meditation` and `shrine` (on area headings). Lines without a token are shown as guidance. Both files must keep the same line order. The exe reads a `data/` folder next to it if present, so you can edit the checklist without rebuilding.

## Notes

- The app only **reads** your save file. It never writes to it.
- Sources include game8, PowerPyx, bmwukong.info, BWIKI and 3DM.
- This is a personal fan project, not affiliated with Game Science.
