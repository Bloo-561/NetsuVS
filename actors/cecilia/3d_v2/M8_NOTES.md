# Milestone 8: sprite test

`renders/idle_test.png` is her idle stance rendered as a game sprite:
- transparent, 1024 x 1024, facing right;
- 247 px tall including the ahoge (rows 374–620), the same height as idle1.png;
- feet on row 620 and the rear foot's leftmost pixel on column 403;
- seen through a camera fitted to idle1.png.

`renders/idle_test_smooth.png` is the same frame with anti-aliased alpha instead of the pixel-art cut-out.

| check | value |
|---|---|
| framing | rows 374–620, columns 403–595 (idle1: 375–621, 403–587) |
| silhouette IoU against idle1.png | **0.695** |
| contour darkness (mean / median luminance of the outermost pixels) | 65.8 / 48 (idle1: 60.5 / 48) |

The review sheet is `renders/m8_review.png`. It shows the sprite next to idle1 at 3x with a 50 % overlay and the silhouette difference. It also shows:
- the full frames with the row 620 / column 403 guides;
- a second frame through the same camera next to `5m4.png`;
- the skirt-shadow fix, before and after;
- the camera fit.

## The camera (`scripts/sprite.py`, scene SPRITE, camera CAM_sprite)

**Angle.** Orthographic, 80° round to her right from her front, level. That is the fighting-game side view: her legs nearly side-on, the camera slightly in front of her right side. 5.23 mm per pixel.

**How the angle was found.** The angle was fitted, together with the idle stance, by matching silhouettes.
- `sprite.fit()` poses the stance, renders a white silhouette and maps it onto idle1's framing: same height, lowest row 620, rear foot on column 403.
- It scores the overlap with idle1's own silhouette and adjusts by coordinate descent on 13 parameters: camera azimuth and elevation, the feet, hip height and turn, lean, chest and head turn, and where the sheath is held.
- The search states are in `renders/checks/sprite_fit_v2.json` and `_v3.json`.

| step | IoU |
|---|---|
| M7 stance at the M7 guess (40°, 5° up) | 0.29 |
| fitted | 0.66 |
| face and sword fixed by hand, then refitted | 0.68 |
| final sprite (supersampled, outlines) | 0.695 |

**Fixed by hand.** The silhouette can't see a face, so the fit turned her head until the face was hidden behind her hair. I turned it back to show her face 3/4, as on idle1. The fit also tucked the short sword into the body, to avoid paying for idle1's long one. I set it back in front of her at the belt.

**Framing.** `sprite.frame_camera()` frames the current pose exactly: a few silhouette passes set the scale and the camera's position. `idle_test()` framed the camera on the idle stance.

**Keep the camera fixed for every other frame.** Pose the rig and render. The camera stays put, so scale and ground line stay the same.
- The draw-slash `renders/5m4_test.png` was rendered that way with the camera untouched, its rear foot planted where the idle's stands. It landed with its feet on row 620 and its rear foot on column 403, exactly where `5m4.png` has them.
- Silhouette IoU against 5m4: 0.554. The sprite's blade is 1 m long, and its lunge is deeper than her legs reach.

## The render (`sprite.render`)

1. EEVEE renders at 4x the size: 4096 x 4096.
2. The outline hulls are 1 output pixel wide: idle1's outline is one dark pixel.
3. The image is box-filtered down to 1024.
4. Alpha is cut at 50 %, giving hard edges like the pixel-art sprites. `smooth=True` keeps the anti-aliased alpha instead.

PNGs are read and written with straight alpha. OpenImageIO would otherwise premultiply them.

## The skirt's shadow on the legs is now live (M7 known issue 3)

The occlusion map was baked in the rest pose, so the thighs kept the old skirt shadow when the skirt lifted, including the lace's scalloped edge.

**Fix.** The legs no longer bake the skirt's shadow:
- `shade_bake` bakes their sky share without the skirt and lace (raw, in R).
- A Geometry Nodes modifier on each leg (`GG_skirt_occ`, `toon.skirt_occ_group`) ray-casts the posed skirt and lace from every vertex. It uses 32 directions over its hemisphere, cosine-weighted, out to 0.6 m.
- The leg material (`toon.gg_leg_material`) multiplies the two and remaps the result like the bake did.

**Result.**
- In the rest pose the narrow band under the lace is unchanged (front view: 43 pixels differ, by at most 42 levels).
- In the idle and the lunge, the shadow now follows the skirt. The lace pattern is gone.

**Guards added.** The bake, the materials and the M6 renders now force the rig's Rest Position while they run (`shade_bake.run`, `toon.apply`, `m6_preview.run`). `toon.apply` also re-creates the eye drivers after rebuilding the face material.

## What still looks wrong

1. **The sword.** It is the sheet's 41 cm, so her hands are close together. On idle1 they hold a 1 m tachi at both ends. This is the open question from M7, still undecided; the sheet's length was kept.
2. **Proportions.** At equal height, the sprite draws her head about a third bigger, and her hair fuller and more violet. The model keeps the sheet's proportions and colours, so the head and hair are most of the remaining silhouette difference (the red at the top of the diff).
3. **Detail at 250 px.**
   - The face is the sheet's, so the eyes are 2–3 px and read as small dots; the sprites draw them larger.
   - Interior lines are the sheet's coloured line art, lighter than the sprites' near-black pixel outlines. The outer contour matches idle1's darkness.
4. **Pose details.**
   - idle1's elbows flare wider and its sword sits a little higher.
   - The draw-slash is more upright and higher than 5m4, with bent arms where 5m4's are straight.
5. **Not pixel art.** The frames are a clean downscaled cel render: no palette, no hand-placed pixels. Matching the hand-made sprites exactly would take a pixel-art cleanup pass.
6. **Under the skirt.** Nothing is modelled there; your call, from M7.

## Files

| file | what |
|---|---|
| `scripts/sprite.py` | new: sprite camera and scenes, framing, the idle1 fit, beauty render, `idle_test()`, `frame_test()` |
| `scripts/rig_poses.py` | `IDLE` refitted (M7 values kept as `IDLE_M7`, pose `idle_m7`); `pose_idle` and `pose_draw_slash` take keyword overrides; `draw_slash_sprite` (the cut laid out for the sprite camera, rear foot planted); `root_to()` |
| `scripts/shade_bake.py` | legs baked without the skirt and lace (`SKIRT_RECEIVERS` / `SKIRT_OCCLUDERS`); rest-pose guard |
| `scripts/toon.py` | `skirt_occ_group`, `skirt_occlusion`, `gg_leg_material`; rest-pose guard; eye drivers re-created |
| `scripts/m6_preview.py` | rest-pose guard |
| `scripts/m7_review.py` | renders M7's idle (`idle_m7`), so M7's sheet stays reproducible |
| `scripts/m8_sheet.py` | review sheet (plain Python + Pillow) |
| `textures/body_ctrl.png`, `body_ao.png`, `hair_*`, `shade_report.json` | re-baked (legs only changed) |
| `renders/idle_test.png`, `idle_test_smooth.png`, `5m4_test.png`, `5m4_test_diff.png`, `m8_review.png`, `m8_*` | results |
| `renders/checks/` | fitting states, silhouettes and trial renders |

## Backups

`backup/m7/` holds:
- the M7 `cecilia_v2.blend`;
- `M7_NOTES.md`;
- the control textures this milestone re-baked (`textures/`).
