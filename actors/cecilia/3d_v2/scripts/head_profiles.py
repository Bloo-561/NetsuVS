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
LOWER_GAP = 10            # rows of no hair bridged when tracing where hair ends (a stray strand
                          # above a flicked-out lock; ears/background gaps are longer) ...
FACE_COLS_GAP = {"front": (236, 304), "side": (134, 182)}   # ... but only 2 across the face/bangs
CROWN_ROWS = 45           # front rows above which ring extents use the longest run only
HOLD_FRONT_ROW = 96       # front row from which the hair rings' front extent is held
TAPER_ROW = 110           # front row from which the hair rings' hem taper is limited
TAPER_RATE = 0.8          # px per row, width (front/back views): the drawn lock taper
TAPER_RATE_Y = 2.0        # px per row, depth (side view): the drawn nape curl
LOCK_RAMP = 14            # rows over which the temple steps back from the bangs to the side lock
CHIN_ROW = 141            # last front row of the face (chin bottom)
JAW_ROW = 136             # front row where the jaw underside starts to come forward (side view)
CHIN_BACK_U = 150         # side-view column of the chin's underside at the chin row
NOSE_ROWS = (113, 122)    # front rows the nose bump spans in the side profile
BROW_ROW = 106            # front row of the brow line in the side profile (above it: lashes)
PROFILE_BELOW_BANGS = 111 # front row from which the side silhouette is the face profile (bangs end)
FACE_TOP_ROW = 76         # face rings start under the bangs (forehead held from the brow row)
EAR_SEED = (110, 106)     # side view (u, front row) inside the ear
EYE_ROWS = (96, 126)      # front rows of the eyes (lashes to lower lid)
EYE_COLS = {"front": (236, 304), "side": (134, 168), "back": (0, 0)}   # face columns
W_FRONT = 0.30            # head rings: front/back edge blend. The body uses 0.45 (profiles.py); the
                          # head's hem tips disagree more between front and back, and 0.30 lands
                          # both views' whole-figure IoU above 0.95 (front 0.9522, back 0.9503)


# ----------------------------------------------------------------------------- image helpers
def load(view):
    rgb = imgio.load(cfg.ref_path(view), channels=3).astype(np.int32)
    return rgb, imgio.load_mask(cfg.mask_path(view))


def classes(view):
    a, m = load(view)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    rows = np.arange(a.shape[0])[:, None] - OFF[view]
    cols = np.arange(a.shape[1])[None, :]
    in_face = (cols >= EYE_COLS[view][0]) & (cols < EYE_COLS[view][1])
    purple = (r - g > 25) & (b - g > 25) & (r > 55)
    dark = mx < 125
    teal = (g - r > 15) & (b - r > 15)
    # eyes: orange/red iris and the red-brown lashes (the bangs are neutral
    # grey-black, the lashes clearly red: R - G >= 0.4 R), eye rows only
    eye = m & in_face & (rows >= EYE_ROWS[0]) & (rows < EYE_ROWS[1]) & ~purple & (
        ((r - g > 40) & (r > 90) & (b < 0.75 * r)) | (dark & (r - g >= 0.4 * r) & (r - g >= 6)))
    hair = m & (purple | (dark & (rows < JACKET_ROW)) | (teal & (rows < 90))) & ~eye
    skin = m & (r > 200) & (g > 145) & (b > 120) & (r - b > 10) & (r - b < 100) & (r >= g)
    skin_light = m & (mn > 230) & (r >= b) & (r - b < 25)
    ear = np.zeros_like(m)
    if view == "side":
        # the ear (side view only): skin patch around EAR_SEED plus its outline
        seed = np.zeros_like(m)
        seed[EAR_SEED[1] + OFF["side"], EAR_SEED[0]] = True
        e = grow(seed, (skin | skin_light) & erode3(m))
        if 10 <= e.sum() <= 600:
            ear = fill_holes(dilate3(e)) & m
            hair &= ~ear
    band = m & (((r > 150) & (r - g > 70) & (r - b > 60)) | ((r > 180) & (g > 120) & (b < 110) & (r - b > 90)))
    clip = m & teal
    return dict(rgb=a, mask=m, hair=hair, skin=skin, skin_light=skin_light, band=band, clip=clip, eye=eye,
                ear=ear)


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
    skin = (c["skin"] | c["skin_light"] | c["eye"]) & erode3(c["mask"])
    band = np.zeros_like(skin)
    band[rows[0]:rows[1]] = True
    seed = np.zeros_like(skin)
    seed[seed_uv[1], seed_uv[0]] = True
    f = grow(seed, skin & band)
    f = fill_holes(f)
    f = erode3(dilate3(f))          # closing
    return fill_holes(f)


def face_gg(C):
    """smooth face description per front row (FACE_TOP_ROW .. CHIN_ROW), for the
    sculpted face of build_head.face_mesh:
      xc, hw   centre and half-width (front view's face outline; held at the
               eye-level width above row 104, where the bangs cover it)
      yp       centre-line profile incl. the nose (side view silhouette below
               the bangs, the face's front edge under them, held above row 95)
      ybase    the same with the nose taken out (interpolated over it)
      ys       how far back the face's sides go (side view: the skin's back
               edge, i.e. the side lock's front; at the chin the jaw underside)
    all world metres; smoothed ([1 2 1]/4) so the surface has no pixel steps"""
    fr = face_region("front", (270, 125))
    sr = face_region("side", (158, 125))
    m = C["side"]["mask"]
    rows = np.arange(FACE_TOP_ROW, CHIN_ROW + 1)
    xc, hw, yp, ys = [], [], [], []
    for r in rows:
        f = ext(fr[r])
        if f and r >= 104:
            xc.append(pr.fx((f[0] + f[1] + 1) / 2.0)); hw.append((f[1] + 1 - f[0]) / 2.0 * P)
        else:
            xc.append(np.nan); hw.append(np.nan)
        rr = r + OFF["side"]
        s = ext(sr[rr])
        if r >= PROFILE_BELOW_BANGS:
            mm = np.where(m[rr, 100:200])[0]
            yp.append(pr.sy(100 + int(mm.max()) + 1) if len(mm) else np.nan)
        elif s and r >= 95:
            yp.append(pr.sy(s[1] + 2))                         # face front edge + its outline
        else:
            yp.append(np.nan)
        ys.append(pr.sy(s[0]) if s else np.nan)
    xc, hw, yp, ys = (np.array(a, float) for a in (xc, hw, yp, ys))
    i104 = int(np.where(rows == 104)[0][0])
    hw[:i104] = np.nanmax(hw[i104:i104 + 10])
    xc[:i104] = np.nanmean(xc[i104:i104 + 10])
    # above the eye line the side view's face edge is eyelashes, not face:
    # hold the profile at the brow (anime foreheads are near vertical under bangs)
    ib = int(np.where(rows == BROW_ROW)[0][0])
    yp[:ib] = yp[ib]
    i95 = int(np.where(rows == 95)[0][0])
    ys[:i95] = ys[i95]
    xc, hw, yp, ys = (pr.fill_nans(a) for a in (xc, hw, yp, ys))
    # jaw underside: the side view's skin ends at the jaw line, which runs from
    # behind the cheek forward to the chin over the last rows
    ij = int(np.where(rows == JAW_ROW)[0][0])
    ys[ij:] = np.linspace(ys[ij], pr.sy(CHIN_BACK_U), len(rows) - ij)
    # nose: out of the base profile
    i0, i1 = (int(np.where(rows == r)[0][0]) for r in NOSE_ROWS)
    ybase = yp.copy()
    ybase[i0:i1 + 1] = np.linspace(yp[i0], yp[i1], i1 - i0 + 1)
    # one centre line for the whole face (the drawn face is symmetric; the
    # traced centre only wobbles by the outline's pixel steps)
    xc[:] = float(np.median(xc[i104:]))
    hw, ys = pr.smooth(hw, 2), pr.smooth(ys, 2)
    yp, ybase = pr.smooth(yp, 1), pr.smooth(ybase, 2)
    return dict(z=[pr.zc(r) for r in rows], xc=xc.tolist(), hw=hw.tolist(), yp=yp.tolist(),
                ybase=ybase.tolist(), ys=ys.tolist(), rows=rows.tolist())


def lower_boundary(cover, gap=2, max_row=160, start_row=0, min_len=6, stray_end=60, gaps=None):
    """per column: last row of the first contiguous covered run from the top
    (scanning from start_row, i.e. below the ahoge), bridging up to `gap`
    uncovered rows (per-column override in `gaps`). Short runs ending above
    stray_end (pieces of the ahoge loop hanging below start_row) are skipped."""
    H, W = cover.shape
    out = np.full(W, -1, int)
    for c in range(W):
        gap_c = gaps[c] if gaps is not None else gap
        col = cover[:max_row, c].copy()
        col[:start_row] = False
        r = start_row
        while True:
            idx = np.where(col[r:])[0]
            if len(idx) == 0:
                break
            first = r + idx[0]
            r = last = first
            miss = 0
            while r < max_row - 1:
                r += 1
                if col[r]:
                    last, miss = r, 0
                else:
                    miss += 1
                    if miss > gap_c:
                        break
            if last - first + 1 < min_len and last < stray_end:
                r = last + 1
                continue
            out[c] = last
            break
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
def main_run(row):
    """extent of the longest run in a row (the dome, not ahoge pieces beside it)"""
    c = np.where(row)[0]
    if len(c) == 0:
        return None
    br = np.where(np.diff(c) > 1)[0]
    starts = np.r_[c[0], c[br + 1]]
    ends = np.r_[c[br], c[-1]]
    k = int(np.argmax(ends - starts))
    return int(starts[k]), int(ends[k])


def hair_rings(C):
    rings = []
    for r in range(31, 148):
        ex = main_run if r < CROWN_ROWS else ext            # crown: skip the ahoge stem beside the dome
        f = ex(C["front"]["hair"][r] | C["front"]["band"][r] | C["front"]["clip"][r])
        b = ex(C["back"]["hair"][r + OFF["back"]])
        s_all = ex(C["side"]["hair"][r + OFF["side"]] | C["side"]["band"][r + OFF["side"]] |
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
    rings = pr.smooth_rings(rings, 2)
    # hem: below TAPER_ROW the extents may shrink by at most TAPER_RATE(_Y) px
    # per row, the drawn taper of the locks (and the nape curl in depth).
    # Faster shrinking is just the last tips ending: the column ends trace
    # those, so it must not pull the whole curtain inward.
    lim, lim_y = TAPER_RATE * P, TAPER_RATE_Y * P
    rings = sorted(rings, key=lambda q: -q[0])
    # below the bangs the box front is held (never retreats): the bangs ending
    # must not shift the whole curtain backwards; build_head cuts everything in
    # front of the side locks / face instead
    for i in range(1, len(rings)):
        if rings[i][0] <= pr.zc(HOLD_FRONT_ROW):
            rings[i][3] = min(rings[i][3], rings[i - 1][3])
    for i in range(1, len(rings)):
        if pr.zc(TAPER_ROW) < rings[i][0]:
            continue
        a, b = rings[i - 1], rings[i]
        b[1] = min(b[1], a[1] + lim)
        b[2] = max(b[2], a[2] - lim)
        b[3] = min(b[3], a[3] + lim_y)
        b[4] = max(b[4], a[4] - lim_y)
    return rings


def face(C):
    fr = face_region("front", (270, 125))
    sr = face_region("side", (158, 125))
    rows = np.arange(FACE_TOP_ROW, 142)
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


def side_lock(C, ramp=LOCK_RAMP):
    """per front row: front edge (world y) of the hair just behind the face in
    the side view, i.e. the side lock's front edge. Where the side view shows
    the face (temple, cheek, jaw) between the bangs and the side locks, no hair
    may be further forward than this outside the face's width, or it would
    cover skin the side view shows. Rows above the first such row ramp from
    the hair front to it. Returns [[z, y_lock], ...] top to bottom."""
    s = C["side"]
    cover = s["hair"] | s["band"] | s["clip"]
    fr = face_region("side", (158, 125))
    rows, ys = [], []
    for r in range(70, 150):
        rr = r + OFF["side"]
        f = np.where(fr[rr])[0]
        if len(f) == 0:
            continue
        h = np.where(cover[rr, :f.min()])[0]
        if len(h) == 0:
            continue
        rows.append(r)
        ys.append(pr.sy(int(h.max()) + 1))
    ys = np.array(ys, float)
    for _ in range(2):                                   # [1, 2, 1] / 4
        p = np.pad(ys, 1, mode="edge")
        ys = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
    out = [[pr.zc(r), float(y)] for r, y in zip(rows, ys)]
    # ramp above the first row: from the hair's front (no cut) to the lock
    hr = {round(q[0], 6): q for q in hair_rings(C)}
    r0 = rows[0]
    yf0 = hr[min(hr, key=lambda z: abs(z - pr.zc(r0 - ramp)))][3]
    head = []
    for k in range(ramp, 0, -1):
        t = 1.0 - k / float(ramp)
        head.append([pr.zc(r0 - k), float(yf0 + (ys[0] - yf0) * t)])
    return head + out


def lower_boundaries(C):
    out = {}
    for v in ("front", "back", "side"):
        cover = C[v]["hair"] | C[v]["band"] | C[v]["clip"] | C[v]["ear"]   # hair runs on behind the ear
        gaps = np.full(cover.shape[1], LOWER_GAP)
        lo, hi = FACE_COLS_GAP.get(v, (0, 0))
        gaps[lo:hi] = 2                     # bangs over the face: separate tips stay separate
        out[v] = lower_boundary(cover, start_row=31 + OFF[v], gaps=gaps).tolist()
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
                lock=side_lock(C), face_gg=face_gg(C), headband=headband(C), clips=clips(C), ear=ear(C),
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
