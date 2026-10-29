"""Milestone 3: head, face and hair profiles traced from the reference crops.

numpy only (runs in Blender or plain Python). Writes refs/profiles_head.json
for build_head.py. Rows are FRONT-crop rows (back = r-1, side = r+1), world
coords as in cfg.py / profiles.py.

Colour classes in the head region (checked by eye, see renders/m3_*):
  hair  = magenta-purple (R-G > 25 and B-G > 25) anywhere, or dark (max < 125)
          above the jacket line (front row 138); the lower hair is purple, the
          jacket is neutral grey, which is what separates them.
  skin  = light peach; face region = the connected skin area around the
          cheek, with holes (eyes, mouth) filled.
  band  = red/yellow (headband + its mark); clip = teal.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402
import profiles as pr  # noqa: E402

P = cfg.PX
OFF = {"front": 0, "back": pr.D_BACK, "side": pr.D_SIDE}   # image row = front row + OFF
JACKET_ROW = 138          # front rows: below this, dark-neutral pixels are the jacket, not hair
W_FRONT = pr.W_FRONT


# ----------------------------------------------------------------------------- image helpers
def load(view):
    rgb = imgio.load(cfg.ref_path(view), channels=3).astype(np.int32)
    return rgb, imgio.load_mask(cfg.mask_path(view))


def classes(view):
    a, m = load(view)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    rows = np.arange(a.shape[0])[:, None] - OFF[view]
    purple = (r - g > 25) & (b - g > 25) & (r > 55)
    dark = mx < 125
    teal = (g - r > 15) & (b - r > 15)
    hair = m & (purple | (dark & (rows < JACKET_ROW)) | (teal & (rows < 90)))
    skin = m & (r > 200) & (g > 145) & (b > 120) & (r - b > 10) & (r - b < 100) & (r >= g)
    skin_light = m & (mn > 230) & (r >= b) & (r - b < 25)
    band = m & (((r > 150) & (r - g > 70) & (r - b > 60)) | ((r > 180) & (g > 120) & (b < 110) & (r - b > 90)))
    clip = m & teal
    return dict(rgb=a, mask=m, hair=hair, skin=skin, skin_light=skin_light, band=band, clip=clip)


def erode3(m):
    p = np.pad(m, 1, constant_values=False)
    h, w = m.shape
    out = np.ones_like(m)
    for dy in range(3):
        for dx in range(3):
            out &= p[dy:dy + h, dx:dx + w]
    return out


def dilate3(m):
    p = np.pad(m, 1, constant_values=False)
    h, w = m.shape
    out = np.zeros_like(m)
    for dy in range(3):
        for dx in range(3):
            out |= p[dy:dy + h, dx:dx + w]
    return out


def grow(seed, allowed):
    """4-connected geodesic fill of `allowed` from `seed`."""
    cur = seed & allowed
    while True:
        prev = cur
        for _ in range(16):
            g = cur.copy()
            g[1:, :] |= cur[:-1, :]
            g[:-1, :] |= cur[1:, :]
            g[:, 1:] |= cur[:, :-1]
            g[:, :-1] |= cur[:, 1:]
            cur = g & allowed
        if np.array_equal(cur, prev):
            return cur


def fill_holes(m):
    border = np.zeros_like(m)
    border[0, :] = border[-1, :] = True
    border[:, 0] = border[:, -1] = True
    outside = grow(border & ~m, ~m)
    return ~outside


def face_region(view, seed_uv, rows=(70, 150)):
    c = classes(view)
    skin = (c["skin"] | c["skin_light"]) & erode3(c["mask"])
    band = np.zeros_like(skin)
    band[rows[0]:rows[1]] = True
    seed = np.zeros_like(skin)
    seed[seed_uv[1], seed_uv[0]] = True
    f = grow(seed, skin & band)
    f = fill_holes(f)
    f = erode3(dilate3(f))          # closing
    return fill_holes(f)


def lower_boundary(cover, gap=2, max_row=160, start_row=0):
    """per column: last row of the first contiguous covered run from the top
    (scanning from start_row, i.e. below the ahoge)"""
    H, W = cover.shape
    out = np.full(W, -1, int)
    for c in range(W):
        col = cover[:max_row, c].copy()
        col[:start_row] = False
        idx = np.where(col)[0]
        if len(idx) == 0:
            continue
        r = last = idx[0]
        miss = 0
        while r < max_row - 1:
            r += 1
            if col[r]:
                last, miss = r, 0
            else:
                miss += 1
                if miss > gap:
                    break
        out[c] = last
    return out


def ext(row):
    c = np.where(row)[0]
    return (int(c.min()), int(c.max())) if len(c) else None


def blobs(m, min_px=20):
    """bounding boxes of 4-connected blobs (rows, cols) of at least min_px pixels"""
    left = m.copy()
    out = []
    while left.any():
        ys, xs = np.where(left)
        seed = np.zeros_like(left)
        seed[ys[0], xs[0]] = True
        b = grow(seed, left)
        left &= ~b
        if b.sum() >= min_px:
            ys, xs = np.where(b)
            out.append(dict(px=int(b.sum()), r0=int(ys.min()), r1=int(ys.max()) + 1, c0=int(xs.min()),
                            c1=int(xs.max()) + 1, cy=float(ys.mean() + 0.5), cx=float(xs.mean() + 0.5)))
    return out


# ----------------------------------------------------------------------------- profiles
def hair_rings(C):
    rings = []
    for r in range(31, 148):
        f = ext(C["front"]["hair"][r] | C["front"]["band"][r] | C["front"]["clip"][r])
        b = ext(C["back"]["hair"][r + OFF["back"]])
        s_all = ext(C["side"]["hair"][r + OFF["side"]] | C["side"]["band"][r + OFF["side"]] |
                    C["side"]["clip"][r + OFF["side"]])
        if s_all is None:
            continue
        if f is None and b is None:
            f = b = rings_last_x
        elif f is None:
            f = (None, None)
        if b is None:
            b = (None, None)
        xs_lo, xs_hi = [], []
        if f[0] is not None:
            xs_lo.append(("f", pr.fx(f[0]))); xs_hi.append(("f", pr.fx(f[1] + 1)))
        if b[0] is not None:
            xs_lo.append(("b", pr.bx(b[1] + 1))); xs_hi.append(("b", pr.bx(b[0])))

        def mix(lst):
            d = dict(lst)
            if "f" in d and "b" in d:
                return W_FRONT * d["f"] + (1 - W_FRONT) * d["b"]
            return list(d.values())[0]
        x0, x1 = mix(xs_lo), mix(xs_hi)
        rings_last_x = f if f[0] is not None else b
        y_back = pr.sy(s_all[0])
        y_front = pr.sy(s_all[1] + 1)
        rings.append([pr.zc(r), float(x0), float(x1), float(y_front), float(y_back)])
    return pr.smooth_rings(rings, 2)


def face(C):
    fr = face_region("front", (270, 125))
    sr = face_region("side", (158, 125))
    rows = np.arange(86, 142)
    yfront, yside, xc, hw = [], [], [], []
    for r in rows:
        s = ext(sr[r + OFF["side"]])
        f = ext(fr[r])
        yfront.append(pr.sy(s[1] + 1) if s else np.nan)
        yside.append(pr.sy(s[0]) if s else np.nan)
        if f and r >= 104:
            xc.append(pr.fx((f[0] + f[1] + 1) / 2.0)); hw.append((f[1] + 1 - f[0]) / 2.0 * P)
        else:
            xc.append(np.nan); hw.append(np.nan)
    yfront, yside, xc, hw = map(lambda a: np.array(a, float), (yfront, yside, xc, hw))
    # forehead/temples under the bangs (rows 86-97): only slivers of skin show
    # between the bang tips, so hold the brow-level (row 98) face front and
    # cheek depth straight up (anime foreheads are near vertical under bangs)
    i98 = int(np.where(rows == 98)[0][0])
    yfront[:i98] = yfront[i98]
    yside[:i98] = yside[i98]
    yfront = pr.fill_nans(yfront)
    yside = pr.fill_nans(yside)
    # temples/forehead (rows 86-103, partly under bangs): face as wide as at the eyes
    i104 = int(np.where(rows == 104)[0][0])
    hw[:i104] = np.nanmax(hw[i104:i104 + 10])
    xc[:i104] = np.nanmean(xc[i104:i104 + 10])
    hw, xc = pr.fill_nans(hw), pr.fill_nans(xc)
    # nose: the profile bump between rows 112 and 122 -> face plane interpolated across it
    i0, i1 = int(np.where(rows == 112)[0][0]), int(np.where(rows == 122)[0][0])
    plane = yfront.copy()
    plane[i0:i1 + 1] = np.linspace(yfront[i0], yfront[i1], i1 - i0 + 1)
    nose = []
    for i in range(i0, i1 + 1):
        if yfront[i] < plane[i] - 0.5 * P:
            nose.append([pr.zc(rows[i]), float(xc[i]), float(plane[i]), float(yfront[i])])
    rings = [[pr.zc(r), float(xc[i] - hw[i]), float(xc[i] + hw[i]), float(plane[i]), float(yside[i])]
             for i, r in enumerate(rows)]
    return dict(rings=rings, nose=nose, chin_row=141)


def lower_boundaries(C):
    out = {}
    for v in ("front", "back", "side"):
        cover = C[v]["hair"] | C[v]["band"] | C[v]["clip"]
        out[v] = lower_boundary(cover, start_row=31 + OFF[v]).tolist()
    return out


def headband(C):
    f = C["front"]["band"]
    cols = {}
    for c in range(240, 305):
        rr = np.where(f[40:80, c])[0]
        if len(rr) >= 2:
            cols[c] = (40 + int(rr.min()), 40 + int(rr.max()) + 1)
    s = C["side"]["band"]
    scol = {}
    for c in range(130, 185):
        rr = np.where(s[40:80, c])[0]
        if len(rr) >= 2:
            scol[c] = (40 + int(rr.min()) - OFF["side"], 40 + int(rr.max()) + 1 - OFF["side"])
    return dict(front={str(k): v for k, v in cols.items()}, side={str(k): v for k, v in scol.items()})


def clips(C):
    fb = [b for b in blobs(C["front"]["clip"][:75]) if b["px"] >= 30]
    sb = [b for b in blobs(C["side"]["clip"][:75]) if b["px"] >= 30]
    return dict(front=fb, side=sb)


def ear(C):
    """the ear's skin patch in the side view (separate from the face region)"""
    s = C["side"]
    skin = (s["skin"] | s["skin_light"]) & erode3(s["mask"])
    seed = np.zeros_like(skin)
    seed[106 + OFF["side"], 110] = True
    e = grow(seed, skin)
    if e.sum() < 10 or e.sum() > 600:
        return None
    ys, xs = np.where(e)
    return dict(r0=int(ys.min()) - OFF["side"], r1=int(ys.max()) + 1 - OFF["side"], u0=int(xs.min()), u1=int(xs.max()) + 1)


def main():
    C = {v: classes(v) for v in cfg.VIEW_ORDER}
    data = dict(px_m=P, hair_rings=hair_rings(C), lower=lower_boundaries(C), face=face(C),
                headband=headband(C), clips=clips(C), ear=ear(C),
                neck=dict(z0=pr.zc(152), z1=pr.zc(126), half_w=14.0 * P, y0=-0.016, y1=0.060),
                views={v: dict(centre_u=cfg.VIEWS[v]["centre_u"], sole_v=cfg.VIEWS[v]["sole_v"]) for v in cfg.VIEW_ORDER},
                jacket_row=JACKET_ROW)
    path = os.path.join(cfg.REFS, "profiles_head.json")
    with open(path, "w") as fh:
        json.dump(data, fh)
    return path, data


if __name__ == "__main__":
    p, d = main()
    print(p, len(d["hair_rings"]), d["clips"], d["ear"])
