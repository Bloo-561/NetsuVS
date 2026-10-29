# Rebuild Cecilia from scratch, add outlines, save the .blend.
# In Blender's Python console:  exec(open(r"<3d>/scripts/build_all.py").read())
import bpy, sys, os, importlib
S = os.path.join(r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d", "scripts")
if S not in sys.path: sys.path.insert(0, S)
import lib; importlib.reload(lib)

PARTS = ["body", "hair", "outfit", "tachi"]

def run(parts=PARTS, outline=0.002, save=True):
    done = []
    for p in parts:
        if not os.path.exists(os.path.join(S, p + ".py")): continue
        mod = importlib.import_module(p); importlib.reload(mod); mod.build(); done.append(p)
    for o in bpy.data.objects:
        if o.type == 'MESH' and any(c.name in ("Cecilia", "Hair", "Outfit", "Tachi") for c in o.users_collection):
            th = outline
            if o.name.startswith(("Hair_BandMark", "Outfit_Stripe", "Body_Finger", "Body_Thumb")): th = outline * 0.5
            if o.get("no_outline"): continue
            lib.add_outline(o, th)
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, "cecilia.blend"))
    return done

if __name__ == "__main__":
    run()
