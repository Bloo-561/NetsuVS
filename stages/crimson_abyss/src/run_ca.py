# Background pipeline for Crimson Abyss. Launched as:
#   blender --background --factory-startup --python run_ca.py -- STEPS=build,preview TAG=gb
import bpy, sys, os, json, time, traceback
S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\crimson_abyss\src"
R = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\crimson_abyss\renders"
args = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
STEPS = set(args.get("STEPS", "build,preview").split(","))
TAG = args.get("TAG", "gb")
CAMS = args.get("CAMS", "CAM_mid,CAM_far,CAM_near").split(",")
status = S + r"\cache\_status.json"
if os.path.exists(status): os.remove(status)
info = {"steps": sorted(STEPS)}; t0 = time.time()
try:
    bpy.context.preferences.filepaths.save_version = 0
    if "build" in STEPS:
        ns = {"__name__": "__main__"}
        exec(open(S + r"\build_crimson_abyss.py", encoding="utf-8").read(), ns)
        info["build"] = ns["BUILD_INFO"]
        bpy.ops.wm.save_as_mainfile(filepath=S + r"\crimson_abyss.blend")
    else:
        bpy.ops.wm.open_mainfile(filepath=S + r"\crimson_abyss.blend")
    bk = None
    if STEPS & {"bake", "pv", "export", "regrade"}:
        bk = {"__name__": "lib"}
        exec(open(S + r"\bake_crimson_abyss.py", encoding="utf-8").read(), bk)
    if "bake" in STEPS:
        info["bake"] = bk["bake_all"]()
        bpy.ops.wm.save_mainfile()          # keep the Bake UVs even if a later step fails
    if "regrade" in STEPS: bk["regrade"]()
    if "pv" in STEPS: info["pv"] = bk["make_preview"]()
    if "preview" in STEPS or "pv" in STEPS:
        sc = bpy.context.scene
        cards = [bpy.data.objects[n] for n in ("CA_Mist", "CA_Tendrils", "CA_Streaks") if n in bpy.data.objects]
        if "pv" not in STEPS:
            for o in cards: o.hide_render = False        # show the animated cards in lit previews
        for c in CAMS:
            sc.camera = bpy.data.objects[c]; sc.render.filepath = R + "\\" + TAG + "_" + c + ".png"
            bpy.ops.render.render(write_still=True)
        for o in cards: o.hide_render = True
    if "export" in STEPS: info["export"] = bk["export_glb"]()
    bpy.ops.wm.save_mainfile()
    info["ok"] = True
except Exception:
    info["error"] = traceback.format_exc()
info["seconds"] = time.time() - t0
open(status, "w").write(json.dumps(info, indent=1))
