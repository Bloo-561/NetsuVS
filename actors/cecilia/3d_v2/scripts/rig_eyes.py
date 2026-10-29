"""Milestone 7: eye controls (run in Blender, after rig_build.py).

The eyes are texture (the sheet's eyes panel, face_texture / gg_face), so
the eye bones move the irises in the face material:
  * face_texture.main() writes three layers next to face_eyes.png: the frame
    (each iris painted over with the sclera), the iris (a full ellipse) and
    the eye opening;
  * gg_face.material() composites them, the iris sampled at an offset held in
    two Value nodes per eye (iris_du.R / iris_dv.R, ... in sheet px);
  * drivers here feed those nodes from the eye bones' swing (local space, so
    the head's own turn does not count): IRIS_GAIN sheet px per radian,
    clamped to LIMIT_U / LIMIT_V, minus the rest swing (the bones converge
    on eyes_target, 45 cm in front), so the rest pose is the sheet's eyes.
Animate with eyes_target (both eyes) or by rotating eye.R / eye.L.
Simple expressions only (no Python auto-run needed).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\rig_eyes.py")["run"]()
"""
import importlib
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RIG = "CEC_rig"
IRIS_GAIN = 17.5                      # sheet px per radian (an eyeball radius of about 4 cm)
LIMIT_U, LIMIT_V = 6.0, 3.0           # sheet px: the iris stops at the eye's corners / lids
AXES = (("du", "ROT_Z", 1.0, LIMIT_U), ("dv", "ROT_X", -1.0, LIMIT_V))


def _reset_pose(rig):
    saved = {}
    for pb in rig.pose.bones:
        saved[pb.name] = (tuple(pb.location), tuple(pb.rotation_quaternion), tuple(pb.rotation_euler), tuple(pb.scale))
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    return saved


def _restore_pose(rig, saved):
    for pb in rig.pose.bones:
        loc, q, eu, sc = saved[pb.name]
        pb.location, pb.rotation_quaternion, pb.rotation_euler, pb.scale = loc, q, eu, sc


def _driver(sock, rig, bone, ttype, expr):
    sock.driver_remove("default_value")
    fc = sock.driver_add("default_value")
    d = fc.driver
    d.type = "SCRIPTED"
    for v in list(d.variables):
        d.variables.remove(v)
    v = d.variables.new()
    v.name = "a"
    v.type = "TRANSFORMS"
    t = v.targets[0]
    t.id = rig
    t.bone_target = bone
    t.transform_type = ttype
    t.transform_space = "LOCAL_SPACE"
    t.rotation_mode = "SWING_TWIST_Y"
    d.expression = expr
    return fc


def drivers(mat_name="PROJ_face"):
    import gg_face
    rig = bpy.data.objects[RIG]
    nt = bpy.data.materials[mat_name].node_tree
    saved = _reset_pose(rig)
    pos = rig.data.pose_position
    rig.data.pose_position = "POSE"
    # pass 1: the raw swing, to read the rest values
    for e in ("R", "L"):
        for axis, ttype, sign, lim in AXES:
            _driver(nt.nodes[gg_face.iris_node_name(axis, e)].outputs[0], rig, "eye." + e, ttype, "a")
    bpy.context.view_layer.update()
    rest = {}
    for e in ("R", "L"):
        for axis, ttype, sign, lim in AXES:
            rest[(e, axis)] = float(nt.nodes[gg_face.iris_node_name(axis, e)].outputs[0].default_value)
    # pass 2: offset in sheet px from the rest swing, clamped
    out = {}
    for e in ("R", "L"):
        for axis, ttype, sign, lim in AXES:
            a0 = rest[(e, axis)]
            expr = "max(%.1f, min(%.1f, (a - %.6f) * %.3f))" % (-lim, lim, a0, sign * IRIS_GAIN)
            fc = _driver(nt.nodes[gg_face.iris_node_name(axis, e)].outputs[0], rig, "eye." + e, ttype, expr)
            out["%s.%s" % (axis, e)] = dict(rest_rad=round(a0, 5), expr=expr, valid=fc.driver.is_valid,
                                            simple=fc.driver.is_simple_expression)
    _restore_pose(rig, saved)
    rig.data.pose_position = pos
    bpy.context.view_layer.update()
    return out


def run(regen=True):
    import face_texture as ft
    import gg_face
    import toon
    for m in (ft, gg_face, toon):
        importlib.reload(m)
    res = {}
    if regen:
        res["layers"] = ft.main()["iris_fits"]
    # the material's anchors ray-cast the face in world space: build it at rest
    rig = bpy.data.objects[RIG]
    pos = rig.data.pose_position
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    try:
        res["material"] = gg_face.material()
    finally:
        rig.data.pose_position = pos
        bpy.context.view_layer.update()
    face = bpy.data.objects["face"]
    for m in face.data.materials:
        if m and m.name.startswith("PROJ_"):
            toon.toonify(m, toon.kind("face"), toon.BIAS_OBJ.get("face"))
    res["drivers"] = drivers(res["material"]["material"])
    return res


if __name__ == "__main__":
    print(run())
