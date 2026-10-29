"""Milestone 4 driver (run in Blender): trace -> build the clothing parts ->
projection + toon -> silhouette IoU -> review close-ups.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\m4_preview.py")["run"]("m4_x")

Whole model from scratch (the order matters: the blockout clears the MODEL
collection; the belts are cast onto the skirt; the hands replace the M2 arms;
the bows cut the M2 bow lofts to the drawn outline):
    run("tag", build=FULL)
"""
import os
import runpy
import sys
import time

S = os.path.dirname(os.path.abspath(__file__))
MODULES = ("cfg", "imgio", "profiles", "head_profiles", "build_blockout", "layers", "build_head", "projection",
           "silhouette", "review_head", "review_body", "face_texture", "toon", "gg_face", "trace_clothes",
           "build_clothes", "decals", "bake", "shade_bake", "uv_unwrap", "fit_patterns")
FULL = ("blockout", "head", "torso", "neck", "skirt", "belts", "hands", "sword", "bows")


def fresh(name):
    for m in MODULES:
        sys.modules.pop(m, None)
    return runpy.run_path(os.path.join(S, name + ".py"))


def run(tag, trace=True, build=("torso", "neck"), names=None, angles=True, sil=True, shade=True):
    t0 = time.time()
    out = {}
    if trace:
        fresh("trace_clothes")["main"]()
    build = tuple(build or ())
    if "blockout" in build:                       # M2 parts; clears the MODEL collection first
        out["blockout"] = fresh("build_blockout")["build"]()
    if "head" in build:
        out["head"] = fresh("build_head")["build"]()
    build = tuple(b for b in build if b not in ("blockout", "head"))
    if build:
        bc = fresh("build_clothes")
        unknown = [b for b in build if b not in ("torso", "neck") and ("build_" + b) not in bc]
        if unknown:
            raise ValueError("unknown parts: %s" % unknown)
        if "torso" in build:
            out["torso"] = bc["build"]()
        if "neck" in build:
            out["neck"] = bc["build_neck"]()
        for b in build:
            if b not in ("torso", "neck"):
                out[b] = bc["build_" + b]()
    if sil:
        s = fresh("silhouette")["run"](tag)
        out["iou"] = {v: [round(s[v]["iou"], 4)] + [(b["band"], round(b["iou"], 4)) for b in s[v]["bands"]] for v in s}
    if shade:
        fresh("projection")["apply"]()
        fresh("toon")["apply"]()
    if names is not None or angles:
        rb = fresh("review_body")
        out["renders"] = sorted(rb["run"](tag, names=names, angles=angles))
    out["t"] = round(time.time() - t0, 1)
    return out
