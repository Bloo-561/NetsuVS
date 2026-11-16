# Miniature "illustration-style" stage technique (E's Laf reference, 2026-11-09)

Reference: two clips by Free (E's Laf dev, @FreeEslaf), plus blog entries 952 / 954 / 957 on eslaf.blog136.fc2.com.

## What the blog says (short)
- 952: the dragon-skull clip is his tweet from 2020-04-02: an illustration-style background seen from the work view. He likes the miniature feel, and **in a fighting game the camera only ever sees it from straight in front**, so nothing outside that view is built. He works in 3ds Max and is moving to Blender.
- 954: his new roguelike + fighting game project. The images are a Blender base body and pixel sprite tests, with no stage technique.
- 957: about UI. One stage idea: an **options toggle that greys out all backgrounds**. Rather than fully grey, it lowers saturation and pulls brightness to the middle, adjusted per stage.

## What the clips show
- **Dragon-skull town (projection):** a painted illustration is camera-projected onto rough low-poly shapes. The sea and clouds are curved painted strips in arcs at several depths. Only what the front camera sees exists.
- **Snow station (modelled):** full 3D props with flat cel-style grey-blue shading, one huge painted backdrop card, a floor with painted shadow decals, and a thin wedge-shaped diorama aimed at the fight camera.

## Pilot: Septian Chapel (2026-11-09)
- Thors Hall was already a projected painting (`stages/thors_hall/`, a 5-plane box), so the chapel was used instead: it has real depth layers.
- **Files:** `stages/septian_chapel/src/projection/` (has a `.gdignore`).
  - `chapel_plate.png`: the camera-matched 3840×2160 plate to paint over. PROJ camera at Godot (0, 3.35, 16), 64° horizontal, shift_y 0.08. It covers the far-camera pans (x ±4.75) and the near-right view (x 9.3), plus the spire and jump room.
  - `paint_project.py` (run in a background Blender on `septian_chapel.blend`, about 50 s):
    - renders each atlas group alone, unlit, from PROJ, plus a view-depth EXR;
    - bakes every atlas texel's world position and normal;
    - projects it into the plate with a depth test and a facing weight, and blends the painted colour into the atlas;
    - exports `septian_chapel_painted.glb` and A/B renders `ab_orig_*` / `ab_painted_*`.
  - `PLATE=<painted.png>` uses a real painting of the plate's view; without it a Kuwahara filter (`KSIZE`) stands in.
- **Result:** the projection lines up exactly from all fight cameras. The Kuwahara stand-in only blurs detail, so it was **not added to Stage Select**.
- **Coverage:** PROJ paints about 9% of the Chapel and Village atlas texels and about 1% of Land. Side and back faces keep the original texture.
- **Missing ingredient:** a real painting of `chapel_plate.png` (same layout). The low-poly silhouettes (icosphere and cone trees) stay as they are unless those meshes are replaced by painted cards.
