# Milestone 4: clothing and tachi, detailed to the sheet

Every clothing part and the tachi are now their own traced geometry. The silhouettes pass in all three views:

| band | front | back | side |
|---|---|---|---|
| head/hair | 0.949 | 0.945 | 0.939 |
| arms | 0.951 | 0.948 | 0.970 |
| jacket | 0.937 | 0.929 | 0.961 |
| skirt+sword | 0.977 | 0.972 | 0.970 |
| legs | 0.941 | 0.946 | 1.000 |
| feet | 0.902 | 0.922 | 0.959 |
| **whole** | **0.9503** | **0.9504** | **0.9669** |

Targets: front/back ≥ 0.95, side ≥ 0.92. IoU is measured on the binary masks with the toon outline hulls hidden.

- Review sheet: `renders/m4_review.png` (sheet | model | 50 % overlay | silhouette diff per view, 3/4 views, close-ups).
- Single renders: `renders/m4_final_*.png`.
- Silhouettes and diffs: `renders/sil/m4_final_*`.
- Saved file: `cecilia_v2.blend`. The previous save is in `backup/m4_pre/`.

The colours are still the raw sheet projection. Cleaning them up is Milestone 5.

## What was built

All of it is scripted and rebuilds from scratch in about 5 s:

```python
m = runpy.run_path(S + r"\m4_preview.py")
m["run"]("tag", build=m["FULL"])
```

`FULL` builds, in order: M2 blockout → head → body + jacket → neck pieces → skirt → belts → hands → tachi. Then it projects, applies the toon shading, measures the silhouettes and renders the close-ups. A rebuild reproduces the saved model exactly (same vertex counts on all 43 objects, same IoU).

### Measurements (`trace_clothes.py` → `refs/profiles_m4.json`)

Each crop is split into colour classes (jacket, grey, red, maroon, gold, white, skin, hair, teal, brown). From those, per row or per column:

- **Jacket:** the front edges of the open jacket (front view) and the jacket's front edge (side view).
- **Bodice:** its front, which lies under the neckerchief tails.
- **Hems:** the jacket hem in all three views.
- **Skirt:** the red skirt's hem and the lace's bottom edge in all three views.

### Parts (`build_clothes.py`)

- **Body (bodice):** rings from the shoulder line into the skirt. Under the jacket, each ring's front curvature is solved so the jacket's traced front edges lie on top of it (6 mm gap). Below the jacket it becomes the traced waist.
- **Jacket:** an open shell from the shoulder line to the hem, 4 mm thick (Solidify). Its front edges are the traced opening. Its hem is blended per column from the front, back and side traces according to which way the column faces. A yoke runs in to the neckline.
- **Collar:** a band built from three traced loops (base, fold and outer edge) with the two points at the front.
- **Neck pieces:** neckerchief (bow and both tails), brooch, tie knot and shirt collar (`decals.py`). Each outline is traced in the front view and gridded at 0.5 px. Every vertex is ray-cast onto the body and lifted 1.5–3 mm, so in the front view each piece covers exactly what the drawing covers.
- **Belts:** two maroon belts with square buckles. Each one is a smooth loop z(θ) fitted to its centre line as traced in all three views (weighted Fourier fit), sitting 1.5 mm off the skirt/body.
- **Skirt:** 22 box pleats, 7 mm deep at the hem, on the M2 skirt rings. The hem follows the front, back and side traces by facing.
- **Lace petticoat:** scalloped (9 px period), sits inside the pleats above the hem and shows 9–12 px below it.
- **Hands:** fingerless-glove hands that replace the M2 arm ends. The palm is a rounded loft whose height comes from the front view's outline and whose depth comes from the side view's end-on hand. Four fingers fan slightly, plus the thumb.
- **Tachi:** built on the M2 centre lines. It has:
  - kashira (end cap), wrapped grip (tsuka) and guard plate (tsuba);
  - the saya's red mouth band, the white saya and its red/gold tip cap;
  - a flat blade inside the saya, hidden in renders and kept for the M7 draw;
  - the M2 hanger strap.

  Radii come from the front view (grip 10 px, cap 12 px) and proportions from the katana detail panel.
- **Loafers and ankle bows:** kept from M2 (traced in three views). They already match the side view's shoe and bow (see the close-up).

### Hair and face (`build_head.py`)

- **Bangs:** split into 4 locks at the traced notches between the tips. Every other lock sits 2.5 mm further forward, so the locks overlap and outline each other instead of reading as one visor.
- **Temples:** the face's sides run back under the hair. At the temples they poked out through the hair shell, which showed as the jagged skin patch at 3/4 and at the idle angle. Every face vertex that lies outside the hair is now pulled 2.5 mm inside it (955 vertices, rows 82–113). The visible face is untouched.

### Shading (`toon.py`)

The lofted parts follow the traced outline ring by ring, 1 sheet px apart. The binary masks' leftover 1-px staircase tilted the normals ring to ring, and the hard toon step turned that into a saw-toothed light/shadow edge on the legs. A small Geometry Nodes modifier now blurs the normals into custom normals on the legs (8 iterations), arms, body (6) and shoes (4). Geometry and silhouettes are unchanged.

## Decisions

- **Front vs back disagree.** The two drawings are not mirror images of one shape. The jacket's sides are 8–10 px wider in front than at the back (rows 210–240), her left hand reaches 15 px further in front, and the legs are spread 3–4 px wider. Orthographic silhouettes of one 3D object are exact mirrors, so every such pixel is wrong in one view or the other.
  - Of the 3,919 front pixels that miss, only 493 are places where the front and back drawings agree. The rest are this dispute.
  - The model sits between the two drawings. The jacket was widened 0.5 px per side towards the front view to bring both views over 0.95 (front was 0.9497).
- **The hilt is bent on the sheet.** The front view draws the hilt about 36° outward from the saya's line, pointing up and out. A straight sword would point it up and in. This is an illustration cheat:
  - the back view hides the hilt (a straight sword would be hidden there);
  - `idle1.png` holds the sword straight.

  The model follows the sheet at the hip, because the front and side views both need it and the front IoU depends on it. The hilt is its own set of parts (kashira, tsuka and tsuba, plus the blade) meeting the saya at the guard. **M7:** the hilt and blade pivot at the guard, so in hand (idle, draw-slash) they line up straight with the saya.

## Known issues

These are projection colours, for Milestone 5 unless noted:

1. **Leg streaks.** White or grey streaks run down the inner thighs and her left leg's inner calf, where the side view's colours wrap round. Her left thigh's back takes a grey-lavender colour.
2. **Back of the hilt.** It takes the back view's background (white), because the back view hides the hilt (see Decisions).
3. **Colour bleeds:**
   - the neckerchief's gold onto the bodice and jacket at the bust;
   - a dark band across the skirt's front at mid-height (from the side view);
   - white blotches on the skirt's side stripes.
4. **Hands.** The model's fingers are a little thicker and squarer than the drawing's.
5. **Back of the head (M6).** It renders darker than the sheet, because the key light comes from the front and the back is in shadow. Lighting and shadow tints are tuned in M6.
