# North Ambria (v3) - one-shot pipeline for a BACKGROUND Blender (never touches open windows):
#   blender --background --factory-startup --python "<project>/stages/north_ambria/src/run_na.py" -- \
#           STEPS=build,bake,preview,export,beauty CAMS=CAM_mid
# STEPS    blockout (grey blockout render from the game camera, nothing else), or any of
#          build, bake, regrade, preview, export, beauty   (export needs preview: it makes the unlit materials)
#          beauty = the final Cycles camera render of the full lit scene with a real storm -> renders/final_CAM_mid.png
# CAMS     preview renders to write into renders/ (default: none - "all" for the six fight cameras)
# Writes src/cache/_status_<VARIANT>.json when done.
import bpy, sys, time, json, traceback, os

S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\north_ambria\src"
R = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\north_ambria\renders"
args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
VARIANT = args.get("VARIANT", "storm")
STEPS = set(args.get("STEPS", "build,bake,preview,export,beauty").split(","))
TAG = args.get("TAG", "pv")
CAMS = args.get("CAMS", "")
if CAMS == "all":
    CAMS = "CAM_mid,CAM_far,CAM_near,CAM_far_left,CAM_near_right,CAM_jump_far"
BLEND = S + "\\north_ambria.blend"
status = S + r"\cache\_status_" + ("blockout" if "blockout" in STEPS else VARIANT) + ".json"
os.makedirs(S + r"\cache", exist_ok=True); os.makedirs(R, exist_ok=True)
if os.path.exists(status):
    os.remove(status)
t0 = time.time(); info = {"variant": VARIANT, "steps": sorted(STEPS)}
try:
    bpy.context.preferences.filepaths.save_version = 0
    sc = bpy.context.scene
    if "blockout" in STEPS:
        ns = {"__name__": "__main__", "VARIANT": VARIANT, "BLOCKOUT": True}
        exec(open(S + r"\build_north_ambria.py", encoding="utf-8").read(), ns)
        info["build"] = ns["BUILD_INFO"]
        sc = bpy.context.scene
        for o in bpy.data.objects:
            if o.name in ("NA_Mist", "NA_Fog", "NA_Drift") or o.name.startswith("Preview"):
                o.hide_render = True
        sc.camera = bpy.data.objects["CAM_mid"]
        sc.render.resolution_percentage = 100; sc.cycles.samples = 32
        sc.render.filepath = R + "\\blockout_CAM_mid.png"
        bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=S + "\\north_ambria_blockout.blend")
    else:
        if "build" in STEPS:
            ns = {"__name__": "__main__", "VARIANT": VARIANT}
            exec(open(S + r"\build_north_ambria.py", encoding="utf-8").read(), ns)
            info["build"] = ns["BUILD_INFO"]
            bpy.ops.wm.save_as_mainfile(filepath=BLEND)
        else:
            bpy.ops.wm.open_mainfile(filepath=BLEND)
            ns = {"__name__": "lib", "VARIANT": VARIANT}
            exec(open(S + r"\build_north_ambria.py", encoding="utf-8").read(), ns)
        bk = {"__name__": "lib", "VARIANT": VARIANT}
        exec(open(S + r"\bake_north_ambria.py", encoding="utf-8").read(), bk)
        if "bake" in STEPS:
            info["bake"] = bk["bake_all"]()
            bpy.ops.wm.save_mainfile()          # keep the Bake UVs even if a later step fails
        if "regrade" in STEPS:
            bk["regrade"]()
        if "preview" in STEPS:
            info["preview"] = bk["make_preview"]()
            for o in bpy.data.objects:
                if o.name.startswith("Preview"):
                    o.hide_render = True
            sc = bpy.context.scene
            for c in [c for c in CAMS.split(",") if c]:
                sc.camera = bpy.data.objects[c]
                sc.render.filepath = R + "\\" + TAG + "_" + VARIANT + "_" + c + ".png"
                bpy.ops.render.render(write_still=True)
        if "export" in STEPS:
            info["export"] = bk["export_glb"]()
        if "beauty" in STEPS:
            info["beauty"] = ns["make_beauty"]("CAM_mid")
            sc = bpy.context.scene
            sc.render.filepath = R + "\\final_CAM_mid.png"
            bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_mainfile()
    info["ok"] = True
except Exception:
    info["error"] = traceback.format_exc()
info["seconds"] = time.time() - t0
open(status, "w").write(json.dumps(info, indent=1))
