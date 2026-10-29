"""Milestone 6 driver (run in Blender): colour bake (bake.py: base / shadow /
outline colours), shading-control bake (shade_bake.py), GG Xrd shading
(toon.py), renders.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\m6_preview.py")["run"]("m6_x")

From scratch: m4_preview.run(tag, build=FULL, shade=False) for the geometry,
then run(tag, unwrap=True) here.
"""
import os
import runpy
import time

S = os.path.dirname(os.path.abspath(__file__))


def run(tag, unwrap=False, bake=True, shade=True, names=None, angles=True, head=True, sil=False):
    """rest pose throughout (Milestone 7+: the rig's Rest Position while
    baking, shading and rendering the reference views)"""
    import bpy
    rig = bpy.data.objects.get("CEC_rig")
    old = rig.data.pose_position if rig is not None else None
    if rig is not None:
        rig.data.pose_position = "REST"
        bpy.context.view_layer.update()
    try:
        return _run(tag, unwrap, bake, shade, names, angles, head, sil)
    finally:
        if rig is not None:
            rig.data.pose_position = old
            bpy.context.view_layer.update()


def _run(tag, unwrap=False, bake=True, shade=True, names=None, angles=True, head=True, sil=False):
    m4 = runpy.run_path(os.path.join(S, "m4_preview.py"))
    fresh = m4["fresh"]
    t0 = time.time()
    out = {}
    if unwrap:
        out["uv"] = fresh("uv_unwrap")["run"]()
    bk = fresh("bake")
    if bake:
        out["bake_t"] = bk["run"]()["t"]
    if shade:
        out["shade_t"] = fresh("shade_bake")["run"]()["t"]
    bk["apply_materials"]()
    fresh("toon")["apply"]()
    if sil:
        s = fresh("silhouette")["run"](tag)
        out["iou"] = {v: round(s[v]["iou"], 4) for v in s}
    if names is not None or angles:
        out["renders"] = sorted(fresh("review_body")["run"](tag, names=names, angles=angles))
    if head:
        out["head"] = sorted(fresh("review_head")["run"](tag, toon=True))
    out["t"] = round(time.time() - t0, 1)
    return out
