# Cecilia 3D v2: Milestone 3 (head and hair)

**Result:** silhouette IoU **front 0.9523, back 0.9501, side 0.9735** (targets 0.95 / 0.95 / 0.92).

Head band (rows 0-150) on its own: front 0.951, back 0.945, side 0.945. In M2 these were 0.953, 0.968 and 0.954: the M2 blockout was a smooth helmet. The real hair has the face opening, separate bangs and jagged tips.

Figures (in `renders/`):
- `m3_head_sheet.png`: sheet, model and 50 % overlay for front, side and back. Also three 3/4 views and the idle-sprite angle next to `idle1.png` and the design sheet's 3/4 head (that one for looks only).
- `m3_head_diffs.png`: silhouette diffs of the head.
- `m3_head_v3_*.png`: the single close-ups.
- `sil/m3_v3_*`: full-figure silhouettes, diffs and IoU json.

## What's in the file

`cecilia_v2.blend`, collection `MODEL`. The M2 helmet head, stand-in tips and ahoge are replaced by these objects:

| object | what it is |
|---|---|
| `hair` | One shell of 160 columns hanging from the crown. 3 mm thick (Solidify). |
| `bangs` | The bangs as solid locks, from the drawn front back to the forehead. |
| `face`, `nose` | Face front half-rings and the nose ridge. |
| `skull` | Inner volume, so no see-through in 3/4 views. |
| `neck` | |
| `ear_R`, `ear_L` | |
| `headband` | |
| `clip_R`, `clip_L` | |
| `ahoge` | |

Every object has a live preview material `PROJ_<name>` (emission only) that projects the sheet onto it. This is not the final texture: M5 bakes and cleans it, M6 replaces the shading.

Rebuild in Blender (after the M2 steps in `M2_NOTES.md`):
```python
import runpy; S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
runpy.run_path(S + r"\head_profiles.py", run_name="__main__")   # traced head data -> refs/profiles_head.json
runpy.run_path(S + r"\layers.py", run_name="__main__")          # colour layers -> refs/layers/
runpy.run_path(S + r"\build_head.py", run_name="__main__")      # head meshes
runpy.run_path(S + r"\silhouette.py")["run"]("my_tag")          # IoU + diffs
runpy.run_path(S + r"\projection.py")["apply"]()                # preview colours
runpy.run_path(S + r"\review_head.py")["run"]("my_tag")         # close-ups
```

## How it was built (traced, not guessed)

### Hair

**Cross-section.** Each pixel row is a ring whose width comes from the front/back edges and whose depth comes from the side edges.

The head blends the front and back views 30 / 70, not the body's 45 / 55. The front and back drawings disagree more at the hem tips. 30 / 70 is the split that puts both whole-figure IoUs over 0.95.

At the face rows the side view shows skin between the bangs and the side locks (temple, eye, cheek). So the ring is reshaped there:
- **Outside the face's width:** nothing is further forward than the side lock's front edge, which is traced from the side view.
- **Across the face:** the bangs keep their traced front in the middle and recede onto the forehead at the edges, 2 mm clear of it. So from the side, the eye and temple stay visible behind them.

**Where each column ends.** Walking down, a column continues while its own projection is still inside the drawing's hair in the view that owns it:
- the front view owns the bangs, the side locks' front faces, and anything facing the front;
- otherwise the back or side view owns it.

Neighbouring ends are joined diagonally, so the tips are pointed. Bigger jumps stay as separate locks.

**Bangs.** They are solid, from the drawn front back to the forehead. As a thin shell, the side view looked hollow.

**Ear.** Where the side view shows the ear, the hair tucks in behind it, so the ear shows as drawn.

### Face

- **Width:** from the front view's visible face.
- **Profile:** from the side view.
- **Cheek depth:** where the side view's skin meets the side lock.
- **Front:** a flat superellipse (exponent 3.4) down to the cheeks, rounding to 2 at the chin. With that exponent the eye corners land in the same 3D place from the front and from the side:
  - outer corner: 6.85 cm from the centre line, 3.9 cm in front of the waist mid-plane;
  - inner corner: 2.9 cm from the centre line, 7.6 cm in front of it.

### Colour (preview)

Each part projects only its own colours from per-class layers (`refs/layers`): hair, skin, band, clip. Everything else is filled with the nearest class colours. Without this, the side view's eye landed on the side locks, background white on bang tips, and the ahoge came out grey.

- The face uses the front drawing on its front and the side drawing, with the eye filled in, on its sides.
- The ears use the side drawing only.

## Changes from the M1 plan

- **Hair is one traced shell plus solid bangs, not 25-40 separate clumps.** The shell reproduces all three silhouettes by construction, which separately placed clumps would not guarantee. Clump meshes on top of the shell, for volume at near-profile angles, are proposed for M4.
- **Eyes are part of the projected face colours for now.** For the rig (M7) the irises become separate decal meshes, so the eyes can move.

## What looks wrong (honest list)

1. **No eye in the side close-up.** The front and side drawings put the iris in different 3D places:
   - front: iris 1.4 cm from the inner corner;
   - side: iris near the back of the eye.

   No single texture can show both. With the side eye kept, every 3/4 view showed two irises side by side (tested). I kept the front eye, so 3/4 views are clean and the exact profile shows only the eye's edge.

   Fix if you want the profile eye: a view-dependent eye in the M6 shader, where the drawn profile eye fades in only when the camera is near side-on. This is a common anime-rendering trick.

2. **Idle angle (62°) is the weakest view.** The hair reads as a smooth helmet with projected strands. The near eye is narrow, as real foreshortening makes it; the sprite draws it wide. The bangs end in a straight edge. A skin patch shows between bang tips at the temple.

   M5/M6 should help: flattened colours, cel ramp, outlines. But the hair has no real strand clumps. Adding a few clump meshes on the shell for volume would be M4 work.

3. **Front view.**
   - The side locks' inner edges are straight where they meet the face.
   - The locks' inward curl under the jaw is missing.
   - The face's top edge is straight between the bang gaps.

   Small.

4. **Side view.**
   - The bangs end flat in profile; the drawing has separate tips.
   - The back of the hair is fuller than drawn. The drawing has one loose strand standing off the back, and the model fills the gap behind it: 195 of the side head's 417 model-only px.

5. **Back view.** Most of the remaining head error (311 of 455 model-only px) is the side locks' tips seen from behind. Their ends are traced from the side view, so they fill notches the back view draws between tips. I tried bounding them by both views: that traded the same pixels the other way.

6. **Two teal clips.** The sheet's front view and the design sheet both show one clip on each side. The brief mentions one, on her right. I kept both; easy to remove.

## Go / no-go

**Go.**
- In the three sheet views the head matches by construction (silhouettes above target, the drawing's own colours on traced geometry).
- At 25-40° it reads as Cecilia with a clean face.

The open risk is near-profile angles like the idle sprite. Problems 1 and 2 above are what I would work on next (M4 hair clumps, M6 view-dependent eye).

If you judge the 3/4 views not good enough, the fallbacks from the brief:

- **(a) AI multi-view image-to-3D.** You run the three crops in `refs/` through a multi-view generator such as Hunyuan3D-2mv and drop the mesh into `3d_v2/_incoming`. I clean it, retopologise, re-project, rig and shade it. Expect better strand volume but looser silhouettes.
- **(b) VRoid.** You build her head (or the whole figure) in VRoid Studio and export a VRM; I import it and do the rest. VRoid's eye and hair systems handle 3/4 faces well, but matching the sheet's exact shapes is manual work on your side.

Either fallback can be limited to the head and fitted onto the traced body.

---

# Face rework: Guilty Gear style (after the M3 review)

You said the M3 face looked chunky and that you want it like Guilty Gear. Milestone 4 is on hold until you OK this direction.

**Silhouettes are unchanged and still pass:** front **0.9521**, back **0.9503**, side **0.9732** (measured with the toon outlines hidden, see below).

Review sheet: `renders/m3_gg_face_review.png` (before/after, sheet vs model, 3/4 views, idle angle). Single renders: `renders/m3_gg8_toon_*.png` (transparent background).

## What changed

### The face

- **Shape.** One smooth sculpted face replaces the stacked rings. The front outline comes from the front view, the profile from the side view, and the cheek depth from where the side view's skin meets the side lock. A small nose ridge sits on the centre line. There is no separate nose object any more.
- **Texture.** The turnaround's face is only about 60 px wide, too blurry for cel shading. The eyes now come from the sheet's **high-resolution eyes panel**, registered onto the front view (cross-correlation, scale 6.34, NCC 0.82). Everything else is flat skin plus clean redrawn lines at their traced positions: the cat-mouth smile, the nose dot and a soft blush. Script: `face_texture.py`.
- **View-dependent eyes.** The sheet draws the eyes out to the face's visible edge, where the 3D face turns back towards the ears, so an eye projected from the front smeared at 3/4. The shader now handles each eye separately (`gg_face.py`):
  - **Near eye:** drawn in screen space at its front-view size, hung from its inner corner. Between 60° and 90° it slides back and narrows to where and how wide the side view draws it.
  - **Far eye:** stays front-planar, so it compresses and tucks behind the cheek like a real far eye.
  - **Front view:** identical to the sheet.
- **Hair shadow on the forehead.** Cast by the key light. Only the bangs cast shadows, so the face never shadows itself (that was the noise in the first toon test).

### Cel shading (preview of M6; `toon.py`)

- **Light.** One fixed key direction: from her right-front, 46° round from the front and 30° up.
- **Two-tone step.** The step is on N·L, computed in the shader. There are no shadow maps except the bangs' cast shadow, so every render is clean and repeatable.
- **Shadow tints** (sRGB multipliers): skin 0.95/0.80/0.78, hair 0.60/0.58/0.72.
- **Neck:** always in the chin's shadow.
- **Normals:**
  - face: radial from a point inside the head, giving one clean shadow shape;
  - hair: copied from a capsule around the head (a hemisphere on a cylinder), so the hair's light/shadow edge is one clean curve. This is the usual anime/GG trick.
- **Outlines.** Inverted hulls, 1.6 mm. The seam where the bangs meet the hair shell has zero outline width (vertex group `outline_w`). The skull filler has no outline.
- **Flat colours:**
  - **Hair:** a dark base (73, 74, 82), a mid purple and the tip purple (140, 68, 124). The cut points come from a projected purple mask, `refs/layers/hairp_*.png`, made from the sheet's hue and saturation, so the flame-shaped tips follow the drawing.
  - **Headband:** flat red with a gold emblem.
  - **Ears and neck:** flat skin.

### Hair geometry

- **Hem:** neighbouring column ends are always joined diagonally (`FAN_ROWS` 4 → 30), giving pointed tips. The old rectangular notches drew stair-step outlines.
- **Bangs:** their thickness now eases down to 3 mm over the last 9 px above each tip, so the locks end in thin points instead of a solid visor block.

### Pipeline fixes

- **Projection:**
  - its view weights now come from the geometry's own normals, stored as the attribute `proj_n`, so the toon normals don't change what projects where;
  - toon outline hulls and non-rendering helpers no longer count as occluders.
- **Silhouette IoU:** measured with the toon outline hulls hidden.

Rebuild everything: `runpy.run_path(S + r"\gg_preview.py")["run"]("tag", textures=True)`.

## What still looks wrong (honest list)

1. **The hair is still one traced shell.** At 3/4 and idle angles the bangs read as one block, almost a cap visor; the drawing has separate spiky locks. A jagged skin patch (the temple) shows between the bangs and the side hair.

   Fix: M4 hair clumps on top of the shell, with the GG strand lines and highlights in M5/M6.
2. **Side view:**
   - the bangs' tips make a beak-like shape;
   - the ear is a plain skin-coloured egg (no inner ear line yet);
   - outlines show inside the lower hair near the ear (where the hair tucks in behind the ear).
3. **No hair highlight yet.** The design sheet has a bluish sheen on the hair. Planned for M6.
4. **The far cheek's shadow edge is a straight line at 40°** (radial face normals). M6 can shape it with painted normal offsets, as GG does.
5. **Below the chin** a straight edge of the back hair's inside shows. It belongs with the jacket collar in M4.
