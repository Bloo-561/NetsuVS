"""Milestone 3: head, face and hair meshes from refs/profiles_head.json (run in Blender).

Replaces the M2 head blockout (head, hair_tips_blockout, ahoge) in MODEL with:
  face        front half-rings: profile from the side view (nose taken out),
              width from the front view's visible face, cheek depth from the
              side view's skin/hair boundary; chin closed underneath
  nose        small ridge whose tip follows the side profile
  skull       closed volume inside the hair (keeps the head solid in 3/4)
  neck, ears  ears where the side view shows them
  hair        one shell of angle columns hanging from the crown; each column
              ends where the drawing's hair ends when seen from the view that
              faces it (front: bang tips / side locks, side: locks / ear
              notch / back tips, back: nape tips), so the bangs, the face
              opening, the side locks and the jagged tips are all traced
  headband, clip_R, clip_L, ahoge
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\build_head.py", run_name="__main__")
"""
import importlib
import json
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)
import build_blockout as bb  # noqa: E402

importlib.reload(bb)

P = cfg.PX
N_HAIR = 2.1            # superellipse exponent of the hair cross-section
N_FACE = 2.2            # face front half: slightly flatter than an ellipse
N_COLS = 160            # hair columns around the head
HAIR_THICK = 0.003
REMOVE = ("head", "hair_tips_blockout", "ahoge")
COL = dict(face=(0.98, 0.86, 0.8, 1), hair=(0.12, 0.1, 0.14, 1), band=(0.8, 0.15, 0.15, 1),
           clip=(0.3, 0.6, 0.65, 1))


def sole_z(view, row):
    return (cfg.VIEWS[view]["sole_v"] - row) * P


class Rings:
    """interpolate [z, x0, x1, y0, y1] rings at any z"""

    def __init__(self, rings):
        r = sorted(rings, key=lambda q: q[0])
        self.z = np.array([q[0] for q in r])
        self.c = [np.array([q[k] for q in r]) for k in (1, 2, 3, 4)]

    def box(self, z):
        return [float(np.interp(z, self.z, c)) for c in self.c]

    def point(self, z, t, n=N_HAIR):
        x0, x1, y0, y1 = self.box(z)
        cx, sy = bb.se(t, n)
        return (0.5 * (x0 + x1) + 0.5 * (x1 - x0) * cx, 0.5 * (y0 + y1) + 0.5 * (y1 - y0) * sy)

    def normal(self, z, t, n=N_HAIR):
        x0, x1, y0, y1 = self.box(z)
        a, b = max(0.5 * (x1 - x0), 1e-4), max(0.5 * (y1 - y0), 1e-4)
        nx, ny = math.cos(t) / a, math.sin(t) / b
        L = math.hypot(nx, ny)
        return nx / L, ny / L

    def front_y(self, z, x, n=N_HAIR):
        """y of the shell's front surface at (x, z)"""
        x0, x1, y0, y1 = self.box(z)
        xc, a, yc, b = 0.5 * (x0 + x1), 0.5 * (x1 - x0), 0.5 * (y0 + y1), 0.5 * (y1 - y0)
        u = min(abs(x - xc) / max(a, 1e-6), 0.999)
        return yc - b * (1.0 - u ** n) ** (1.0 / n)


# ----------------------------------------------------------------------------- hair
def column_bottoms(R, lower, z_ref, z_min):
    """z where each column's hair ends, looked up in the view that faces it."""
    lf, lb, ls = (np.array(lower[v]) for v in ("front", "back", "side"))
    cf, cbk, cs = (cfg.VIEWS[v]["centre_u"] for v in ("front", "back", "side"))
    out, who = [], []
    for j in range(N_COLS):
        t = 2 * math.pi * j / N_COLS
        z = z_ref
        view = None
        for _ in range(4):
            x, y = R.point(z, t)
            nx, ny = R.normal(z, t)
            if ny < -abs(nx):
                view = "front"
                u = int(math.floor(x / P + cf))
                row = lf[u] if 0 <= u < len(lf) else -1
                zz = sole_z("front", row + 1) if row >= 0 else None
            elif ny > abs(nx):
                view = "back"
                u = int(math.floor(cbk - x / P))
                row = lb[u] if 0 <= u < len(lb) else -1
                zz = sole_z("back", row + 1) if row >= 0 else None
            else:
                view = "side"
                u = int(math.floor(cs - y / P))
                row = ls[u] if 0 <= u < len(ls) else -1
                zz = sole_z("side", row + 1) if row >= 0 else None
            if zz is None:
                zz = z_min
            zz = max(zz, z_min)
            if abs(zz - z) < 0.5 * P:
                z = zz
                break
            z = zz
        out.append(z)
        who.append(view)
    return out, who


def hair_shell(d, coll):
    R = Rings(d["hair_rings"])
    z_top = float(R.z.max())
    z_min = float(R.z.min())
    bottoms, who = column_bottoms(R, d["lower"], z_ref=sole_z("front", 112), z_min=z_min)
    # common height levels, one per pixel row
    levels = np.arange(z_top, z_min - 1e-6, -P)
    nlev = [int(np.clip(round((z_top - zb) / P), 1, len(levels) - 1)) for zb in bottoms]
    verts, faces, idx = [], [], []
    top_id = 0
    x0, x1, y0, y1 = R.box(z_top)
    verts.append((0.5 * (x0 + x1), 0.5 * (y0 + y1), z_top + 0.4 * P))
    for j in range(N_COLS):
        t = 2 * math.pi * j / N_COLS
        col = []
        for k in range(nlev[j] + 1):
            x, y = R.point(levels[k], t)
            col.append(len(verts))
            verts.append((x, y, float(levels[k])))
        idx.append(col)
    for j in range(N_COLS):
        jn = (j + 1) % N_COLS
        a, b = idx[j], idx[jn]
        faces.append((top_id, a[0], b[0])[::-1])
        for k in range(min(len(a), len(b)) - 1):
            faces.append((a[k], a[k + 1], b[k + 1], b[k])[::-1])
    ob = bb.make_obj("hair", verts, faces, coll, COL["hair"])
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = HAIR_THICK
    mod.offset = -1.0
    ob["bottoms"] = [round(z, 4) for z in bottoms]
    ob["bottom_view"] = "".join(w[0] for w in who)
    return ob, R


# ----------------------------------------------------------------------------- face, skull, neck
def face_mesh(d, coll, M=40):
    rings = sorted(d["face"]["rings"], key=lambda q: -q[0])
    verts, faces = [], []
    tuck = [(0.98, 0.010), (0.90, 0.022)]          # wrap the cheek edge back under the hair
    cols = M + 1 + 2 * len(tuck)
    for z, x0, x1, yf, ys in rings:
        xc, hw = 0.5 * (x0 + x1), 0.5 * (x1 - x0)
        row = []
        for s, dy in reversed(tuck):
            row.append((xc - hw * s, ys + dy, z))
        for i in range(M + 1):
            u = -1.0 + 2.0 * i / M
            y = ys + (yf - ys) * (1.0 - abs(u) ** N_FACE) ** (1.0 / N_FACE)
            row.append((xc + hw * u, y, z))
        for s, dy in tuck:
            row.append((xc + hw * s, ys + dy, z))
        verts += row
    R = len(rings)
    for i in range(R - 1):
        for j in range(cols - 1):
            a, b = i * cols + j, i * cols + j + 1
            faces.append((a, b, (i + 1) * cols + j + 1, (i + 1) * cols + j))
    faces.append(tuple(range((R - 1) * cols, R * cols)))       # chin underside
    return bb.make_obj("face", verts, faces, coll, COL["face"])


def nose_mesh(d, coll):
    pts = sorted(d["face"]["nose"], key=lambda q: -q[0])
    if len(pts) < 2:
        return None
    w = 0.006
    verts, faces = [], []
    for z, xc, plane, tip in pts:
        verts += [(xc - w, plane + 0.002, z), (xc, tip, z), (xc + w, plane + 0.002, z)]
    for i in range(len(pts) - 1):
        a = 3 * i
        faces += [(a, a + 1, a + 4, a + 3), (a + 1, a + 2, a + 5, a + 4)]
    n = 3 * (len(pts) - 1)
    faces += [(0, 1, 2), (n + 2, n + 1, n)]
    return bb.make_obj("nose", verts, faces, coll, COL["face"])


def skull_mesh(d, R, coll):
    """closed volume inside the hair: hair rings pulled in, front = behind the face"""
    face = {round(q[0], 6): q for q in d["face"]["rings"]}
    fz = sorted(face)
    rings = []
    for z in np.arange(float(R.z.max()) - 2 * P, sole_z("front", 141), -2 * P):
        x0, x1, y0, y1 = R.box(z)
        xc = 0.5 * (x0 + x1)
        hw = min(0.5 * (x1 - x0) - 0.012, 0.074)                 # real head ~15 cm wide
        hw = max(hw, 0.02)
        yb = y1 - 0.025
        if z <= fz[-1]:
            q = face[min(fz, key=lambda k: abs(k - z))]
            yf = q[3] + 0.008                                     # just behind the face surface
            hw = max(hw, 0.5 * (q[2] - q[1]))
        else:
            yf = y0 + 0.018
        if yb - yf < 0.04:
            yb = yf + 0.04
        rings.append([float(z), xc - hw, xc + hw, float(yf), float(yb)])
    return bb.loft("skull", rings, 2.0, coll, COL["face"])


def neck_mesh(d, coll):
    n = d["neck"]
    rings = [[z, -n["half_w"], n["half_w"], n["y0"], n["y1"]] for z in np.linspace(n["z1"], n["z0"], 8)]
    return bb.loft("neck", rings, 2.0, coll, COL["face"])


def ear_meshes(d, R, coll):
    e = d.get("ear")
    if not e:
        return []
    cs = cfg.VIEWS["side"]["centre_u"]
    zc = 0.5 * (sole_z("front", e["r0"]) + sole_z("front", e["r1"]))
    h = (e["r1"] - e["r0"]) * P
    yc = -((e["u0"] + e["u1"]) / 2.0 - cs) * P
    dep = (e["u1"] - e["u0"]) * P
    out = []
    for side, sgn in (("R", -1), ("L", 1)):
        x = sgn * 0.074                                           # on the skull's side
        rings = []
        for k in range(9):
            a = -math.pi / 2 + math.pi * k / 8
            zz = zc + 0.5 * h * math.sin(a)
            r = math.cos(a)
            rings.append([zz, x - 0.006 * r, x + 0.006 * r, yc - 0.5 * dep * r, yc + 0.5 * dep * r])
        out.append(bb.loft("ear_" + side, rings, 2.0, coll, COL["face"]))
    return out


# ----------------------------------------------------------------------------- band, clips, ahoge
def headband(d, R, coll, lift=0.002):
    cols = sorted((int(k), v) for k, v in d["headband"]["front"].items())
    cf = cfg.VIEWS["front"]["centre_u"]
    verts, faces = [], []
    for i, (u, (t, b)) in enumerate(cols):
        x = (u + 0.5 - cf) * P
        for row in (t, b):
            z = sole_z("front", row)
            verts.append((x, R.front_y(z, x) - lift, z))
    for i in range(len(cols) - 1):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))
    ob = bb.make_obj("headband", verts, faces, coll, COL["band"])
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = 0.003
    return ob


def clips(d, R, coll):
    cf = cfg.VIEWS["front"]["centre_u"]
    out = []
    for blob, name in zip(sorted(d["clips"]["front"], key=lambda b: b["cx"]), ("clip_R", "clip_L")):
        x = (blob["cx"] - cf) * P
        z = sole_z("front", blob["cy"])
        hw = 0.5 * (blob["c1"] - blob["c0"]) * P
        hh = 0.5 * (blob["r1"] - blob["r0"]) * P
        y = R.front_y(z, x) - 0.003
        v = [(x, y, z + hh), (x + hw, y, z), (x, y, z - hh), (x - hw, y, z), (x, y - 0.004, z), (x, y + 0.004, z)]
        f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)]
        out.append(bb.make_obj(name, v, f, coll, COL["clip"]))
    return out


def build():
    with open(os.path.join(cfg.REFS, "profiles_head.json")) as fh:
        d = json.load(fh)
    with open(os.path.join(cfg.REFS, "profiles_m2.json")) as fh:
        d2 = json.load(fh)
    coll = bb.get_model_coll()
    for name in REMOVE + ("hair", "face", "nose", "skull", "neck", "ear_R", "ear_L", "headband", "clip_R", "clip_L"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    hair, R = hair_shell(d, coll)
    objs = [hair, face_mesh(d, coll), nose_mesh(d, coll), skull_mesh(d, R, coll), neck_mesh(d, coll),
            headband(d, R, coll)]
    objs += ear_meshes(d, R, coll) + clips(d, R, coll)
    objs.append(bb.tube("ahoge", d2["ahoge"], coll, COL["hair"], N=10))
    return {o.name: len(o.data.vertices) for o in objs if o is not None}


if __name__ == "__main__":
    print(build())
