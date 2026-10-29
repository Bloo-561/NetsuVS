"""Silhouette check (run inside Blender 5.2): flat white model on black, IoU vs ref masks.

For each view: render the MODEL collection with CAM_<view> at the crop's exact
resolution (Workbench, flat white, 32x AA, transparent film), threshold alpha
at 0.5, compare with refs/masks/mask_<view>.png and write
  renders/sil/<tag>_<view>.png        the silhouette render
  renders/sil/<tag>_<view>_diff.png   white = both, RED = reference only, BLUE = model only
  renders/sil/<tag>_iou.json          IoU per view + per height band
Run:  import runpy; ns = runpy.run_path(r"<3d_v2>\\scripts\\silhouette.py"); ns["run"]("m2_try1")
"""
import importlib
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

importlib.reload(cfg)
importlib.reload(imgio)

SIL_SCENE = "SIL"
BANDS = [(0, 150, "head/hair"), (150, 192, "arms"), (192, 252, "jacket"), (252, 390, "skirt+sword"),
         (390, 630, "legs"), (630, 706, "feet")]


def sil_scene(collections=("MODEL",)):
    sc = bpy.data.scenes.get(SIL_SCENE) or bpy.data.scenes.new(SIL_SCENE)
    for child in list(sc.collection.children):
        sc.collection.children.unlink(child)
    for name in tuple(collections) + ("CAMS",):
        sc.collection.children.link(bpy.data.collections[name])
    r = sc.render
    r.engine = "BLENDER_WORKBENCH"
    r.film_transparent = True
    r.filter_size = 1.5
    r.resolution_percentage = 100
    r.pixel_aspect_x = r.pixel_aspect_y = 1.0
    r.use_border = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1.0, 1.0, 1.0)
    sh.show_object_outline = False
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_specular_highlight = False
    sh.show_xray = False
    sh.show_backface_culling = False
    sc.display.render_aa = "32"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    return sc


def render_view(sc, view, path):
    c = cfg.VIEWS[view]
    sc.camera = bpy.data.objects["CAM_" + view]
    sc.render.resolution_x = c["W"]
    sc.render.resolution_y = c["H"]
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)


def centroid(weights):
    h, w = weights.shape
    tot = float(weights.sum())
    if tot <= 0:
        return (float("nan"), float("nan"))
    ys, xs = np.mgrid[0:h, 0:w]
    return (float((weights * (xs + 0.5)).sum() / tot), float((weights * (ys + 0.5)).sum() / tot))


def compare(view, render_png, diff_png):
    ref = imgio.load_mask(cfg.mask_path(view))
    alpha = imgio.load_alpha(render_png)
    mod = alpha >= 0.5
    if mod.shape != ref.shape:
        raise RuntimeError("size mismatch %s vs %s" % (mod.shape, ref.shape))
    both, ref_only, mod_only = ref & mod, ref & ~mod, mod & ~ref
    diff = np.zeros(ref.shape + (3,), np.uint8)
    diff[both] = (255, 255, 255)
    diff[ref_only] = (255, 0, 0)
    diff[mod_only] = (0, 90, 255)
    imgio.save(diff_png, diff)
    union = int((ref | mod).sum())
    cm, cr = centroid(alpha), centroid(ref.astype(np.float32))
    out = dict(iou=round(float(both.sum()) / max(union, 1), 4), ref_px=int(ref.sum()), model_px=int(mod.sum()),
               ref_only_px=int(ref_only.sum()), model_only_px=int(mod_only.sum()),
               alpha_area_px=round(float(alpha.sum()), 1),
               centroid_offset_px=[round(cm[0] - cr[0], 3), round(cm[1] - cr[1], 3)],
               target=cfg.IOU_TARGET[view], bands=[])
    for r0, r1, name in BANDS:
        a, b = ref[r0:r1], mod[r0:r1]
        u = int((a | b).sum())
        out["bands"].append(dict(band=name, rows=[r0, r1], iou=round(float((a & b).sum()) / max(u, 1), 4),
                                 ref_only_px=int((a & ~b).sum()), model_only_px=int((b & ~a).sum())))
    return out


def run(tag, collections=("MODEL",), views=cfg.VIEW_ORDER):
    outdir = os.path.join(cfg.RENDERS, "sil")
    os.makedirs(outdir, exist_ok=True)
    sc = sil_scene(collections)
    res = {}
    # the toon outlines (inverted hulls, toon.add_outline) are not part of the
    # shape: hide them while measuring
    hulls = [m for ob in bpy.data.objects for m in ob.modifiers if m.name == "GG_outline" and m.show_render]
    for m in hulls:
        m.show_render = False
    try:
        for view in views:
            png = os.path.join(outdir, "%s_%s.png" % (tag, view))
            render_view(sc, view, png)
            res[view] = compare(view, png, os.path.join(outdir, "%s_%s_diff.png" % (tag, view)))
    finally:
        for m in hulls:
            m.show_render = True
    with open(os.path.join(outdir, "%s_iou.json" % tag), "w") as fh:
        json.dump(res, fh, indent=1)
    return res


# ------------------------------------------------------------------ self test
def _runs(row):
    c = np.where(row)[0]
    if len(c) == 0:
        return []
    br = np.where(np.diff(c) > 1)[0]
    return list(zip(np.r_[c[0], c[br + 1]].tolist(), np.r_[c[br], c[-1]].tolist()))


def mask_to_mesh(view, name, coll):
    """Flat mesh, one quad per run of mask pixels, placed exactly where the ref sits."""
    m = imgio.load_mask(cfg.mask_path(view))
    verts, faces = [], []
    for r in range(m.shape[0]):
        for a, b in _runs(m[r]):
            i = len(verts)
            for (u, v) in ((a, r + 1), (b + 1, r + 1), (b + 1, r), (a, r)):
                verts.append(cfg.img_to_world(view, u, v))
            faces.append((i, i + 1, i + 2, i + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def selftest(keep=False):
    """Extrude-free test: flat meshes cut from the front and side masks must
    reproduce those masks exactly (IoU 1.0); the front mesh seen by the back
    camera must give the front-vs-mirrored-back overlap measured in M1."""
    tc = bpy.data.collections.get("TEST_SIL") or bpy.data.collections.new("TEST_SIL")
    if bpy.context.scene.collection.children.get(tc.name) is None:
        bpy.context.scene.collection.children.link(tc)
    for o in list(tc.objects):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    mask_to_mesh("front", "TEST_front_mask", tc)
    mask_to_mesh("side", "TEST_side_mask", tc)
    res = run("selftest", collections=("TEST_SIL",))
    if not keep:
        for o in list(tc.objects):
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(me)
        bpy.data.collections.remove(tc)
        sc = bpy.data.scenes.get(SIL_SCENE)
        if sc is not None:
            sil_scene(("MODEL",))
    return {v: dict(iou=r["iou"], centroid_offset_px=r["centroid_offset_px"], alpha_area_px=r["alpha_area_px"],
                    ref_px=r["ref_px"]) for v, r in res.items()}


if __name__ == "__main__":
    print(selftest())
