# Changelog

## v1.3.2

### Checklist
- Every line was checked against the official Vietnamese localization: names now match the game, and 393 lines tick from the save (up from about 320).
- Added the missing Journal entries, including the spider sisters, Hong Yi, Crane Immortal, Mandrill Chief, Fuban and several Chapter 5 chiefs.
- Added the six relics, the missing curios and gourds, staffs with how to craft or upgrade them, drinks, soaks and seeds.
- Added the six missing meditation spots and the missing shrines.
- Spirits, gourds and Coconut Wine stay ticked after you upgrade them.

### Minimap
- All meditation spots guide you to the actual cushion and hide once you have meditated there.
- Spirit points use their base ids, so they hide once you own the spirit.

## v1.3.1

### Minimap
- Opened chests are matched to the save by each chest's own GUID, so chests that share an actor name in different areas no longer hide each other.
- A chest only counts as opened when the save marks it opened; chests you only touched stay on the map.
- A failed memory read no longer looks like an empty spot, so pickups and chests are not hidden by mistake.
- Materials dropped by a boss or chief hide once that boss is defeated; pills, curios and other pickups inside opened chests hide too.
- Standing near a point shows its name and distance (e.g. "📍 Bích Ngẫu Kim Đan · 2 m"), and nearby icons are drawn above the player arrow.
- Points that only had generic labels (chests, pills, NPCs, meditation spots) now have full Vietnamese names.

### Checklist
- Spirits stay ticked after you upgrade them (every upgrade tier has its own id in the save).
- Ids were checked against the official localization: added the six missing meditation spots (Chapters 3 and 5), missing shrines and several boss, NPC and item ids.
- Meditation lines guide you to the actual cushion on the map and tick from the save.
- The starting gourd uses its official name, Lão Hồ Lô.

## v1.3.0

### Playing comfort
- The overlay never steals focus from the game: by default the mouse passes straight through it (🔒). Press the backtick key (`) to click the overlay (🖱) and press it again to lock.
- Tray icon next to the clock shows the app is running. Left-click shows / hides it; right-click opens show/hide, mouse lock, minimap and Quit.

### Directions
- Routes follow the roads and valleys painted on the map (A* on cost grids built from the map images) instead of a straight line through mountains.
- Shows the walking distance and a turn hint for the next stretch (e.g. "→ right"); the route updates when you stray.
- Checklist lines can point to map locations in other chapters (e.g. the Red Loong from Chapter 2).

### Minimap
- Every boss, chief and spirit point has its Vietnamese name, and most hide once the save shows them defeated or collected.
- Empty pickup points (celestial pills, vines, wine worms, curios) disappear when you stand nearby and nothing is there.

### Checklist
- Content is listed in the chapter where you can actually do it: the Red Loong, Boshen Censer and Unrequited Benevolence moved to Chapter 2; the Wandering Wight now follows the Gourd step with clear notes.
- Items that get used up or handed over stay ticked; celestial pills are guidance only because the save does not record eating them.
- The Black Wind Mountain Land God ticks once you have Immobilize.

### Quality
- `smoke_test.py` checks the checklists, assets, save decoding, routing, map lookups and a live app run.

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
