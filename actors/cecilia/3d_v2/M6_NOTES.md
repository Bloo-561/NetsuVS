# Milestone 6: toon shading (Guilty Gear Xrd style)

The model now uses a cel shader built on the published Guilty Gear Xrd / Arc System Works model: Motomura's GDC 2015 talk, galloscript/GGXrdShading and Aerthas' ASW shaders for Unity and Blender. It has a two-tone ramp plus a darker second tone and a specular term. Every colour is sampled from the sheet, there is one fixed key light, and the inverted-hull outlines are as wide as the sheet's line art.

Silhouettes are unchanged; shading doesn't move geometry:

| | front | back | side |
|---|---|---|---|
| IoU | **0.9503** | **0.9503** | **0.9676** |
| target | 0.95 | 0.95 | 0.92 |

Outline width is the FWHM of the dark band at the outer contour, measured the same way on both (`scripts/measure_lines.py`). Values are in sheet px:

| | front | back | side |
|---|---|---|---|
| sheet | 1.86 | 1.83 | 1.98 |
| model (beauty renders, 2x) | 1.76 | 1.75 | 1.76 |

- Review sheet: `renders/m6_review.png`. It has, per view, the sheet, the model, a 50 % overlay and the silhouette diff, then 3/4 views, head close-ups, part close-ups, the palette and the control maps.
- Single renders: `renders/m6_final_*.png`.
- Test passes: `renders/m6_t1..t8_*`, plus `m6_s05/s08/s11_*` from the jacket sheen sweep.
- Saved file: `cecilia_v2.blend`. The M5 file is in `backup/m5/`, see Backups.

## The shader (`toon.py`, node group `GG_Shade`)

Per pixel:

```
light   = ((N.L + 1) * occlusion) / 2 + (2 * threshold - 1) + bias
shadow1 = light < 0.5                         -> the sheet's shadow tone
shadow2 = occlusion < 0.1 or threshold < 0.1  -> shadow^2 / lit (darker, more saturated)
spec    = N.H > 1 - size, inside the specular mask, lit areas only -> specular colour
```

- `N` uses smoothed shading normals:
  - the face: radial normals;
  - the hair: normals from a smooth proxy;
  - body parts: blurred normals (`NORMAL_BLUR`, now including the jacket).
- The steps are hard, with 0.008 of anti-aliasing.
- No shadow maps. The only exception is the bangs' shadow on the forehead (`gg_face`), which now stops above the eyes (`CAST_ROWS`).

**Key light.** One direction, fixed in world space: from her right-front, 46° round from the front, 30° up (`KEY_DIR`). This is the ASW shaders' default, a scene light or a fixed direction; they also offer a light that follows the view, which isn't used. Front and side are therefore lit like the sheet, and the back view is mostly her own shadow (see Known issues).

**Outlines.** Inverted hulls 1.75 sheet px thick, and never thinner than 1 render px. The width is set per render from its scale (`set_line_width`). Colours:
- body parts: the colour of the sheet's own contour next to each colour family (`bake.outline_colours` → `textures/body_lineclr.png`, e.g. dark red on red);
- hair: near black on the black, dark purple on the tips;
- face, neck, ears: the jaw line's brown.
- No outline where the hair is pushed in round the ears (`EAR_PIT`).

## Control textures (`shade_bake.py`, about 30 s)

GG's artists paint these; here they are measured from the model:

| channel | what | how |
|---|---|---|
| `body_ctrl` / `hair_ctrl` R | occlusion | sky visibility per texel from 96 directions (numpy depth maps, 3 mm). Mapped so that < 0.18 is always shadow 2, < 0.34 shadow 1 and > 0.55 plain N.L. The skull filler and the ear pits count as open. |
| G | threshold | 0.5 neutral. 0.2 (always shadow 1) on the jacket's lapel facing, a 19 mm band along the front opening that the sheet draws dark in front and side views. |
| B | specular mask | metal fittings (gold, silver, steel; not the headband's printed emblem), the whole black jacket (its sheen, placed by the N.H lobe), and hair sheen strands (64 thin tapered streaks along the hair's flow, crown to the top of the purple). |

`body_ao.png` and `hair_ao.png` hold the raw occlusion, for debugging. `body_sheen.png` is where the sheet itself draws the jacket's sheen. It was tried as the mask and dropped (see Decisions); it is kept as a measurement.

## Colours (all sampled from the sheet)

- **Fabrics, skin, metal.** The M5 families: lit and shadow tone, each measured on the sheet. The second shadow is computed from them.
- **Hair.** From the hair pixels' luminance clusters, the same in all three views:
  - black: lit 78/79/84, shadow 66/67/72 (the sheet's hair shading is subtle, and M3's bluish shadow was too dark);
  - mid purple: 118/56/106 and 84/36/80;
  - tips: 154/81/137 and 100/44/94;
  - sheen: grey 100/100/106. The blue marks on the sheet are the teal clips, not highlights.
- **Neck.** Always in shadow, 246/172/152, the sheet's warmer tone under the chin.
- **Ear.** 245/211/183 and 223/177/154, from the side view.
- **Jacket sheen.** 121/121/125, the sheet's light-grey cluster, with a lobe size of 0.06.
- **Neckerchief satin.** 255/232/146, the sheet's lightest yellow, not the metal's white.

## Changes to earlier milestones found while shading

- **Stocking ribbons: criss-cross wrap, not the M5 lattice.** This settles the open question from M5. The sheet's own socks panel (`refs/cecilia_ref_detail_socks.png`, "wears crisscross sock") draws two ribbons wound round the leg in opposite directions, as does the main render. They cross in front at the three fitted rows and behind, half-way between.
  - From the front the X's are now thin and reach the leg's edges, like the sheet.
  - At 3/4 they read as lacing instead of a chain of diamonds.
  - Ribbons are 4.5 px wide, from the front view's red runs (the lattice fit had 6.8).
  - `bake.RIBBON_STYLE = "lattice"` brings the M5 pattern back.
- **Headband emblem.** At the old texel density the emblem blurred into "TV". The detail sheet draws "IV".
  - The headband's UV islands now get 3x the density (`uv_unwrap.TEXEL_BOOST`).
  - It takes no projected line art (those lines were its own edges) and no metal glint.
- **Ear pits.** M3 pushed the hair in round each ear, so the ear shows as on the side view. The pit's walls rendered as a dark framed box. They now shade like the hair around them, with no outline.
- **No long key-light shadow on the thighs.** The sheet has only a narrow band under the lace, which the occlusion term gives. `KEY_RECEIVERS` is empty.

## Decisions

- **World-fixed key light** for every render, including the reference views: one light, as the brief asks. A light per view would make the back view match the sheet better, but the model would then be lit differently in every shot.
- **Jacket sheen from the N.H lobe, not from the sheet's mask.** The sheet's highlight shapes differ from view to view. Projected onto the model they gave blocky patches. A narrow lobe over the whole jacket gives clean shapes: the upper chest and front panels from the front, the bust and shoulder from the side. Together with the dark lapel band, the jacket reads as black with sheen, as on the sheet. The sweep is in `renders/m6_s05/08/11_*` (lobe 0.05, 0.08, 0.11) and `m6_t2` (the sheet mask).
- **Hair sheen stays subtle.** It uses the sheet's grey, thin streaks, shown only near the highlight direction.

## Known issues (what still looks wrong)

1. **Side and back views of the ribbons.** The sheet's side and back views draw an X on every face at the same three heights. No continuous wrap can do that, and the socks panel, front view and main render all show the wrap. From the side our ribbons show as crossing diagonals, not centred X's; from the back the X's sit between the front ones.
2. **Back view is darker than the sheet.** The fixed key light is in front of her, so her back is mostly in shadow tone. The sheet's back view is drawn lit.
3. **Hair shadow edge is a straight line** across the hair at 3/4. It is the terminator on the smooth proxy normals. GG's hair shadows follow the clumps (painted thresholds); that would need hand-painted hair thresholds.
4. **Face shadow at 3/4** is one clean straight diagonal from the radial normals. It is clean, but not shaped like an artist's face shadow.
5. **Jacket sheen** follows the light, not the sheet's exact shapes. From the front it is smaller on her left side than on the sheet.
6. **Emblem close-up.** The "IV" is as sharp as the sheet's few pixels allow. Very close views would want a hand-drawn decal.
7. **Still open from M4/M5:**
   - the loafers' vamp and the bows' loops;
   - the end-on hand in the side view (skin where the sheet has the glove);
   - the hilt's bent angle, which M7 straightens.

## Files

| file | what changed |
|---|---|
| `scripts/toon.py` | `GG_Shade` group; materials for baked parts, hair, flat skin; outline materials and width; colour constants above; ear pits |
| `scripts/shade_bake.py` | new: occlusion, threshold, specular and strand maps |
| `scripts/bake.py` | outline colour atlas; sheen measurement (`smooth3d`); criss-cross ribbons (`ribbon_phase`, `helix_mask`); headband line rule |
| `scripts/uv_unwrap.py` | `TEXEL_BOOST` for the headband |
| `scripts/gg_face.py` | the bangs' shadow stops above the eyes |
| `scripts/review_body.py`, `review_head.py` | line width set per render |
| `scripts/m6_preview.py` | driver: bake → shade bake → materials → renders (+ IoU) |
| `scripts/measure_lines.py`, `scripts/m6_sheet.py` | line-width check and review sheet (plain Python + Pillow, outside Blender) |
| `textures/body_ctrl.png`, `hair_ctrl.png`, `body_lineclr.png`, `body_sheen.png`, `body_ao.png`, `hair_ao.png` | new maps |
| `textures/body_*.png`, `hair_mask.png` | re-baked (new UV layout for the headband; ribbons) |

## Backups

`backup/m5/` holds:
- the M5 `cecilia_v2.blend`;
- its textures, which M6 re-baked in place. They were reproduced with the M5 settings: same UVs, lattice ribbons. The atlas matches the one on `renders/m5_review.png` to 0.2/255 mean difference;
- the `refs/` files the M5 file links (relative paths);
- `M5_NOTES.md`.

## Rebuild

```python
S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
m4 = runpy.run_path(S + r"\m4_preview.py")
m4["run"]("tag", build=m4["FULL"], shade=False)                               # geometry (5 s)
runpy.run_path(S + r"\m6_preview.py")["run"]("tag", unwrap=True, sil=True)    # UVs, bake, shade bake, materials, renders (~2 min)
```

A rebuild from the saved file reproduces the M6 textures byte for byte (checked: all 11 maps identical md5).
