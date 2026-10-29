# Blender stand-in (for checking stage build scripts without Blender)

A tiny fake `bpy` / `bmesh` / `mathutils` that is just enough to run a stage's `build_*.py`, plus
`run_mock.py`, which runs the build and writes a flat-colour `.glb` (one colour per material, simple shading)
with the same node names as the real export. Godot can then render that from the fight cameras to check the
layout, scale and framing before any bake. It catches script errors (missing materials, bad faces) too.
It does NOT do lighting, textures or materials.

```
python3 run_mock.py ../../ordis_manor/src/build_ordis_manor.py day out.glb om_names.json om_prev.json
```

`*_names.json` maps build groups to export node names, `*_prev.json` gives each material a preview colour.
Not used by the game (this folder has a `.gdignore`).
