"""Milestone 7 review renders (run in Blender after rig_build, rig_weights,
rig_eyes). Writes renders/m7_*.png and renders/m7_bones.json (the rest
pose's bones and the overview cameras, for m7_sheet.py to draw).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\m7_review.py")["run"]()
"""
import json
import math
import os
import runpy
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cfg  # noqa: E402

CAM = ("cam", -40.0, 5.0)                   # the idle sprite's angle (her right-front)
BODY = dict(size=1.9, res=(900, 900), target=(0.0, 0.0, 0.74))
OVERVIEW = [("front", 0.0, 0.0), ("side", -90.0, 0.0)]


def _P():
    return runpy.run_path(os.path.join(HERE, "rig_poses.py"))


def bones_json(path):
    rig = bpy.data.objects["CEC_rig"]
    out = []
    for b in rig.data.bones:
        h, t = rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local
        out.append(dict(name=b.name, head=list(h), tail=list(t), deform=b.use_deform,
                        coll=[c.name for c in b.collections], hidden=all(not c.is_visible for c in b.collections)))
    cams = []
    for nm, az, el in OVERVIEW:
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        f = -d
        right = f.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(f).normalized()
        cams.append(dict(name=nm, right=list(right), up=list(up), **BODY))
    with open(path, "w") as fh:
        json.dump(dict(bones=out, cams=cams), fh, indent=1)
    return len(out)


def run(tag="m7"):
    P = _P()
    R = lambda t, views, **kw: [os.path.basename(p) for p in P["render"](t, views, **kw)]   # noqa: E731
    out = {}
    # rig overview (rest pose) + bones
    P["pose"]("rest")
    out["overview"] = R(tag + "_rest", OVERVIEW + [CAM], **BODY)
    out["bones"] = bones_json(os.path.join(cfg.RENDERS, tag + "_bones.json"))
    # the poses at the sprite angle; idle and the slash from all sides
    for name in ("idle", "draw_slash", "right_hand", "overhead"):
        P["pose"]("idle_m7" if name == "idle" else name)       # Milestone 7's idle (M8 refitted pose("idle"))
        views = [CAM]
        if name in ("idle", "draw_slash"):
            views += [("front", 0.0, 0.0), ("side", -90.0, 0.0), ("back", 180.0, 0.0)]
        out[name] = R("%s_%s" % (tag, name), views, **BODY)
        pel = P["bone_point"]("pelvis")
        sR, sL = P["bone_point"]("upper_arm.R"), P["bone_point"]("upper_arm.L")
        mid = tuple(0.5 * (a + b) for a, b in zip(sR, sL))
        # deformation close-ups: shoulders and hips / skirt
        if name in ("idle", "draw_slash"):
            out[name + "_sh"] = R("%s_%s_sh" % (tag, name), [("cam", -40.0, 10.0), ("back", 140.0, 10.0)],
                                  size=0.55, res=(700, 700), target=mid)
            out[name + "_hip"] = R("%s_%s_hip" % (tag, name),
                                   [("cam", -40.0, 0.0), ("back", 140.0, 0.0), ("front", 30.0, -10.0), ("low", -40.0, -35.0)],
                                   size=0.75, res=(700, 700), target=(pel[0], pel[1], pel[2] - 0.12))
        if name == "overhead":
            out[name + "_sh"] = R("%s_%s_sh" % (tag, name),
                                  [("front", -20.0, 5.0), ("back", 160.0, 5.0), ("side", -90.0, 5.0), ("pit", -60.0, -20.0)],
                                  size=0.5, res=(700, 700), target=(sR[0], sR[1], sR[2] - 0.02))
        # the sword in its socket
        hilt = P["bone_point"]("hilt")
        out[name + "_sock"] = R("%s_%s_sock" % (tag, name), [("cam", -40.0, 5.0)], size=0.55, res=(700, 700), target=hilt)
    P["pose"]("rest")
    hilt = P["bone_point"]("hilt")
    out["rest_sock"] = R(tag + "_rest_sock", [("cam", -40.0, 5.0), ("front", 0.0, 0.0)], size=0.55, res=(700, 700),
                         target=hilt)
    # eye controls: eyes_target moved (both eyes follow)
    rig = bpy.data.objects["CEC_rig"]
    head = dict(size=0.30, res=(700, 700), target=(0.0, -0.03, 1.40))
    for nm, dx, dz in (("ahead", 0.0, 0.0), ("left", 0.15, 0.0), ("right", -0.15, 0.0), ("up", 0.0, 0.08),
                       ("down", 0.0, -0.08)):
        P["pose"]("rest")
        pb = rig.pose.bones["eyes_target"]
        M = rig.matrix_world @ pb.matrix
        M.translation = M.translation + Vector((dx, 0.0, dz))
        pb.matrix = rig.matrix_world.inverted() @ M
        bpy.context.view_layer.update()
        out["eyes_" + nm] = R("%s_eyes_%s" % (tag, nm), [("front", 0.0, 0.0), ("q", -40.0, 5.0)], **head)
    P["pose"]("rest")
    return out


if __name__ == "__main__":
    print(run())
