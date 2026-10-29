# Handoff — Oct 26 2026, evening (TamaDeez: menus & art)

No C# changed: no Build needed. Godot re-imports the changed pictures when it opens.

## Character select icons and match portraits
- **Noah's icon is centred** like everyone else's (his face was small and off to the left of the slot).
- **Cecilia and Leticia** now use the face from their **standing select render** (the big picture on the select screen)
  for their **select icon** and their **match portrait** (the battle HUD corner).
- Made by a new script, `tools/sprite_port/face_icons.py`: each face is scaled so the eyes are the same distance apart
  and placed on the same spot (select slot: `PORTRAIT`, HUD: `HUD` at its top). To re-do or add a fighter, measure the
  two eye centres in the source picture and add it to `FACES`. Noah's old portrait is kept as its source
  (`tools/sprite_port/derived/noah/Noah_Select_Portrait_src.png`). Running `make_artwork.py` again overwrites these
  pictures: run `face_icons.py` after it.
- Files: `actors/cecilia/Artwork/Cecilia_Select_Portrait.png`, `HUD_Portrait.png`; `actors/leticia/Artwork/
  Leticia_Select_Portrait.png`, `HUD_Portrait.png`; `actors/noah/Artwork/Noah_Select_Portrait.png`.

## VS screen
Noah's render is drawn with a smaller head than the others, so he looked far away. He's now zoomed 1.4× and moved up
45 px, about Cecilia's size: `render_framing` on the VS screen's root (`scenes/vs_screen/vs_screen.gd`, by the render's
file name: zoom, nudge across, nudge up). See `docs/vs_screen.md`.

## Testing checklist
1. Character select: the four slots, faces in the same place and about the same size; Cecilia's and Leticia's are the
   faces from their big renders.
2. A fight with Cecilia and Leticia: the HUD corner faces.
3. VS screen Cecilia vs Noah: about the same size.

## Backups
`_backup_stage_select/pre_push_oct26_art/` (every file this replaced, `.bak`).
