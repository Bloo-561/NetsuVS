# One-shot pipeline: build -> bake -> preview renders -> export glb.
# In Blender's Python console (or via the MCP connector):
#   exec(open(r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\thors_hall_3d\src\run_all.py", encoding="utf-8").read())
# Set STEPS to skip parts, e.g. STEPS = {"preview", "export"} to re-export after a regrade.
import bpy, time, json, traceback, os

S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\thors_hall_3d\src"
R = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\thors_hall_3d\renders"
STEPS = globals().get("STEPS") or {"build", "bake", "preview", "export"}
TAG = globals().get("TAG") or "pv"
status = S + r"\cache\_status.json"
os.makedirs(S + r"\cache", exist_ok=True)
if os.path.exists(status):
    os.remove(status)
t0 = time.time(); info = {"steps": sorted(STEPS)}
try:
    bpy.context.preferences.filepaths.save_version = 0
    if "build" in STEPS:
        ns = {"__name__": "__main__"}
        exec(open(S + r"\build_thors_hall.py", encoding="utf-8").read(), ns)
        info["build"] = ns["BUILD_INFO"]
        bpy.ops.wm.save_as_mainfile(filepath=S + r"\thors_hall_3d.blend")
    bk = {"__name__": "lib"}
    exec(open(S + r"\bake_thors_hall.py", encoding="utf-8").read(), bk)
    if "bake" in STEPS:
        info["bake"] = bk["bake_all"]()
    if "regrade" in STEPS:
        bk["regrade"]()
    if "preview" in STEPS:
        info["preview"] = bk["make_preview"]()
        for o in bpy.data.objects:
            if o.name.startswith("Preview"):
                o.hide_render = True
        sc = bpy.context.scene
        for c in ("CAM_mid", "CAM_far", "CAM_near", "CAM_far_left", "CAM_near_right", "CAM_jump_far"):
            sc.camera = bpy.data.objects[c]; sc.render.filepath = R + "\\" + TAG + "_" + c + ".png"
            bpy.ops.render.render(write_still=True)
    if "export" in STEPS:
        info["export"] = bk["export_glb"]()
    bpy.ops.wm.save_mainfile()
    info["ok"] = True
except Exception:
    info["error"] = traceback.format_exc()
info["seconds"] = time.time() - t0
open(status, "w").write(json.dumps(info, indent=1))
