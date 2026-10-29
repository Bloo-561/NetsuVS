"""Milestone 6: shading-control textures for the GG Xrd style shader (run in
Blender; numpy only).

Guilty Gear Xrd's character shader takes, besides the base colour and the
shadow ("SSS") colour, a control texture ("ILM") and vertex colours painted
by its artists:
  vertex R / ILM G  bias the light/shadow threshold: crevices, the neck under
                    the chin, the inside of clothes fall into shadow sooner;
                    below a floor they are always in the darker second shadow
  ILM B / ILM R     where a specular highlight may appear, and how strong.
Here those maps are measured from the model itself instead of painted:
  occlusion  ambient occlusion per texel: the share of the sky (96
             directions, cosine weighted) a texel sees past the rest of the
             model, from orthographic depth maps in each direction (numpy
             rasteriser of bake.py, 3 mm pixels, normal offset + tolerance
             against self-shadowing)
  key        whether the key light (toon.KEY_DIR) reaches the texel (a 1.5 mm
             depth map from the light); used only on the receivers in
             KEY_RECEIVERS (none at present)
  sheen      the jacket's sheen as the sheet draws it (bake.SHEEN ->
             body_sheen.png) joins the specular mask
Outputs (textures/):
  body_ctrl.png / hair_ctrl.png  R = occlusion remapped (1 open .. 0 closed;
                                 the legs: raw sky share without the skirt, M8),
                                 G = threshold (0.5 neutral, lower = shadow sooner),
                                 B = specular mask, A = 1
  body_ao.png / hair_ao.png      raw occlusion (debug)
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\shade_bake.py")["run"]()
"""
import importlib
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bake as bk  # noqa: E402
import cfg  # noqa: E402
import imgio  # noqa: E402

importlib.reload(bk)


def toon_in_ear_pit(pos):
    import toon
    return toon.in_ear_pit(pos)


N_DIRS = 96
AO_PX = 0.003             # m per depth-map pixel
AO_TOL = 0.006            # m: a texel this far behind the nearest surface still sees the sky
AO_NOFF = 0.002           # m: texels are lifted off their surface along the normal first
KEY_PX = 0.0015
KEY_TOL = 0.003
KEY_DIR = (-0.62, -0.60, 0.50)                      # = toon.KEY_DIR (towards the light)
# the key light's cast shadow is baked only onto these parts. Empty since M6
# t2: on the sheet the skirt's shadow on the thighs is a narrow band under the
# lace (the occlusion term gives it); the key light's own long shadow there
# read as a dark block
KEY_RECEIVERS = ()
# the jacket's sheen: "sheet" = only inside the mask projected from the sheet
# (bake.SHEEN, body_sheen.png); "all" = anywhere on the jacket's black, the
# shader's N.H lobe (toon.SPEC_OBJ) decides where. M6 t3: the projected mask
# came out as blocky patches (the sheet's soft, view-by-view highlights do not
# agree on the model's surface), so the lobe places it
SHEEN_MODE = "all"
# the jacket's front facing: the sheet draws a dark band ~8 px (19 mm) wide
# along the opening, front and side views. Texels this close to the opening
# edge (the jacket's boundary in front, above the hem) are always in the first
# shadow (G) and take no sheen
LAPEL = dict(obj="jacket", width=0.019, y_max=-0.035, z_min=1.045)
# parts whose occlusion is ignored (R = 1): the skull filler sits inside the
# hair, so its measured sky is near zero; it only shows through gaps in the
# hair (round the ears) and must shade like the hair around it
OPEN_OBJECTS = ("skull",)
# occlusion -> R: below AO_DEEP texels sit in the second (darker) shadow, below
# AO_SHADOW in the first whatever the light; above AO_OPEN shading is plain N.L
AO_DEEP, AO_SHADOW, AO_OPEN = 0.18, 0.34, 0.55
# Milestone 8: the skirt moves, so its shadow on the legs can't be baked. The
# legs' occlusion is baked WITHOUT the skirt and the lace and stored raw (R =
# sky share 0..1, not remapped); the shader multiplies it by the skirt's live
# occlusion (toon.skirt_occlusion, a ray-cast from the posed legs) and does the
# remap itself (toon.gg_leg_material)
SKIRT_RECEIVERS = ("leg_R", "leg_L")
SKIRT_OCCLUDERS = ("skirt", "lace")
SPEC_FAMILIES = {"gold": 1.0, "silver": 1.0, "steel": 1.0}   # family -> specular mask
SPEC_NONE = ("headband",)          # the emblem is printed on cloth: no glint (M6 t7)
# hair sheen strands (GG paints these into ILM B): thin tapered streaks along
# the hair's flow (meridians of the head) between the crown and the top of the
# purple tips; the shader shows them only inside the N.H highlight spot
STRANDS = dict(n=64, rows=(16.0, 100.0), length=(18.0, 44.0), width=(0.06, 0.14), seed=7,
               axis=(0.0, 0.01), max_purple=0.25)


def strand_mask(pos, purple):
    rng = np.random.default_rng(STRANDS["seed"])
    n = STRANDS["n"]
    th = np.arctan2(pos[:, 0] - STRANDS["axis"][0], -(pos[:, 1] - STRANDS["axis"][1]))
    row = cfg.VIEWS["front"]["sole_v"] - pos[:, 2] / bk.P
    out = np.zeros(len(pos), bool)
    spacing = 2 * math.pi / n
    for k in range(n):
        c = -math.pi + spacing * (k + 0.5 + rng.uniform(-0.3, 0.3))
        hw = spacing * rng.uniform(*STRANDS["width"])
        L = rng.uniform(*STRANDS["length"])
        r0 = rng.uniform(STRANDS["rows"][0], STRANDS["rows"][1] - L)
        t = (row - r0) / L                                  # 0..1 along the strand
        d = np.abs((th - c + math.pi) % (2 * math.pi) - math.pi)
        out |= (t > 0) & (t < 1) & (d < hw * np.sin(math.pi * np.clip(t, 0, 1)) ** 0.7)
    return out & (purple < STRANDS["max_purple"])


def lapel_band(pos):
    """texels within LAPEL width of the jacket's front opening edge"""
    import bmesh
    import bpy
    from mathutils import kdtree
    ob = bpy.data.objects.get(LAPEL["obj"])
    if ob is None:
        return np.zeros(len(pos), bool)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    mw = ob.matrix_world
    pts = [mw @ v.co for v in bm.verts if v.is_boundary]
    bm.free()
    pts = [p for p in pts if p.y < LAPEL["y_max"] and p.z > LAPEL["z_min"]]
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    d = np.array([kd.find(tuple(q))[2] for q in pos.tolist()])
    return d < LAPEL["width"]


def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def basis(d):
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    up = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(up, d)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return u, v, d


def scene_triangles(exclude=()):
    """world-space triangles of everything that renders (outline hulls off),
    except the objects named in exclude"""
    import bpy  # noqa: F401
    objs = [o for o in bk.render_objects() if o.name not in exclude]
    hulls = [m for o in objs for m in o.modifiers if m.name == "GG_outline" and m.show_viewport]
    for m in hulls:
        m.show_viewport = False
    try:
        tris = [bk.mesh_arrays(o, evaluated=True)["pos"] for o in objs]
    finally:
        for m in hulls:
            m.show_viewport = True
    return np.concatenate(tris).astype(np.float64)


def _rest(on):
    """bake in the rest pose: the rig's Rest Position on (True) / restored"""
    import bpy
    rig = bpy.data.objects.get("CEC_rig")
    if rig is None:
        return None
    if on:
        old = rig.data.pose_position
        rig.data.pose_position = "REST"
        bpy.context.view_layer.update()
        return old
    return None


def dir_buffer(d, tris, px):
    """orthographic depth map looking along -d (from the side d points to)"""
    u, v, d = basis(d)
    P = tris.reshape(-1, 3)
    x, y, z = P @ u / px, P @ v / px, -(P @ d)             # z: smaller = nearer the light side
    x0, y0 = x.min() - 2, y.min() - 2
    W, H = int(math.ceil(x.max() - x0)) + 3, int(math.ceil(y.max() - y0)) + 3
    xy = np.stack([x - x0, y - y0], 1).reshape(-1, 3, 2)
    zz = z.reshape(-1, 3)
    i, j, t, l = bk.raster(xy)
    keep = (i >= 0) & (i < W) & (j >= 0) & (j < H)
    i, j, t, l = i[keep], j[keep], t[keep], l[keep]
    dep = (l * zz[t]).sum(1)
    depth = np.full(W * H, np.inf)
    np.minimum.at(depth, j * W + i, dep)
    return dict(depth=depth.reshape(H, W), u=u, v=v, d=d, x0=x0, y0=y0, px=px, W=W, H=H)


def visible(buf, pos, nrm, tol, noff):
    q = pos + nrm * noff
    x = q @ buf["u"] / buf["px"] - buf["x0"]
    y = q @ buf["v"] / buf["px"] - buf["y0"]
    z = -(q @ buf["d"])
    ix = np.clip(np.floor(x).astype(np.int64), 0, buf["W"] - 1)
    iy = np.clip(np.floor(y).astype(np.int64), 0, buf["H"] - 1)
    # the min of the 2x2 neighbourhood: a texel next to an occluding edge is not
    # judged by the half-pixel that misses the edge
    ix1, iy1 = np.minimum(ix + 1, buf["W"] - 1), np.minimum(iy + 1, buf["H"] - 1)
    D = buf["depth"]
    dmax = np.maximum(np.maximum(D[iy, ix], D[iy, ix1]), np.maximum(D[iy1, ix], D[iy1, ix1]))
    return z <= np.where(np.isfinite(dmax), dmax, np.inf) + tol


def atlas_texels(names, size):
    import bpy
    out = []
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None or ob.data.uv_layers.get(bk.UV_NAME) is None:
            continue
        idx, pos, nrm = bk.texels(ob, size)
        out.append((n, idx, pos.astype(np.float64), nrm.astype(np.float64)))
    return out


def run():
    import bpy
    rig = bpy.data.objects.get("CEC_rig")
    old = _rest(True)
    try:
        return _run()
    finally:
        if rig is not None and old is not None:
            rig.data.pose_position = old
            bpy.context.view_layer.update()


def _run():
    t0 = time.time()
    tris = scene_triangles()
    tris_ns = scene_triangles(exclude=SKIRT_OCCLUDERS)
    dirs = fib_dirs(N_DIRS)
    groups = {"body": atlas_texels(list(bk.PALETTE), bk.SIZE["body"]),
              "hair": atlas_texels(list(bk.HAIR_OBJECTS), bk.SIZE["hair"])}
    acc = {g: [(n, idx, pos, nrm, np.zeros(len(idx)), np.zeros(len(idx))) for n, idx, pos, nrm in lst]
           for g, lst in groups.items()}
    t_buf = 0.0
    for d in dirs:
        tb = time.time()
        buf = dir_buffer(d, tris, AO_PX)
        buf_ns = dir_buffer(d, tris_ns, AO_PX)
        t_buf += time.time() - tb
        for g in acc:
            for n, idx, pos, nrm, s, w in acc[g]:
                c = nrm @ d
                on = c > 0.05
                if not on.any():
                    continue
                vis = visible(buf_ns if n in SKIRT_RECEIVERS else buf, pos[on], nrm[on], AO_TOL, AO_NOFF)
                s[on] += vis * c[on]
                w[on] += c[on]
    key = dir_buffer(np.array(KEY_DIR), tris, KEY_PX) if KEY_RECEIVERS else None
    report = dict(dirs=N_DIRS, t_buffers=round(t_buf, 1), objects={})
    labels = imgio.load(os.path.join(bk.TEX_DIR, "body_label.png"), channels=1)[::-1, :, 0].reshape(-1)
    hair_purple = imgio.load(os.path.join(bk.TEX_DIR, "hair_mask.png"), channels=1)[::-1, :, 0].reshape(-1) / 255.0
    sp = os.path.join(bk.TEX_DIR, "body_sheen.png")
    sheen = (imgio.load(sp, channels=1)[::-1, :, 0].reshape(-1) / 255.0 if os.path.exists(sp)
             else np.zeros(bk.SIZE["body"] ** 2))
    for g, size in (("body", bk.SIZE["body"]), ("hair", bk.SIZE["hair"])):
        S = size
        ao = np.ones(S * S, np.float32)
        ctrl = np.zeros((S * S, 4), np.float32)
        ctrl[:, 0], ctrl[:, 1], ctrl[:, 3] = 1.0, 0.5, 1.0
        filled = np.zeros(S * S, bool)
        for n, idx, pos, nrm, s, w in acc[g]:
            a = np.where(w > 0, s / np.maximum(w, 1e-9), 1.0)
            ao[idx] = a
            # piecewise: AO_DEEP -> 0.1, AO_SHADOW -> 0.5, AO_OPEN -> 1 (the shader's thresholds)
            r = np.interp(a, [0.0, AO_DEEP, AO_SHADOW, AO_OPEN, 1.0], [0.0, 0.1, 0.5, 1.0, 1.0])
            if n in OPEN_OBJECTS:
                r = np.ones_like(r)
            elif n in SKIRT_RECEIVERS:
                r = a                                             # raw: the leg material remaps it
            elif n == "hair":
                r = np.where(toon_in_ear_pit(pos), 1.0, r)
            gch = np.full(len(idx), 0.5)
            if n in KEY_RECEIVERS:
                lit = visible(key, pos, nrm, KEY_TOL, AO_NOFF) | ((nrm @ (np.array(KEY_DIR) / np.linalg.norm(KEY_DIR))) <= 0)
                gch = np.where(lit, 0.5, 0.2)                 # cast shadow: first shadow, not the second
            spec = np.zeros(len(idx))
            if g == "hair" and n in ("hair", "bangs"):
                spec = strand_mask(pos, hair_purple[idx]).astype(float)
            if g == "body":
                fam = labels[idx].astype(np.int64) - 1
                for f, val in SPEC_FAMILIES.items():
                    spec[fam == bk.FAMILY_NAMES.index(f)] = val
                if n in SPEC_NONE:
                    spec[:] = 0.0
                if n in bk.SHEEN:                             # the black jacket's sheen
                    fam_sheen = fam == bk.FAMILY_NAMES.index(bk.SHEEN[n][0])
                    spec = np.maximum(spec, fam_sheen if SHEEN_MODE == "all" else sheen[idx] * fam_sheen)
                if n == LAPEL["obj"]:
                    band = lapel_band(pos)
                    spec[band] = 0.0
                    gch = np.where(band, 0.2, gch)
                    report["lapel_texels"] = int(band.sum())
            ctrl[idx, 0], ctrl[idx, 1], ctrl[idx, 2] = r, gch, spec
            filled[idx] = True
            report["objects"][n] = dict(ao_mean=round(float(a.mean()), 3), deep=round(float((a < AO_DEEP).mean()), 3),
                                        shadow=round(float((a < AO_SHADOW).mean()), 3))
        arrs = dict(c=ctrl.reshape(S, S, 4), ao=ao.reshape(S, S))
        bk.pad_islands(arrs, filled.reshape(S, S))
        imgio.save(os.path.join(bk.TEX_DIR, "%s_ctrl.png" % g),
                   np.clip(arrs["c"][::-1] * 255 + 0.5, 0, 255).astype(np.uint8))
        imgio.save(os.path.join(bk.TEX_DIR, "%s_ao.png" % g),
                   np.clip(arrs["ao"][::-1] * 255 + 0.5, 0, 255).astype(np.uint8))
    report["t"] = round(time.time() - t0, 1)
    with open(os.path.join(bk.TEX_DIR, "shade_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    return report


if __name__ == "__main__":
    print(run())
