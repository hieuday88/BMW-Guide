<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">An in-game checklist overlay for <b>Black Myth: Wukong</b> that ticks itself from your save file.<br>
<a href="README.md">Tiếng Việt</a> · <b>English</b></p>

---

## Features

- **Always-on-top overlay.** The window is translucent, has rounded corners and can be dragged around. The game must run in *Borderless / Windowed* mode.
- **Follows game progression.** All 6 chapters are ordered by Keeper's Shrine and cover bosses, spirits, items, spells, quests, secret areas, meditation spots and tips.
- **Auto-ticks from your save.** The app reads the game's save file and marks everything you have done: bosses met in the Journal, items, equipment, spirits, spells and meditation spots.
  - The save is re-read only when it changes, so CPU cost is near zero.
  - Auto-ticked entries show a teal ◆. You can still tick or untick entries by hand, and the app keeps your manual choices.
- **Finds your save automatically** (Steam, Epic or standalone installs). You can also pick a save file manually from ⚙.
- **Vietnamese / English:** switch under ⚙ → Language.
- **Compact mode (F10):** shows only the next 3 steps and their tips, taking up very little screen space.

## Install

1. Install [Python 3.10+](https://www.python.org/downloads/) and tick *Add to PATH*. No extra packages are needed.
2. Download this repo (**Code → Download ZIP**) and extract it.
3. Run the shortcut installer. It creates a **BMW Guide** shortcut on the Desktop and in the Start Menu, with the hotkey **Ctrl+Alt+B**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
   ```
4. Set the game to **Borderless / Windowed**, then launch BMW Guide.

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

The `@category:id` token at the end of a line is the in-game ID used for auto-ticking. Categories are `card` (Journal), `item`, `equip`, `soul` (spirit) and `meditation`. Both files must keep the same line order.

## Notes

- The app only **reads** your save file. It never writes to it.
- Sources include game8, PowerPyx, bmwukong.info, BWIKI and 3DM.
- This is a personal fan project, not affiliated with Game Science.
