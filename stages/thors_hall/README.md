# Thors Training Hall (2.5D painted stage)

`thors_hall_day.tscn` and `thors_hall_dusk.tscn` turn ONE painting into a 3D room:
floor, back wall, two side walls and a ceiling. The shader
`assets/shaders/projected_stage.gdshader` paints the room by projecting the
picture from a "reference camera", so the fight camera gets real parallax
when it pans and zooms.

## Swap the picture (same room, new lighting/time of day)
1. Put the new image next to these files (same size and same perspective works best).
2. Duplicate `thors_hall_day.tscn`, open it and change the `painting` texture on the
   four materials (Room > Floor / Ceiling / BackWall / LeftWall: Material > Shader Parameters).
3. Add it to `data/stage_list.tres` (ScenePath = the .tscn, Name, Thumbnail). It appears in the Stage Select.
   (Since Oct 24 the list names each stage's scene with ScenePath instead of loading it with Instance.)

## Make a stage from a different painting
The room has to match the painting's perspective. Measure in an image editor:
| Shader parameter | What to measure |
|---|---|
| `painting_size` | Image width, height in pixels |
| `horizon_px` | The vanishing point: where floor lines meet (x is usually the middle) |
| `focal_px` | Leave at `0.5 * height / tan(15deg)` (= 1756 for a 941 px tall image, matches the game camera) |
| `ref_position` | Where the "painter" stood. Keep x = 0, y = 1.5, z = 9 |
Then size the room (same values on the shader AND on the meshes in the scene):
- back wall distance:  `d = focal_px * ref_y / (floor_line_row - horizon_row)` -> `back_wall_z = 9 - d`
- half width:          `(back_wall_right_x - horizon_x) * d / focal_px`
- ceiling height:      `ref_y + (horizon_row - ceiling_line_row) * d / focal_px`

Thors Hall: horizon (836, 515), floor line row 588, back wall x 80..1590, ceiling row 180
-> back wall at z = -27.1, half width 15.5, ceiling 8.4.

Fighters stand on z = 0, walls are at x = +-12, the camera sits 6.5-16 m in front.
