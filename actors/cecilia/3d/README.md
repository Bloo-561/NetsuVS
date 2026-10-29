# Cecilia 3D (test)

T-pose test model of Cecilia Richter for Netsu VS, built entirely by Python scripts in Blender 5.2.
Reference: `reference/Cecilia_Turnaround.png` (front/back/side sheet). `Artwork/Cecilia_DesignSheet.png` still wins on conflicts
(e.g. only ONE arm band, on her right arm).

## Files
- `cecilia.blend` - the model (collections: Cecilia = body/head, Hair, Outfit, Tachi).
- `scripts/` - everything is rebuilt from these:
  - `lib.py` helpers (lofting, toon materials, inverted-hull outlines), `palette.py` colors (base, shadow).
  - `body.py`, `hair.py`, `outfit.py`, `tachi.py` - one script per part, each has `build()`.
  - `build_all.py` - rebuilds everything, adds outlines, saves `cecilia.blend`.
  - `render_views.py` - front / 3-4 / side / back review renders into `renders/`.
  - `make_face_texture.py` - paints `textures/face.png` (eyes, brows, mouth, blush). Run with normal Python + Pillow.
  - `compare.py` - puts review renders next to the sheet at the same scale.
- `textures/face.png` - face decal (front-projected onto the head).
- `renders/` - review images.

## Rebuild / render
In Blender's Python console:
```python
import sys; sys.path.insert(0, r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d\scripts")
import build_all, render_views
build_all.run()          # rebuild + save
render_views.render()    # writes renders/review_*.png
```
Change colors in `palette.py`, proportions in the tables at the top of `body.py` (TORSO, LEG) and re-run.

## Conventions
1 unit = 1 m, Z up, she faces -Y, her LEFT is +X. Height ~1.56 m (1.61 with ahoge). Shading is a 2-tone toon emission
material driven by a FIXED world-space light direction (`lib.LIGHT_DIR`), so every frame shades the same way.
Outlines are inverted-hull Solidify modifiers named "Outline" (thickness 2 mm).

## Sword
`Tachi_Sword` (empty at the grip, children: hilt, guard, blade) and `Tachi_Sheath` (empty at the sheath mouth) are
separate, so the sword can be re-parented to a hand bone later.

## Not done yet (next milestones)
Rig (armature, IK, hair/skirt/neckerchief bones, sword sockets), posing, sprite camera + idle render test.

## Needs an artist's touch
Hair is a smooth helmet of clumps (no highlight shapes or strand detail yet); face is a painted decal (no expression
variants); clothes have no wrinkles/inner line art; jacket back slit not modeled.
