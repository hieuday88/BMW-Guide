# Changelog

## Unreleased
- The overlay never steals focus from the game; the mouse passes through it by default and the backtick key (`) toggles clicking the overlay.
- Directions follow the roads and valleys painted on the map (A* on a cost grid built from the map images), with walking distance and a turn hint for the next stretch.
- Chapter-2 dragon content (Red Loong, Boshen Censer, Unrequited Benevolence) is listed only in Chapter 2.
- Every boss, chief and spirit point on the minimap has its Vietnamese name.
- Celestial pills are guidance only; items that get used up or handed over stay ticked.

## v1.2.0

### Minimap
- The minimap is now part of the overlay window, square, above the checklist, using sharper 2048px maps.
- Smooth 60 fps rendering: the map layer is redrawn only when the view moves (about 2% of one CPU core).
- Green player arrow with a white outline that stands out on the map.
- Hover a point to see its official Vietnamese name.

### Points hidden from the save
- Activated shrines, defeated bosses and chiefs, owned spirits and unique items are hidden straight from the save, including progress made before the app was installed.
- Opened chests are matched to their in-game actor and hidden.
- Chest, pickup and NPC points disappear once you stand nearby and nothing is there any more.
- Learned points reset when you start a new game or switch to a different save.

### Guidance
- Click a checklist line or area title to get directions: the map stays centred on your character and draws a dashed line and a blue arrow toward the target, with the distance and a turn hint relative to where you face (e.g. "↗ ahead right"). Click the map to stop guiding.
- Lines without their own map point guide you to the area's Keeper's Shrine.

### Checklist fixes
- The starting Medicine Gourd now ticks from the save.
- The pre-order Red Immortal Gourd is shown as guidance only.
- The Black Wind Mountain Land God line ticks once you have Immobilize, since his Journal entry unlocks later.

## v1.1.0
- Live minimap (F11) read from game memory (read-only, no DLL injection), with automatic discovery of the game's world pointer.
- Map images, icons and points from [jaskang/wukong-minimap](https://github.com/jaskang/wukong-minimap) (Apache-2.0).
- Activated shrines hide from the save; pickups are learned from save changes.

## v1.0.0
- Ticks come only from the save file: Journal entries, items, equipment, spirits, spells, meditation spots and activated shrines.
- Untracked lines (story, quests, consumed items) are shown as dimmed guidance and do not count toward progress.
- Standalone `BMW_Guide.exe` built with PyInstaller.

## v0.1.0 (first commit)
- Always-on-top checklist overlay with compact mode, F9/F10 hotkeys and smooth scrolling.
- Automatic and manual save selection, Vietnamese and English checklists for all 6 chapters, BMW icon and shortcut installer.
