# Handoff Nov 2 2026 (evening): Character select in the Melty Blood Act Cadenza style

Reference: "Melty Blood: Evolution of Select Screen" (YouTube), 3:19–4:43 (Act Cadenza). Kept Netsu's colours, fonts, renders, background and select theme.
Backup of the previous screen and intro: `_backup_stage_select/pre_select_mb_nov02/`.

## Screen
- **Top centre:** a light line across the screen with a NETSU VS plate. Below it is the heat emblem: a crimson ring that turns and pulses on the beat, a blue tick ring, seven element stones and a twelve-ray sun. The mode (TRAINING / VERSUS…) sits over the emblem, where the reference shows its time limit. The old CHARACTER SELECT and mode headers in the top corners are gone.
- **Middle:** a faint block of lore text behind the renders.
- **Scrolling lines:** a bright line shows the fighter under the cursor and their bio (`FighterProfile.Bio`), scrolling right to left and coloured by side. Under it, a faint theme line scrolls left to right.
- **CHARACTER SELECT** sits over the roster, with blue and crimson hairlines.
- **Roster:** two rows of upright portrait tiles at the bottom centre with thin white frames. The top row is shifted left and the bottom row right. Settings: `tile_size`, `tile_gap`, `tile_rows_y`, `tile_rows_shift`.
- The big renders slide in from farther out (160 px) when the cursor changes. Name plates, assists, colours and the sprite preview are unchanged.
- Files: `scenes/character_select/netsu_select_mb.gd` is new. It is two nodes: kind 0 (back: emblem and lore) and kind 1 (front: plate, mode, scrolling lines, label). `character_select.gd` builds them.

## Intro (timed to the select theme, 166 BPM)
- Starts dark; the scrolling lines fade up before the first beat.
- **Beat 1 (0.34 s):** CHARACTER SELECT flashes in.
- **Every half beat after that:** a pair of portraits flies in with a white flash. The top row comes in from the left, left to right. The bottom row comes in from the right, right to left.
- **Beat 4 (1.42 s):** the dark lifts and the emblem flares. The plate and mode fade in, the fighters slide in and the cursors appear. Input opens here.
- Skipped when coming back from the stage select (the theme is already playing).
- `netsu_select_intro.gd` (the full-art intro) is no longer used. It is still in the folder.
