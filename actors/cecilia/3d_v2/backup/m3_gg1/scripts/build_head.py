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

Hair cross-section (v2): a superellipse through the traced front/back/side
extents, except at the face rows, where the side view shows the face between
the bangs and the side locks:
  - outside the face's width, no hair is further forward than the side
    lock's front edge (traced from the side view, lock table);
  - across the face, the bangs keep their traced front in the middle and
    recede onto the forehead/temples at the face's edges (2 mm clearance),
    so from the side the temple and eye stay visible behind them.
The hem joins neighbouring columns diagonally (pointed tips) when their ends
are within FAN_ROWS rows of each other; bigger jumps stay vertical edges
(separate locks, the face opening).
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
N_FACE_TOP = 4.5        # face front half exponent down to the cheeks: flat anime face front
NOSE_HW = 0.0065        # half-width of the nose ridge at its base
N_FACE_CHIN = 2.0       # ... easing to an ellipse at the chin
FACE_N_ROWS = (120, 141)  # front rows over which the exponent eases
FAN_ROWS_BANGS = 14     # ... over the face (bangs): pointed tips, the silhouette isn't affected
FAN_ROWS = 4            # hem: join neighbouring column ends diagonally up to this many rows apart
VISOR_U0 = 0.55         # bangs: traced front kept for |x| < VISOR_U0 * face half-width
VISOR_GAP = 0.002       # bangs: clearance in front of the face at the face's edge
EAR_X = 0.074           # ears sit on the skull's side at |x| = EAR_X
EAR_TUCK_X = 0.070      # hair tucked behind the ear: the shell dips to |x| = EAR_TUCK_X there
EAR_FEATHER = 7.0       # px of smooth falloff around the ear's traced extent (above, below, behind)
EAR_FEATHER_FRONT = 2.0 # ... and in front of it
VIEW_ROW = 96           # front row where a column's facing picks the view its end is looked up in
LOOKUP_TOL = 2          # image columns of tolerance for a column's secondary views
FRONT_NY = 0.35         # ... the front view owns a column if its normal's -y component exceeds this,
BACK_NY = 0.5           # ... the back view if its +y component exceeds this, else the side view
VIEW_T = 1.01           # ... other views also bound it if its normal's component towards them exceeds
                        # this (off: tested 0.35-0.75, it trades model-only px for ref-only px)
MIN_BOTTOM_ROW = 70     # no hair column ends above this front row (top of the head is all hair)
LOCK_RAMP = 14          # rows over which the face-row shaping eases in (= head_profiles.LOCK_RAMP)
N_COLS = 160            # hair columns around the head
HAIR_THICK = 0.003
REMOVE = ("head", "hair_tips_blockout", "ahoge")
COL = dict(face=(0.98, 0.86, 0.8, 1), hair=(0.12, 0.1, 0.14, 1), band=(0.8, 0.15, 0.15, 1),
           clip=(0.3, 0.6, 0.65, 1))


def sole_z(view, row):
    return (cfg.VIEWS[view]["sole_v"] - row) * P


def face_n(z):
    """face front-half exponent at height z: flat down to the cheeks, rounder at the chin"""
    r = sole_z_inv(z)
    t = min(max((r - FACE_N_ROWS[0]) / float(FACE_N_ROWS[1] - FACE_N_ROWS[0]), 0.0), 1.0)
    return N_FACE_TOP + (N_FACE_CHIN - N_FACE_TOP) * t


def sole_z_inv(z, view="front"):
    """front-crop row (continuous v) at height z"""
    return cfg.VIEWS[view]["sole_v"] - z / P


def se_arr(t, n):
    c, s = np.cos(t), np.sin(t)
    return np.sign(c) * np.abs(c) ** (2.0 / n), np.sign(s) * np.abs(s) ** (2.0 / n)


class Rings:
    """hair cross-sections: interpolate [z, x0, x1, y0, y1] rings at any z, with
    the face-row shaping (side-lock cut + bangs receding onto the face)"""

    def __init__(self, rings, lock=None, face=None, ear=None):
        self.ear = ear
        r = sorted(rings, key=lambda q: q[0])
        self.z = np.array([q[0] for q in r])
        self.c = [np.array([q[k] for q in r]) for k in (1, 2, 3, 4)]
        self.lock = None
        if lock:
            lk = sorted(lock, key=lambda q: q[0])
            self.lock = (np.array([q[0] for q in lk]), np.array([q[1] for q in lk]))
            top = sorted(lock, key=lambda q: -q[0])
            self.ramp = (top[0][0], top[min(LOCK_RAMP, len(top) - 1)][0])   # z where shaping eases in
        self.face = None
        if face:
            fr = sorted(face, key=lambda q: q[0])
            self.face = [np.array([q[k] for q in fr]) for k in range(5)]   # z, x0, x1, yf, ys

    def box(self, z):
        return [float(np.interp(z, self.z, c)) for c in self.c]

    def face_at(self, z):
        """(xc, hw, yf, ys, n) of the face at z (held at the table's ends)"""
        fz, x0, x1, yf, ys = self.face
        g = lambda a: float(np.interp(z, fz, a))
        return 0.5 * (g(x0) + g(x1)), 0.5 * (g(x1) - g(x0)), g(yf), g(ys), face_n(z)

    def shaped(self, z):
        """face-row shaping applies from the lock table's top all the way down
        (below the table the last lock front and the chin are held)"""
        return self.lock is not None and self.face is not None and z <= self.lock[0].max() + 1e-9

    def points(self, z, ts, n=N_HAIR):
        """ring points (x, y arrays) for column angles ts at height z"""
        x0, x1, y0, y1 = self.box(z)
        xc, a, yc, b = 0.5 * (x0 + x1), 0.5 * (x1 - x0), 0.5 * (y0 + y1), 0.5 * (y1 - y0)
        cx, sy = se_arr(np.asarray(ts, float), n)
        x = xc + a * cx
        y = yc + b * sy
        if self.shaped(z):
            y_lock = float(np.interp(z, *self.lock))
            fxc, fhw, fyf, fys, fn = self.face_at(z)
            u = np.abs(x - fxc) / max(fhw, 1e-6)
            front = sy < 0
            y_out = np.maximum(y, y_lock)                 # outside the face: behind the lock front
            out = front & (u >= 1.0)
            inn = front & (u < 1.0)
            uu = np.minimum(u[inn], 1.0)
            y_face = fys + (fyf - fys) * (1.0 - uu ** fn) ** (1.0 / fn)
            yi = y[inn]
            w = min(max((self.ramp[0] - z) / max(self.ramp[0] - self.ramp[1], 1e-9), 0.0), 1.0)
            # bangs recede onto the face (eased in over the ramp rows), never behind the lock plane
            target = np.minimum(yi + (y_face - VISOR_GAP - yi) * w, y_out[inn])
            t = np.clip((uu - VISOR_U0) / (1.0 - VISOR_U0), 0.0, 1.0)
            s = t * t * (3.0 - 2.0 * t)
            y[inn] = np.maximum(yi, yi + (target - yi) * s)
            y[out] = y_out[out]
        if self.ear:
            x = self.ear_dent(z, x, y)
        return x, y

    def ear_dent(self, z, x, y):
        """the side view shows the ear with hair around it: there the hair is
        tucked behind the ear, so the shell dips in to just inside the ear
        (smooth bump over the ear's traced extent in the side view)"""
        e = self.ear
        r = sole_z_inv(z)
        cs = cfg.VIEWS["side"]["centre_u"]
        su = cs - y / P                                           # side-view column of each point
        def bump(v, lo, hi, f_lo, f_hi):
            a = np.clip((v - (lo - f_lo)) / f_lo, 0, 1)
            b = np.clip(((hi + f_hi) - v) / f_hi, 0, 1)
            a, b = a * a * (3 - 2 * a), b * b * (3 - 2 * b)
            return np.minimum(a, b)
        wz = float(bump(np.array([r]), e["r0"], e["r1"], EAR_FEATHER, EAR_FEATHER)[0])
        if wz <= 0:
            return x
        # towards the face the pocket wall is steep: the hair's widest point (seen
        # in the front/back views) lies just in front of the ear and must stay
        w = wz * bump(su, e["u0"], e["u1"], EAR_FEATHER, EAR_FEATHER_FRONT)
        ax = np.abs(x)
        target = np.minimum(ax, EAR_TUCK_X)
        return np.sign(x) * (ax + (target - ax) * w)

    def point(self, z, t, n=N_HAIR):
        x, y = self.points(z, [t], n)
        return float(x[0]), float(y[0])

    def front_y(self, z, x, n=N_HAIR):
        """y of the (unshaped) shell's front surface at (x, z)"""
        x0, x1, y0, y1 = self.box(z)
        xc, a, yc, b = 0.5 * (x0 + x1), 0.5 * (x1 - x0), 0.5 * (y0 + y1), 0.5 * (y1 - y0)
        u = min(abs(x - xc) / max(a, 1e-6), 0.999)
        return yc - b * (1.0 - u ** n) ** (1.0 / n)


def ring_normals(x, y):
    """outward normals of a closed counter-clockwise polygon (central differences)"""
    tx = np.roll(x, -1) - np.roll(x, 1)
    ty = np.roll(y, -1) - np.roll(y, 1)
    L = np.maximum(np.hypot(tx, ty), 1e-9)
    return ty / L, -tx / L


# ----------------------------------------------------------------------------- hair
def lookup_row(view, x, y, lower, tol=0):
    """last image row of the first hair run (from the top) at the point's
    projection in a view, the most permissive within +-tol image columns
    (the front/back blend puts edges 1-2 px off either drawing); -1 where
    there is no hair"""
    lf, lb, ls = lower
    if view == "front":
        u, arr = int(math.floor(x / P + cfg.VIEWS["front"]["centre_u"])), lf
    elif view == "back":
        u, arr = int(math.floor(cfg.VIEWS["back"]["centre_u"] - x / P)), lb
    else:
        u, arr = int(math.floor(cfg.VIEWS["side"]["centre_u"] - y / P)), ls
    lo, hi = max(u - tol, 0), min(u + tol + 1, len(arr))
    return int(max(arr[lo:hi])) if lo < hi else -1


def bangs_mask(R, ts):
    """columns in front of the face (within its width at VIEW_ROW): the bangs"""
    zv = sole_z("front", VIEW_ROW)
    xr, _ = R.points(zv, ts)
    fxc, fhw = R.face_at(zv)[:2]
    return (np.sin(ts) < 0) & (np.abs(xr - fxc) < fhw)


def face_y(R, x, z):
    """y of the face's front surface at (x, z) (clamped to the face's width)"""
    fxc, fhw, fyf, fys, fn = R.face_at(z)
    u = min(abs(x - fxc) / max(fhw, 1e-6), 0.999)
    return fys + (fyf - fys) * (1.0 - u ** fn) ** (1.0 / fn)


def column_bottoms(R, lower, levels, ts):
    """z where each column's hair ends: walking down the column level by
    level, it continues while its projection is still inside the drawing's
    first hair run from the top in the view that owns it and in any other
    view that sees it well (corner columns: both drawings bound the hem
    there). The column follows its own position as the hem curls in. Views
    come from the normal at the eye-top row (VIEW_ROW): the front view owns
    the bangs (columns in front of the face: it frames the face and draws
    their tips) and anything facing it noticeably (FRONT_NY), else the back
    or side view by the larger normal component; other views join when the
    normal's component towards them exceeds VIEW_T."""
    lw = tuple(np.array(lower[v]) for v in ("front", "back", "side"))
    zv = sole_z("front", VIEW_ROW)
    xr, yr = R.points(zv, ts)
    nx, ny = ring_normals(xr, yr)
    bangs = bangs_mask(R, ts)
    # columns moved back onto the side locks' front plane face the front
    # camera whatever the ring's normal says at the plane's ends
    x0r, x1r, y0r, y1r = R.box(zv)
    _, sy = se_arr(ts, N_HAIR)
    y_plain = 0.5 * (y0r + y1r) + 0.5 * (y1r - y0r) * sy
    on_plane = (sy < 0) & (yr > y_plain + 0.002) & ~bangs
    views = []
    for j in range(len(ts)):
        if bangs[j] or on_plane[j]:
            vs = ["front"]
        else:
            comp = {"front": -ny[j], "back": ny[j], "side": abs(nx[j])}
            main = "front" if -ny[j] > FRONT_NY else ("back" if ny[j] > BACK_NY else "side")
            vs = [main] + [v for v in ("front", "back", "side") if v != main and comp[v] > VIEW_T]
        views.append(vs)
    k_min = int(np.searchsorted(-levels, -sole_z("front", MIN_BOTTOM_ROW)))   # hairline safety
    rings = [R.points(float(z), ts) for z in levels]
    out = []
    for j in range(len(ts)):
        z_end = float(levels[-1])
        for k, z in enumerate(levels):
            x, y = rings[k]
            ends = []
            for n_v, view in enumerate(views[j]):
                row = lookup_row(view, x[j], y[j], lw, 0 if n_v == 0 else LOOKUP_TOL)
                v = cfg.VIEWS[view]["sole_v"] - z / P             # image row coordinate of this level
                if row < 0 or v > row + 1.0:                      # below the drawn hair's end here
                    ends.append(sole_z(view, row + 1) if row >= 0 else float(levels[k - 1]))
            if ends:
                if k <= k_min:
                    continue
                z_end = max(min(max(ends), float(levels[k - 1])), float(z))
                break
        out.append(z_end)
    return out, ["".join(v[0] for v in vs) for vs in views]


def hair_shell(d, coll):
    R = Rings(d["hair_rings"], d.get("lock"), d["face"]["rings"], d.get("ear"))
    z_top = float(R.z.max())
    z_min = float(R.z.min())
    ts = 2 * math.pi * np.arange(N_COLS) / N_COLS
    # common height levels, one per pixel row; each column ends exactly at its bottom
    levels = np.arange(z_top, z_min - 1e-6, -P)
    bottoms, who = column_bottoms(R, d["lower"], levels, ts)
    ring_cache = {}

    def ring(k):
        if k not in ring_cache:
            ring_cache[k] = R.points(float(levels[k]), ts)
        return ring_cache[k]
    verts, faces, idx = [], [], []
    top_id = 0
    x0, x1, y0, y1 = R.box(z_top)
    verts.append((0.5 * (x0 + x1), 0.5 * (y0 + y1), z_top + 0.4 * P))
    for j in range(N_COLS):
        col = []
        zb = bottoms[j]
        k = 0
        while k < len(levels) and levels[k] > zb + 0.3 * P:
            x, y = ring(k)
            col.append(len(verts))
            verts.append((float(x[j]), float(y[j]), float(levels[k])))
            k += 1
        xb, yb = R.points(zb, ts)
        col.append(len(verts))
        verts.append((float(xb[j]), float(yb[j]), float(zb)))
        idx.append(col)
    bangs = bangs_mask(R, ts)
    z_shape = float(R.lock[0].max()) + 1e-6 if R.lock is not None else -1.0
    bang_faces = []
    for j in range(N_COLS):
        jn = (j + 1) % N_COLS
        a, b = idx[j], idx[jn]
        both = bool(bangs[j] and bangs[jn])
        fan_max = (FAN_ROWS_BANGS if both else FAN_ROWS) * P
        strip = [(top_id, a[0], b[0])[::-1]]
        m = min(len(a), len(b))
        for k in range(m - 1):
            strip.append((a[k], a[k + 1], b[k + 1], b[k])[::-1])
        if len(a) != len(b) and abs(bottoms[j] - bottoms[jn]) <= fan_max:
            if len(a) > len(b):
                for i in range(m - 1, len(a) - 1):
                    strip.append((b[-1], a[i + 1], a[i]))
            else:
                for i in range(m - 1, len(b) - 1):
                    strip.append((b[i], b[i + 1], a[-1]))
        for f in strip:
            if both and all(verts[i][2] <= z_shape for i in f):
                bang_faces.append(f)                      # the bangs get their own solid object
            else:
                faces.append(f)
    ob = bb.make_obj("hair", verts, faces, coll, COL["hair"])
    mod = ob.modifiers.new("thickness", "SOLIDIFY")
    mod.thickness = HAIR_THICK
    mod.offset = -1.0
    ob["bottoms"] = [round(z, 4) for z in bottoms]
    ob["bottom_view"] = " ".join(who)
    cols = [[verts[i] for i in c] for c in idx]
    return ob, R, dict(ts=ts, bottoms=bottoms, cols=cols, levels=levels, who=[w[0] for w in who],
                       verts=verts, bang_faces=bang_faces)


def bangs_solid(R, info, coll):
    """The bangs as solid locks: the shell's faces in front of the face, made
    into a solid reaching back to the forehead (Solidify, thickness per
    vertex = its depth in front of the face), so in profile the bangs are a
    mass in front of the face as drawn, not a thin visor. The rim follows
    the shell's hem, pointed tips included."""
    used = sorted({i for f in info["bang_faces"] for i in f})
    if not used:
        return None
    remap = {i: k for k, i in enumerate(used)}
    verts = [info["verts"][i] for i in used]
    faces = [tuple(remap[i] for i in f) for f in info["bang_faces"]]
    ob = bb.make_obj("bangs", verts, faces, coll, COL["hair"])
    depth = []
    for x, y, z in verts:
        depth.append(max(face_y(R, x, z) - VISOR_GAP - y, HAIR_THICK))
    dmax = max(depth)
    vg = ob.vertex_groups.new(name="depth")
    for i, dd in enumerate(depth):
        vg.add([i], dd / dmax, "REPLACE")
    mod = ob.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = dmax
    mod.offset = -1.0
    mod.vertex_group = "depth"
    mod.use_rim = True
    mod.use_even_offset = True
    return ob


# ----------------------------------------------------------------------------- face, skull, neck
def face_mesh(d, coll, M=64, DZ=0.5):
    """sculpted face: smooth half-rings every DZ sheet px from the forehead
    (under the bangs) to the chin, from head_profiles.face_gg:
      outline (front view) -> half-width, profile (side view) -> centre-line
      depth incl. the nose, side view's skin edge -> how far back the sides go.
    Cross-section: superellipse, flat in front (exponent face_n), sampled by
    angle so the vertices crowd where the cheek turns; the nose is a narrow
    ridge added to the centre line. Bottom: closed at the chin."""
    g = d["face_gg"]
    order = np.argsort(g["z"])
    zg = np.array(g["z"])[order]
    get = lambda k, z: float(np.interp(z, zg, np.array(g[k])[order]))
    z_top, z_bot = zg.max() + 0.5 * P, zg.min() - 0.5 * P
    levels = np.arange(z_top, z_bot - 1e-9, -DZ * P)
    tuck = [(0.98, 0.010), (0.90, 0.022)]          # wrap the cheek edge back under the hair
    verts, faces = [], []
    cols = M + 1 + 2 * len(tuck)
    for z in levels:
        z = float(z)
        xc, hw = get("xc", z), get("hw", z)
        yp, yb, ys = get("yp", z), get("ybase", z), get("ys", z)
        n = face_n(z)
        row = []
        for s, dy in reversed(tuck):
            row.append((xc - hw * s, ys + dy, z))
        for i in range(M + 1):
            t = math.pi + math.pi * i / M                      # pi .. 2 pi: her right edge -> left edge
            c, sn = math.cos(t), math.sin(t)
            u = math.copysign(abs(c) ** (2.0 / n), c)
            x = xc + hw * u
            y = ys + (yb - ys) * abs(sn) ** (2.0 / n)
            k = 1.0 - ((x - xc) / NOSE_HW) ** 2
            if k > 0:
                y += (yp - yb) * k ** 1.5                      # nose ridge (yp < yb where the nose is)
            row.append((x, y, z))
        for s, dy in tuck:
            row.append((xc + hw * s, ys + dy, z))
        verts += row
    R = len(levels)
    for i in range(R - 1):
        for j in range(cols - 1):
            a, b = i * cols + j, i * cols + j + 1
            faces.append((a, b, (i + 1) * cols + j + 1, (i + 1) * cols + j))
    # chin: fan to a point just under the last ring's centre
    last = verts[(R - 1) * cols:R * cols]
    cx = sum(v[0] for v in last) / cols
    cy = sum(v[1] for v in last) / cols
    verts.append((cx, cy, float(levels[-1]) - 0.3 * P))
    ci = len(verts) - 1
    for j in range(cols - 1):
        faces.append(((R - 1) * cols + j + 1, (R - 1) * cols + j, ci))
    return bb.make_obj("face", verts, faces, coll, COL["face"])


def skull_mesh(d, R, coll, N=48):
    """closed volume inside the hair: hair rings pulled in, front = behind the
    face. Its front half narrows to the face's width (+4 mm) so from the side
    the cheek and jaw stay the outermost surface; its back half keeps the
    head's width, so from the front/back it still fills the gaps between the
    locks and the jaw."""
    face = {round(q[0], 6): q for q in d["face"]["rings"]}
    fz = sorted(face)
    rings = []
    for z in np.arange(float(R.z.max()) - 2 * P, sole_z("front", 141), -2 * P):
        x0, x1, y0, y1 = R.box(z)
        xc = 0.5 * (x0 + x1)
        hw = min(0.5 * (x1 - x0) - 0.012, 0.074)                 # real head ~15 cm wide
        hw = max(hw, 0.02)
        hw_front = hw
        yb = y1 - 0.025
        if z <= fz[-1]:
            q = face[min(fz, key=lambda k: abs(k - z))]
            yf = q[3] + 0.008                                     # just behind the face surface
            fhw = 0.5 * (q[2] - q[1])
            hw = max(hw, fhw)
            hw_front = min(hw, fhw + 0.004)
        else:
            yf = y0 + 0.018
        if yb - yf < 0.04:
            yb = yf + 0.04
        rings.append((float(z), xc, hw, hw_front, float(yf), float(yb)))
    verts, faces = [], []
    for z, xc, hw, hwf, yf, yb in rings:
        yc, b = 0.5 * (yf + yb), 0.5 * (yb - yf)
        for i in range(N):
            cx, sy = bb.se(2 * math.pi * i / N, 2.0)
            w = hw if sy >= 0 else hw + (hwf - hw) * abs(sy)
            verts.append((xc + w * cx, yc + b * sy, z))
    nr = len(rings)
    for i in range(nr - 1):
        for j in range(N):
            a, c = i * N + j, i * N + (j + 1) % N
            faces.append((a, c, c + N, a + N))
    faces.append(tuple(range(N))[::-1])
    faces.append(tuple(range((nr - 1) * N, nr * N)))
    return bb.make_obj("skull", verts, faces, coll, COL["face"])


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
        x = sgn * EAR_X                                           # on the skull's side
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
    got = {int(k): v for k, v in d["headband"]["front"].items()}
    us = sorted(got)
    cols = []
    for u in range(us[0], us[-1] + 1):                     # bridge columns the mark's outline breaks
        if u in got:
            cols.append((u, got[u]))
        else:
            lo = max(k for k in us if k < u)
            hi = min(k for k in us if k > u)
            t = (u - lo) / float(hi - lo)
            cols.append((u, [got[lo][i] + (got[hi][i] - got[lo][i]) * t for i in (0, 1)]))
    cf = cfg.VIEWS["front"]["centre_u"]
    NS = 8                                                 # rows across the band: it follows the shell's curve
    verts, faces = [], []
    for i, (u, (t, b)) in enumerate(cols):
        x = (u + 0.5 - cf) * P
        for k in range(NS + 1):
            z = sole_z("front", t + (b - t) * k / float(NS))
            verts.append((x, R.front_y(z, x) - lift, z))
    for i in range(len(cols) - 1):
        a, c = (NS + 1) * i, (NS + 1) * (i + 1)
        for k in range(NS):
            faces.append((a + k, c + k, c + k + 1, a + k + 1))
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
    for name in REMOVE + ("hair", "bangs", "hair_lower", "face", "nose", "skull", "neck", "ear_R", "ear_L", "headband", "clip_R", "clip_L"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    hair, R, info = hair_shell(d, coll)
    objs = [hair, bangs_solid(R, info, coll), face_mesh(d, coll), skull_mesh(d, R, coll), neck_mesh(d, coll),
            headband(d, R, coll)]
    objs += ear_meshes(d, R, coll) + clips(d, R, coll)
    objs.append(bb.tube("ahoge", d2["ahoge"], coll, COL["hair"], N=10))
    objs = [o for o in objs if o is not None]
    for o in objs:                                        # smooth shading on all head parts
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        o.data.update()
    return {o.name: len(o.data.vertices) for o in objs}


if __name__ == "__main__":
    print(build())
