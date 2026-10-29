"""Milestone 3: head close-ups with the projected colours (run in Blender).

Front / back / side are framed exactly like a square region of each ref crop
around the head (so they overlay the sheet pixel for pixel, at SCALE x the
sheet resolution); the 3/4 views have no sheet counterpart (q_idle is about
the angle of the idle sprite, actors/cecilia/Sprites/idle1.png).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\review_head.py")["run"]("m3_head")
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)

SCALE = 4
# head regions in each crop: (u0, v0, size) in crop pixels
REGION = {"front": (190.0, 5.0, 160.0), "back": (184.0, 4.0, 160.0), "side": (35.0, 6.0, 160.0)}
ROT = {"front": (90.0, 0.0, 0.0), "back": (90.0, 0.0, 180.0), "side": (90.0, 0.0, -90.0)}
LOOK = {"front": Vector((0, 1, 0)), "back": Vector((0, -1, 0)), "side": Vector((1, 0, 0))}


def scene(toon=False):
    """toon: no world light (the key light alone shades), transparent film
    (composite onto white afterwards)"""
    sc = bpy.data.scenes.get("HEADREVIEW") or bpy.data.scenes.new("HEADREVIEW")
    for ch in list(sc.collection.children):
        sc.collection.children.unlink(ch)
    sc.collection.children.link(bpy.data.collections["MODEL"])
    r = sc.render
    r.engine = "BLENDER_EEVEE"
    r.film_transparent = toon
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if toon else "RGB"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("HEADREVIEW_world")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0, 0, 0, 1) if toon else (1, 1, 1, 1)
        bg.inputs[1].default_value = 0.0 if toon else 1.0
    if toon:
        key = bpy.data.objects.get("GG_Key")
        if key is not None and sc.collection.objects.get(key.name) is None:
            sc.collection.objects.link(key)
    cam = bpy.data.objects.get("CAM_head")
    if cam is None:
        cam = bpy.data.objects.new("CAM_head", bpy.data.cameras.new("CAM_head"))
    if sc.collection.objects.get(cam.name) is None:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.clip_start, cam.data.clip_end = 0.05, 50.0
    sc.camera = cam
    return sc, cam


def lines_for(mpp):
    try:
        import toon
        return toon.set_line_width(mpp)
    except Exception:
        return None


def frame_view(cam, sc, view):
    u0, v0, size = REGION[view]
    cu, cv = u0 + size / 2.0, v0 + size / 2.0
    c = cfg.img_to_world(view, cu, cv)
    cam.data.ortho_scale = size * cfg.PX
    cam.location = Vector(c) - LOOK[view] * 6.0
    cam.rotation_euler = [math.radians(a) for a in ROT[view]]
    sc.render.resolution_x = sc.render.resolution_y = int(size * SCALE)
    lines_for(cfg.PX / SCALE)


def frame_angle(cam, sc, az_deg, el_deg=0.0, target=(0.0, 0.015, 1.415), size=0.37, res=640):
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * 6.0
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = size
    sc.render.resolution_x = sc.render.resolution_y = res
    lines_for(size / res)


def run(tag, extra_angles=((-40, 0, "q_right"), (40, 0, "q_left"), (-25, 10, "q_right_high"), (-62, 0, "q_idle")),
        toon=False):
    sc, cam = scene(toon)
    out = {}
    for view in ("front", "back", "side"):
        frame_view(cam, sc, view)
        p = os.path.join(cfg.RENDERS, "%s_%s.png" % (tag, view))
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True, scene=sc.name)
        out[view] = p
    for az, el, name in extra_angles:
        frame_angle(cam, sc, az, el)
        p = os.path.join(cfg.RENDERS, "%s_%s.png" % (tag, name))
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True, scene=sc.name)
        out[name] = p
    return out
