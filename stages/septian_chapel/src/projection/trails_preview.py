import bpy, json
S = r"E:\Netsu Projects\NetsuVS\stages\septian_chapel\src"; P = S + r"\projection"
ns = {"__name__": "__main__", "VARIANT": "trails"}
exec(open(S + r"\build_septian_chapel.py", encoding="utf-8").read(), ns)
info = ns["BUILD_INFO"]; info.pop("objects", None)
sc = bpy.context.scene
sc.render.resolution_x = 1280; sc.render.resolution_y = 720; sc.cycles.samples = 48
try: sc.cycles.device = 'GPU'
except Exception: pass
for c in ("CAM_mid", "CAM_far", "CAM_near_right"):
    sc.camera = bpy.data.objects[c]; sc.render.filepath = P + r"\trails_pre_" + c + ".png"; bpy.ops.render.render(write_still=True)
print("TP:", json.dumps(info))
