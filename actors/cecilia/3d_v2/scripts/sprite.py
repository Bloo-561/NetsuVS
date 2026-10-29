"""Milestone 8: sprite renders (run in Blender, after the rig scripts).

A sprite frame is a fixed orthographic camera on the posed model, framed like
the game's sprites: 1024 x 1024, transparent, facing right. The camera is the
SPRITE scene's CAM_sprite; its angle and framing come from idle1.png:

  fit(...)        fits the camera angle (and the idle stance) to idle1.png:
                  the model's silhouette, framed like idle1 (247 px tall incl.
                  the ahoge, lowest row 620, rear foot's leftmost pixel at
                  x 403), against idle1's own silhouette (IoU)
  frame_camera()  places CAM_sprite so the current pose lands on that framing
                  exactly (a few silhouette passes)
  render(path)    the beauty frame: EEVEE at SS x the size, outlines 1 px wide
                  at the sprite's scale, box-filtered down, alpha cut at 50 %
                  (hard edges like the pixel-art sprites) or kept (smooth=True)
Every later frame keeps the camera: pose the rig, F12 in the SPRITE scene (or
render() here) and she stays on the same scale and ground line.
Run: import runpy; S = runpy.run_path(r"<3d_v2>\\scripts\\sprite.py"); S["idle_test"]()
"""
import json
import math
import os
import runpy
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cfg  # noqa: E402
import imgio  # noqa: E402

SPRITES = os.path.join(os.path.dirname(cfg.ROOT), "Sprites")
IDLE1 = os.path.join(SPRITES, "idle1.png")
FRAME = dict(res=1024, height=247, bottom=620, rear_x=403)   # the brief; idle1's silhouette is 247 rows (375..621)
CAM = dict(az=-80.0, el=0.0)                                  # camera angle (deg), fitted to idle1.png (fit(), M8_NOTES)
SS = 4                                                        # supersampling of the beauty render
FIT_FRAMING = dict(target=(0.0, 0.0, 0.62), ortho=1.9)        # generous framing for the fitting passes
CHECKS = os.path.join(cfg.RENDERS, "checks")
SPRITE_MPP = 0.0056                                           # ~ m per sprite pixel (idle1 scale): outline width while fitting


def read_rgba(path):
    """PNG -> uint8 RGBA with STRAIGHT alpha (OpenImageIO would premultiply)"""
    import OpenImageIO as oiio
    hint = oiio.ImageSpec()
    hint.attribute("oiio:UnassociatedAlpha", 1)
    inp = oiio.ImageInput.open(path, hint)
    spec = inp.spec()
    px = inp.read_image(0, 0, 0, spec.nchannels, oiio.UINT8)
    inp.close()
    return np.asarray(px, np.uint8).reshape(spec.height, spec.width, spec.nchannels)


def write_rgba(path, arr):
    """uint8 RGBA with straight alpha -> PNG, as is"""
    import OpenImageIO as oiio
    arr = np.ascontiguousarray(arr, np.uint8)
    h, w, c = arr.shape
    spec = oiio.ImageSpec(w, h, c, oiio.UINT8)
    spec.attribute("oiio:UnassociatedAlpha", 1)
    out = oiio.ImageOutput.create(path)
    out.open(path, spec)
    out.write_image(arr)
    out.close()


# ----------------------------------------------------------------------------- scenes
def _link(sc, key=False):
    for ch in list(sc.collection.children):
        sc.collection.children.unlink(ch)
    for n in ("MODEL", "RIG"):
        c = bpy.data.collections.get(n)
        if c is not None:
            sc.collection.children.link(c)
    if key:
        k = bpy.data.objects.get("GG_Key")
        if k is not None and sc.collection.objects.get(k.name) is None:
            sc.collection.objects.link(k)


def camera():
    cam = bpy.data.objects.get("CAM_sprite")
    if cam is None:
        cam = bpy.data.objects.new("CAM_sprite", bpy.data.cameras.new("CAM_sprite"))
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "AUTO"
    cam.data.clip_start, cam.data.clip_end = 0.05, 50.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    return cam


def sil_scene():
    sc = bpy.data.scenes.get("SPRITE_SIL") or bpy.data.scenes.new("SPRITE_SIL")
    _link(sc)
    cam = camera()
    if sc.collection.objects.get(cam.name) is None:
        sc.collection.objects.link(cam)
    sc.camera = cam
    r = sc.render
    r.engine = "BLENDER_WORKBENCH"
    r.film_transparent = True
    r.resolution_x = r.resolution_y = FRAME["res"]
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.single_color = "FLAT", "SINGLE", (1.0, 1.0, 1.0)
    sh.show_object_outline = sh.show_cavity = sh.show_shadows = sh.show_specular_highlight = False
    sc.display.render_aa = "8"
    sc.view_settings.view_transform = "Standard"
    return sc


def beauty_scene():
    """the SPRITE scene: what an animator renders frames from (F12)"""
    src = bpy.data.scenes.get("HEADREVIEW")
    sc = bpy.data.scenes.get("SPRITE") or bpy.data.scenes.new("SPRITE")
    _link(sc, key=True)
    cam = camera()
    if sc.collection.objects.get(cam.name) is None:
        sc.collection.objects.link(cam)
    sc.camera = cam
    r = sc.render
    r.engine = "BLENDER_EEVEE"
    r.film_transparent = True
    r.resolution_x = r.resolution_y = FRAME["res"]
    r.resolution_percentage = 100
    r.filter_size = 1.0
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    if src is not None:
        sc.world = src.world
        try:
            sc.eevee.taa_render_samples = src.eevee.taa_render_samples
        except AttributeError:
            pass
    return sc


def aim(cam, az, el, target, ortho):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = Vector(target) + d * 6.0
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = ortho
    bpy.context.view_layer.update()


def _hulls(on):
    for ob in bpy.data.collections["MODEL"].all_objects:
        m = ob.modifiers.get("GG_outline") if ob.type == "MESH" else None
        if m is not None:
            m.show_render = on


def line_width(mpp):
    import toon
    return toon.set_line_width(mpp)


def render_sil(sc, path=None):
    path = path or os.path.join(CHECKS, "_sprite_sil.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return imgio.load_alpha(path)


def bbox(alpha, thr=0.5, foot_rows=16):
    """top row, lowest row, and the leftmost column among the lowest
    foot_rows rows (the rear foot)"""
    m = alpha >= thr
    rows = np.nonzero(m.any(axis=1))[0]
    top, bot = int(rows.min()), int(rows.max())
    low = m[max(top, bot - foot_rows + 1):bot + 1]
    left = int(np.nonzero(low.any(axis=0))[0].min())
    cols = np.nonzero(m.any(axis=0))[0]
    return dict(top=top, bottom=bot, left=left, right=int(cols.max()), min_x=int(cols.min()))


# ----------------------------------------------------------------------------- framing
def frame_camera(az=None, el=None, iters=4, sc=None):
    """put CAM_sprite at the camera angle and frame the current pose like
    idle1: FRAME height (rows top..bottom inclusive), lowest row on
    FRAME['bottom'], the rear foot's leftmost pixel on FRAME['rear_x']"""
    az = CAM["az"] if az is None else az
    el = CAM["el"] if el is None else el
    sc = sc or sil_scene()
    cam = sc.camera
    aim(cam, az, el, FIT_FRAMING["target"], FIT_FRAMING["ortho"])
    R = FRAME["res"]
    log = []
    for it in range(iters):
        line_width(max(cam.data.ortho_scale / R, SPRITE_MPP * 0.5))
        b = bbox(render_sil(sc))
        h = b["bottom"] - b["top"]
        log.append(dict(it=it, **b, ortho=round(cam.data.ortho_scale, 5)))
        want = FRAME["height"] - 1
        if abs(h - want) <= 0.5 and abs(b["bottom"] - FRAME["bottom"]) <= 0 and abs(b["left"] - FRAME["rear_x"]) <= 0:
            break
        # scale about the image centre, then move: the camera's right / up axes
        s = h / float(want)
        cx, cy = R / 2.0, R / 2.0
        new_ortho = cam.data.ortho_scale * s
        bot_new = cy + (b["bottom"] + 0.5 - cy) / s - 0.5
        left_new = cx + (b["left"] + 0.5 - cx) / s - 0.5
        cam.data.ortho_scale = new_ortho
        mpp = new_ortho / R
        rot = cam.rotation_euler.to_matrix()             # (matrix_world is stale: the camera is not in the active scene)
        right, up = rot.col[0].normalized(), rot.col[1].normalized()
        dx = (left_new - FRAME["rear_x"]) * mpp            # image content must move left by dx -> camera right
        dy = (FRAME["bottom"] - bot_new) * mpp             # content must move down -> camera up
        cam.location = cam.location + right * dx + up * dy
        bpy.context.view_layer.update()
    line_width(cam.data.ortho_scale / R)
    b = bbox(render_sil(sc))
    log.append(dict(it="final", **b, ortho=round(cam.data.ortho_scale, 5)))
    return dict(az=az, el=el, ortho=cam.data.ortho_scale, mpp=cam.data.ortho_scale / R, bbox=b, log=log)


# ----------------------------------------------------------------------------- fitting to idle1
_IDLE1 = {}


def idle1_mask():
    if "m" not in _IDLE1:
        _IDLE1["m"] = imgio.load_alpha(IDLE1) >= 0.5
    return _IDLE1["m"]


def framed_mask(alpha, ss=2, foot_rows=16):
    """the silhouette (any framing) mapped onto idle1's framing: scaled to
    FRAME height, lowest row on FRAME bottom, rear foot on FRAME rear_x"""
    b = bbox(alpha, foot_rows=foot_rows)
    k = (FRAME["height"] - 1) / float(b["bottom"] - b["top"])      # target px per source px
    R = FRAME["res"]
    ys, xs = np.mgrid[0:R, 0:R]
    acc = np.zeros((R, R), np.float32)
    H, W = alpha.shape
    for oy in range(ss):
        for ox in range(ss):
            xt = xs + (ox + 0.5) / ss
            yt = ys + (oy + 0.5) / ss
            xsrc = b["left"] + 0.5 + (xt - (FRAME["rear_x"] + 0.5)) / k - 0.5
            ysrc = b["bottom"] + 0.5 - ((FRAME["bottom"] + 0.5) - yt) / k - 0.5
            x0 = np.clip(np.floor(xsrc).astype(np.int64), 0, W - 2)
            y0 = np.clip(np.floor(ysrc).astype(np.int64), 0, H - 2)
            fx, fy = np.clip(xsrc - x0, 0, 1), np.clip(ysrc - y0, 0, 1)
            v = (alpha[y0, x0] * (1 - fx) * (1 - fy) + alpha[y0, x0 + 1] * fx * (1 - fy) +
                 alpha[y0 + 1, x0] * (1 - fx) * fy + alpha[y0 + 1, x0 + 1] * fx * fy)
            inside = (xsrc >= 0) & (xsrc <= W - 1) & (ysrc >= 0) & (ysrc <= H - 1)
            acc += np.where(inside, v, 0.0)
    return (acc / (ss * ss)) >= 0.5


def diff_image(mask, path, ref=None):
    """white = both, red = idle1 only, blue = model only"""
    ref = idle1_mask() if ref is None else ref
    img = np.full(mask.shape + (3,), 0, np.uint8)
    img[mask & ref] = (255, 255, 255)
    img[ref & ~mask] = (255, 0, 0)
    img[mask & ~ref] = (0, 90, 255)
    imgio.save(path, img)
    return path


def iou(mask, ref=None):
    ref = idle1_mask() if ref is None else ref
    u = (mask | ref).sum()
    return float((mask & ref).sum()) / max(int(u), 1)


def evaluate(params, sc=None, P=None):
    """pose the idle stance with params (rig_poses.IDLE keys + az, el),
    render its silhouette at the fitting framing, IoU against idle1"""
    P = P or runpy.run_path(os.path.join(HERE, "rig_poses.py"))
    sc = sc or sil_scene()
    pp = {k: v for k, v in params.items() if k not in ("el",)}
    P["pose"]("idle", **pp)
    aim(sc.camera, params["az"], params.get("el", CAM["el"]), FIT_FRAMING["target"], FIT_FRAMING["ortho"])
    line_width(SPRITE_MPP)                                               # ~1 sprite px of outline
    a = render_sil(sc)
    m = framed_mask(a, foot_rows=int(round(0.08 / (FIT_FRAMING["ortho"] / FRAME["res"]))))
    return iou(m), m


# the stance / camera parameters searched, with steps and bounds
SEARCH = [
    ("az", 5.0, (-90.0, -15.0)), ("el", 2.5, (-6.0, 15.0)),
    ("front", 0.03, (0.12, 0.48)), ("rear", 0.03, (0.24, 0.66)), ("drop", 0.02, (0.10, 0.32)),
    ("torso_fwd", 0.03, (-0.18, 0.06)), ("hips_yaw", 5.0, (-30.0, 30.0)),
    ("lean", 3.0, (-6.0, 24.0)), ("chest_yaw", 4.0, (-50.0, 14.0)), ("head_yaw", 6.0, (-10.0, 50.0)),
    ("sheath_up", 0.02, (-0.04, 0.16)), ("sheath_cam", 0.03, (0.0, 0.32)), ("sheath_fwd", 0.03, (-0.10, 0.16)),
]
SEARCH_START = dict(lean=6.0, chest_yaw=-8.0, head_yaw=20.0)     # = the IDLE rotations these override


FAST_OFF = ("GG_skirt_occ", "GG_normal_blur", "GG_outline")    # shading-only modifiers: off while fitting silhouettes


_FAST = {}


def _layer_coll(lc, name):
    if lc.name == name:
        return lc
    for ch in lc.children:
        r = _layer_coll(ch, name)
        if r is not None:
            return r
    return None


def fast(on):
    """silhouette passes only: the shading-only modifiers off, and the model
    left out of the active view layer (posing then re-evaluates the rig
    alone; the SPRITE_SIL scene still renders the model) / all restored"""
    if on:
        _FAST.clear()
        for ob in bpy.data.collections["MODEL"].all_objects:
            if ob.type != "MESH":
                continue
            for m in ob.modifiers:
                if m.name in FAST_OFF:
                    _FAST[(ob.name, m.name)] = (m.show_viewport, m.show_render)
                    m.show_viewport = m.show_render = False
        lc = _layer_coll(bpy.context.view_layer.layer_collection, "MODEL")
        if lc is not None:
            _FAST["_exclude"] = lc.exclude
            lc.exclude = True
    else:
        for key, val in list(_FAST.items()):
            if key == "_exclude":
                lc = _layer_coll(bpy.context.view_layer.layer_collection, "MODEL")
                if lc is not None:
                    lc.exclude = val
                continue
            ob = bpy.data.objects.get(key[0])
            m = ob.modifiers.get(key[1]) if ob is not None else None
            if m is not None:
                m.show_viewport, m.show_render = val
        _FAST.clear()
    bpy.context.view_layer.update()


def fit(state_path=None, passes=1, budget_s=50.0, search=None, start=None, step_scale=1.0):
    """coordinate descent on `search` (default SEARCH: (key, step, (lo, hi)));
    `start` overrides the starting parameters (keys outside the search stay
    fixed at their start value). Resumable: the state lives in state_path
    (renders/checks); call again until it reports done"""
    fast(True)
    try:
        return _fit(state_path, passes, budget_s, search or SEARCH, start or {}, step_scale)
    finally:
        fast(False)


def _fit(state_path, passes, budget_s, search, start, step_scale):
    state_path = state_path or os.path.join(CHECKS, "sprite_fit_v2.json")
    os.makedirs(CHECKS, exist_ok=True)
    P = runpy.run_path(os.path.join(HERE, "rig_poses.py"))
    sc = sil_scene()
    if os.path.exists(state_path):
        st = json.load(open(state_path))
    else:
        base = dict(az=CAM["az"], el=CAM["el"])
        for k, _, _ in SEARCH:
            if k not in base:
                base[k] = SEARCH_START[k] if k in SEARCH_START else P["IDLE"][k]
        base.update(start)
        s0, _ = evaluate(base, sc, P)
        st = dict(params=base, score=s0, start=s0, i=0, passes=0,
                  steps={k: d * step_scale for k, d, _ in search}, history=[])
    t0 = time.time()
    while st["passes"] < passes and time.time() - t0 < budget_s:
        k, _, (lo, hi) = search[st["i"]]
        step = st["steps"][k]
        improved = False
        for sgn in (1.0, -1.0):
            trial = dict(st["params"])
            trial[k] = min(hi, max(lo, trial[k] + sgn * step))
            if trial[k] == st["params"][k]:
                continue
            sc_, _ = evaluate(trial, sc, P)
            if sc_ > st["score"] + 1e-4:
                st["params"], st["score"], improved = trial, sc_, True
                st["history"].append([k, round(trial[k], 4), round(sc_, 4)])
                break
        if not improved:
            st["i"] += 1
            if st["i"] >= len(search):
                st["i"] = 0
                st["passes"] += 1
        json.dump(st, open(state_path, "w"), indent=1)
    st["done"] = st["passes"] >= passes
    return st


# ----------------------------------------------------------------------------- beauty render
def render(path, smooth=False, ss=SS):
    """the current pose through CAM_sprite: EEVEE at ss x the size, 1 px
    outlines at the sprite scale, box-filtered to FRAME res; alpha cut at
    50 % unless smooth"""
    sc = beauty_scene()
    cam = sc.camera
    R = FRAME["res"]
    mpp = cam.data.ortho_scale / R
    line_width(mpp)
    tmp = os.path.join(CHECKS, "_sprite_ss.png")
    sc.render.resolution_x = sc.render.resolution_y = R * ss
    sc.render.filepath = tmp
    try:
        bpy.ops.render.render(write_still=True, scene=sc.name)
    finally:
        sc.render.resolution_x = sc.render.resolution_y = R
    big = read_rgba(tmp).astype(np.float32) / 255.0                   # straight alpha
    a = big[..., 3:4]
    prem = big[..., :3] * a
    def box(x):
        return x.reshape(R, ss, R, ss, -1).mean(axis=(1, 3))
    A = box(a)
    C = box(prem) / np.maximum(A, 1e-6)
    if not smooth:
        A = (A >= 0.5).astype(np.float32)
    out = np.concatenate([np.clip(C, 0, 1), A], axis=-1)
    out[A[..., 0] <= 0] = 0.0
    write_rgba(path, (out * 255.0 + 0.5).astype(np.uint8))
    return dict(path=path, mpp_mm=round(mpp * 1000, 3), bbox=bbox(A[..., 0]))


def idle_test(out=None, smooth_too=True, **pose_kw):
    """Milestone 8: the idle stance through the fitted camera, framed like
    idle1.png -> renders/idle_test.png (+ idle_test_smooth.png)"""
    P = runpy.run_path(os.path.join(HERE, "rig_poses.py"))
    P["pose"]("idle", **pose_kw)
    fr = frame_camera()
    out = out or os.path.join(cfg.RENDERS, "idle_test.png")
    res = dict(frame=fr, hard=render(out))
    if smooth_too:
        res["smooth"] = render(out.replace(".png", "_smooth.png"), smooth=True)
    m = imgio.load_alpha(out) >= 0.5
    res["iou_idle1"] = round(iou(m), 4)
    return res


def frame_test(pose_name, ref, out=None, smooth=False, **pose_kw):
    """another frame through the FIXED sprite camera (as idle_test left it),
    compared with a game sprite (Sprites/<ref>.png): for the draw-slash the
    rear foot is planted where the idle's stands (the game's frames keep it
    on x 403)"""
    P = runpy.run_path(os.path.join(HERE, "rig_poses.py"))
    rig = bpy.data.objects["CEC_rig"]
    if pose_name.startswith("draw_slash") and "anchor" not in pose_kw:
        P["pose"]("idle")
        h = rig.matrix_world @ rig.pose.bones["foot_ik.R"].head
        pose_kw["anchor"] = (h.x, h.y)
    P["pose"](pose_name, **pose_kw)
    out = out or os.path.join(cfg.RENDERS, "%s_test.png" % ref)
    r = render(out, smooth=smooth)
    m = imgio.load_alpha(out) >= 0.5
    refm = imgio.load_alpha(os.path.join(SPRITES, ref + ".png")) >= 0.5
    diff_image(m, out.replace(".png", "_diff.png"), refm)
    rb = bbox(refm.astype(np.float32))
    return dict(render=r, ref_bbox=rb, iou=round(iou(m, refm), 4))


if __name__ == "__main__":
    print(idle_test())
