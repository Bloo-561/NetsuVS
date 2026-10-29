# Handoff — Oct 25 2026, night (Noah, Leticia's portrait, the seven-element emblem, select music)

**Build first:** C# changed (two new engine actions). Open the project in Godot and press **Build** (hammer, top right)
before playing. Godot imports Noah's new pictures the first time it opens (a minute or two).

## 1. Noah is playable
Fourth on the roster (after Leticia). Everything is in `docs/characters/noah.md`; the short version:
- Built from the Noah_Complete pack and its `COMMAND_LIST.md`: all basics, normals, 13 specials / EX moves and both
  supers (Raging Storm, God Press), with his own projectiles (shadow waves, the energy wall, two kinds of black hole).
- His gimmicks: **black holes** (623A near / 623B far, they wait 5 s; 623 again snaps his fingers: they suck the opponent
  in and burst — the near one throws them away, the far one toward him) and **stocked energy** (Void Grasp 214A / Void
  Devour 214C drain the opponent; the next 214 + A / B is the Overflow Ray beam).
- Frame data is my first pass (nothing was given): `data/frame_data/Noah.xlsx`. Health 10000.
- Colours: Umbra (as drawn), Crimson, Azure, Pale. Win quotes, bio and the pause-menu command list are placeholders
  in `tools/sprite_port/setup_noah.py`.
- CPU: all six levels (`tools/ai/build_noah_ai.py`). Sounds are borrowed from the others for now.
- New engine actions: `NetsuSpawnTriggerAction` (the snap sets off waiting holes), `NetsuPullOpponentAction` (suction).

## 2. Leticia's new portrait
The arms-crossed render is her character-select picture and super cut-in (`actors/leticia/Artwork/Leticia_Select_FullBody.png`,
`CutIn_Super.png`); her win screen keeps the old one. The dual-gun render is saved at
`actors/leticia/Artwork/Gallery/Leticia_DualGuns.png` for a gallery later.

## 3. Loading emblem: the seven elements
The medallion now has seven stones in the Trails element colours — Earth (brown), Water (blue), Fire (red), Wind (green),
Time (black), Space (gold), Mirage (silver) — each with its own engraved sign (mountain, drop, flame, gusts, hourglass,
star, eye). Colours: `stone_colors` / `glow_colors` in `game/ui/netsu/netsu_emblem.gd`.

## 4. Character select music
Starts when the screen actually appears (after the loading fade), not while the emblem is still up
(`SceneRouter.wait_shown()`, `scenes/character_select/character_select.gd`).

## Checked (in a test copy of the project)
- Every Noah move run in Training and looked at (positions, hits, damage, launches); character select, VS screen, cut-ins.
- Rollback sync test (save, run 8 frames, load, run again, compare, every frame): Noah vs Cecilia / Flan / Leticia / Noah,
  random play plus scripted runs of his specials (holes + snap, waves, wall, grabs, supers): no difference anywhere.
- Not played on your PC yet: press Build first, then the checklist.

## Testing checklist
1. **Build.** Character select: Noah is the 4th slot; his portrait; the music starts as the screen appears.
2. Any screen change: the emblem with seven coloured stones.
3. Training as Noah: 236A / 236B (waves), 623A then 623A again (hole, snap), 623B then 623B (far hole pulls them in and
   throws them toward you), 214A on hit then 214A again (the beam), 214B (overhead), jump 214A, 236C, 214C,
   236236 + A (Raging Storm), 214214 + A (God Press: carries them toward the wall).
4. Leticia on character select: the arms-crossed portrait.

## Backups
Everything this update replaced on the PC: `_backup_stage_select/pre_push_oct25_noah/` (same folders, `.bak`); the list:
`_backup_stage_select/push_oct25_noah/push_manifest.tsv`.
