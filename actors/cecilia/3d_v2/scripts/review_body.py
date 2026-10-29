"""Milestone 4+: toon close-ups of any region of the sheet (run in Blender).

region(tag, view, u0, v0, w, h, scale): renders exactly the crop rectangle
(u0, v0, w, h) of a reference view (front / back / side), orthographic, at
`scale` render px per sheet px, toon-lit, transparent background, so it
overlays the sheet's crop pixel for pixel.
angle(tag, name, az, el, target, size, res): free 3/4 views (az 0 = front,
-90 = her right side).
REGIONS holds the standard part close-ups; run(tag) renders them all.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\review_body.py")["run"]("m4")
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import review_head as rh  # noqa: E402

importlib.reload(cfg)
importlib.reload(rh)

ROT = rh.ROT
LOOK = rh.LOOK
# name: (view, u0, v0, w, h, scale) in crop pixels
REGIONS = {
    "full_front": ("front", 0, 0, 549, 706, 2),
    "full_back": ("back", 0, 0, 533, 706, 2),
    "full_side": ("side", 0, 0, 220, 706, 2),
    "torso_front": ("front", 180, 120, 180, 170, 4),
    "torso_back": ("back", 175, 120, 180, 170, 4),
    "torso_side": ("side", 40, 120, 160, 170, 4),
    "skirt_front": ("front", 170, 250, 200, 200, 4),
    "skirt_back": ("back", 165, 250, 200, 200, 4),
    "skirt_side": ("side", 30, 250, 170, 200, 4),
    "hand_R_front": ("front", 0, 140, 90, 90, 6),
    "hand_L_front": ("front", 459, 140, 90, 90, 6),
    "feet_front": ("front", 170, 560, 200, 146, 4),
    "feet_side": ("side", 30, 560, 170, 146, 4),
    "sword_front": ("front", 300, 270, 140, 200, 4),
    "sword_back": ("back", 100, 270, 140, 200, 4),
}


def lines_for(mpp):
    """outline hulls as wide as the sheet's lines at this render scale (toon.set_line_width)"""
    try:
        import toon
        return toon.set_line_width(mpp)
    except Exception:
        return None


def frame_region(cam, sc, view, u0, v0, w, h, scale):
    cu, cv = u0 + w / 2.0, v0 + h / 2.0
    c = cfg.img_to_world(view, cu, cv)
    cam.data.sensor_fit = "AUTO"
    cam.data.ortho_scale = max(w, h) * cfg.PX
    cam.location = Vector(c) - LOOK[view] * 6.0
    cam.rotation_euler = [math.radians(a) for a in ROT[view]]
    sc.render.resolution_x = int(round(w * scale))
    sc.render.resolution_y = int(round(h * scale))
    lines_for(cfg.PX / scale)


def region(tag, name, view, u0, v0, w, h, scale=4):
    sc, cam = rh.scene(True)
    frame_region(cam, sc, view, u0, v0, w, h, scale)
    p = os.path.join(cfg.RENDERS, "%s_%s.png" % (tag, name))
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return p


def angle(tag, name, az, el=0.0, target=(0.0, 0.0, 0.79), size=1.7, res=(640, 900)):
    sc, cam = rh.scene(True)
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = Vector(target) + d * 6.0
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "AUTO"
    cam.data.ortho_scale = size
    sc.render.resolution_x, sc.render.resolution_y = res
    lines_for(size / max(res))
    p = os.path.join(cfg.RENDERS, "%s_%s.png" % (tag, name))
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return p


ANGLES = [("q_front_right", -40, 6), ("q_front_left", 40, 6), ("q_back_right", -140, 6), ("idle", -62, 0)]


def run(tag, names=None, angles=True):
    out = {}
    for n, args in REGIONS.items():
        if names is None or n in names:
            out[n] = region(tag, n, *args)
    if angles:
        for n, az, el in ANGLES:
            out[n] = angle(tag, n, az, el)
    return out
