"""Milestone 5 driver (run in Blender): bake the sheet into the UV atlases
(bake.py), put the baked textures on the model, toon-shade, render.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\m5_preview.py")["run"]("m5_x")

From scratch: m4_preview.run(tag, build=FULL, shade=False) for the geometry,
uv_unwrap.run() for the UV atlases, then run(tag) here.
"""
import os
import runpy
import time

S = os.path.dirname(os.path.abspath(__file__))


def run(tag, bake=True, names=None, angles=True, sil=False, unwrap=False):
    m4 = runpy.run_path(os.path.join(S, "m4_preview.py"))
    fresh = m4["fresh"]
    t0 = time.time()
    out = {}
    if unwrap:
        out["uv"] = fresh("uv_unwrap")["run"]()
    bk = fresh("bake")
    if bake:
        rep = bk["run"]()
        out["bake_t"] = rep["t"]
        out["seen"] = {k: v.get("seen") for k, v in rep["objects"].items()}
    out["textured"] = len(bk["apply_materials"]())
    fresh("toon")["apply"]()
    if sil:
        s = fresh("silhouette")["run"](tag)
        out["iou"] = {v: round(s[v]["iou"], 4) for v in s}
    if names is not None or angles:
        out["renders"] = sorted(fresh("review_body")["run"](tag, names=names, angles=angles))
    out["t"] = round(time.time() - t0, 1)
    return out
