"""Milestone 5: measurements behind bake.py's drawn patterns (numpy only; runs
inside or outside Blender).

ribbons(): the right stocking's three X bands. In each view (front, back,
  side) and band, a grid search fits (crossing row h, upper arm reach up,
  lower arm reach down, ribbon width w, tilt t) to the sheet's red pixels on
  the leg: upper arms at row h + t*x_n - up*|x_n|, lower arms h + t*x_n +
  down*|x_n| (x_n: -1..1 across the leg in that row), scored by IoU. The
  views draw the X at the same heights; their mean (h, up, down) per band and
  the mean width are bake.RIBBON_BANDS / RIBBON_W. (The tilt only helps the
  fit at the knee, where each view draws the X skewed a different way; it is
  not used.)
stripes(): the skirt's two white stripes. Per column, the two brightness
  peaks (min channel) nearest the traced red hem (profiles_m4.json), with
  sub-pixel peak positions and their full width at half the peak's height
  above the red; the mean over the three views is bake.STRIPES / STRIPE_W.
Run: python fit_patterns.py   (prints both; ~2 min)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bake  # noqa: E402
import cfg  # noqa: E402
import imgio  # noqa: E402

OFF = {"front": 0, "back": -1, "side": 1}          # crop row = front row + OFF
LEG_COLS = {"front": (178, 262), "back": (290, 352), "side": (68, 148)}   # the stocking leg in each crop
BANDS = [(414, 470), (490, 552), (580, 628)]       # front rows around each X
FIRST = [(448.5, 27, 16), (527, 18, 20), (608, 17, 12)]   # search centres (rough reading of the sheet)


def _leg_rows(view, b0, b1, fig, red):
    c0, c1 = LEG_COLS[view]
    rows = np.arange(b0, b1) + OFF[view]
    L, R = [], []
    for r in rows:
        xs = np.where(fig[r, c0:c1])[0] + c0
        br = np.where(np.diff(xs) > 1)[0]
        runs = list(zip(np.r_[xs[0], xs[br + 1]], np.r_[xs[br], xs[-1]] + 1))
        a, b = max(runs, key=lambda t: t[1] - t[0])
        L.append(a)
        R.append(b)
    L, R = np.array(L, float), np.array(R, float)
    cc, hw = (L + R) / 2, (R - L) / 2
    U = np.arange(c0, c1) + 0.5
    XN = (U[None, :] - cc[:, None]) / hw[:, None]
    inside = np.abs(XN) <= 0.92
    RR = (rows - OFF[view] + 0.5)[:, None] * np.ones_like(XN)
    target = red[rows][:, c0:c1] & inside
    return XN, inside, RR, target, hw


def _score(p, XN, inside, RR, target, hw):
    h, up, dn, w, t = p
    hh = h + t * XN
    du = np.abs(RR - (hh - up * np.abs(XN))) / np.sqrt(1 + (up / hw[:, None]) ** 2)
    dl = np.abs(RR - (hh + dn * np.abs(XN))) / np.sqrt(1 + (dn / hw[:, None]) ** 2)
    pred = ((du < w / 2) | (dl < w / 2)) & inside
    return (pred & target).sum() / max((pred | target).sum(), 1)


def ribbons():
    per_view = {}
    for view in ("front", "back", "side"):
        clean, line, fig = bake.sheet(view)
        lab = bake.classify(clean.reshape(-1, 3), ["legwear", "red", "skin", "loafer"]).reshape(fig.shape)
        red = (lab == 1) & fig
        out = []
        for (b0, b1), (h0, u0, d0) in zip(BANDS, FIRST):
            A = _leg_rows(view, b0, b1, fig, red)
            best = (-1.0, None)
            for h in np.arange(h0 - 6, h0 + 6.1, 1.0):              # coarse
                for up in np.arange(max(8, u0 - 10), u0 + 10.1, 2.0):
                    for dn in np.arange(max(6, d0 - 10), d0 + 10.1, 2.0):
                        for w in (5.0, 6.0, 7.0, 8.0):
                            for t in (-6, -4, -2, 0, 2, 4, 6):
                                s = _score((h, up, dn, w, t), *A)
                                if s > best[0]:
                                    best = (s, (h, up, dn, w, t))
            h1, u1, d1, w1, t1 = best[1]
            for h in np.arange(h1 - 1, h1 + 1.01, 0.5):              # fine
                for up in np.arange(u1 - 2, u1 + 2.01, 1.0):
                    for dn in np.arange(d1 - 2, d1 + 2.01, 1.0):
                        for w in np.arange(w1 - 1, w1 + 1.01, 0.5):
                            for t in np.arange(t1 - 2, t1 + 2.01, 1.0):
                                s = _score((h, up, dn, w, t), *A)
                                if s > best[0]:
                                    best = (s, (h, up, dn, w, t))
            s, (h, up, dn, w, t) = best
            out.append(dict(iou=round(float(s), 3), h=float(h), up=float(up), down=float(dn), w=float(w), tilt=float(t)))
        per_view[view] = out
    bands = []
    for k in range(len(BANDS)):
        ps = [per_view[v][k] for v in per_view]
        bands.append(tuple(round(float(np.mean([p[key] for p in ps])), 1) for key in ("h", "up", "down")))
    width = round(float(np.mean([p["w"] for v in per_view for p in per_view[v]])), 1)
    return dict(per_view=per_view, RIBBON_BANDS=bands, RIBBON_W=width)


def stripes():
    with open(os.path.join(cfg.REFS, "profiles_m4.json")) as fh:
        d4 = json.load(fh)
    res = {}
    for view in ("front", "back", "side"):
        rgb = imgio.load(cfg.ref_path(view), channels=3).astype(float)
        W = rgb.min(-1)                                   # white stripes: high min channel; red: low
        lo_off, hi_off, widths = [], [], []
        for u, hr in d4["skirt"][view]["hem"]:
            c = int(u - 0.5)
            edge = hr + OFF[view]
            r0, r1 = int(edge) - 22, int(edge) - 3
            prof = W[r0:r1, c]
            pk = [i for i in range(1, len(prof) - 1)
                  if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and prof[i] > 140]
            if len(pk) < 2:
                continue
            sub = []
            base = np.percentile(prof, 20)                    # the red between and around the stripes
            for i in pk:
                a, b, cc = prof[i - 1], prof[i], prof[i + 1]
                den = a - 2 * b + cc
                sub.append((r0 + i + (0.5 * (a - cc) / den if den != 0 else 0.0) + 0.5, i))
                half = base + 0.5 * (b - base)                # full width at half height
                j0 = i
                while j0 > 0 and prof[j0 - 1] > half:
                    j0 -= 1
                j1 = i
                while j1 < len(prof) - 1 and prof[j1 + 1] > half:
                    j1 += 1
                f0 = (prof[j0] - half) / max(prof[j0] - prof[j0 - 1], 1e-6) if j0 > 0 else 0.0
                f1 = (prof[j1] - half) / max(prof[j1] - prof[j1 + 1], 1e-6) if j1 < len(prof) - 1 else 0.0
                widths.append((j1 - j0 + 1) + min(f0, 1.0) + min(f1, 1.0) - 1.0)
            sub = sorted(sub)[-2:]
            hi_off.append(edge - sub[0][0])
            lo_off.append(edge - sub[1][0])
        res[view] = dict(lower=round(float(np.mean(lo_off)), 2), upper=round(float(np.mean(hi_off)), 2),
                         width=round(float(np.median(widths)), 2), columns=len(lo_off))
    stripes_ = (round(float(np.mean([res[v]["lower"] for v in res])), 1),
                round(float(np.mean([res[v]["upper"] for v in res])), 1))
    width = round(float(np.mean([res[v]["width"] for v in res])), 1)
    return dict(per_view=res, STRIPES=stripes_, STRIPE_W=width)


if __name__ == "__main__":
    print(json.dumps(stripes(), indent=1))
    print(json.dumps(ribbons(), indent=1))
