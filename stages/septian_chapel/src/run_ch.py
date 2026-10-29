# Septian Chapel - one-shot pipeline for a BACKGROUND Blender (never touches open windows):
#   blender --background --factory-startup --python "<project>/stages/septian_chapel/src/run_ch.py" -- \
#           STEPS=build,bake,preview,export TAG=pv CAMS=CAM_mid,CAM_far
# VARIANT  afternoon (the only one)
# STEPS    any of build, bake, regrade, preview, export   (export needs preview: it makes the unlit materials)
# CAMS     preview renders to write into renders/ (default: none - use "all" for the six fight cameras)
# Writes src/cache/_status_<VARIANT>.json when done.
import bpy, sys, time, json, traceback, os

S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\septian_chapel\src"
R = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\septian_chapel\renders"
args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
VARIANT = args.get("VARIANT", "afternoon")
STEPS = set(args.get("STEPS", "build,bake,preview,export").split(","))
TAG = args.get("TAG", "pv")
CAMS = args.get("CAMS", "")
if CAMS == "all":
    CAMS = "CAM_mid,CAM_far,CAM_near,CAM_far_left,CAM_near_right,CAM_jump_far"
BLEND = S + ("\\septian_chapel.blend" if VARIANT == "afternoon" else "\\septian_chapel_%s.blend" % VARIANT)
status = S + r"\cache\_status_" + VARIANT + ".json"
os.makedirs(S + r"\cache", exist_ok=True); os.makedirs(R, exist_ok=True)
if os.path.exists(status):
    os.remove(status)
t0 = time.time(); info = {"variant": VARIANT, "steps": sorted(STEPS)}
try:
    bpy.context.preferences.filepaths.save_version = 0
    if "build" in STEPS:
        ns = {"__name__": "__main__", "VARIANT": VARIANT}
        exec(open(S + r"\build_septian_chapel.py", encoding="utf-8").read(), ns)
        info["build"] = ns["BUILD_INFO"]
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    else:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    bk = {"__name__": "lib", "VARIANT": VARIANT}
    exec(open(S + r"\bake_septian_chapel.py", encoding="utf-8").read(), bk)
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
    bpy.ops.wm.save_mainfile()
    info["ok"] = True
except Exception:
    info["error"] = traceback.format_exc()
info["seconds"] = time.time() - t0
open(status, "w").write(json.dumps(info, indent=1))
