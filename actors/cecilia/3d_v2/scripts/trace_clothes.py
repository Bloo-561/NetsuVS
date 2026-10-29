"""Milestone 4: traced measurements of the clothing parts (numpy only).

Colour classes of the three crops (classes()), then per-part traces in
front-crop rows (side row = front row + 1, back row = front row - 1, as in
profiles.py) and continuous image columns. Everything lands in
refs/profiles_m4.json for build_clothes.py.

Jacket / bodice (torso()):
  open_R, open_L  front view: the jacket's front edges, i.e. the first black
                  jacket pixel scanning out from the centre column (the
                  opening shows shirt, neckerchief and red bodice)
  jf              side view: the jacket's front edge (end of the jacket run
                  that contains the torso's middle)
  bf              side view: the red bodice's front edge just in front of it
  gold_f, gold_b  side view: the neckerchief's front / back edge
  hem_front/back/side: last jacket row per column in each view
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\trace_clothes.py", run_name="__main__")
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

P = cfg.PX
OFF = {"front": 0, "side": 1, "back": -1}           # crop row = front row + OFF
NAMES = ["bg", "white", "skin", "gold", "red", "maroon", "jacket", "grey", "brown", "hair", "teal", "other"]
IDX = {n: i for i, n in enumerate(NAMES)}


def classes(view):
    """per-pixel colour class (NAMES) of a crop; background from the mask"""
    rgb = imgio.load(cfg.ref_path(view), channels=3).astype(np.float32)
    mask = imgio.load_mask(cfg.mask_path(view))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    lum = rgb.mean(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    c = np.full(r.shape, IDX["other"], np.uint8)

    def put(m, name):
        c[m & (c == IDX["other"])] = IDX[name]
    put(~mask, "bg")
    put((hue > 30) & (hue < 60) & (sat > 0.35) & (r > 170), "gold")
    put((hue > 160) & (hue < 200) & (sat > 0.25), "teal")
    put((hue > 260) & (hue < 345) & (sat > 0.25), "hair")
    put((lum > 200) & (mx - mn < 22), "white")
    put((lum > 185) & (r - b >= 12) & (r - b < 70) & (sat < 0.3), "skin")
    put(((hue < 15) | (hue > 345)) & (sat > 0.45) & (r > 130), "red")
    put(((hue < 15) | (hue > 345)) & (sat > 0.45) & (r <= 130) & (r > 70), "maroon")
    put((mx - mn < 28) & (lum < 92), "jacket")
    put((mx - mn < 28) & (lum >= 92) & (lum <= 200), "grey")
    put((hue < 40) & (sat > 0.15) & (lum < 130), "brown")
    return c


def runs(b):
    c = np.where(b)[0]
    if len(c) == 0:
        return []
    br = np.where(np.diff(c) > 1)[0]
    return list(zip(np.r_[c[0], c[br + 1]].tolist(), np.r_[c[br], c[-1]].tolist()))


def fill(rows, vals):
    """linear interpolation over missing (None) entries, held at the ends"""
    v = np.array([np.nan if x is None else float(x) for x in vals])
    ok = ~np.isnan(v)
    if ok.sum() == 0:
        return v
    return np.interp(np.asarray(rows, float), np.asarray(rows, float)[ok], v[ok])


def smooth(a, k=1):
    a = np.asarray(a, float).copy()
    for _ in range(k):
        b = a.copy()
        b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
        a = b
    return a


# ----------------------------------------------------------------------------- jacket + bodice
OPEN_ROWS = (157, 249)          # front rows where the jacket's front edges are traced
OPEN_BOW = (175, 182)           # rows where the neckerchief's bow hides them: interpolated
SIDE_ROWS = (150, 249)
SIDE_JF_TOP = (150, 141.0)      # side view, the jacket's front edge at the collar (behind the end-on cuff)
SIDE_JF_FROM = 192              # traced from this row down (above it the cuff ring hides the edge)
HEM_COLS = {"front": (211, 332), "back": (214, 316), "side": (89, 152)}
GOLD_ROWS = (194, 232)          # side rows where the neckerchief's tails hang in front of the bust
TAIL_PX = 1.3                   # tail thickness + clearance, sheet px (3 mm)
VENT_BOX = (220, 253, 255, 277)  # back crop (rows r0:r1, cols u0:u1) around the centre vent


def torso():
    cf, cs, cb = classes("front"), classes("side"), classes("back")
    cu = cfg.VIEWS["front"]["centre_u"]
    rows = list(range(OPEN_ROWS[0], OPEN_ROWS[1] + 1))
    oR, oL = [], []
    for r in rows:
        row = cf[r]
        c0 = int(cu)
        L = R = None
        if not (OPEN_BOW[0] <= r <= OPEN_BOW[1]):
            for k in range(c0, c0 - 60, -1):
                if row[k] == IDX["jacket"]:
                    L = k + 1.0
                    break
            for k in range(c0, c0 + 60):
                if row[k] == IDX["jacket"]:
                    R = float(k)
                    break
        oR.append(L)
        oL.append(R)
    oR, oL = smooth(fill(rows, oR), 1), smooth(fill(rows, oL), 1)
    srows = list(range(SIDE_ROWS[0], SIDE_ROWS[1] + 1))
    JG = np.isin(cs, [IDX["jacket"], IDX["grey"]])
    jf, bf, gf, gb = [], [], [], []
    for r in srows:
        rr = r + OFF["side"]
        j = None
        if r >= SIDE_JF_FROM:
            for a, b in runs(JG[rr]):
                if a <= 120 <= b:
                    j = b + 1.0
        jf.append(j)
        red = np.isin(cs[rr], [IDX["red"], IDX["maroon"]])
        rr_runs = [(a, b) for a, b in runs(red) if j is not None and j - 2 <= a <= j + 4]
        bf.append(rr_runs[0][1] + 1.0 if rr_runs else None)
        gr = runs(cs[rr] == IDX["gold"])
        gf.append(gr[-1][1] + 1.0 if gr else None)
        gb.append(float(gr[0][0]) if gr else None)
    jf[0] = SIDE_JF_TOP[1]
    jf = smooth(fill(srows, jf), 2)
    bf = smooth(fill(srows, bf), 2)
    # the bodice's front under the neckerchief tails: the tails lie on the
    # bust, so its front is the tails' front edge less their thickness
    g_rows = [r for r, g in zip(srows, gf) if g is not None and GOLD_ROWS[0] <= r <= GOLD_ROWS[1]]
    g_vals = [g for r, g in zip(srows, gf) if g is not None and GOLD_ROWS[0] <= r <= GOLD_ROWS[1]]
    gsm = smooth(np.interp(srows, g_rows, g_vals), 2)
    body_front = []
    for k, r in enumerate(srows):
        if GOLD_ROWS[0] <= r <= GOLD_ROWS[1]:
            body_front.append(max(float(bf[k]), float(gsm[k]) - TAIL_PX))
        else:
            body_front.append(float(bf[k]))
    body_front = smooth(np.array(body_front), 2)
    hems = {}
    for view, c in (("front", cf), ("back", cb), ("side", cs)):
        JGv = np.isin(c, [IDX["jacket"], IDX["grey"]])
        if view == "back":
            # the centre vent's pink lining (classed "hair": magenta) is the
            # jacket's inside showing through the slit, not a gap in its hem
            r0, r1, u0, u1 = VENT_BOX
            vent = np.zeros_like(JGv)
            vent[r0:r1, u0:u1] = c[r0:r1, u0:u1] == IDX["hair"]
            JGv |= vent
        lo, hi = HEM_COLS[view]
        out = []
        for u in range(lo, hi + 1):
            col = JGv[:, u]
            start = 230 + OFF[view]
            last = None
            for rr in range(start, start + 35):
                if col[rr]:
                    last = rr
                elif last is not None and rr > last + 1:
                    break
            if last is not None:
                out.append([u + 0.5, last + 1.0 - OFF[view]])          # bottom edge of the last jacket row, front rows
        hems[view] = out
    return dict(rows=rows, open_R=oR.tolist(), open_L=oL.tolist(), side_rows=srows, jf=jf.tolist(), bf=bf.tolist(),
                gold_f=gf, gold_b=gb, hem=hems, body_front=body_front.tolist())


# ----------------------------------------------------------------------------- skirt + lace
SKIRT_COLS = {"front": (186, 356), "back": (180, 350), "side": (40, 190)}
SKIRT_SCAN = (330, 400)          # front rows scanned for the red hem and the lace's bottom
RED_GAP = 3                      # stripes / anti-aliasing inside the red: gaps up to this many rows


def skirt():
    """per column of each view: the red skirt's hem (bottom edge of its last
    red row) and the lace petticoat's bottom edge, in front-row coordinates"""
    out = {}
    for view in ("front", "back", "side"):
        c = classes(view)
        red = np.isin(c, [IDX["red"], IDX["maroon"]])
        lace = np.isin(c, [IDX["white"], IDX["grey"], IDX["other"]])
        bg = c == IDX["bg"]
        skin = c == IDX["skin"]
        lo, hi = SKIRT_COLS[view]
        rows_red, rows_lace = [], []
        for u in range(lo, hi + 1):
            r0 = SKIRT_SCAN[0] + OFF[view]
            r1 = SKIRT_SCAN[1] + OFF[view]
            col_red = red[r0:r1, u]
            if not col_red[:5].any():
                continue
            last, miss = None, 0
            for k in range(len(col_red)):
                if col_red[k]:
                    last, miss = k, 0
                else:
                    miss += 1
                    if miss > RED_GAP and last is not None:
                        break
            if last is None:
                continue
            hem = r0 + last + 1                       # crop row (edge below the last red row)
            # lace: from the hem down while lace-like; stops at 4 rows of skin / background
            k = hem
            end = hem
            run = 0
            while k < r1 + 12 and k < c.shape[0]:
                if lace[k, u]:
                    end, run = k + 1, 0
                elif skin[k, u] or bg[k, u] or red[k, u]:
                    run += 1
                    if run >= 4:
                        break
                k += 1
            rows_red.append([u + 0.5, float(hem - OFF[view])])
            rows_lace.append([u + 0.5, float(end - OFF[view])])
        out[view] = dict(hem=rows_red, lace=rows_lace)
    return out


def main():
    out = dict(torso=torso(), skirt=skirt())
    p = os.path.join(cfg.REFS, "profiles_m4.json")
    with open(p, "w") as fh:
        json.dump(out, fh)
    return p


if __name__ == "__main__":
    print(main())
