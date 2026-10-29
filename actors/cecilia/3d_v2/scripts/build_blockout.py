"""Milestone 2: build the silhouette blockout in Blender from refs/profiles_m2.json.

Every part is generated from the traced profiles (scripts/profiles.py):
  vertical parts  -> stacks of superellipse rings, one per traced row; each
                     ring's x-extent = the front/back edges, y-extent = the
                     side edges, so the ortho silhouettes follow the masks.
  skirt           -> grid of angle columns running from the waist down to a
                     saddle-shaped hem (low at front/back centre, as drawn in
                     the front/back views).
  arms            -> rings sliced along x (front/back give top/bottom), round
                     sections around the arm axis measured from the side view.
  sword, ahoge    -> tubes along fitted centre lines.
Run:  import runpy; runpy.run_path(r"<3d_v2>\\scripts\\build_blockout.py", run_name="__main__")
"""
import importlib
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)

N_RING = 48
EXP = dict(leg=2.2, shoe=3.0, bow=2.0, torso=2.4, head=2.1, skirt=2.0)
K_ARM = 1.0                 # arm depth / arm height (side view: cuff ring is round)
HAND_X0 = 0.453             # |x| where the glove/hand starts (front col 75 / 465)
HAND_HALF_W = (0.029, 0.022)  # hand half-depth at wrist, at fingertips (side view, end-on hand)

COLORS = dict(leg=(0.22, 0.15, 0.13, 1), shoe=(0.35, 0.2, 0.12, 1), bow=(0.8, 0.15, 0.15, 1),
              skirt=(0.75, 0.12, 0.13, 1), torso=(0.12, 0.12, 0.13, 1), head=(0.08, 0.06, 0.1, 1),
              ahoge=(0.08, 0.06, 0.1, 1), arm=(0.35, 0.35, 0.37, 1), sword=(0.92, 0.9, 0.85, 1),
              hilt=(0.7, 0.15, 0.12, 1), guard=(0.85, 0.65, 0.2, 1))


def se(t, n):
    c, s = math.cos(t), math.sin(t)
    return (math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s))


def get_model_coll():
    c = bpy.data.collections.get("MODEL")
    if c is None:
        c = bpy.data.collections.new("MODEL")
        bpy.context.scene.collection.children.link(c)
    return c


def clear(coll):
    for o in list(coll.objects):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me is not None and me.users == 0 and isinstance(me, bpy.types.Mesh):
            bpy.data.meshes.remove(me)


def make_obj(name, verts, faces, coll, color, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.color = color
    coll.objects.link(ob)
    return ob


def loft(name, rings, n, coll, color, cap_top=True, cap_bot=True, N=N_RING):
    """rings: [z, x0, x1, y0, y1]; superellipse ring per entry, quads between."""
    rings = sorted(rings, key=lambda r: -r[0])
    verts, faces = [], []
    for z, x0, x1, y0, y1 in rings:
        xc, yc, a, b = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (x1 - x0), 0.5 * (y1 - y0)
        for i in range(N):
            cx, sy = se(2 * math.pi * i / N, n)
            verts.append((xc + a * cx, yc + b * sy, z))
    R = len(rings)
    for i in range(R - 1):
        for j in range(N):
            a, b = i * N + j, i * N + (j + 1) % N
            c, d = (i + 1) * N + (j + 1) % N, (i + 1) * N + j
            faces.append((a, d, c, b))
    if cap_top:
        faces.append(tuple(range(N)))
    if cap_bot:
        faces.append(tuple(range((R - 1) * N, R * N))[::-1])
    return make_obj(name, verts, faces, coll, color)


def skirt_mesh(name, rings, hem, n, coll, color, N=72, K=64):
    rings = sorted(rings, key=lambda r: -r[0])
    Z = np.array([r[0] for r in rings])
    cols = [np.array([r[k] for r in rings]) for k in (1, 2, 3, 4)]
    z_top = Z[0]

    def box(z):
        return [float(np.interp(z, Z[::-1], A[::-1])) for A in cols]
    verts, faces = [], []
    for j in range(N):
        t = 2 * math.pi * j / N
        s = math.sin(t)
        zh = hem["side"] + (hem["front"] - hem["side"]) * max(0.0, -s) ** 2 + (hem["back"] - hem["side"]) * max(0.0, s) ** 2
        cx, sy = se(t, n)
        for i in range(K):
            z = z_top + (zh - z_top) * i / (K - 1)
            x0, x1, y0, y1 = box(z)
            verts.append((0.5 * (x0 + x1) + 0.5 * (x1 - x0) * cx, 0.5 * (y0 + y1) + 0.5 * (y1 - y0) * sy, z))
    for j in range(N):
        jn = (j + 1) % N
        for i in range(K - 1):
            a, b, c, d = j * K + i, jn * K + i, jn * K + i + 1, j * K + i + 1
            faces.append((a, d, c, b))
    return make_obj(name, verts, faces, coll, color)


def arm_mesh(name, arm, axis_y, coll, color, N=24):
    xs, zt, zb = arm["x"], arm["ztop"], arm["zbot"]
    order = sorted(range(len(xs)), key=lambda k: abs(xs[k]))
    xmax = max(abs(x) for x in xs)
    verts, faces = [], []
    for k in order:
        x = xs[k]
        zc, hz = 0.5 * (zt[k] + zb[k]), 0.5 * (zt[k] - zb[k])
        if abs(x) >= HAND_X0:
            u = (abs(x) - HAND_X0) / max(xmax - HAND_X0, 1e-6)
            hy = HAND_HALF_W[0] * (1 - u) + HAND_HALF_W[1] * u
        else:
            hy = hz * K_ARM
        for i in range(N):
            t = 2 * math.pi * i / N
            verts.append((x, axis_y + hy * math.cos(t), zc + hz * math.sin(t)))
    R = len(order)
    for i in range(R - 1):
        for j in range(N):
            faces.append((i * N + j, i * N + (j + 1) % N, (i + 1) * N + (j + 1) % N, (i + 1) * N + j))
    faces.append(tuple(range((R - 1) * N, R * N)))     # fingertip cap
    return make_obj(name, verts, faces, coll, color)


def frame(tan):
    t = np.array(tan, float)
    t /= np.linalg.norm(t)
    up = np.array([0.0, 0.0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(t, up)
    u /= np.linalg.norm(u)
    v = np.cross(t, u)
    return t, u, v


def tube(name, pts, coll, color, N=12, cap=True):
    """pts: [[x, y, z, r], ...] polyline with radius."""
    P = np.array([p[:3] for p in pts], float)
    R = [p[3] for p in pts]
    verts, faces = [], []
    for i in range(len(P)):
        tan = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        _, u, v = frame(tan)
        for j in range(N):
            a = 2 * math.pi * j / N
            q = P[i] + R[i] * (math.cos(a) * u + math.sin(a) * v)
            verts.append(tuple(q))
    for i in range(len(P) - 1):
        for j in range(N):
            faces.append((i * N + j, i * N + (j + 1) % N, (i + 1) * N + (j + 1) % N, (i + 1) * N + j))
    if cap:
        faces.append(tuple(range(N)))
        faces.append(tuple(range((len(P) - 1) * N, len(P) * N)))
    return make_obj(name, verts, faces, coll, color)


def cylinder(name, p0, p1, r, coll, color, N=16, rounded_end=False):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    pts = [[*p0, r], [*p1, r]]
    if rounded_end:
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        pts = [[*p0, r], [*(p1 - d * r * 0.5), r], [*(p1 - d * r * 0.1), r * 0.7], [*p1, r * 0.25]]
    return tube(name, pts, coll, color, N=N)


def tip_cards(name, tips, px, coll, color, half_t=0.0015):
    """Strand-tip stand-ins: one thin box per traced pixel run (x0, x1, z, y)."""
    verts, faces = [], []
    for x0, x1, z, y, _view in tips:
        i = len(verts)
        for (x, zz) in ((x0, z - px / 2), (x1, z - px / 2), (x1, z + px / 2), (x0, z + px / 2)):
            verts.append((x, y - half_t, zz))
        for (x, zz) in ((x0, z - px / 2), (x1, z - px / 2), (x1, z + px / 2), (x0, z + px / 2)):
            verts.append((x, y + half_t, zz))
        faces += [(i, i + 1, i + 2, i + 3), (i + 7, i + 6, i + 5, i + 4), (i, i + 4, i + 5, i + 1),
                  (i + 1, i + 5, i + 6, i + 2), (i + 2, i + 6, i + 7, i + 3), (i + 3, i + 7, i + 4, i)]
    return make_obj(name, verts, faces, coll, color, recalc=False)


def build(profile_path=None):
    profile_path = profile_path or os.path.join(cfg.REFS, "profiles_m2.json")
    with open(profile_path) as fh:
        d = json.load(fh)
    coll = get_model_coll()
    clear(coll)
    objs = []
    for s_ in ("R", "L"):
        objs.append(loft("leg_" + s_, d["legs"][s_], EXP["leg"], coll, COLORS["leg"]))
        objs.append(loft("shoe_" + s_, d["shoes"][s_], EXP["shoe"], coll, COLORS["shoe"]))
        objs.append(loft("bow_" + s_, d["bows"][s_], EXP["bow"], coll, COLORS["bow"]))
        objs.append(arm_mesh("arm_" + s_, d["arms"][s_], d["arm_axis_y"], coll, COLORS["arm"]))
    objs.append(skirt_mesh("skirt", d["skirt"]["rings"], d["skirt"]["hem"], EXP["skirt"], coll, COLORS["skirt"]))
    objs.append(loft("torso", d["torso"], EXP["torso"], coll, COLORS["torso"]))
    objs.append(loft("head", d["head"], EXP["head"], coll, COLORS["head"]))
    objs.append(tube("ahoge", d["ahoge"], coll, COLORS["ahoge"], N=10))
    sw = d["sword"]
    objs.append(tube("sheath", sw["sheath"], coll, COLORS["sword"], N=16))
    objs.append(tube("hilt", sw["hilt"], coll, COLORS["hilt"], N=16))
    objs.append(tube("hanger_strap", sw["strap"], coll, COLORS["torso"], N=8))
    if d.get("hair_tips"):
        objs.append(tip_cards("hair_tips_blockout", d["hair_tips"], d["px_m"], coll, COLORS["head"]))
    return {o.name: len(o.data.vertices) for o in objs}


if __name__ == "__main__":
    print(build())
