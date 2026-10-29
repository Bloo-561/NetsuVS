"""Milestone 4: clothing parts, traced (run in Blender).

Replaces the M2 one-piece torso with:
  body    the bodice / waist under the jacket (and the shirt bib at the
          neck): only its front shows, through the jacket's opening; its
          front is the side view's red bodice edge, falling off towards the
          jacket's front edges so they always lie on top of it
  jacket  the cropped jacket as an open shell: outer surface = the traced
          silhouette (front/back edges, side back edge), cut open at the
          front between the jacket's front edges traced in the front view,
          those edges at the depth the side view draws them; each column
          ends at the hem traced in the view it faces; 4 mm thick
Inputs: refs/profiles_m2.json (silhouette rings) and refs/profiles_m4.json
(trace_clothes.py). Other objects are left alone.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\build_clothes.py")["build"]()
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
import build_blockout as bb  # noqa: E402

importlib.reload(cfg)
importlib.reload(bb)

P = cfg.PX
CF, CB, CS = (cfg.VIEWS[v]["centre_u"] for v in ("front", "back", "side"))
SOLE_F = cfg.VIEWS["front"]["sole_v"]
N_TORSO = 2.4                 # superellipse exponent of the torso cross-section (as M2)
JACKET_TOP_ROW = 151.0        # shoulder line (front rows): the jacket's top edge
JACKET_THICK = 0.004
JACKET_COLS = 96              # columns from the right front edge round the back to the left one
# The front view draws the jacket's sides 8-10 px wider than the back view
# does (rows 210-240); the M2 torso sits at the mean. Half a pixel per side
# towards the front view balances the two views' IoU (front was 0.9497).
JACKET_WIDEN = 0.5 * P
BODY_GAP = 0.006              # body surface behind the jacket's outer surface (thickness + clearance)
BODY_TOP_ROW = 150.0
BODY_BOTTOM_ROW = 262.0
BODY_N = 64
COL = dict(jacket=(0.12, 0.12, 0.13, 1), body=(0.75, 0.12, 0.13, 1))
REMOVE = ("torso",)


def fx(u):
    return (u - CF) * P


def bx(u):
    return -(u - CB) * P


def sy(u):
    return -(u - CS) * P


def zedge(v):
    return (SOLE_F - v) * P


def row_of(z):
    return SOLE_F - z / P


def load():
    with open(os.path.join(cfg.REFS, "profiles_m2.json")) as fh:
        d2 = json.load(fh)
    with open(os.path.join(cfg.REFS, "profiles_m4.json")) as fh:
        d4 = json.load(fh)
    return d2, d4


class Torso:
    """the M2 torso silhouette rings, interpolated at any height"""

    def __init__(self, rings):
        r = sorted(rings, key=lambda q: q[0])
        self.z = np.array([q[0] for q in r])
        self.c = [np.array([q[k] for q in r]) for k in (1, 2, 3, 4)]

    def box(self, z):
        return [float(np.interp(z, self.z, a)) for a in self.c]


def se_point(t, xc, yc, a, b_back, b_front, n):
    c, s = math.cos(t), math.sin(t)
    x = xc + a * math.copysign(abs(c) ** (2.0 / n), c)
    b = b_back if s >= 0 else b_front
    y = yc + b * math.copysign(abs(s) ** (2.0 / n), s)
    return x, y


def front_b(x_edge, y_edge, xc, yc, a, n):
    """front half-depth of a superellipse quadrant that passes through (x_edge, y_edge)"""
    u = min(abs(x_edge - xc) / a, 0.98)
    return abs(y_edge - yc) / (1.0 - u ** n) ** (1.0 / n)


def edge_angle(x_edge, xc, a, n, right):
    u = min(abs(x_edge - xc) / a, 0.98) ** (n / 2.0)
    s = -math.sqrt(max(1.0 - u * u, 0.0))
    return math.atan2(s, -u if right else u)


class Trace:
    def __init__(self, d4):
        t = d4["torso"]
        self.rows = np.array(t["rows"], float)
        self.oR = np.array(t["open_R"])
        self.oL = np.array(t["open_L"])
        self.srows = np.array(t["side_rows"], float)
        self.jf = np.array(t["jf"])
        self.bf = np.array(t["bf"])
        self.bfront = np.array(t["body_front"])
        self.hem = {k: np.array(v) for k, v in t["hem"].items()}

    def opening(self, row):
        return fx(float(np.interp(row, self.rows, self.oR))), fx(float(np.interp(row, self.rows, self.oL)))

    def jacket_front_y(self, row):
        return sy(float(np.interp(row, self.srows, self.jf)))

    def bodice_front_y(self, row):
        return sy(float(np.interp(row, self.srows, self.bfront)))

    def hem_row(self, x, y, nx, ny):
        """hem (front row, continuous) for a jacket column at (x, y) facing (nx, ny)"""
        h = self.hem
        f = np.interp(x / P + CF, h["front"][:, 0], h["front"][:, 1])
        b = np.interp(-x / P + CB, h["back"][:, 0], h["back"][:, 1])
        s = np.interp(-y / P + CS, h["side"][:, 0], h["side"][:, 1])
        wf, wb, ws = max(-ny, 0.0) ** 2, max(ny, 0.0) ** 2, nx ** 2
        return float((wf * f + wb * b + ws * s) / max(wf + wb + ws, 1e-6))


def jacket(T, tr, coll):
    z_top = zedge(JACKET_TOP_ROW)
    hem_rows = []
    # columns: parameter s from the right front edge (0) round the back to the left one (1)
    S = np.linspace(0.0, 1.0, JACKET_COLS + 1)
    max_hem = max(float(v.max()) for v in [tr.hem["front"][:, 1], tr.hem["back"][:, 1], tr.hem["side"][:, 1]])
    levels = np.arange(z_top, zedge(max_hem) - 1e-6, -P)

    def ring(z):
        x0, x1, y0, y1 = T.box(z)
        xc, a = 0.5 * (x0 + x1), 0.5 * (x1 - x0) + JACKET_WIDEN
        yc = 0.5 * (y0 + y1)
        row = row_of(z)
        xR, xL = tr.opening(min(max(row, tr.rows[0]), tr.rows[-1]))
        yj = tr.jacket_front_y(min(max(row, tr.srows[0]), tr.srows[-1]))
        yj = min(yj, yc - 0.004)
        bR = front_b(xR, yj, xc, yc, a, N_TORSO)
        bL = front_b(xL, yj, xc, yc, a, N_TORSO)
        tR = edge_angle(xR, xc, a, N_TORSO, True) % (2 * math.pi)        # in (pi, 1.5 pi)
        tL = edge_angle(xL, xc, a, N_TORSO, False)                       # in (-0.5 pi, 0)
        pts = []
        for s in S:
            t = tR - s * (tR - tL)
            bf = bR if math.cos(t) < 0 else bL
            x, y = se_point(t, xc, yc, a, y1 - yc, bf, N_TORSO)
            pts.append((x, y, t))
        return pts, (xc, yc, a)

    rings = [ring(float(z)) for z in levels]
    # per column hem from the column's position/facing at mid-height of the hem band
    zm = zedge(246.0)
    pts_m, (xc, yc, a) = ring(zm)
    col_hem = []
    for x, y, t in pts_m:
        nx, ny = math.cos(t), math.sin(t)
        col_hem.append(zedge(tr.hem_row(x, y, nx, ny)))
    verts, faces = [], []
    idx = []
    for j in range(len(S)):
        col = []
        zb = col_hem[j]
        for i, z in enumerate(levels):
            if z <= zb + 0.3 * P:
                break
            x, y, _ = rings[i][0][j]
            col.append(len(verts))
            verts.append((x, y, float(z)))
        pb, _ = ring(zb)
        x, y, _ = pb[j]
        col.append(len(verts))
        verts.append((x, y, float(zb)))
        idx.append(col)
    for j in range(len(S) - 1):
        a_, b_ = idx[j], idx[j + 1]
        m = min(len(a_), len(b_))
        for k in range(m - 1):
            faces.append((a_[k], b_[k], b_[k + 1], a_[k + 1]))
        if len(a_) > len(b_):
            for k in range(m - 1, len(a_) - 1):
                faces.append((b_[-1], a_[k + 1], a_[k]))
        elif len(b_) > len(a_):
            for k in range(m - 1, len(b_) - 1):
                faces.append((a_[-1], b_[k], b_[k + 1]))
    # shoulder yoke: the top ring pulled in to the neckline
    x0, x1, y0, y1 = T.box(z_top)
    top = [idx[j][0] for j in range(len(S))]
    inner = []
    xn, yn0, yn1 = 0.055, -0.035, 0.06                      # neckline box (under the collar)
    for j in top:
        x, y, z = verts[j]
        # radial pull towards the neck ellipse
        cx, cy = 0.0, 0.5 * (yn0 + yn1)
        dx, dy = x - cx, y - cy
        r = math.hypot(dx / xn, dy / (0.5 * (yn1 - yn0)))
        inner.append(len(verts))
        verts.append((cx + dx / max(r, 1e-6), cy + dy / max(r, 1e-6), z + 0.004))
    for j in range(len(top) - 1):
        faces.append((top[j], inner[j], inner[j + 1], top[j + 1]))
    ob = bb.make_obj("jacket", verts, faces, coll, COL["jacket"])
    face_out(ob, axis=(0.0, 0.01))
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = JACKET_THICK
    mod.offset = -1.0
    mod.use_rim = True
    mod.use_even_offset = True
    return ob


def face_out(ob, toward=None, axis=(0.0, 0.005)):
    """make a thin piece's normals point outward: away from the vertical axis
    through `axis` (x, y), or along `toward` (a direction, e.g. the camera of
    the view it was traced in). Projection and visibility read these normals."""
    me = ob.data
    s = 0.0
    for p in me.polygons:
        c, n = p.center, p.normal
        if toward is not None:
            s += (n.x * toward[0] + n.y * toward[1] + n.z * toward[2]) * p.area
        else:
            s += (n.x * (c.x - axis[0]) + n.y * (c.y - axis[1])) * p.area
    if s < 0:
        me.flip_normals()
        me.update()
    return s < 0


def _normals_inward(ob):
    """True if the mesh's normals point to the torso axis (then Solidify
    offset +1 thickens inwards)"""
    me = ob.data
    s = 0.0
    for p in me.polygons[:200]:
        c = p.center
        s += p.normal.x * c.x + p.normal.y * (c.y - 0.01)
    return s < 0


WAIST_ROW = 250.0             # first row below the jacket: the bodice is the outer surface from here
BLEND_ROWS = (222.0, 246.0)   # body narrows from the under-jacket shape to the waist over these rows
# rows from which the body's front falls off under the jacket's front edges. M4
# started at 182 (below the neckerchief's bow); above it the body's front sat
# at the torso's outline (the bow) and poked 1-2 cm out through the jacket's
# upper front, hidden only by the projected colours. From the shoulder line now.
CONSTRAIN_FROM = 151.0


def _ring_under_jacket(T, tr, z):
    row = row_of(z)
    x0, x1, y0, y1 = T.box(z)
    xc, a = 0.5 * (x0 + x1), 0.5 * (x1 - x0)
    yc = 0.5 * (y0 + y1)
    ab = a - BODY_GAP
    bback = (y1 - yc) - BODY_GAP
    xR, xL = tr.opening(min(max(row, tr.rows[0]), tr.rows[-1]))
    yj = tr.jacket_front_y(min(max(row, tr.srows[0]), tr.srows[-1]))
    if row >= 194:
        yf = tr.bodice_front_y(row)
    elif row >= 176:
        t = (row - 176) / 18.0
        yf = (1 - t) * y0 + t * tr.bodice_front_y(194)
    else:
        yf = y0 + 0.004
    bfront = max(yc - yf, 0.01)
    nf = N_TORSO
    if row >= CONSTRAIN_FROM:
        # front exponent so that at the nearer jacket edge the body is
        # BODY_GAP behind the edge (the edge lies on top of it)
        need = (yc - (yj + BODY_GAP)) / bfront              # (1 - u^n)^(1/n) <= need
        u = min(min(abs(xR - xc), abs(xL - xc)) / ab, 0.95)
        if need < 1.0:
            nf = 1.05
            for nn in np.linspace(N_TORSO, 1.05, 80):
                if (1 - u ** nn) ** (1.0 / nn) <= need:
                    nf = float(nn)
                    break
            f = (1 - u ** nf) ** (1.0 / nf)
            if f > need:                    # even the pointiest front reaches past the edge: pull it back
                bfront = max((yc - (yj + BODY_GAP)) / f, 0.01)
    return xc, yc, ab, bback, bfront, nf


def _ring_profile(T, z):
    x0, x1, y0, y1 = T.box(z)
    xc, a = 0.5 * (x0 + x1), 0.5 * (x1 - x0)
    yc = 0.5 * (y0 + y1)
    return xc, yc, a, y1 - yc, yc - y0, N_TORSO


def body(T, tr, coll):
    """bodice / waist: rings from the shoulder line into the skirt"""
    levels = np.arange(zedge(BODY_TOP_ROW), zedge(BODY_BOTTOM_ROW) - 1e-6, -P)
    z_waist = zedge(WAIST_ROW)
    verts, faces = [], []
    for z in levels:
        z = float(z)
        row = row_of(z)
        if row >= WAIST_ROW:
            ring = _ring_profile(T, z)
        else:
            A = _ring_under_jacket(T, tr, z)
            B = _ring_profile(T, z_waist)
            w = min(max((row - BLEND_ROWS[0]) / (BLEND_ROWS[1] - BLEND_ROWS[0]), 0.0), 1.0)
            w = w * w * (3 - 2 * w)
            ring = tuple(A[k] + (B[k] - A[k]) * w for k in range(6))
        xc, yc, ab, bback, bfront, nf = ring
        for i in range(BODY_N):
            t = 2 * math.pi * i / BODY_N
            c, s = math.cos(t), math.sin(t)
            n = N_TORSO if s >= 0 else nf
            x = xc + ab * math.copysign(abs(c) ** (2.0 / n), c)
            b = bback if s >= 0 else bfront
            y = yc + b * math.copysign(abs(s) ** (2.0 / n), s)
            verts.append((x, y, z))
    R = len(levels)
    for i in range(R - 1):
        for j in range(BODY_N):
            a_, b_ = i * BODY_N + j, i * BODY_N + (j + 1) % BODY_N
            faces.append((a_, (i + 1) * BODY_N + j, (i + 1) * BODY_N + (j + 1) % BODY_N, b_))
    faces.append(tuple(range(BODY_N)))
    faces.append(tuple(range((R - 1) * BODY_N, R * BODY_N))[::-1])
    return bb.make_obj("body", verts, faces, coll, COL["body"])


def build(parts=("body", "jacket")):
    d2, d4 = load()
    coll = bb.get_model_coll()
    T = Torso(d2["torso"])
    tr = Trace(d4)
    for name in REMOVE + tuple(parts):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    out = {}
    if "body" in parts:
        ob = body(T, tr, coll)
        out["body"] = len(ob.data.vertices)
    if "jacket" in parts:
        ob = jacket(T, tr, coll)
        out["jacket"] = len(ob.data.vertices)
    for name in out:
        ob = bpy.data.objects[name]
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
        ob.data.update()
    return out


# ----------------------------------------------------------------------------- neck: collar, shirt, neckerchief
import decals as dc  # noqa: E402

NECK_C = (0.0, 0.022)            # neck centre (x, y), from build_head's neck
# the jacket's turned-down collar, as three loops round the neck (rx, ry, row):
#   base  where it leaves the neckline;  fold  its top edge (back view: row
#   137-139 at the back, side view: 141-143);  edge  the folded part's outer
#   edge lying on the shoulders (back view: cols 242-302 at row 150 -> 7 cm
#   half-width; side view: 5.4 cm behind / in front of the neck centre)
COLLAR_LOOPS = dict(base=(0.040, 0.045, 149.0), fold=(0.044, 0.049, 139.0), edge=(0.060, 0.054, 150.5))
COLLAR_SIDE_FOLD_ROW = 141.0
COLLAR_TIP = dict(x=0.046, y=-0.030, row=165.0)   # the points at the front (front view cols 250 / 290)
COLLAR_FOLD_FRONT = dict(x=0.024, y=-0.020, row=150.0)
COLLAR_ALPHA_MAX = math.radians(150.0)
COLLAR_FRONT_FROM = math.radians(95.0)
COLLAR_THICK = 0.003
COL.update(collar=(0.12, 0.12, 0.13, 1), neckerchief=(0.92, 0.7, 0.3, 1), brooch=(0.97, 0.97, 0.97, 1),
           tie=(0.1, 0.12, 0.1, 1), shirt_collar=(0.8, 0.82, 0.88, 1))


def _loop_point(name, al):
    rx, ry, row = COLLAR_LOOPS[name]
    cx, cy = NECK_C
    if name == "fold":
        a = min(abs(al), math.pi / 2) / (math.pi / 2)
        row = row + (COLLAR_SIDE_FOLD_ROW - row) * a
    return (cx + rx * math.sin(al), cy + ry * math.cos(al), zedge(row))


def collar_band(coll, NA=64, NS=8):
    """the jacket's turned-down collar: standing from the neckline up to the
    fold, then falling outward onto the shoulders; at the front it runs down
    into the two points"""
    verts, faces = [], []
    alphas = np.linspace(-COLLAR_ALPHA_MAX, COLLAR_ALPHA_MAX, NA + 1)
    for al in alphas:
        a = abs(al)
        sgn = 1.0 if al >= 0 else -1.0
        base, fold, edge = (_loop_point(n, al) for n in ("base", "fold", "edge"))
        if a > COLLAR_FRONT_FROM:
            t = (a - COLLAR_FRONT_FROM) / (COLLAR_ALPHA_MAX - COLLAR_FRONT_FROM)
            t = t * t * (3 - 2 * t)
            tip = (sgn * COLLAR_TIP["x"], COLLAR_TIP["y"], zedge(COLLAR_TIP["row"]))
            ff = (sgn * COLLAR_FOLD_FRONT["x"], COLLAR_FOLD_FRONT["y"], zedge(COLLAR_FOLD_FRONT["row"]))
            fold = tuple(fold[i] + (ff[i] - fold[i]) * t for i in range(3))
            edge = tuple(edge[i] + (tip[i] - edge[i]) * t for i in range(3))
            base = tuple(base[i] + (ff[i] - base[i]) * t for i in range(3))
        # strip: base -> fold (stand) -> edge (fall), NS segments each half
        pts = []
        for s in np.linspace(0.0, 1.0, NS + 1):
            pts.append(tuple(base[i] + (fold[i] - base[i]) * s for i in range(3)))
        for s in np.linspace(0.0, 1.0, NS + 1)[1:]:
            # the fall bows outward a little over the fold
            q = [fold[i] + (edge[i] - fold[i]) * s for i in range(3)]
            q[2] += 0.002 * math.sin(math.pi * s)
            pts.append(tuple(q))
        verts += pts
    K = 2 * NS + 1
    for i in range(NA):
        for j in range(K - 1):
            a_, b_ = i * K + j, (i + 1) * K + j
            faces.append((a_, b_, b_ + 1, a_ + 1))
    ob = bb.make_obj("collar", verts, faces, coll, COL["collar"])
    face_out(ob, axis=NECK_C)
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = COLLAR_THICK
    mod.offset = 0.0
    mod.use_rim = True
    return ob


def neck_pieces(coll):
    body = bpy.data.objects["body"]
    neck = bpy.data.objects.get("neck")
    jacket = bpy.data.objects.get("jacket")
    tg = [o for o in (body, neck) if o is not None]
    out = []
    # neckerchief: bow and both tails, lying on the shirt / bust
    soft = dc.mask("front", "gold", (240, 168, 305, 238), grow=1, close=1)
    ob = dc.piece("neckerchief", "front", soft, (240, 168, 305, 238), tg, 0.0016, 0.003, coll, COL["neckerchief"])
    out.append(ob)
    # brooch: the white flower on the knot
    soft = dc.mask("front", "white", (263, 174, 278, 187), grow=0, close=1)
    m = dc.largest(soft > 0.5, 1)
    soft = dc.box_blur(m.astype(np.float32), 1)
    out.append(dc.piece("brooch", "front", soft, (263, 174, 278, 187), [ob] + tg, 0.003, 0.004, coll, COL["brooch"]))
    # tie knot
    soft = dc.mask("front", "dark", (265, 151, 276, 163), grow=0, close=1)
    m = dc.largest(soft > 0.5, 1)
    soft = dc.box_blur(m.astype(np.float32), 1)
    out.append(dc.piece("tie", "front", soft, (265, 151, 276, 163), tg, 0.002, 0.003, coll, COL["tie"]))
    # shirt collar points (grey-blue), on the neck front
    soft = dc.mask("front", "shirt", (246, 137, 294, 158), grow=1, close=1)
    m = dc.largest(soft > 0.5, 1)
    soft = dc.box_blur(m.astype(np.float32), 1)
    out.append(dc.piece("shirt_collar", "front", soft, (246, 137, 294, 158), tg, 0.0015, 0.002, coll, COL["shirt_collar"]))
    out.append(collar_band(coll))
    return [o for o in out if o is not None]


def build_neck():
    coll = bb.get_model_coll()
    for name in ("neckerchief", "brooch", "tie", "shirt_collar", "collar"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    objs = neck_pieces(coll)
    for ob in objs:
        if ob.name != "collar":
            face_out(ob, toward=(0.0, -1.0, 0.0))
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
        ob.data.update()
    return {o.name: len(o.data.vertices) for o in objs}


# ----------------------------------------------------------------------------- belts
# centre lines of the two maroon belts, traced on the 10x zooms of each crop
# (crop columns, crop rows). Belt A is high on her right hip and low on her
# left; belt B the other way; they cross in front (left of centre) and in an
# X at the back. Side view = her right side.
BELT_TRACE = {
    "A": {"front": [(232, 258), (252, 266), (265, 272), (280, 279), (295, 286), (308, 292)],
          "back": [(300, 259), (285, 265), (270, 271), (255, 277), (240, 283), (228, 287)],
          "side": [(100, 256), (110, 259), (120, 262), (130, 265), (146, 269), (155, 276)]},
    "B": {"front": [(210, 288), (239, 288.5), (255, 286), (270, 283), (285, 279), (300, 272)],
          "back": [(235, 263), (250, 268), (265, 273), (280, 278), (300, 284), (320, 290)],
          "side": [(85, 282), (100, 285), (120, 287), (143, 288), (155, 290)]},
}
BUCKLES = {"A": (252.0, 266.0), "B": (239.0, 288.5)}      # front view centres (on her right front)
BELT_W = 0.014                   # belt width (6 sheet px)
BELT_T = 0.0025
BELT_LIFT = 0.0015
BUCKLE_SIZE = 0.017              # outer square side (7 px)
BUCKLE_BAR = 0.003
COL.update(belt=(0.42, 0.12, 0.14, 1), buckle=(0.75, 0.75, 0.78, 1))


def _bvh(objs):
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ps = [], []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(vs)
        mw = ob.matrix_world
        vs += [mw @ v.co for v in me.vertices]
        ps += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs, ps)


def _cast(bvh, o, d):
    from mathutils import Vector
    loc, nrm, idx, dist = bvh.ray_cast(Vector(o), Vector(d).normalized(), 5.0)
    return (None, None) if loc is None else (tuple(loc), tuple(nrm))


AXIS_Y = 0.005                   # the hips' centre line (side view waist mid-depth = 0, skirt centred a little back)


def _surface_at(bvh, theta, z, out_r=0.6):
    """outermost surface point at azimuth theta (0 = front, +90 deg = her left)
    and height z"""
    d = (math.sin(theta), -math.cos(theta), 0.0)
    o = (d[0] * out_r, AXIS_Y + d[1] * out_r, z)
    return _cast(bvh, o, (-d[0], -d[1], 0.0))


BELT_ORDER = 3                   # Fourier order of z(theta)


def _fit_belt(bvh, pts):
    """theta, z samples of a belt's centre line -> weighted Fourier fit
    z(theta). Each sample counts by how squarely its view sees that part of
    the body (front: cos^2 theta, back: cos^2 (theta - 180), side: sin^2
    theta on her right), so where views disagree the one looking straight
    at it wins"""
    samples = []
    for view, lst in pts.items():
        for u, v in lst:
            z = zedge(v + 0.5 - (1 if view == "side" else (-1 if view == "back" else 0)))
            if view == "front":
                loc, _ = _cast(bvh, (fx(u), -1.0, z), (0, 1, 0))
            elif view == "back":
                loc, _ = _cast(bvh, (bx(u), 1.0, z), (0, -1, 0))
            else:
                loc, _ = _cast(bvh, (-1.0, sy(u), z), (1, 0, 0))
            if loc is None:
                continue
            th = math.atan2(loc[0], -(loc[1] - AXIS_Y))
            if view == "front":
                w = max(math.cos(th), 0.0) ** 2
            elif view == "back":
                w = max(-math.cos(th), 0.0) ** 2
            else:
                w = max(-math.sin(th), 0.0) ** 2
            samples.append((th, z, max(w, 0.02)))
    A, b, W = [], [], []
    for th, z, w in samples:
        A.append(_basis(th))
        b.append(z)
        W.append(w)
    A, b, W = np.array(A), np.array(b), np.sqrt(np.array(W))
    # light ridge on the higher harmonics keeps it smooth where samples are sparse
    lam = 1e-4
    reg = np.diag([0.0] + [lam * (k // 2 + 1) ** 2 for k in range(2 * BELT_ORDER)])
    coef = np.linalg.solve((A * W[:, None] ** 2).T @ A + reg, (A * W[:, None] ** 2).T @ b)
    res = b - A @ coef
    return coef, samples, float(np.abs(res * (W > 0.5)).max())


def _basis(th):
    row = [1.0]
    for k in range(1, BELT_ORDER + 1):
        row += [math.cos(k * th), math.sin(k * th)]
    return row


def _z_of(coef, th):
    return float(np.dot(coef, _basis(th)))


def belt_mesh(name, bvh, coef, coll, N=240):
    verts, faces = [], []
    for k in range(N):
        th = 2 * math.pi * k / N
        zc = _z_of(coef, th)
        for dz in (BELT_W / 2, -BELT_W / 2):
            loc, nrm = _surface_at(bvh, th, zc + dz)
            if loc is None:
                loc, nrm = _surface_at(bvh, th, zc)
            d = (math.sin(th), -math.cos(th), 0.0)
            verts.append((loc[0] + d[0] * BELT_LIFT, loc[1] + d[1] * BELT_LIFT, zc + dz))
    for k in range(N):
        a, b2 = 2 * k, 2 * ((k + 1) % N)
        faces.append((a, b2, b2 + 1, a + 1))
    ob = bb.make_obj(name, verts, faces, coll, COL["belt"])
    face_out(ob)
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = BELT_T
    mod.offset = 0.0
    return ob


def buckle_mesh(name, bvh, coef, u_front, coll):
    """square ring on the belt at the buckle's front-view column"""
    x = fx(u_front)
    # find theta on the front where the surface point has this x
    best = None
    for k in range(-900, 1):
        th = math.radians(k / 10.0)
        loc, nrm = _surface_at(bvh, th, _z_of(coef, th))
        if loc is None:
            continue
        if best is None or abs(loc[0] - x) < abs(best[1][0] - x):
            best = (th, loc, nrm)
    th, loc, nrm = best
    zc = _z_of(coef, th)
    dz = (_z_of(coef, th + 0.01) - _z_of(coef, th - 0.01))
    # local frame: tangent along the belt, normal outward, up across it
    d = np.array([math.sin(th), -math.cos(th), 0.0])
    t = np.array([math.cos(th), math.sin(th), 0.0]) * 0.02 * 0.5 / 0.01
    tan = np.array([math.cos(th) * 0.02, math.sin(th) * 0.02, dz])
    tan /= np.linalg.norm(tan)
    up = np.cross(d, tan)
    if up[2] < 0:
        up = -up
    c = np.array(loc) + d * (BELT_LIFT + BELT_T + 0.0012)
    h, b2 = BUCKLE_SIZE / 2, BUCKLE_BAR
    verts, faces = [], []
    loops = [(h, h), (h - b2, h - b2)]
    for s0, s1 in loops:
        for sx, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = c + tan * sx * s0 + up * sy_ * s1
            verts.append(tuple(p))
    for i in range(4):
        j = (i + 1) % 4
        faces.append((i, j, 4 + j, 4 + i))
    ob = bb.make_obj(name, verts, faces, coll, COL["buckle"], recalc=False)
    face_out(ob)
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = 0.002
    mod.offset = 0.0
    return ob


def build_belts():
    coll = bb.get_model_coll()
    for name in ("belt_A", "belt_B", "buckle_A", "buckle_B"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    targets = [o for o in (bpy.data.objects.get("skirt"), bpy.data.objects.get("body")) if o is not None]
    bvh = _bvh(targets)
    out = {}
    for k in ("A", "B"):
        coef, samples, err = _fit_belt(bvh, BELT_TRACE[k])
        ob = belt_mesh("belt_" + k, bvh, coef, coll)
        bk = buckle_mesh("buckle_" + k, bvh, coef, BUCKLES[k][0], coll)
        for o in (ob, bk):
            o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
            o.data.update()
        out[k] = dict(n=len(samples), max_err_mm=round(err * 1000, 1),
                      z_front=round(_z_of(coef, 0.0), 3), z_right=round(_z_of(coef, -math.pi / 2), 3),
                      z_left=round(_z_of(coef, math.pi / 2), 3), z_back=round(_z_of(coef, math.pi), 3))
    return out


# ----------------------------------------------------------------------------- skirt (pleated) + lace petticoat
SKIRT_N = 2.0                    # cross-section exponent (as M2)
PLEATS = 22                      # box pleats round the skirt (front view: ~4 cm panels at the hem)
PLEAT_DEPTH = 0.007              # crease depth at the hem
PLEAT_HALF_W = 0.35              # crease half-width, fraction of the pleat period
SKIRT_COLS = PLEATS * 8
SKIRT_TOP_ROW = 258.5
LACE_TOP_ROW = 345.0             # the petticoat starts well inside the skirt
LACE_DROP = {"front": 9.0, "back": 9.0, "side": 12.0}   # lace below the red hem, sheet px
SCALLOP_PERIOD = 0.022           # m along the hem (front view: ~9 px between scallop points)
SCALLOP_DEPTH = 3.0              # px
LACE_INSET = 0.0005              # lace surface (below the skirt's hem) just inside the traced outline
COL.update(skirt=(0.75, 0.12, 0.13, 1), lace=(0.95, 0.95, 0.97, 1))


class Rings:
    def __init__(self, rings):
        r = sorted(rings, key=lambda q: q[0])
        self.z = np.array([q[0] for q in r])
        self.c = [np.array([q[k] for q in r]) for k in (1, 2, 3, 4)]

    def box(self, z):
        return [float(np.interp(z, self.z, a)) for a in self.c]


def _view_blend(tr_front, tr_back, tr_side, x, y, nx, ny):
    """blend a per-column trace (arrays [[u, row]]) of the three views at a
    surface column (x, y) with outward normal (nx, ny)"""
    f = np.interp(x / P + CF, tr_front[:, 0], tr_front[:, 1])
    b = np.interp(-x / P + CB, tr_back[:, 0], tr_back[:, 1])
    s = np.interp(-y / P + CS, tr_side[:, 0], tr_side[:, 1])
    wf, wb, ws = max(-ny, 0.0) ** 2, max(ny, 0.0) ** 2, nx ** 2
    return float((wf * f + wb * b + ws * s) / max(wf + wb + ws, 1e-6))


def skirt_and_lace(d2, d4, coll):
    R = Rings(d2["skirt"]["rings"])
    sk = d4["skirt"]
    hem = {v: np.array(sk[v]["hem"]) for v in sk}
    z_top = zedge(SKIRT_TOP_ROW)
    z_bot_all = min(R.z)
    # per column: parameter t on the cross-section, its hem / lace bottom
    ts = np.linspace(0, 2 * np.pi, SKIRT_COLS, endpoint=False) - np.pi / 2      # start at the front centre
    zh = zedge(355.0)
    x0, x1, y0, y1 = R.box(zh)
    xc, yc, a, b = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (x1 - x0), 0.5 * (y1 - y0)
    col_hem, col_lace, col_theta, col_s = [], [], [], []
    arc = 0.0
    prev = None
    for t in ts:
        c, s = math.cos(t), math.sin(t)
        x, y = xc + a * c, yc + b * s
        nx, ny = c / a, s / b
        nn = math.hypot(nx, ny)
        nx, ny = nx / nn, ny / nn
        h = _view_blend(hem["front"], hem["back"], hem["side"], x, y, nx, ny)
        wf, wb, ws = max(-ny, 0.0) ** 2, max(ny, 0.0) ** 2, nx ** 2
        drop = (wf * LACE_DROP["front"] + wb * LACE_DROP["back"] + ws * LACE_DROP["side"]) / max(wf + wb + ws, 1e-6)
        if prev is not None:
            arc += math.hypot(x - prev[0], y - prev[1])
        prev = (x, y)
        col_hem.append(h)
        col_lace.append(h + drop)
        col_theta.append(math.atan2(x - xc, -(y - yc)))
        col_s.append(arc)

    def ring_point(t, z, inset=0.0, pleat=True):
        x0, x1, y0, y1 = R.box(z)
        xc_, yc_, a_, b_ = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (x1 - x0), 0.5 * (y1 - y0)
        c, s = math.cos(t), math.sin(t)
        x, y = xc_ + a_ * c, yc_ + b_ * s
        nx, ny = c / a_, s / b_
        nn = math.hypot(nx, ny)
        nx, ny = nx / nn, ny / nn
        off = -inset
        if pleat:
            th = math.atan2(x - xc_, -(y - yc_))
            ph = (th / (2 * math.pi) * PLEATS) % 1.0           # 0 at the front centre = middle of a panel
            dist = abs(ph - 0.5)                                # creases at ph = 0.5 (between panels)
            p = max(0.0, 1.0 - dist / PLEAT_HALF_W) if dist < PLEAT_HALF_W else 0.0
            fz = min(max((z_top - z) / max(z_top - zedge(370.0), 1e-6), 0.0), 1.2)
            off -= PLEAT_DEPTH * p * fz ** 1.4
        return (x + nx * off, y + ny * off)

    def lace_inset(j, z):
        """inside the skirt (above its hem, deeper than the pleat creases),
        easing out to LACE_INSET over 3 px below the hem"""
        zh = zedge(col_hem[j])
        fz = min(max((z_top - z) / max(z_top - zedge(370.0), 1e-6), 0.0), 1.2)
        deep = PLEAT_DEPTH * fz ** 1.4 + 0.002
        w = min(max((z - (zh - 3 * P)) / (3 * P), 0.0), 1.0)
        return LACE_INSET + deep * w * w * (3 - 2 * w)

    def column_mesh(name, z_from, ends, inset, pleat, scallop):
        verts, faces, idx = [], [], []
        levels = np.arange(z_from, zedge(max(ends) + SCALLOP_DEPTH) - 1e-6, -P)
        for j, t in enumerate(ts):
            zb = zedge(ends[j])
            if scallop:
                ph = (col_s[j] / SCALLOP_PERIOD) % 1.0
                tooth = abs(math.sin(math.pi * ph)) ** 0.6
                zb = zedge(ends[j] - SCALLOP_DEPTH * (1.0 - tooth))
            col = []
            for z in levels:
                if z <= zb + 0.3 * P:
                    break
                ins = inset if inset is not None else lace_inset(j, float(z))
                x, y = ring_point(t, float(z), ins, pleat)
                col.append(len(verts))
                verts.append((x, y, float(z)))
            ins = inset if inset is not None else lace_inset(j, zb)
            x, y = ring_point(t, zb, ins, pleat)
            col.append(len(verts))
            verts.append((x, y, zb))
            idx.append(col)
        n = len(ts)
        for j in range(n):
            a_, b_ = idx[j], idx[(j + 1) % n]
            m = min(len(a_), len(b_))
            for k in range(m - 1):
                faces.append((a_[k], b_[k], b_[k + 1], a_[k + 1]))
            if len(a_) > len(b_):
                for k in range(m - 1, len(a_) - 1):
                    faces.append((b_[-1], a_[k + 1], a_[k]))
            elif len(b_) > len(a_):
                for k in range(m - 1, len(b_) - 1):
                    faces.append((a_[-1], b_[k], b_[k + 1]))
        return bb.make_obj(name, verts, faces, coll, COL["skirt" if name == "skirt" else "lace"])

    skirt = column_mesh("skirt", z_top, col_hem, 0.0, True, False)
    face_out(skirt, axis=(0.0, 0.003))
    mod = skirt.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = 0.002
    mod.offset = -1.0
    lace = column_mesh("lace", zedge(LACE_TOP_ROW), col_lace, None, False, True)
    face_out(lace, axis=(0.0, 0.003))
    mod = lace.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = 0.0015
    mod.offset = -1.0
    return skirt, lace


def build_skirt():
    d2, d4 = load()
    coll = bb.get_model_coll()
    for name in ("skirt", "lace"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    sk, la = skirt_and_lace(d2, d4, coll)
    for o in (sk, la):
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        o.data.update()
    return {o.name: len(o.data.vertices) for o in (sk, la)}


# ----------------------------------------------------------------------------- hands (fingerless gloves)
# measured on the front view (her right hand; the left is its mirror, the back
# view agrees) and the side view's end-on hand inside the cuff ring
WRIST_U = 79.0                   # front col where the glove starts (wrist)
KNUCKLE_U = 40.0                 # palm ends, fingers start
HAND_YC = 0.032                  # hand centre line in depth (side view: cols 100-130 -> centre 115)
PALM_HALF_Y = (0.025, 0.036)     # half-width across the palm at the wrist / knuckles (side view: 7 cm hand)
FINGERS = [  # (offset in y from HAND_YC, tip short of the middle finger's (m), radius) index .. pinky
    (-0.026, 0.006, 0.0078), (-0.0085, 0.0, 0.0082), (0.0085, 0.008, 0.0079), (0.0255, 0.022, 0.0070)]
FINGER_ROW = 167.0               # finger stack centre (front view rows 162-172)
FINGER_ROLL = 0.15               # thumb side up: dz = -dy * roll (the drawn fingers fan over ~3 px)
THUMB = dict(base=(53.0, -0.024, 169.0), tip=(32.0, -0.033, 176.0), r=0.0085)   # (front col, y offset, row)
# M7: rings along each finger / the thumb, so they bend at three joints
# (M4 had 3 rings: they could only pivot at the knuckle). Same outline: the
# rings are spread along the same control points
FINGER_SEG = 12
THUMB_SEG = 8


def _spread(ctrl, n):
    """n + 1 rings, evenly spaced in arc length along the polyline ctrl
    ([[x, y, z, r], ...]), linear in position and radius"""
    C = np.array(ctrl, float)
    seg = np.linalg.norm(np.diff(C[:, :3], axis=0), axis=1)
    cum = np.r_[0.0, np.cumsum(seg)]
    out = []
    for t in np.linspace(0.0, cum[-1], n + 1):
        k = min(int(np.searchsorted(cum, t, side="right")) - 1, len(seg) - 1)
        f = (t - cum[k]) / max(seg[k], 1e-12)
        out.append([float(v) for v in C[k] + (C[k + 1] - C[k]) * f])
    return out
COL.update(hand=(0.08, 0.08, 0.09, 1))


def _arm_cut(arm, x_wrist):
    keep = [k for k, x in enumerate(arm["x"]) if abs(x) <= x_wrist]
    return {k: [arm[k][i] for i in keep] for k in ("x", "ztop", "zbot")}


def hand_mesh(name, arm, side, coll):
    """palm (rounded box loft wrist -> knuckles, height from the front view's
    outline), four fingers and the thumb as capped tubes"""
    import bmesh
    sg = -1.0 if side == "R" else 1.0
    xs = np.array(arm["x"])
    zt, zbm = np.array(arm["ztop"]), np.array(arm["zbot"])
    order = np.argsort(np.abs(xs))
    ax, azt, azb = np.abs(xs)[order], zt[order], zbm[order]
    xw, xk = abs(fx(WRIST_U)), abs(fx(KNUCKLE_U))
    verts, faces = [], []
    NR = 20
    levels = np.linspace(xw - 0.004, xk, 14)
    for i, X in enumerate(levels):
        t = (X - xw) / (xk - xw)
        top = float(np.interp(X, ax, azt))
        bot = float(np.interp(X, ax, azb))
        if X > abs(fx(46.0)):                      # thumb region below: keep the palm's own bottom
            bot = max(bot, top - 0.030)
        zc, hz = 0.5 * (top + bot), 0.5 * (top - bot)
        hy = PALM_HALF_Y[0] + (PALM_HALF_Y[1] - PALM_HALF_Y[0]) * min(max(t, 0.0), 1.0)
        for k in range(NR):
            a = 2 * math.pi * k / NR
            c, s = math.cos(a), math.sin(a)
            # superellipse (n = 3) in y-z: flat-ish palm
            yy = HAND_YC + hy * math.copysign(abs(c) ** (2 / 3.0), c)
            zz = zc + hz * math.copysign(abs(s) ** (2 / 3.0), s)
            verts.append((sg * X, yy, zz))
    R = len(levels)
    for i in range(R - 1):
        for k in range(NR):
            a, b = i * NR + k, i * NR + (k + 1) % NR
            faces.append((a, b, b + NR, a + NR))
    faces.append(tuple(range(NR))[::-1])
    faces.append(tuple(range((R - 1) * NR, R * NR)))
    palm = bb.make_obj(name + "_palm", verts, faces, coll, COL["hand"])
    parts = [palm]
    x_tip = float(np.abs(xs).max())             # middle fingertip: the arm profile's end (front/back blend)
    for j, (dy, short, r) in enumerate(FINGERS):
        zf = zedge(FINGER_ROW + 0.5) - dy * FINGER_ROLL
        x0 = xk - 0.012
        x1 = x_tip - short - r * 0.6
        # rounded tip: the last ring still half the finger's radius, so the
        # outline reaches x_tip (a pointed tip lost ~1.5 px of the reach both views agree on)
        body = [[sg * x0, HAND_YC + dy, zf, r * 1.05], [sg * (0.5 * (x0 + x1)), HAND_YC + dy, zf - 0.001, r],
                [sg * x1, HAND_YC + dy, zf - 0.002, r * 0.92]]
        pts = _spread(body, FINGER_SEG) + [[sg * (x1 + r * 0.4), HAND_YC + dy, zf - 0.002, r * 0.78],
                                           [sg * (x1 + r * 0.6), HAND_YC + dy, zf - 0.002, r * 0.5]]
        parts.append(bb.tube(name + "_f%d" % j, pts, coll, COL["hand"], N=12))
    b, t_ = THUMB["base"], THUMB["tip"]
    p0 = [sg * abs(fx(b[0])), HAND_YC + b[1], zedge(b[2] + 0.5)]
    p1 = [sg * abs(fx(t_[0])), HAND_YC + t_[1], zedge(t_[2] + 0.5)]
    r = THUMB["r"]
    d = np.array(p1) - np.array(p0)
    d /= np.linalg.norm(d)
    body = [p0 + [r * 1.1], list(np.array(p0) + (np.array(p1) - np.array(p0)) * 0.5) + [r],
            list(np.array(p1) - d * r * 0.4) + [r * 0.85]]
    pts = _spread(body, THUMB_SEG) + [list(np.array(p1)) + [r * 0.2]]
    parts.append(bb.tube(name + "_thumb", pts, coll, COL["hand"], N=12))
    return join_objects(parts, name, coll, COL["hand"])


def join_objects(parts, name, coll, color):
    """merge mesh objects (world space) into one new object, removing the parts"""
    verts, faces = [], []
    for o in parts:
        mw = o.matrix_world
        base = len(verts)
        verts += [tuple(mw @ v.co) for v in o.data.vertices]
        faces += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    for o in parts:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    ob = bb.make_obj(name, verts, faces, coll, color)
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    ob.data.update()
    return ob


def build_hands():
    d2, _ = load()
    coll = bb.get_model_coll()
    out = {}
    for side in ("R", "L"):
        for name in ("arm_" + side, "hand_" + side):
            ob = bpy.data.objects.get(name)
            if ob is not None:
                me = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if me is not None and me.users == 0:
                    bpy.data.meshes.remove(me)
        arm = d2["arms"][side]
        xw = abs(fx(WRIST_U))
        cut = _arm_cut(arm, xw)
        ob = bb.arm_mesh("arm_" + side, cut, d2["arm_axis_y"], coll, bb.COLORS["arm"])
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
        ob.data.update()
        h = hand_mesh("hand_" + side, arm, side, coll)
        out["arm_" + side] = len(ob.data.vertices)
        out["hand_" + side] = len(h.data.vertices)
    return out


# ----------------------------------------------------------------------------- tachi
# The M2 centre lines (traced from front/back: hilt end x +15 cm z 1.02 m,
# sheath tip x +24 cm z 0.66 m; tilt bounded by the side view) are kept; the
# parts and their proportions come from the katana detail panel (192 x 470 px):
# end cap ~8 % of the hilt, guard plate about 2.4 x the grip's width, the
# sheath's mouth band and tip cap red + gold, blade = sheath length less 2 cm.
COL.update(gold=(0.85, 0.65, 0.2, 1), grip=(0.65, 0.12, 0.12, 1), saya=(0.95, 0.95, 0.95, 1),
           blade=(0.85, 0.87, 0.9, 1))
GRIP_R = 0.0115                  # front view: the wrapped grip is 10 px wide
CAP_R = 0.013                    # end cap, 12 px
TSUBA_R = (0.019, 0.015)         # guard plate (front view ~14-16 px across at an angle; panel: 2.4 x the grip)


def _polyline_at(P_, s):
    """point and tangent at arc-length fraction s of a polyline (N, 3)"""
    seg = np.linalg.norm(np.diff(P_, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seg)]
    L = cum[-1]
    t = s * L
    k = min(int(np.searchsorted(cum, t, side="right")) - 1, len(seg) - 1)
    f = (t - cum[k]) / max(seg[k], 1e-9)
    p = P_[k] + (P_[k + 1] - P_[k]) * f
    tan = (P_[k + 1] - P_[k]) / max(seg[k], 1e-9)
    return p, tan, L


def _tube_along(name, P_, s0, s1, radius_fn, coll, color, n=16, steps=12, cap=True):
    pts = []
    for i in range(steps + 1):
        s = s0 + (s1 - s0) * i / steps
        p, _, _ = _polyline_at(P_, s)
        pts.append([float(p[0]), float(p[1]), float(p[2]), float(radius_fn(s))])
    return bb.tube(name, pts, coll, color, N=n, cap=cap)


def _disc(name, centre, axis, rx, ry, thick, coll, color, n=24):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    _, u, v = bb.frame(axis)
    verts, faces = [], []
    for side in (-0.5, 0.5):
        for k in range(n):
            a = 2 * math.pi * k / n
            p = np.asarray(centre) + axis * thick * side + u * rx * math.cos(a) + v * ry * math.sin(a)
            verts.append(tuple(p))
    for k in range(n):
        j = (k + 1) % n
        faces.append((k, j, n + j, n + k))
    faces.append(tuple(range(n))[::-1])
    faces.append(tuple(range(n, 2 * n)))
    return bb.make_obj(name, verts, faces, coll, color)


def build_sword():
    d2, _ = load()
    coll = bb.get_model_coll()
    names = ("hilt", "sheath", "kashira", "tsuka", "tsuba", "saya", "saya_mouth", "saya_tip", "blade")
    for name in names:
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    sw = d2["sword"]
    H = np.array(sw["hilt"])          # cap end -> guard
    S_ = np.array(sw["sheath"])       # mouth -> tip
    hr = H[:, 3]
    sr = S_[:, 3]
    Hp, Sp = H[:, :3], S_[:, :3]
    grip_r = GRIP_R
    saya_r = float(np.median(sr[3:-6]))
    out = {}
    objs = [
        _tube_along("kashira", Hp, 0.0, 0.10, lambda s: CAP_R, coll, COL["gold"], steps=3),
        _tube_along("tsuka", Hp, 0.08, 0.95, lambda s: grip_r, coll, COL["grip"], steps=10),
    ]
    p_g, t_g, _ = _polyline_at(Hp, 0.985)
    objs.append(_disc("tsuba", p_g, t_g, TSUBA_R[0], TSUBA_R[1], 0.006, coll, COL["gold"]))
    # sheath: mouth band (red + gold), body, tip cap
    _, _, Ls = _polyline_at(Sp, 0.0)
    r_of = lambda s: float(np.interp(s, np.linspace(0, 1, len(sr)), np.minimum(sr, saya_r * 1.05)))
    objs.append(_tube_along("saya_mouth", Sp, 0.0, 0.07, lambda s: r_of(s) * 1.06, coll, COL["grip"], steps=3))
    objs.append(_tube_along("saya", Sp, 0.06, 0.88, r_of, coll, COL["saya"], steps=24))
    objs.append(_tube_along("saya_tip", Sp, 0.87, 1.0, lambda s: r_of(s) * 1.05, coll, COL["grip"], steps=6))
    # blade: hidden in the sheath, flat (2.6 x 0.6 cm), following its curve
    pts = []
    for i in range(25):
        s = 0.02 + 0.9 * i / 24
        p, _, _ = _polyline_at(Sp, s)
        pts.append(p)
    verts, faces = [], []
    w, th = 0.011, 0.003
    for i, p in enumerate(pts):
        tan = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        _, u, v = bb.frame(tan)
        taper = 1.0 if i < len(pts) - 3 else (len(pts) - 1 - i) / 3.0 + 0.05
        for a, b in ((w * taper, th), (-w * taper, th), (-w * taper, -th), (w * taper, -th)):
            verts.append(tuple(p + u * a + v * b))
    for i in range(len(pts) - 1):
        for k in range(4):
            j = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + j, (i + 1) * 4 + j, (i + 1) * 4 + k))
    faces.append((0, 1, 2, 3)[::-1])
    faces.append(tuple(range((len(pts) - 1) * 4, len(pts) * 4)))
    blade = bb.make_obj("blade", verts, faces, coll, COL["blade"])
    blade.hide_render = True          # inside the sheath; the rig (M7) draws it
    objs.append(blade)
    for o in objs:
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        o.data.update()
        out[o.name] = len(o.data.vertices)
    out["grip_r"] = round(grip_r, 4)
    out["saya_r"] = round(saya_r, 4)
    out["sheath_len"] = round(Ls, 3)
    return out


# ----------------------------------------------------------------------------- ankle bows
# The M2 bows are lofts of per-row rings: their front-view outline is the
# bow's outer envelope, a rounded block (it showed once the colours were
# flattened in M5). The sheet's bow has two loops and a knot, with notches
# above and below the knot. The loft is cut to the bow's drawn front-view
# outline (red, holes filled) by a boolean intersect with that outline
# extruded front to back, so the side and back keep the loft's traced depth.
BOW_BOX = {"R": (176, 624, 224, 664), "L": (294, 624, 344, 664)}    # front-crop boxes (u0, v0, u1, v1)
BOW_BOX_BACK = {"R": (305, 624, 357, 664), "L": (190, 624, 244, 664)}   # back crop: the loops either side of the ankle
BOW_PRISM_Y = (-0.25, 0.35)


def _fill_holes(m):
    """fill background pockets enclosed by a mask (4-connected flood from the border)"""
    H, W = m.shape
    bg = ~m
    reach = np.zeros_like(m)
    stack = [(y, x) for y in range(H) for x in (0, W - 1) if bg[y, x]]
    stack += [(y, x) for x in range(W) for y in (0, H - 1) if bg[y, x]]
    for y, x in stack:
        reach[y, x] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and bg[yy, xx] and not reach[yy, xx]:
                reach[yy, xx] = True
                stack.append((yy, xx))
    return m | (bg & ~reach)


def _prism(name, uv, quads, y0, y1, coll):
    """the outline grid (crop coords) extruded from y0 to y1: a closed solid"""
    n = len(uv)
    verts = [(fx(u), y0, zedge(v)) for u, v in uv] + [(fx(u), y1, zedge(v)) for u, v in uv]
    faces = [tuple(q) for q in quads] + [tuple(n + i for i in q[::-1]) for q in quads]
    use = {}
    for q in quads:
        for a, b in zip(q, q[1:] + q[:1]):
            use[(a, b)] = use.get((a, b), 0) + 1
    for (a, b) in use:
        if (b, a) not in use:                             # boundary edge: wall
            faces.append((b, a, n + a, n + b))
    return bb.make_obj(name, verts, faces, coll, COL.get("bow", (0.8, 0.1, 0.1, 1)))


def build_bows():
    import decals as dc
    importlib.reload(dc)
    d2, _ = load()
    coll = bb.get_model_coll()
    out = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for side in ("R", "L"):
        name = "bow_" + side
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
        bow = bb.loft(name, d2["bows"][side], bb.EXP["bow"], coll, bb.COLORS["bow"])
        u0, v0, u1, v1 = BOW_BOX[side]
        soft = dc.mask("front", "red", (u0, v0, u1, v1), grow=1, close=2)
        m = dc.largest(soft > 0.5, 1)
        # plus the loops the back view shows beside the ankle (mirrored into front coords)
        bsoft = dc.mask("back", "red", BOW_BOX_BACK[side], grow=1, close=1)
        bm = dc.largest(bsoft > 0.5, 2)
        cb, cf = cfg.VIEWS["back"]["centre_u"], cfg.VIEWS["front"]["centre_u"]
        dv = int(round(cfg.VIEWS["back"]["sole_v"] - cfg.VIEWS["front"]["sole_v"]))
        for v in range(v0, v1):
            for u in range(u0, u1):
                ub = int(math.floor(cb + cf - (u + 0.5)))       # x mirrored: u_b + .5 = cb - (u + .5 - cf)
                vb = v + dv
                if 0 <= vb < bm.shape[0] and 0 <= ub < bm.shape[1] and bm[vb, ub]:
                    m[v, u] = True
        sub = _fill_holes(m[v0 - 1:v1 + 1, u0 - 1:u1 + 1])
        m[v0 - 1:v1 + 1, u0 - 1:u1 + 1] = sub
        soft = dc.box_blur(m.astype(np.float32), 1)
        uv, quads = dc.grid(soft, (u0, v0, u1, v1), step=0.5)
        prism = _prism(name + "_cut", uv, quads, BOW_PRISM_Y[0], BOW_PRISM_Y[1], coll)
        mod = bow.modifiers.new("cut", "BOOLEAN")
        mod.operation = "INTERSECT"
        mod.solver = "EXACT"
        mod.object = prism
        dg.update()
        new_me = bpy.data.meshes.new_from_object(bow.evaluated_get(dg))
        bow.modifiers.remove(mod)
        old = bow.data
        bow.data = new_me
        new_me.name = name
        if old.users == 0:
            bpy.data.meshes.remove(old)
        pme = prism.data
        bpy.data.objects.remove(prism, do_unlink=True)
        if pme.users == 0:
            bpy.data.meshes.remove(pme)
        bow.data.polygons.foreach_set("use_smooth", [True] * len(bow.data.polygons))
        bow.data.update()
        out[name] = dict(verts=len(bow.data.vertices), outline_px=int(m[v0:v1, u0:u1].sum()))
    return out
