"""Rebuild the head and render the GG-style preview close-ups (run in Blender).

  run(tag, rebuild=True): [face texture, purple masks, head meshes] ->
  projection (sheet colours + visibility) -> toon -> review_head close-ups
  (renders/<tag>_*.png, transparent).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\gg_preview.py")["run"]("m3_gg")
"""
import os
import runpy
import sys
import time

S = os.path.dirname(os.path.abspath(__file__))
MODULES = ("cfg", "imgio", "profiles", "head_profiles", "build_blockout", "layers", "build_head", "projection",
           "silhouette", "review_head", "face_texture", "toon", "gg_face")


def fresh(name):
    for m in MODULES:
        sys.modules.pop(m, None)
    return runpy.run_path(os.path.join(S, name + ".py"))


def run(tag, rebuild=True, textures=False, render=True, extra_angles=None):
    t0 = time.time()
    out = {}
    if textures:
        out["face_tex"] = str(fresh("face_texture")["main"]())[:200]
        ly = fresh("layers")
        out["hairp"] = {v: ly["hair_purple"](v) for v in ("front", "side", "back")}
    if rebuild:
        out["build"] = fresh("build_head")["build"]()
    out["proj"] = len(fresh("projection")["apply"]())
    out["toon"] = len(fresh("toon")["apply"]())
    if render:
        rv = fresh("review_head")
        kw = dict(toon=True)
        if extra_angles is not None:
            kw["extra_angles"] = extra_angles
        out["renders"] = sorted(rv["run"](tag, **kw).keys())
    out["t"] = round(time.time() - t0, 1)
    return out
