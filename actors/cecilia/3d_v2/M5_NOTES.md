# Milestone 5: textures (projected, cleaned, flattened)

The sheet's colours are now baked into UV textures: projected from the three views, cleaned, and flattened to the design's base colours with the sheet's line art kept. The live projection preview is gone; every part reads its colours through its UVs, so the colours stay on the model when it is posed (M7).

Silhouettes after the M5 geometry fixes (below):

| | front | back | side |
|---|---|---|---|
| IoU | **0.9503** | **0.9503** | **0.9676** |
| target | 0.95 | 0.95 | 0.92 |

- Review sheet: `renders/m5_review.png`. For each view it shows sheet, model, 50 % overlay and silhouette diff, then 3/4 views, close-ups and the baked textures.
- Single renders: `renders/m5_final_*.png`.
- Saved file: `cecilia_v2.blend`. Texture paths are now relative. The M4 file is in `backup/m4/`.

The renders use the preview toon light from M3. Final shading, line weights and the light are M6.

## Files

| file | what it is |
|---|---|
| `textures/body_base.png` | 2048 px atlas for every part except the face and hair: flat lit colours plus the sheet's line art |
| `textures/body_shade.png` | same layout: each colour's own shadow tone, sampled from the sheet's shaded areas (the toon shadow uses it) |
| `textures/hair_mask.png` | 1024 px: how purple the hair is at each point (the toon hair cuts it into three flat colours) |
| `textures/body_label.png`, `body_line.png` | debug: which colour family each texel took, and where the lines are |
| `textures/bake_report.json` | per part: texels, share seen by a view, colour shares, line share |
| `refs/m5/` | the sheet with its line art removed, and the detected lines |

The face keeps its drawn texture from the GG face rework (`refs/face/`). Neck and ears are flat skin.

## How it was done

1. **UVs** (`uv_unwrap.py`). Smart UV Project, then exact-shape packing with rotation. Two atlases:
   - body: 1.0–1.3 texels per mm;
   - hair: 2.4–2.6 texels per mm.
2. **Where each texel is.** The UV triangles are rasterised, which gives every texel its 3D position and normal.
3. **What each view sees** (`bake.py`). For each view, a numpy depth map of the whole model is drawn from that view's orthographic camera at twice the sheet's resolution. A texel takes a view's colour only if all of these hold:
   - it is the nearest surface there (no painting through to hidden surfaces);
   - it is more than 1.5 sheet px from any outline of the model in that view (0.5 px for small parts). The sheet draws its outlines there, and the toon outlines take that job;
   - it is inside the drawn figure;
   - it faces the view by less than about 68°. Views are weighted by cos⁴ of that angle.

   Her left side takes the side view mirrored, except the plain knee sock and the tachi, which are only on one side.
4. **Line art.** The sheet's thin dark strokes are found in each crop. A stroke is darker than the pixels 2–3 px away on both sides, and is either a darkened version of one side or near black. Specks under 16 px are dropped. The strokes are painted out before classifying, then put back as crisp lines.
   - **Line colour.** Each colour family has its own line colour, measured from the sheet's lines next to it (e.g. dark red on red, warm brown on gold).
   - **No lines on:** skin, the black jacket, loafers, socks, the saya and the lace. Their "lines" were other parts' edges or shading strokes.
5. **Flattening.** Each part has a short list of the design's colour families: 21 in all, each with a lit and a shadow tone measured on the sheet. A sample is assigned to the family whose shading range it is closest to, so soft shading and highlights all fold into one flat colour. The views then vote, weighted.
   - Where a family may appear is limited by boundaries traced on the sheet:
     - stocking top: row 416;
     - sock top: row 518;
     - shirt above the bodice: row 180;
     - glove, cuff, forearm and sleeve band: columns on each arm;
     - shoe soles: row 684 down;
     - skirt stripes: below row 325;
     - the jacket vent's pink: back centre only.
   - A 3×3 majority filter removes single-texel noise.
6. **Hidden areas.** Texels no view sees (soles, under the arms, inner thighs, inside the skirt, the bodice under the jacket, the top of the shoulders) take the nearest seen family, filled through a 4 mm voxel grid. UV islands are padded 8 texels, so no seams show.
7. **Two regular patterns are drawn from measurements** (`fit_patterns.py` reproduces the numbers). Projected, they broke up where one view handed over to the next, because each view draws them slightly differently.
   - **Stocking ribbons.** The front, side and back views each draw an X at the same three heights, in the middle of the leg. The only 3D pattern that shows an X on every face is a lattice: diamonds between the faces, which is what you see at 3/4.
     - Each view's X was fitted; the views agree. Crossing rows are 447.7 / 527.0 / 608.3, with upper and lower arm reaches per band, and the ribbons are 6.8 px wide.
     - The knee X is drawn skewed differently in each view, so its fit is looser.
   - **Skirt stripes.** Two white lines 8.6 and 14.1 px above the hem, 1.7 px wide. All three views agree within 0.6 px (sub-pixel peaks, 390 columns). They are drawn above the model's own hem, so they run unbroken all round.
8. **Shading** (`toon.py`). The textured parts use the same hard light/shadow step as the face and hair. Lit areas take `body_base`; shadow areas take `body_shade`, the sheet's own shadow colour for each family.

## Geometry fixes found while texturing

- **Bodice front.** Under the jacket's upper front, the bodice poked 1–2 cm out through the jacket. The projected colours had hidden this. Its front is now kept behind the jacket's front edges from the shoulder line down (it was from row 182).
- **Jacket vent.** The back hem was traced following the vent's notch, which left a slit showing the red bodice. The vent's pink now counts as jacket when tracing, and the vent is painted as the sheet's pink triangle.
- **Ankle bows.** The M2 lofts were a rounded block. They are cut to the drawn outline: the front view's red, plus the loops the back view shows beside the ankle.
- **Normal smoothing.** Now also on the neckerchief, collar pieces and skirt, whose faceting flickered in the toon step.

## Decisions

- **The jacket's light-grey areas are highlights, not grey panels**, so they are flattened to black. The main render confirms it: its jacket is plain black.
- **Ribbons: lattice, as the sheet draws them.** Your main render (`Artwork/Cecilia_MainRender.png`) reads more like a spiral criss-cross lacing: X's in front and at the back, diagonals between. That pattern can't put an X on the side, which is what the side view draws. Easy to switch if you prefer the main render's look.

## Known issues

1. **Bows.** From the front the bow has the right outline, but its inside is a flat block with a notch. The sheet's two loops and knot aren't modelled; from the side and at 3/4 it reads as a red block.
2. **Loafers** lost the vamp's line: the sheet's shoe shading came out as scribbles. Flat brown with a dark sole for now. A drawn vamp line could come in M6.
3. **Inside of the skirt.** It shows the stripes too: the solidified skirt reuses the outside's UVs. Only visible from low angles.
4. **Hands, side view.** The end-on hand shows skin fingertips where the sheet draws the black glove. The sheet's hand is a curled fist, ours is straight; the M7 rig poses it.
5. **The hilt** keeps the sheet's bent angle (see M4). Its colours are flat red and gold now, so it no longer takes the back view's white.

## Rebuild

```python
S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
m4 = runpy.run_path(S + r"\m4_preview.py")
m4["run"]("tag", build=m4["FULL"], shade=False)                   # geometry (5 s)
runpy.run_path(S + r"\m5_preview.py")["run"]("tag", unwrap=True)    # UVs, bake, materials, toon, renders (~1 min)
```

A from-scratch rebuild reproduces the saved model (same vertex counts, same IoU).
