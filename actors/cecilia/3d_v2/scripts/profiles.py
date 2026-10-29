"""Milestone 2: per-part silhouette profiles traced from the reference masks.

numpy only (runs in Blender or plain Python). Writes refs/profiles_m2.json,
which build_blockout.py turns into meshes. Every number comes from the
masks; the rules below only decide WHICH silhouette edge belongs to which
part, and how to bridge rows where a part's edge is hidden behind another.

Conventions (see cfg.py): rows are FRONT-crop rows r; the same height is
back row r-1 and side row r+1 (crops sit 1 px apart). World x from front
and mirrored back (averaged 50/50: the near-optimal compromise found in M1),
world y from the side view (front of body = -y).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

P = cfg.PX
CF, CB, CS = (cfg.VIEWS[v]["centre_u"] for v in ("front", "back", "side"))
SOLE_F = cfg.VIEWS["front"]["sole_v"]
D_BACK = int(round(cfg.VIEWS["back"]["sole_v"] - SOLE_F))     # -1
D_SIDE = int(round(cfg.VIEWS["side"]["sole_v"] - SOLE_F))     # +1

# Front/back compromise. 0.5 = split the difference. The disputed area is
# not symmetric (the front view has more front-only features: wider jacket,
# longer left arm, the hilt), so a 50/50 edge average leaves the back view
# lower; W_FRONT is tuned so both views land about equally. M2 sweep with
# 2 smoothing passes: 0.50 -> front 0.9557 / back 0.9499; 0.45 -> 0.9526 / 0.9534.
W_FRONT = 0.45


# Sub-pixel run ends from the coverage maps (refs/masks/cov_*.png). Off for
# the M2 blockout: the IoU is scored on the BINARY masks, and integer edges
# reproduce that staircase exactly (side legs 0.9996), while sub-pixel edges
# put many boundary pixels near the 0.5 threshold, where they flip (side
# IoU 0.976 -> 0.965). Sub-pixel is the truer drawn line; revisit for the
# smooth final surfaces in M4.
SUBPIXEL = False

# Which views' strand tips the hair blockout keeps (each one is "disputed":
# the other view draws different tips there).
TIP_VIEWS = ("back",)


def blend(front_val, back_val):
    return W_FRONT * front_val + (1.0 - W_FRONT) * back_val


# measured in M1 from the side view's end-on cuff ring
ARM_AXIS_Y = -(118.2 - CS) * P
SIDE_PICK = {}


def runs(row):
    c = np.where(row)[0]
    if len(c) == 0:
        return []
    br = np.where(np.diff(c) > 1)[0]
    return list(zip(np.r_[c[0], c[br + 1]].tolist(), np.r_[c[br], c[-1]].tolist()))


class Masks:
    """Masks + coverage maps. Runs come back with SUB-PIXEL ends: (left, right-1),
    so `right + 1` is the edge. The binary mask makes a slanted edge a 1-px
    staircase; the coverage of the two pixels straddling each run end puts the
    edge where the drawn (anti-aliased) line actually is."""

    def __init__(self):
        self.m = {v: imgio.load_mask(cfg.mask_path(v)) for v in cfg.VIEW_ORDER}
        self.C = {}
        for v in cfg.VIEW_ORDER:
            p = os.path.join(cfg.MASKS, "cov_%s.png" % v)
            self.C[v] = imgio.load16(p) if (SUBPIXEL and os.path.exists(p)) else self.m[v].astype(np.float32)

    def _sub(self, view, rr):
        rs = runs(self.m[view][rr])
        C = self.C[view][rr]
        W = len(C)
        out = []
        for a, b in rs:
            left = a + 1.0 - ((C[a - 1] if a > 0 else 0.0) + C[a])
            right = b + C[b] + (C[b + 1] if b + 1 < W else 0.0)
            left = min(max(left, a - 0.5), a + 0.5)
            right = min(max(right, b + 0.5), b + 1.5)
            out.append((float(left), float(right - 1.0)))
        return out

    def f(self, r):
        return self._sub("front", r)

    def b(self, r):
        return self._sub("back", r + D_BACK)

    def s(self, r):
        return self._sub("side", r + D_SIDE)

    def vedge(self, view, c, t, b):
        """sub-pixel (top, bottom) edges of a vertical run t..b in column c"""
        C = self.C[view][:, c]
        H = len(C)
        top = t + 1.0 - ((C[t - 1] if t > 0 else 0.0) + C[t])
        bot = b + C[b] + (C[b + 1] if b + 1 < H else 0.0)
        return min(max(top, t - 0.5), t + 0.5), min(max(bot, b + 0.5), b + 1.5)

    def col(self, view, c):
        return self.m[view][:, c]


# world conversions (u = continuous image column; run (a, b) spans [a, b+1])
def fx(u):
    return (u - CF) * P


def bx(u):
    return -(u - CB) * P


def sy(u):
    return -(u - CS) * P


def zc(r):
    """height of the centre of front row r"""
    return (SOLE_F - r - 0.5) * P


def zedge(v):
    """height of continuous front row coordinate v (edge between rows)"""
    return (SOLE_F - v) * P


def pick(rs, lo, hi, minw=1):
    """runs whose centre lies in [lo, hi]"""
    return [(a, b) for a, b in rs if lo <= (a + b) / 2.0 <= hi and b - a + 1 >= minw]


def widest(rs):
    return max(rs, key=lambda t: t[1] - t[0]) if rs else None


def fill_nans(a):
    """linear interpolation over NaNs (ends held flat)"""
    a = np.asarray(a, float)
    idx = np.arange(len(a))
    ok = ~np.isnan(a)
    if ok.sum() == 0:
        return a
    return np.interp(idx, idx[ok], a[ok])


def smooth(a, k=1):
    """[1 2 1]/4 smoothing applied k times (edges kept)"""
    a = np.asarray(a, float).copy()
    for _ in range(k):
        b = a.copy()
        b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
        a = b
    return a


# ----------------------------------------------------------------------------- parts
def legs(M):
    """Each leg: front + mirrored back for x, side (shared) for y."""
    out = {}
    rows = np.arange(372, 631)
    for side_name, f_lo, f_hi, b_lo, b_hi in (("R", 150, 265.5, 266.5, 360), ("L", 265.5, 345, 190, 266.5)):
        fx0, fx1, bx0, bx1 = [], [], [], []
        for r in rows:
            fr = pick(M.f(r), f_lo, f_hi, 8)
            br = pick(M.b(r), b_lo, b_hi, 8)
            # rows 372-385: both legs + lace merge into one front/back run; outer edge only
            if r < 386:
                # outer extent of the leg region (the crotch gap may already be open in one view)
                fl = [t for t in M.f(r) if (t[0] + t[1]) / 2 < 345]
                bl = [t for t in M.b(r) if (t[0] + t[1]) / 2 > 190]
                fr_all = (min(t[0] for t in fl), max(t[1] for t in fl))
                br_all = (min(t[0] for t in bl), max(t[1] for t in bl))
                if side_name == "R":
                    fx0.append(fr_all[0]); fx1.append(np.nan)
                    bx0.append(np.nan); bx1.append(br_all[1] + 1)
                else:
                    fx0.append(np.nan); fx1.append(fr_all[1] + 1)
                    bx0.append(br_all[0]); bx1.append(np.nan)
                continue
            a, b = widest(fr)
            fx0.append(a); fx1.append(b + 1)
            a, b = widest(br)
            bx0.append(a); bx1.append(b + 1)
        fx0, fx1, bx0, bx1 = map(fill_nans, (fx0, fx1, bx0, bx1))
        # inner edges above the crotch were held flat by fill_nans -> extrapolate linearly instead
        k = 386 - 372
        for arr in (fx1, ) if side_name == "R" else (fx0, ):
            slope = (arr[k + 10] - arr[k]) / 10.0
            arr[:k] = arr[k] - slope * (k - np.arange(k))
        for arr in (bx0, ) if side_name == "R" else (bx1, ):
            slope = (arr[k + 10] - arr[k]) / 10.0
            arr[:k] = arr[k] - slope * (k - np.arange(k))
        # world x: front u -> x ; back u -> x (mirrored: left edge in back = larger world x)
        xa = blend(fx(fx0), bx(bx1))       # low-x edge
        xb = blend(fx(fx1), bx(bx0))       # high-x edge
        out[side_name] = dict(rows=rows, x0=xa, x1=xb)
    # side: one silhouette for both legs
    y0, y1 = [], []
    for r in rows:
        a, b = widest(M.s(r))
        if r < 382:                      # front edge hidden by lace at rows 372-381
            y0.append(np.nan)
        else:
            y0.append(b + 1)
        y1.append(a)
    y0 = fill_nans(y0)
    k = 382 - 372
    slope = (y0[k + 10] - y0[k]) / 10.0
    y0[:k] = y0[k] - slope * (k - np.arange(k))
    yf, yb = sy(np.array(y0)), sy(np.array(y1))
    rings = {}
    for s_ in ("R", "L"):
        d = out[s_]
        rr = []
        for i, r in enumerate(rows):
            rr.append([zc(r), float(d["x0"][i]), float(d["x1"][i]), float(yf[i]), float(yb[i])])
        # hidden extensions: up into the skirt, down into the shoe
        top = rr[0]
        for r in range(340, 372):
            rr.insert(r - 340, [zc(r)] + top[1:])
        bot = rr[-1]
        for r in range(631, 652):
            rr.append([zc(r)] + bot[1:])
        rings[s_] = rr
    return rings


def shoes(M):
    rings = {"R": [], "L": []}
    bow = {"R": [], "L": []}
    rows = np.arange(631, 695)
    data = {"R": {"fx0": [], "fx1": [], "bx0": [], "bx1": []}, "L": {"fx0": [], "fx1": [], "bx0": [], "bx1": []}}
    for r in rows:
        for s_, f_lo, f_hi, b_lo, b_hi in (("R", 150, 265.5, 266.5, 380), ("L", 265.5, 380, 150, 266.5)):
            fr = widest(pick(M.f(r), f_lo, f_hi, 4))
            br = widest(pick(M.b(r), b_lo, b_hi, 4))
            d = data[s_]
            d["fx0"].append(fr[0] if fr else np.nan)
            d["fx1"].append(fr[1] + 1 if fr else np.nan)
            d["bx0"].append(br[0] if br else np.nan)
            d["bx1"].append(br[1] + 1 if br else np.nan)
    ys0, ys1 = [], []
    for r in rows:
        rs = M.s(r)
        ys0.append(max(b for a, b in rs) + 1)    # toe / bow front
        ys1.append(min(a for a, b in rs))        # heel
    ys0, ys1 = np.array(ys0, float), np.array(ys1, float)
    for s_ in ("R", "L"):
        d = {k: fill_nans(v) for k, v in data[s_].items()}
        xa = blend(fx(d["fx0"]), bx(d["bx1"]))
        xb = blend(fx(d["fx1"]), bx(d["bx0"]))
        # bow rows (front 632-656): the silhouette is the bow; the shoe/ankle under it is narrower.
        ib = (rows >= 632) & (rows <= 656)
        # shoe proper starts at row 642; under the bow interpolate shoe width from row 657 up to ankle width
        i657 = int(np.where(rows == 657)[0][0])
        i631 = 0
        xs0 = xa.copy(); xs1 = xb.copy()
        for i in np.where(ib)[0]:
            t = (rows[i] - 631) / (657 - 631.0)
            xs0[i] = (1 - t) * xa[i631] + t * xa[i657]
            xs1[i] = (1 - t) * xb[i631] + t * xb[i657]
        # side: toe/vamp front hidden by the bow at rows 632-656 -> interpolate 631 .. 657
        yf_raw = ys0.copy()
        for i in np.where(ib)[0]:
            t = (rows[i] - 631) / (657 - 631.0)
            yf_raw[i] = (1 - t) * ys0[i631] + t * ys0[i657]
        for i, r in enumerate(rows):
            if r >= 642:
                rings[s_].append([zc(r), float(xs0[i]), float(xs1[i]), float(sy(yf_raw[i])), float(sy(ys1[i]))])
            if 631 <= r <= 656:
                # bow: x from the silhouette, y from ankle front (u=116) to the drawn front edge
                bow[s_].append([zc(r), float(xa[i]), float(xb[i]), float(sy(ys0[i])), float(sy(116.0))])
    # sole: close at the bottom edge
    for s_ in ("R", "L"):
        last = rings[s_][-1]
        rings[s_].append([zedge(695.0)] + last[1:])
    return rings, bow


def skirt(M):
    """Skirt + lace. Hem follows the front/back views (saddle: low at front/back centre)."""
    rows = np.arange(258, 386)
    xr_f, xr_b = [], []          # her RIGHT side edge (low world x), from front-left and back-right edges
    xl_obs = []                  # her LEFT side edge where visible (front rows 364-371)
    yf, yb = [], []
    for r in rows:
        fr = widest(M.f(r))
        br = widest([t for t in M.b(r) if t[1] > 250])
        if r <= 369:
            xr_f.append(fr[0])
        else:
            xr_f.append(np.nan)
        if r <= 373 and br is not None:
            xr_b.append(br[1] + 1)
        else:
            xr_b.append(np.nan)
        # her left edge visible between skirt and sheath, rows 364-371
        if 364 <= r <= 371:
            cand = [t for t in M.f(r) if t[0] < 300]
            xl_obs.append(widest(cand)[1] + 1)
        else:
            xl_obs.append(np.nan)
        rs = M.s(r)
        main = widest(rs)
        # back edge: outermost incl. lace scallop runs at the back
        yb.append(min(a for a, b in rs) if r <= 371 else np.nan)
        # front edge: skip the sword hilt cap (rows 259-275)
        if 259 <= r <= 275 or r > 381:
            yf.append(np.nan)
        else:
            yf.append(max(b for a, b in rs if a < 160 or b < 182) + 1)
    xr_f, xr_b, xl_obs = np.array(xr_f, float), np.array(xr_b, float), np.array(xl_obs, float)
    # world: her right edge (front-left & back-right), average where both, else whichever exists
    wr_f = fx(xr_f)
    wr_b = bx(xr_b)
    wr = np.where(np.isnan(wr_f), wr_b, np.where(np.isnan(wr_b), wr_f, blend(wr_f, wr_b)))
    wr = fill_nans(wr)
    # centre line: x = 0 at the waist, x = -1.0 cm at the hem (both views agree, M2 analysis)
    zr = zc(rows)
    t = np.clip((rows - 258) / (369 - 258.0), 0, 1)
    centre = -0.010 * t
    wl = 2 * centre - wr
    # where her left edge is visible (rows 364-371), use it
    obs = ~np.isnan(xl_obs)
    wl[obs] = 0.5 * (wl[obs] + fx(xl_obs[obs]))
    yf = fill_nans(yf)
    yb = np.array(yb, float)
    # back edge below the drawn back hem: lace hangs straight (extend last observed)
    yb = fill_nans(yb)
    rings = []
    for i, r in enumerate(rows):
        rings.append([float(zr[i]), float(wr[i]), float(wl[i]), float(sy(yf[i])), float(sy(yb[i]))])
    hem = dict(front=zedge(384.0), back=zedge(385.0), side=zedge(372.0))
    return rings, hem


def torso(M):
    """Neck/collar (rows 140-151), shoulders (152-191, hidden by arms), jacket + waist (192-262)."""
    rows = np.arange(140, 263)
    xa_f, xb_f, xa_b, xb_b, y0, y1 = [], [], [], [], [], []
    for r in rows:
        fr, br = M.f(r), M.b(r)
        if r <= 151:
            f_ = widest(pick(fr, 240, 300, 20))
            b_ = widest(pick(br, 235, 295, 20))
        elif r <= 191:
            f_ = b_ = None
        else:
            f_ = widest(pick(fr, 200, 330, 40))
            b_ = widest(pick(br, 200, 330, 40))
        xa_f.append(f_[0] if f_ else np.nan); xb_f.append(f_[1] + 1 if f_ else np.nan)
        xa_b.append(b_[0] if b_ else np.nan); xb_b.append(b_[1] + 1 if b_ else np.nan)
        s_ = widest(M.s(r))
        y1.append(s_[0])
        # front edge: skip the hilt cap at rows 259-262
        y0.append(s_[1] + 1 if r < 259 else np.nan)
    xa_f, xb_f, xa_b, xb_b = map(lambda a: np.array(a, float), (xa_f, xb_f, xa_b, xb_b))
    # shoulders: rows 152-191 take the row-192 extent (flat-topped square shoulders, as drawn)
    i192 = int(np.where(rows == 192)[0][0])
    for arr in (xa_f, xb_f, xa_b, xb_b):
        arr[(rows >= 152) & (rows <= 191)] = arr[i192]
    xlo = blend(fx(xa_f), bx(xb_b))
    xhi = blend(fx(xb_f), bx(xa_b))
    y0 = fill_nans(y0)
    rings = []
    for i, r in enumerate(rows):
        rings.append([zc(r), float(xlo[i]), float(xhi[i]), float(sy(y0[i])), float(sy(y1[i]))])
    # flat shoulder top: duplicate the row-152 ring at the top edge of row 152,
    # and the neck ring just above it, so the top is a step, not a slope
    return rings


def head(M):
    rows = np.arange(31, 141)
    out = []
    for r in rows:
        f_ = widest(M.f(r))
        b_ = widest(M.b(r))
        rs = M.s(r)
        main = widest(rs)
        yb = main[0]
        # front edge: face/bangs; at the chin rows include the separate chin run
        yfr = max(b for a, b in rs) + 1
        xlo = blend(fx(f_[0]), bx(b_[1] + 1))
        xhi = blend(fx(f_[1] + 1), bx(b_[0]))
        out.append([zc(r), float(xlo), float(xhi), float(sy(yfr)), float(sy(yb))])
    # crown cap at the top edge of row 31
    out.insert(0, [zedge(31.0)] + out[0][1:])
    return out


def ahoge(M):
    """Centre line of the hair loop, from front + side.

    Front: stem = left run (rises from the crown), hook = right run (free tip).
    Side:  stem = back (left) leg of the loop, hook = front (right) leg.
    Apex rows (one run in both views) join the two. Points: [x, y, z, radius].
    """
    stem, hook, apex = [], [], []
    for r in range(15, 31):
        fr, sr = M.f(r), M.s(r)
        if not fr or not sr:
            continue
        if len(fr) == 1 and len(sr) == 1:
            (a, b), (sa, sb) = fr[0], sr[0]
            apex.append([fx((a + b + 1) / 2.0), sy((sa + sb + 1) / 2.0), zc(r), (b - a + 1) / 4.0 * P])
            continue
        a, b = fr[0]
        sa, sb = sr[0]
        if sb - sa + 1 <= 12:            # wider = the head dome, not the stem
            stem.append([fx((a + b + 1) / 2.0), sy((sa + sb + 1) / 2.0), zc(r), min(b - a + 1, 6) / 2.0 * P])
        if len(fr) >= 2 and len(sr) >= 2 and r <= 27:
            a, b = fr[-1]
            sa, sb = sr[-1]
            hook.append([fx((a + b + 1) / 2.0), sy((sa + sb + 1) / 2.0), zc(r), max(0.8, (b - a + 1) / 2.0) * P])
    # path: crown -> up the stem -> apex -> down the hook. The apex rows are a
    # near-horizontal arc (one wide run per row), so keep only the topmost one.
    stem.sort(key=lambda p: -p[2], reverse=True)  # low to high
    hook.sort(key=lambda p: -p[2])                # high to low
    top = max(apex, key=lambda p: p[2]) if apex else []
    if top:
        top = list(top)
        top[3] = 3.0 * P
    return stem + ([top] if top else []) + hook


def arms(M):
    """Arms sliced along x. Per front column: top/bottom of the vertical run through row 168."""
    out = {}
    F, B = M.m["front"], M.m["back"]

    def vrun(m, c, r0):
        col = m[:, c]
        if c < 0 or c >= m.shape[1] or not col[r0]:
            return None
        a = r0
        while a > 0 and col[a - 1]:
            a -= 1
        b = r0
        while b < len(col) - 1 and col[b + 1]:
            b += 1
        return a, b
    # her right arm: front cols 11..216 ; her left: 326..538 ; back mirrored
    for s_, cols in (("R", range(11, 217)), ("L", range(326, 539))):
        xs, z0, z1 = [], [], []
        for c in cols:
            x = fx(c + 0.5)
            fr = vrun(F, c, 168)
            # matching back column
            ub = CB - x / P
            cb = int(np.floor(ub))
            br = vrun(B, cb, 168 + D_BACK) if 0 <= cb < B.shape[1] else None
            if fr is None and br is None:
                continue
            ft = fb = bt = bb = None
            if fr is not None and fr[1] - fr[0] < 60:      # not merged with the torso
                t_, b_ = M.vedge("front", c, fr[0], fr[1])
                ft, fb = zedge(t_), zedge(b_)
            if br is not None and br[1] - br[0] < 60:
                t_, b_ = M.vedge("back", cb, br[0], br[1])
                bt, bb = zedge(t_ - D_BACK), zedge(b_ - D_BACK)   # to front rows
            if ft is None and bt is None:
                continue
            if ft is None:
                top, bot = bt, bb
            elif bt is None:
                top, bot = ft, fb
            else:
                top, bot = blend(ft, bt), blend(fb, bb)
            xs.append(x); z1.append(top); z0.append(bot)
        xs, z0, z1 = map(np.array, (xs, z0, z1))
        order = np.argsort(xs)
        out[s_] = dict(x=xs[order].tolist(), zbot=z0[order].tolist(), ztop=z1[order].tolist())
    return out


def sword(M):
    """Tachi blockout, traced from the front and back views.

    Sheath (front rows 292-405): its outer edge (her left) is the silhouette
    edge in both views and they agree to 1-2 px, so the centre line = averaged
    outer edge minus the drawn half-width (14.4 px wide where it hangs free).
    It curves slightly, like a tachi. Hilt (rows 257-291): only the front view
    shows it; traced from the front. Hanger strap: the dark band between belt
    and guard (front rows 262-283), sticking out of the skirt outline.
    Depth is drawn nowhere except the hilt cap in the side view (y = -8.4 cm
    at row 259); the sheath is hidden in the side view, so y runs -6 cm at the
    guard to +5 cm at the tip, which keeps it inside the side silhouette.
    """
    hw = 7.2 * P
    rows = np.arange(292, 406)
    xo = []
    for r in rows:
        f = [t for t in M.f(r) if t[1] > 300]
        b = [t for t in M.b(r) if t[0] < 240]
        xo.append(blend(fx(max(t[1] for t in f) + 1), bx(min(t[0] for t in b))))
    xo = smooth(np.array(xo), 3)
    z = zc(rows)
    slope = np.gradient(xo) / np.gradient(z)
    cosang = 1.0 / np.sqrt(1.0 + slope ** 2)
    xcen = xo - hw
    rad = hw * cosang
    z_guard, z_tip = zc(292), zedge(410.5)
    y_cap, y_guard, y_tip = -0.084, -0.060, 0.050

    def ydepth(zz):
        if zz >= z_guard:
            t = (zz - z_guard) / (zedge(257.0) - z_guard)
            return y_guard + t * (y_cap - y_guard)
        t = (z_guard - zz) / (z_guard - z_tip)
        return y_guard + t * (y_tip - y_guard)
    sheath = []
    for i in range(0, len(rows), 3):
        sheath.append([float(xcen[i]), ydepth(z[i]), float(z[i]), float(rad[i])])
    # rounded tip (front rows 405-411)
    last = sheath[-1]
    for r, k in ((407.0, 0.85), (409.5, 0.6), (410.8, 0.25)):
        zz = zedge(r)
        sheath.append([last[0] + (zz - last[2]) * float(slope[-1]), ydepth(zz), zz, last[3] * k])
    # hilt: rows 258-273 both edges visible (separate run), 274-291 right edge only
    hilt = []
    for r in range(258, 292, 2):
        f = [t for t in M.f(r) if t[1] > 300]
        a, b = f[-1]
        if r <= 273:
            xc_, rr = fx((a + b + 1) / 2.0), (b - a + 1) / 2.0 * P
        else:
            xc_, rr = fx(b + 1) - 7.0 * P, 7.0 * P
        hilt.append([float(xc_), ydepth(zc(r)), float(zc(r)), float(rr)])
    cap_top = hilt[0][:]
    cap_top[2] = zedge(257.0)
    cap_top[3] = 2.0 * P
    hilt.insert(0, cap_top)
    hilt.append([float(xcen[0]), y_guard, float(z_guard), float(rad[0])])
    strap = [[fx(316.0), -0.070, zc(262), 3.0 * P], [fx(327.0), -0.064, zc(283), 3.0 * P],
             [float(xcen[0]) - 2 * P, -0.061, float(z_guard), 3.0 * P]]
    return dict(sheath=sheath, hilt=hilt, strap=strap)


def hair_tips(M, head_rings):
    """Strand tips that stick out below/beside the head loft (front + back views).

    Each tip is a connected group of mask pixels outside the loft's x-extent
    in rows 85-145; returned as pixel-run quads (world x, z) to be extruded a
    few mm in y at the head ring's mid-depth. Blockout stand-in until M3.
    """
    zs = np.array([r[0] for r in head_rings])
    order = np.argsort(zs)
    out = []
    for view in TIP_VIEWS:
        m = M.m[view]
        dr = 0 if view == "front" else D_BACK
        for r in range(85, 146):
            rr = r + dr
            z = zc(r)
            i = int(np.argmin(np.abs(zs - z)))
            x0, x1, y0, y1 = head_rings[i][1:]
            if abs(zs[i] - z) > P:
                continue
            for a, b in runs(m[rr]):
                if view == "front":
                    xa, xb = fx(a), fx(b + 1)
                else:
                    xa, xb = bx(b + 1), bx(a)
                # pieces outside the head ring's x-extent (with 1 px tolerance)
                if xb < x0 - P or xa > x1 + P:
                    out.append([float(xa), float(xb), float(z), 0.5 * (y0 + y1), view])
                elif xa < x0 - P:
                    out.append([float(xa), float(x0), float(z), 0.5 * (y0 + y1), view])
                elif xb > x1 + P:
                    out.append([float(x1), float(xb), float(z), 0.5 * (y0 + y1), view])
    return out


# Edge smoothing (passes of [1 2 1]/4 along the traced rows). The masks are
# binary, so a slanted edge is a 1-px staircase; following it exactly makes
# visible ridges ring to ring. Two passes ~ sigma 1 px, close to the true
# (anti-aliased) drawn edge.
SMOOTH_PASSES = 2


def smooth_rings(rings, k=None):
    k = SMOOTH_PASSES if k is None else k
    if k <= 0 or len(rings) < 3:
        return rings
    rings = sorted(rings, key=lambda r: -r[0])
    A = np.array(rings, float)
    for c in (1, 2, 3, 4):
        A[:, c] = smooth(A[:, c], k)
    return A.tolist()


def smooth_arm(arm, k=None):
    k = SMOOTH_PASSES if k is None else k
    if k <= 0:
        return arm
    order = np.argsort(arm["x"])
    out = dict(x=list(np.array(arm["x"])[order]))
    for key in ("ztop", "zbot"):
        out[key] = smooth(np.array(arm[key])[order], k).tolist()
    return out


def main():
    M = Masks()
    sk_rings, hem = skirt(M)
    head_rings = head(M)
    data = dict(
        px_m=P,
        legs={s_: smooth_rings(r) for s_, r in legs(M).items()},
        shoes=None, bows=None,
        skirt=dict(rings=smooth_rings(sk_rings), hem=hem),
        torso=smooth_rings(torso(M)),
        head=smooth_rings(head_rings),
        ahoge=ahoge(M),
        arms={s_: smooth_arm(a) for s_, a in arms(M).items()},
        sword=sword(M),
        arm_axis_y=ARM_AXIS_Y,
    )
    sh, bw = shoes(M)
    data["shoes"] = {s_: smooth_rings(r) for s_, r in sh.items()}
    data["bows"] = {s_: smooth_rings(r, min(1, SMOOTH_PASSES)) for s_, r in bw.items()}
    data["hair_tips"] = hair_tips(M, head_rings)
    path = os.path.join(cfg.REFS, "profiles_m2.json")
    with open(path, "w") as fh:
        json.dump(data, fh)
    return path, data


if __name__ == "__main__":
    p, d = main()
    print(p, {k: (len(v) if hasattr(v, "__len__") else v) for k, v in d.items()})
