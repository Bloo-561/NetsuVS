"""Milestone 1: reference rig for the Cecilia v2 model (run inside Blender 5.2).

Builds, from scratch every time (idempotent):
  REF     image empties: front / back / side refs on the ortho axes, scaled so
          the figure is 1.58 m (ahoge tip to sole), soles on z = 0, torso
          centre line on x = 0, waist mid-depth on y = 0 (see cfg.py).
  CAMS    ortho cameras CAM_front / CAM_back / CAM_side framed exactly like
          each ref crop (same size, same pixel grid) for silhouette renders.
  GUIDES  landmark height lines (front-view heights from refs/landmarks.json)
          and centre lines, with labels; viewport only, never rendered.
  MODEL   empty collection the character goes into.

Run:  import runpy; runpy.run_path(r"<3d_v2>\\scripts\\rig_refs.py", run_name="__main__")
View the refs with numpad 1 (front), ctrl+numpad 1 (back), ctrl+numpad 3 (side).
"""
import importlib
import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)

ROT = {  # Euler XYZ degrees: image planes and cameras share them
    "front": (90.0, 0.0, 0.0),     # camera looks +Y, screen right = +X
    "back": (90.0, 0.0, 180.0),    # camera looks -Y, screen right = -X
    "side": (90.0, 0.0, -90.0),    # camera looks +X, screen right = -Y
}
LOOK = {"front": (0.0, 1.0, 0.0), "back": (0.0, -1.0, 0.0), "side": (1.0, 0.0, 0.0)}
STARTUP_OBJECTS = {"Cube", "Camera", "Light"}


def get_coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if parent.children.get(c.name) is None:
        parent.children.link(c)
    return c


def clear_coll(c):
    for o in list(c.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and getattr(data, "users", 1) == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Camera):
                bpy.data.cameras.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)


def remove_startup_scene():
    """Delete Blender's default cube/camera/light, but only if nothing else exists."""
    names = {o.name for o in bpy.data.objects}
    if names and names <= STARTUP_OBJECTS:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
            for d in list(block):
                if d.users == 0:
                    block.remove(d)
        default = bpy.data.collections.get("Collection")
        if default is not None and len(default.objects) == 0 and len(default.children) == 0:
            bpy.data.collections.remove(default)


def build_refs(coll):
    for view in cfg.VIEW_ORDER:
        c = cfg.VIEWS[view]
        img = bpy.data.images.load(cfg.ref_path(view), check_existing=True)
        img.name = "ref_" + view
        ob = bpy.data.objects.new("REF_" + view, None)
        ob.empty_display_type = "IMAGE"
        ob.data = img
        ob.empty_display_size = max(c["W"], c["H"]) * cfg.PX
        ob.empty_image_offset = (-0.5, -0.5)
        cx, cy, cz = cfg.image_centre_world(view)
        lx, ly, lz = LOOK[view]
        off = cfg.REF_PLANE_OFFSET
        ob.location = (cx + lx * off, cy + ly * off, cz + lz * off)
        ob.rotation_euler = [math.radians(a) for a in ROT[view]]
        ob.empty_image_depth = "BACK"
        ob.empty_image_side = "FRONT"
        ob.show_empty_image_orthographic = True
        ob.show_empty_image_perspective = False
        ob.show_empty_image_only_axis_aligned = True
        ob.use_empty_image_alpha = True
        ob.color[3] = 0.7
        ob.hide_select = True
        ob.hide_render = True
        ob["ref_view"] = view
        coll.objects.link(ob)


def build_cams(coll):
    for view in cfg.VIEW_ORDER:
        c = cfg.VIEWS[view]
        cam = bpy.data.cameras.new("CAM_" + view)
        cam.type = "ORTHO"
        cam.sensor_fit = "VERTICAL"
        cam.ortho_scale = c["H"] * cfg.PX
        cam.clip_start = 0.05
        cam.clip_end = 50.0
        cam.shift_x = cam.shift_y = 0.0
        ob = bpy.data.objects.new("CAM_" + view, cam)
        cx, cy, cz = cfg.image_centre_world(view)
        lx, ly, lz = LOOK[view]
        dist = cfg.CAM_DISTANCE
        ob.location = (cx - lx * dist, cy - ly * dist, cz - lz * dist)
        ob.rotation_euler = [math.radians(a) for a in ROT[view]]
        ob["res_x"] = c["W"]
        ob["res_y"] = c["H"]
        ob["ref_view"] = view
        coll.objects.link(ob)


def load_landmarks():
    path = os.path.join(cfg.REFS, "landmarks.json")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        data = json.load(fh)
    out = []
    for e in data["landmarks"]:
        if e["key"] == "ankle_narrowest":      # info only, not the same point in every view
            continue
        h = None
        for v in ("front", "back", "side"):     # front height first
            if e["height"].get(v):
                h = e["height"][v]["m"]
                break
        if h is not None:
            out.append((e["name"], h))
    return out


def text_obj(coll, name, body, loc, rot, size, align):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    ob.hide_select = True
    ob.hide_render = True
    coll.objects.link(ob)
    return ob


def build_guides(coll):
    lms = load_landmarks()
    verts, edges = [], []

    def seg(a, b):
        verts.extend([a, b])
        edges.append((len(verts) - 2, len(verts) - 1))
    for _, z in lms:
        seg((-0.72, 0.0, z), (0.72, 0.0, z))       # seen in front/back
        seg((0.0, -0.32, z), (0.0, 0.32, z))       # seen in side
    seg((0.0, 0.0, -0.02), (0.0, 0.0, 1.62))       # centre line x=0 / y=0
    me = bpy.data.meshes.new("GUIDE_landmarks")
    me.from_pydata(verts, edges, [])
    ob = bpy.data.objects.new("GUIDE_landmarks", me)
    ob.display_type = "WIRE"
    ob.show_in_front = True
    ob.hide_select = True
    ob.hide_render = True
    coll.objects.link(ob)
    labels = get_coll("GUIDE_labels", coll)
    clear_coll(labels)
    for name, z in lms:
        short = name.split(" (")[0]
        text_obj(labels, "LBL_f_" + short, "%s  %.3f" % (short, z), (-0.74, 0.0, z), ROT["front"], 0.014, "RIGHT")
        text_obj(labels, "LBL_s_" + short, "%s  %.3f" % (short, z), (0.0, 0.34, z), ROT["side"], 0.014, "RIGHT")


def find_layer_coll(lc, name):
    if lc.collection.name == name:
        return lc
    for ch in lc.children:
        r = find_layer_coll(ch, name)
        if r is not None:
            return r
    return None


def setup_scene():
    sc = bpy.context.scene
    lc = find_layer_coll(bpy.context.view_layer.layer_collection, "CAMS")
    if lc is not None:
        lc.hide_viewport = True          # camera frames clutter the ortho views; renders still use them
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    cam = bpy.data.objects.get("CAM_front")
    if cam:
        sc.camera = cam
        sc.render.resolution_x = cam["res_x"]
        sc.render.resolution_y = cam["res_y"]
        sc.render.resolution_percentage = 100


AXIS = {"front": "FRONT", "back": "BACK", "side": "LEFT"}


def frame_viewports(view="front"):
    """Put every 3D viewport into the named ortho axis view, framing the figure."""
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue
            with bpy.context.temp_override(window=win, area=area, region=region):
                bpy.ops.view3d.view_axis(type=AXIS[view])
            space = area.spaces.active
            space.region_3d.view_perspective = "ORTHO"
            space.region_3d.view_location = (0.0, 0.0, 0.80)
            space.region_3d.view_distance = 2.1
            space.clip_end = 100.0
            space.shading.type = "SOLID"


def main(save=True):
    remove_startup_scene()
    ref = get_coll("REF")
    cams = get_coll("CAMS")
    guides = get_coll("GUIDES")
    get_coll("MODEL")
    for c in (ref, cams):
        clear_coll(c)
    for c in list(guides.children):
        clear_coll(c)
    clear_coll(guides)
    build_refs(ref)
    build_cams(cams)
    build_guides(guides)
    setup_scene()
    frame_viewports("front")
    if save:
        os.makedirs(cfg.ROOT, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=cfg.BLEND)
        bpy.ops.file.make_paths_relative()
        bpy.ops.wm.save_mainfile()
    return dict(blend=bpy.data.filepath, px_m=cfg.PX,
                refs={o.name: [round(v, 5) for v in o.location] for o in ref.objects},
                cams={o.name: [round(v, 5) for v in o.location] for o in cams.objects},
                images={i.name: i.filepath for i in bpy.data.images if i.name.startswith("ref_")})


if __name__ == "__main__":
    print(main())
