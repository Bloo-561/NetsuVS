# Stage screen filters: painted and anime, both tried and rejected (2026-11-09)

**Decision:** the user rejected both filters.
- **Painted:** "change it back, keep the realistic look".
- **Anime:** "remove it, we can change the shader in godot or something later".

Stages stay realistic: photo-textured, with leafy clumps and CC0 props (see `septian-chapel-trails.md`). Don't re-propose a full-screen stylisation filter unless the user asks. Smaller look tweaks can come later in Godot, for example per-material shaders or the WorldEnvironment.

## Where the files went
They're in the project's `DELETE/` folder (it has a `.gdignore`; the user deletes it). Paths are kept, so moving a file back to the same place restores it.
- `DELETE/assets/shaders/stage_paint.gdshader` (+ `.uid`): rotated-grid Kuwahara, depth ink lines, value banding, grade.
- `DELETE/assets/shaders/stage_anime.gdshader` (+ `.uid`): bilateral smoothing, cel bands with blue shadows, silhouette outlines, saturation and glow.
- `DELETE/stages/septian_chapel/src/projection/test_scenes/`: the test scenes, including fighter-sprite checks.

`septian_chapel_trails.tscn` has no filter node. A Godot render matched the realistic version (mean pixel difference 0.11, from the animated wind and particles).

## Useful findings, if this is ever revisited
- `hint_screen_texture` and `hint_depth_texture` work in Godot 4.7.2 Compatibility. An identity pass matches the unfiltered render exactly.
- A full-screen QuadMesh (`POSITION = vec4(VERTEX.xy * 2, 0, 1)`, `render_priority -128`, no depth test) restyles only the stage. The fighter Sprite3Ds draw in the transparent pass, after it, and stay crisp.
- Photo textures fight a stylised look: grain turns into speckle under edge filters. A stylised stage would need cleaner, flatter source materials, not just a post-filter.
