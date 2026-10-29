"""Milestone 4: thin clothing pieces traced as outlines in one view and laid
onto the model (run in Blender; the mask part is numpy only).

A piece (neckerchief bow and tails, brooch, tie, shirt collar, collar points,
belts ...) is a region of a reference crop selected by colour (mask()). Its
outline becomes a fine grid of cells (0.5 sheet px) inside the mask (soft
edge at 0.5, boundary vertices relaxed so the outline is smooth); every
vertex is ray-cast from that view's camera direction onto target objects
and lifted off the surface by `offset`; Solidify gives it `thickness`.
So the piece covers exactly what the drawing covers in that view, and sits
on the body in depth.
"""
import importlib
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402
import trace_clothes as tc  # noqa: E402

importlib.reload(cfg)
importlib.reload(tc)

P = cfg.PX


def hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = (mx - mn) / np.maximum(mx, 1)
    return hue, sat, mx, mn


def box_blur(a, k=1):
    h, w = a.shape
    for _ in range(k):
        p = np.pad(a, 1, mode="edge")
        a = sum(p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)) / 9.0
    return a


def dilate(m, k=1):
    for _ in range(k):
        p = np.pad(m, 1)
        h, w = m.shape
        out = np.zeros_like(m)
        for dy in range(3):
            for dx in range(3):
                out |= p[dy:dy + h, dx:dx + w]
        m = out
    return m


def erode(m, k=1):
    return ~dilate(~m, k)


RULES = {
    # name: function(rgb, hue, sat, mx, mn) -> bool core mask
    "gold": lambda rgb, h, s, mx, mn: (h > 24) & (h < 58) & (s > 0.42) & (rgb[..., 0] > 150),
    "white": lambda rgb, h, s, mx, mn: (rgb.mean(-1) > 205) & (mx - mn < 30),
    "shirt": lambda rgb, h, s, mx, mn: (rgb.mean(-1) > 150) & (mx - mn < 45) & (rgb[..., 2] >= rgb[..., 0] - 8),
    "dark": lambda rgb, h, s, mx, mn: (mx - mn < 30) & (rgb.mean(-1) < 95),
    "jacket": lambda rgb, h, s, mx, mn: (mx - mn < 30) & (rgb.mean(-1) < 150),
    "maroon": lambda rgb, h, s, mx, mn: ((h < 20) | (h > 340)) & (s > 0.4) & (rgb[..., 0] < 175) & (rgb[..., 0] > 70),
    "red": lambda rgb, h, s, mx, mn: ((h < 20) | (h > 340)) & (s > 0.4) & (rgb[..., 0] > 120),
    "silver": lambda rgb, h, s, mx, mn: (mx - mn < 40) & (rgb.mean(-1) > 120),
}


def mask(view, rule, box, grow=1, close=0, keep=None):
    """soft (0..1) mask of a rule inside box=(u0, v0, u1, v1) of a crop;
    grow: dilate the core by this many px (the drawn outline belongs to the
    piece); close: fill gaps; keep: optional bool array (crop size) to AND"""
    rgb = imgio.load(cfg.ref_path(view), channels=3).astype(np.float32)
    h, s, mx, mn = hsv(rgb)
    core = RULES[rule](rgb, h, s, mx, mn)
    u0, v0, u1, v1 = box
    m = np.zeros(core.shape, bool)
    m[v0:v1, u0:u1] = core[v0:v1, u0:u1]
    if keep is not None:
        m &= keep
    if close:
        m = erode(dilate(m, close), close)
    if grow:
        m = dilate(m, grow) & (mask_fig(view))
    soft = box_blur(m.astype(np.float32), 1)
    return soft


_FIG = {}


def mask_fig(view):
    if view not in _FIG:
        _FIG[view] = imgio.load_mask(cfg.mask_path(view))
    return _FIG[view]


def largest(m, n=1, min_px=10):
    """keep the n largest 4-connected components of a bool mask"""
    lab = np.zeros(m.shape, np.int32)
    cur = 0
    sizes = []
    ys, xs = np.where(m)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        cnt = 0
        while stack:
            y, x = stack.pop()
            cnt += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1] and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = cur
                    stack.append((yy, xx))
        sizes.append(cnt)
    order = np.argsort(sizes)[::-1][:n]
    out = np.zeros(m.shape, bool)
    for k in order:
        if sizes[k] >= min_px:
            out |= lab == (k + 1)
    return out


def bilinear(a, u, v):
    """sample a (H, W) array at continuous image coords (pixel centres at +0.5)"""
    H, W = a.shape
    x = np.clip(u - 0.5, 0, W - 1.001)
    y = np.clip(v - 0.5, 0, H - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) +
            a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def grid(soft, box, step=0.5, relax=3):
    """cells of `step` px whose 4 corners... -> (uv verts, quads): the cells
    whose centre samples the soft mask above 0.5; boundary vertices are then
    moved onto the 0.5 contour along the mask gradient and relaxed"""
    u0, v0, u1, v1 = box
    us = np.arange(u0, u1 + 1e-6, step)
    vs = np.arange(v0, v1 + 1e-6, step)
    cu = 0.5 * (us[:-1] + us[1:])
    cv = 0.5 * (vs[:-1] + vs[1:])
    CU, CV = np.meshgrid(cu, cv)
    inside = bilinear(soft, CU, CV) > 0.5
    nv, nu = len(vs), len(us)
    vid = -np.ones((nv, nu), np.int64)
    quads = []
    verts = []
    for i in range(inside.shape[0]):
        for j in range(inside.shape[1]):
            if not inside[i, j]:
                continue
            q = []
            for (ii, jj) in ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)):
                if vid[ii, jj] < 0:
                    vid[ii, jj] = len(verts)
                    verts.append([us[jj], vs[ii]])
                q.append(int(vid[ii, jj]))
            quads.append(q)
    verts = np.array(verts, float)
    if len(verts) == 0:
        return verts, quads
    # boundary vertices: used by fewer than 4 quads
    use = np.zeros(len(verts), int)
    for q in quads:
        for k in q:
            use[k] += 1
    bnd = use < 4
    # snap boundary vertices towards the 0.5 contour (a few gradient steps)
    for _ in range(4):
        u, v = verts[bnd, 0], verts[bnd, 1]
        f = bilinear(soft, u, v) - 0.5
        gu = (bilinear(soft, u + 0.25, v) - bilinear(soft, u - 0.25, v)) / 0.5
        gv = (bilinear(soft, u, v + 0.25) - bilinear(soft, u, v - 0.25)) / 0.5
        g2 = gu * gu + gv * gv + 1e-6
        verts[bnd, 0] -= np.clip(f * gu / g2, -0.3, 0.3)
        verts[bnd, 1] -= np.clip(f * gv / g2, -0.3, 0.3)
    # relax boundary along itself
    nb = [[] for _ in range(len(verts))]
    for q in quads:
        for a, b in zip(q, q[1:] + q[:1]):
            nb[a].append(b)
            nb[b].append(a)
    for _ in range(relax):
        new = verts.copy()
        for k in np.where(bnd)[0]:
            ns = [n for n in set(nb[k]) if bnd[n]]
            if len(ns) >= 2:
                new[k] = 0.5 * verts[k] + 0.5 * verts[ns].mean(axis=0)
        verts = new
    return verts, quads


def to_world_ray(view, u, v):
    """ray origin and direction (world) for crop coords (u, v) of a view"""
    from mathutils import Vector
    x, y, z = cfg.img_to_world(view, u, v)
    d = {"front": Vector((0, 1, 0)), "back": Vector((0, -1, 0)), "side": Vector((1, 0, 0))}[view]
    o = Vector((x, y, z)) - d * 2.0
    return o, d


def project(view, uv, targets, offset):
    """ray-cast every uv vertex onto the target objects; returns world
    positions lifted by `offset` towards the camera, and a hit flag"""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ps = [], []
    for ob in targets:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(vs)
        mw = ob.matrix_world
        vs += [mw @ v.co for v in me.vertices]
        ps += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(vs, ps)
    out = np.zeros((len(uv), 3))
    hit = np.zeros(len(uv), bool)
    for k, (u, v) in enumerate(uv):
        o, d = to_world_ray(view, u, v)
        loc, nrm, idx, dist = bvh.ray_cast(o, d, 10.0)
        if loc is not None:
            out[k] = np.array(loc) - np.array(d) * offset
            hit[k] = True
        else:
            out[k] = np.array(o + d * 2.0)
    # vertices that missed: take the depth of the nearest hit vertex
    if hit.any() and not hit.all():
        hv = np.where(hit)[0]
        axis = {"front": 1, "back": 1, "side": 0}[view]
        for k in np.where(~hit)[0]:
            j = hv[np.argmin(((uv[hv] - uv[k]) ** 2).sum(1))]
            out[k, axis] = out[j, axis]
    return out, hit


def piece(name, view, soft, box, targets, offset, thickness, coll, color, step=0.5, depth_fn=None):
    """build a decal piece object"""
    import bmesh
    import bpy
    import build_blockout as bb
    uv, quads = grid(soft, box, step)
    if len(uv) == 0:
        return None
    pos, hit = project(view, uv, targets, offset)
    if depth_fn is not None:
        pos = depth_fn(uv, pos)
    ob = bb.make_obj(name, [tuple(p) for p in pos], [tuple(q) for q in quads], coll, color)
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 0.0
    mod.use_rim = True
    mod.use_even_offset = True
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    ob.data.update()
    return ob
