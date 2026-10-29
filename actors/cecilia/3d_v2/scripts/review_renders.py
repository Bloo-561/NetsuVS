"""Quick review renders of whatever is in MODEL (Workbench, object colours).

Writes renders/<tag>_<view>.png for a turntable of fixed angles. Used to judge
the 3D shape between milestones (silhouette IoU only checks the outline).
Run:  import runpy; runpy.run_path(r"<3d_v2>\\scripts\\review_renders.py")["run"]("m2_review")
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)

# azimuth: 0 = camera in front of her (on -Y), 90 = on her left (+X), -90 = her right (-X)
ANGLES = [("front", 0, 0), ("q_front_right", -40, 8), ("side_right", -90, 0), ("q_back_right", -140, 8),
          ("back", 180, 0), ("q_front_left", 40, 8), ("top", 0, 89)]


def scene(collections=("MODEL",)):
    sc = bpy.data.scenes.get("REVIEW") or bpy.data.scenes.new("REVIEW")
    for ch in list(sc.collection.children):
        sc.collection.children.unlink(ch)
    for n in collections:
        sc.collection.children.link(bpy.data.collections[n])
    r = sc.render
    r.engine = "BLENDER_WORKBENCH"
    r.resolution_x, r.resolution_y, r.resolution_percentage = 640, 900, 100
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_object_outline = True
    sh.object_outline_color = (0.0, 0.0, 0.0)
    sh.show_shadows = False
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.85, 0.85, 0.85)
    sc.display.render_aa = "8"
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.get("CAM_review")
    if cam is None:
        cd = bpy.data.cameras.new("CAM_review")
        cam = bpy.data.objects.new("CAM_review", cd)
    if sc.collection.objects.get(cam.name) is None:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.75
    sc.camera = cam
    return sc, cam


def place(cam, az_deg, el_deg, target=(0.0, 0.0, 0.79), dist=6.0):
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * dist
    look = (Vector(target) - cam.location).normalized()
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()


def run(tag, collections=("MODEL",), angles=ANGLES, scale=1.75, target=(0.0, 0.0, 0.79), res=(640, 900)):
    sc, cam = scene(collections)
    cam.data.ortho_scale = scale
    sc.render.resolution_x, sc.render.resolution_y = res
    out = []
    for name, az, el in angles:
        place(cam, az, el, target)
        path = os.path.join(cfg.RENDERS, "%s_%s.png" % (tag, name))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=sc.name)
        out.append(path)
    return out
