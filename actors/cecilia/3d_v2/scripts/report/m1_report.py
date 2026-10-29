"""Milestone 1 report: cross-view height check + front/back consistency.

Standalone Python 3 (numpy + Pillow), not Blender:
    python m1_report.py
Reads refs/ and refs/masks/ (make the masks first with scripts/ref_masks.py),
writes refs/landmarks.json and renders/m1_*.png.

Landmarks are measured automatically where the drawing allows it; the few
that need a human eye (knee, shoulder in the side view) are fixed values
marked "visual" with their uncertainty.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cfg  # noqa: E402

VIEWS = cfg.VIEW_ORDER


def font(size):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/arial.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_rgb(view):
    return np.asarray(Image.open(cfg.ref_path(view)).convert("RGB")).astype(int)


def load_mask(view):
    return np.asarray(Image.open(cfg.mask_path(view)).convert("L")) >= 128


def runs(row):
    c = np.where(row)[0]
    if len(c) == 0:
        return []
    br = np.where(np.diff(c) > 1)[0]
    return list(zip(np.r_[c[0], c[br + 1]].tolist(), np.r_[c[br], c[-1]].tolist()))


# ---------------------------------------------------------------- measurements
def m_top(view, m):
    return float(np.where(m.any(axis=1))[0].min())


def m_sole(view, m):
    return float(np.where(m.any(axis=1))[0].max() + 1)


def m_crown(view, m):
    """First row where the hair dome (not the ahoge) is wider than 20 px.
    Side view: the ahoge loop is a ~24 px wide run at cols 134-158, so the
    dome run must start left of col 130."""
    for r in range(10, 80):
        for a, b in runs(m[r]):
            if b - a + 1 > 20 and (view != "side" or a < 130):
                return float(r)


def m_chin_side(m):
    """Bottom edge of the separate chin run under the face (side view)."""
    last = None
    for r in range(130, 160):
        rs = [ab for ab in runs(m[r]) if ab[0] > 138]
        if rs:
            last = r
        elif last is not None:
            return float(last + 1)


def m_chin_front(rgb):
    """Darkest pixel of the jaw line on the centre columns, outer (lower) edge."""
    rows = []
    for c in range(266, 275):
        col = rgb[125:150, c, 1]
        rows.append(125 + int(np.argmin(col)))
    return float(np.median(rows) + 1)


def m_jacket_hem(view, rgb, m):
    dark = m & (rgb.max(axis=2) < 95)
    last = None
    for r in range(230, 270):
        rs = runs(m[r])
        a, b = max(rs, key=lambda t: t[1] - t[0])
        if dark[r, a:b + 1].mean() > 0.15:
            last = r
    return float(last + 1)


def m_waist(view, m):
    best = None
    for r in range(244, 262):
        rs = runs(m[r])
        a, b = max(rs, key=lambda t: t[1] - t[0])
        w = b - a + 1
        if best is None or w < best[0]:
            best = (w, r)
    return float(best[1] + 0.5), best[0]


def first_dark(rgb, m, c0, c1, r0, r1):
    dark = m & (rgb.max(axis=2) < 110)
    vals = []
    for c in range(c0, c1):
        rr = np.where(dark[r0:r1, c])[0]
        if len(rr):
            vals.append(r0 + rr.min())
    return float(np.median(vals))


def red_bottom(rgb, m, cols, r0=330, r1=400):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = m & (r > 120) & (r - g > 60) & (r - b > 50)
    vals = []
    for c in cols:
        rr = np.where(red[r0:r1, c])[0]
        if len(rr):
            vals.append(r0 + rr.max() + 1)
    return float(np.median(vals))


def cuff_ring_side(rgb, m):
    mn, mx = rgb.min(axis=2), rgb.max(axis=2)
    white = m & (mn > 200) & (mx - mn < 25)
    ys, xs = np.where(white[150:205, 90:145])
    X, Y = 90 + xs + 0.5, 150 + ys + 0.5
    A = np.c_[2 * X, 2 * Y, np.ones_like(X)]
    c = np.linalg.lstsq(A, X ** 2 + Y ** 2, rcond=None)[0]
    return float(c[1]), float(np.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)), float(c[0])


def cuff_front_back(rgb, m, c0, c1):
    mn, mx = rgb.min(axis=2), rgb.max(axis=2)
    w = m & (mn > 215) & (mx - mn < 20)
    ys, _ = np.where(w[140:200, c0:c1])
    return float((140 + ys.min() + 140 + ys.max() + 1) / 2.0)


def bow_centre(view, rgb, m):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = m & (r > 140) & (r - g > 70) & (r - b > 60)
    rows = []
    for rr in range(620, 675):
        rs = runs(red[rr])
        if rs and max(e - s + 1 for s, e in rs) >= 12:
            rows.append(rr)
    return float((rows[0] + rows[-1] + 1) / 2.0)


def narrowest_ankle(view, m):
    """Narrowest lower-leg width/depth in rows 590-632 (first leg found)."""
    best = None
    for r in range(596, 629):
        rs = runs(m[r])
        w = min(b - a + 1 for a, b in rs) if view != "side" else max(b - a + 1 for a, b in rs)
        if best is None or w < best[0]:
            best = (w, r)
    return float(best[1] + 0.5)


def measure():
    rgb = {v: load_rgb(v) for v in VIEWS}
    m = {v: load_mask(v) for v in VIEWS}
    L = []

    TOL = dict(head_top=1, crown=1, chin=1, shoulder=2, arm_axis=1, jacket_hem=1, waist=7, hem_front=1, hem_back=1,
               stocking_top=1, knee=5, sock_top=1, ankle_narrowest=99, bow=2, sole=0)

    def add(key, name, vals, method, conf, silhouette=None):
        L.append(dict(key=key, name=name, v=vals, method=method, confidence=conf, tol_px=TOL[key],
                      silhouette=silhouette))

    add("head_top", "Head top (ahoge tip)", {v: m_top(v, m[v]) for v in VIEWS},
        "top edge of the first mask row", "exact")
    add("crown", "Crown (hair, no ahoge)", {v: m_crown(v, m[v]) for v in VIEWS},
        "first row where the hair dome is wider than 20 px", "+-1 px")
    add("chin", "Chin", {"front": m_chin_front(rgb["front"]), "back": None, "side": m_chin_side(m["side"])},
        "front: outer edge of the jaw line at the centre; side: bottom of the chin silhouette; back: hidden by hair",
        "+-1 px")
    add("shoulder", "Shoulder (arm top)", {"front": 152.0, "back": 152.0, "side": 151.5},
        "front/back: arm top contour at the shoulder (rows 151-153); side: visual, top of jacket shoulder, partly hidden by hair",
        "+-1 px (side +-2, visual)")
    ring_v, ring_r, ring_u = cuff_ring_side(rgb["side"], m["side"])
    add("arm_axis", "Arm axis (cuff centre)",
        {"front": cuff_front_back(rgb["front"], m["front"], 110, 160),
         "back": cuff_front_back(rgb["back"], m["back"], 100, 160), "side": ring_v},
        "front/back: middle of the white cuff block; side: circle fit of the end-on cuff ring (r=%.1f px, u=%.1f)" % (ring_r, ring_u),
        "+-1 px")
    add("jacket_hem", "Jacket hem (side seams)", {v: m_jacket_hem(v, rgb[v], m[v]) for v in VIEWS},
        "last row where the black jacket covers >15 % of the torso width", "+-1 px")
    wf, wfw = m_waist("front", m["front"])
    wb, wbw = m_waist("back", m["back"])
    add("waist", "Waist (narrowest)", {"front": wf, "back": wb, "side": 254.0},
        "front/back: narrowest torso row (%d / %d px wide); side: middle of the flat 246-261 depth plateau (57-60 px deep)" % (wfw, wbw),
        "front/back +-1 px; side +-7 px")
    add("hem_front", "Skirt hem, front",
        {"front": red_bottom(rgb["front"], m["front"], range(262, 281)), "back": None,
         "side": red_bottom(rgb["side"], m["side"], range(158, 171))},
        "front: lowest red row at the centre (drawn line); side: red hem at the skirt's front extreme (silhouette)",
        "+-1 px", silhouette="side")
    add("hem_back", "Skirt hem, back",
        {"front": None, "back": red_bottom(rgb["back"], m["back"], range(256, 274)),
         "side": red_bottom(rgb["side"], m["side"], range(52, 64))},
        "back: lowest red row at the centre (drawn line); side: red hem at the skirt's back extreme (silhouette)",
        "+-1 px", silhouette="side")
    add("stocking_top", "Stocking top (R leg)",
        {"front": first_dark(rgb["front"], m["front"], 205, 250, 395, 440),
         "back": first_dark(rgb["back"], m["back"], 290, 326, 395, 440),
         "side": first_dark(rgb["side"], m["side"], 92, 140, 395, 440)},
        "median first dark row across the leg", "+-1 px")
    add("knee", "Knee", {"front": 490.0, "back": 484.0, "side": 480.0},
        "visual: front = kneecap/below-kneecap shading (left leg), back = knee crease lines, side = contour bend",
        "+-5 px (no sharp feature)")
    add("sock_top", "Sock top (L leg)",
        {"front": first_dark(rgb["front"], m["front"], 288, 320, 495, 540),
         "back": first_dark(rgb["back"], m["back"], 214, 246, 495, 540), "side": None},
        "median first dark row across the leg; side: far leg, hidden", "+-1 px")
    add("ankle_narrowest", "Ankle (narrowest leg)", {v: narrowest_ankle(v, m[v]) for v in VIEWS},
        "narrowest lower-leg width (front/back) or depth (side); NOT the same anatomical point in every view",
        "info only")
    add("bow", "Ankle (bow centre)", {"front": bow_centre("front", rgb["front"], m["front"]), "back": None,
                                    "side": bow_centre("side", rgb["side"], m["side"])},
        "middle of the rows where the bow is >12 px wide; back: hidden behind the heel", "+-2 px")
    add("sole", "Sole", {v: m_sole(v, m[v]) for v in VIEWS}, "bottom edge of the last mask row", "exact")

    for e in L:
        hs = {}
        for v in VIEWS:
            if e["v"].get(v) is None:
                hs[v] = None
            else:
                hpx = cfg.VIEWS[v]["sole_v"] - e["v"][v]
                hs[v] = dict(px=round(hpx, 1), m=round(hpx * cfg.PX, 4))
        e["height"] = hs
        vals = [h["px"] for h in hs.values() if h is not None]
        e["spread_px"] = round(max(vals) - min(vals), 1) if len(vals) > 1 else None
        e["spread_mm"] = round(e["spread_px"] * cfg.PX * 1000, 1) if e["spread_px"] is not None else None
    return L


# ---------------------------------------------------------------- figures
COL = {"front": (220, 40, 40), "back": (30, 110, 230), "side": (20, 150, 60)}


def height_figure(L, path):
    imgs = {v: Image.open(cfg.ref_path(v)).convert("RGB") for v in VIEWS}
    S = 1.0
    top_pad, left_pad, gap, table_w = 60, 230, 24, 560
    base = 695  # common sole row in the figure
    widths = [imgs[v].width for v in VIEWS]
    W = left_pad + sum(widths) + gap * 2 + table_w
    H = top_pad + 720
    out = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(out)
    f12, f14, f18 = font(12), font(14), font(18)
    x = left_pad
    xs = {}
    for v in VIEWS:
        off = base - cfg.VIEWS[v]["sole_v"]
        out.paste(imgs[v], (x, int(top_pad + off)))
        xs[v] = x
        d.text((x + 4, 30), v.upper(), fill=COL[v], font=f18)
        x += imgs[v].width + gap
    d.text((10, 8), "Cecilia refs, soles aligned (z = 0). 1 px = %.2f mm. Lines = front height; ticks = each view's own measurement." % (cfg.PX * 1000), fill=(0, 0, 0), font=f14)
    keys = ["head_top", "crown", "chin", "shoulder", "arm_axis", "jacket_hem", "waist", "hem_front", "hem_back",
            "stocking_top", "knee", "sock_top", "bow", "sole"]
    L = [e for e in L if e["key"] in keys]
    by = {e["key"]: e for e in L}
    ylab_used = []
    for k in keys:
        e = by[k]
        ref_v = next(e["v"][v] for v in VIEWS if e["v"].get(v) is not None)
        ref_h = next(e["height"][v]["px"] for v in VIEWS if e["height"].get(v) is not None)
        y = top_pad + base - ref_h
        d.line([(left_pad - 12, y), (left_pad - 2, y)], fill=(120, 120, 120), width=1)
        for v in VIEWS:
            hv = e["height"].get(v)
            if hv is None:
                continue
            yy = top_pad + base - hv["px"]
            for x0 in range(xs[v], xs[v] + imgs[v].width, 10):
                d.line([(x0, yy), (min(x0 + 5, xs[v] + imgs[v].width), yy)], fill=COL[v], width=1)
            d.line([(xs[v], yy - 4), (xs[v], yy + 4)], fill=COL[v], width=3)
            d.line([(xs[v] + imgs[v].width - 1, yy - 4), (xs[v] + imgs[v].width - 1, yy + 4)], fill=COL[v], width=3)
        ly = y - 7
        while any(abs(ly - u) < 13 for u in ylab_used):
            ly += 13
        ylab_used.append(ly)
        d.text((8, ly), e["name"][:30], fill=(0, 0, 0), font=f12)
    # table
    tx = left_pad + sum(widths) + 2 * gap + 10
    d.text((tx, 40), "Height above sole (px; 1 px = 2.32 mm)", fill=(0, 0, 0), font=f14)
    hdr = ["landmark", "front", "back", "side", "spread", "+-"]
    cx = [tx, tx + 200, tx + 255, tx + 310, tx + 370, tx + 480]
    for c, h in zip(cx, hdr):
        d.text((c, 64), h, fill=(0, 0, 0), font=f12)
    yy = 84
    for e in L:
        cells = [e["name"][:28]]
        for v in VIEWS:
            h = e["height"].get(v)
            cells.append("-" if h is None else "%.1f" % h["px"])
        sp = "-" if e["spread_px"] is None else "%.1f px  %.0f mm" % (e["spread_px"], e["spread_mm"])
        cells.append(sp)
        cells.append("%d" % e["tol_px"])
        bad = e["spread_px"] is not None and e["spread_px"] > 3 and e["spread_px"] > e["tol_px"]
        for c, t in zip(cx, cells):
            d.text((c, yy), t, fill=(200, 0, 0) if (bad and c == cx[-2]) else (0, 0, 0), font=f12)
        yy += 18
    d.text((tx, yy + 10), "red = views disagree by more than 3 px and more than", fill=(200, 0, 0), font=f12)
    d.text((tx, yy + 26), "the measuring uncertainty (+- column, px)", fill=(200, 0, 0), font=f12)
    out.save(path)


def front_back(path):
    F, B = load_mask("front"), load_mask("back")
    cf, cb = cfg.VIEWS["front"], cfg.VIEWS["back"]
    S = 10
    xs = np.arange(-300 * S, 300 * S) / S + 0.5 / S
    rows = np.arange(0, 706)                       # front rows; z = sole_f - (row+0.5)

    def sample(mask, u, vshift):
        ui = np.floor(u).astype(int)
        ok = (ui >= 0) & (ui < mask.shape[1])
        out = np.zeros((len(rows), len(u)), bool)
        src_rows = rows - vshift
        okr = (src_rows >= 0) & (src_rows < mask.shape[0])
        sub = mask[src_rows[okr]][:, ui[ok]]
        tmp = np.zeros((okr.sum(), len(u)), bool)
        tmp[:, ok] = sub
        out[okr] = tmp
        return out
    Ff = sample(F, xs + cf["centre_u"], 0)
    Bf = sample(B, cb["centre_u"] - xs, int(round(cf["sole_v"] - cb["sole_v"])))
    A = (Ff & Bf).sum() / S
    fo = (Ff & ~Bf).sum() / S
    bo = (Bf & ~Ff).sum() / S
    iou = A / (A + fo + bo)
    best = (0,)
    for x in np.linspace(0, fo, 300):
        for y in np.linspace(0, bo, 300):
            i1 = (A + x) / (A + fo + y)
            i2 = (A + y) / (A + bo + x)
            mm = min(i1, i2)
            if mm > best[0]:
                best = (mm, i1, i2)
    # diff picture at 1 px (take every S-th fine column)
    Fp, Bp = Ff[:, ::S], Bf[:, ::S]
    cols = np.where((Fp | Bp).any(axis=0))[0]
    c0, c1 = max(cols.min() - 15, 0), cols.max() + 15
    Fp, Bp = Fp[:, c0:c1], Bp[:, c0:c1]
    img = np.zeros(Fp.shape + (3,), np.uint8)
    img[Fp & Bp] = (255, 255, 255)
    img[Fp & ~Bp] = (255, 0, 0)
    img[Bp & ~Fp] = (0, 90, 255)
    im = Image.fromarray(img)
    im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    canvas = Image.new("RGB", (im.width, im.height + 90), (0, 0, 0))
    canvas.paste(im, (0, 90))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), "FRONT mask vs MIRRORED BACK mask (what one 3D model would have to satisfy)", fill=(255, 255, 255), font=font(16))
    d.text((10, 32), "white = both   red = front only   blue = back only", fill=(255, 255, 255), font=font(14))
    d.text((10, 54), "IoU %.3f.  Best any single model can score in BOTH views: %.3f" % (iou, best[0]), fill=(255, 220, 0), font=font(14))
    canvas.save(path)
    bands = []
    for r0, r1, name in [(0, 150, "head/hair"), (150, 192, "arms"), (192, 252, "jacket"), (252, 390, "skirt+sword"),
                         (390, 630, "legs"), (630, 706, "feet")]:
        a, b = Ff[r0:r1], Bf[r0:r1]
        bands.append(dict(band=name, rows=[r0, r1], iou=round(float((a & b).sum() / max((a | b).sum(), 1)), 3),
                          front_only_px=round(float((a & ~b).sum() / S)), back_only_px=round(float((b & ~a).sum() / S))))
    return dict(iou=round(float(iou), 4), ceiling_both=round(float(best[0]), 4),
                front_only_px=round(float(fo)), back_only_px=round(float(bo)), both_px=round(float(A)), bands=bands)


def mask_figure(path):
    tiles = []
    for v in VIEWS:
        rgb = np.asarray(Image.open(cfg.ref_path(v)).convert("RGB")).copy()
        m = load_mask(v)
        edge = m & ~(np.pad(m, 1)[2:, 1:-1] & np.pad(m, 1)[:-2, 1:-1] & np.pad(m, 1)[1:-1, 2:] & np.pad(m, 1)[1:-1, :-2])
        rgb[edge] = (255, 0, 255)
        tiles.append(Image.fromarray(rgb))
    W = sum(max(t.width, 330) for t in tiles) + 20 * 2
    out = Image.new("RGB", (W, tiles[0].height + 30), (255, 255, 255))
    d = ImageDraw.Draw(out)
    x = 0
    for v, t in zip(VIEWS, tiles):
        out.paste(t, (x, 30))
        d.text((x + 4, 6), "%s mask edge (magenta), %d px" % (v, load_mask(v).sum()), fill=(0, 0, 0), font=font(14))
        x += max(t.width, 330) + 20
    out.save(path)


def main():
    os.makedirs(cfg.RENDERS, exist_ok=True)
    L = measure()
    fb = front_back(os.path.join(cfg.RENDERS, "m1_front_vs_backmirror.png"))
    height_figure(L, os.path.join(cfg.RENDERS, "m1_height_check.png"))
    mask_figure(os.path.join(cfg.RENDERS, "m1_masks.png"))
    data = dict(px_m=cfg.PX, height_m=cfg.HEIGHT_M, views=cfg.VIEWS, landmarks=L, front_vs_back_mirror=fb,
                note="v = continuous image row (0 = top edge of the crop). height px = sole_v - v.")
    with open(os.path.join(cfg.REFS, "landmarks.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    return data


if __name__ == "__main__":
    d = main()
    for e in d["landmarks"]:
        print("%-34s %s  spread %s px / %s mm" % (e["name"], {k: (None if h is None else h["px"]) for k, h in e["height"].items()}, e["spread_px"], e["spread_mm"]))
    print(json.dumps(d["front_vs_back_mirror"], indent=1))
