"""Milestone 6: outline weight check (plain Python 3 + numpy + Pillow, outside Blender).

Measures the outer contour's line width as the full width at half depth of
the dark band at the figure's edge, row by row, on the sheet (refs/, masks
from refs/masks/) and on the model's beauty renders (renders/<tag>_full_*.png,
2 render px per sheet px), and prints the medians in sheet px.
Run: python measure_lines.py m6_final
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.environ.get('CECILIA_V2', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def lum(a):
    return a[..., :3].astype(float) @ [0.299, 0.587, 0.114]

def widths(L, mask, rows, inner=(7, 10), maxw=8):
    out = []
    for r in rows:
        m = mask[r]
        xs = np.nonzero(m)[0]
        if len(xs) < 30:
            continue
        # every run boundary (left edges of runs, right edges of runs)
        d = np.diff(m.astype(int))
        lefts = np.nonzero(d == 1)[0] + 1
        rights = np.nonzero(d == -1)[0]
        for x0, sgn in [(x, 1) for x in lefts] + [(x, -1) for x in rights]:
            prof = [L[r, x0 + sgn * k] if 0 <= x0 + sgn * k < L.shape[1] else np.nan for k in range(-3, 14)]
            prof = np.array(prof)
            if np.isnan(prof).any():
                continue
            bg = prof[0:2].mean()                       # outside (k = -3, -2)
            body = prof[3 + inner[0]:3 + inner[1]].mean()
            seg = prof[3:3 + maxw]
            mn = seg.min()
            if bg < 235 or body - mn < 25 or np.ptp(prof[3 + inner[0]:3 + inner[1]]) > 20:
                continue
            k = int(seg.argmin()) + 3
            ho, hi = (bg + mn) / 2, (body + mn) / 2
            # outer crossing: from k going outwards (towards index 0)
            o = k
            while o > 0 and prof[o] < ho:
                o -= 1
            xo = o + (ho - prof[o]) / (prof[o + 1] - prof[o]) if prof[o + 1] != prof[o] else o
            i = k
            while i < len(prof) - 1 and prof[i] < hi:
                i += 1
            xi = i - 1 + (hi - prof[i - 1]) / (prof[i] - prof[i - 1]) if prof[i] != prof[i - 1] else i
            w = xi - xo
            if 0.3 < w < maxw:
                out.append(w)
    return np.array(out)

def run(path, maskpath=None, scale=1.0, rows=None):
    im = Image.open(path)
    if im.mode == 'RGBA':
        a = np.asarray(im)
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        L = lum(np.asarray(bg.convert('RGB')))
        mask = a[..., 3] > 127
    else:
        L = lum(np.asarray(im.convert('RGB')))
        mask = np.asarray(Image.open(maskpath).convert('L')) > 127
    H = L.shape[0]
    rows = rows if rows is not None else range(int(H * 0.25), int(H * 0.97), 2)
    w = widths(L, mask, rows)
    return w / scale

if __name__ == '__main__':
    tag = sys.argv[1] if len(sys.argv) > 1 else 'm6_final'
    jobs = [(os.path.join(ROOT, 'refs', 'cecilia_ref_%s.png' % v), os.path.join(ROOT, 'refs', 'masks', 'mask_%s.png' % v), 1.0)
            for v in ('front', 'back', 'side')]
    jobs += [(os.path.join(ROOT, 'renders', '%s_full_%s.png' % (tag, v)), None, 2.0) for v in ('front', 'back', 'side')]
    for p, m, s in jobs:
        w = run(p, m, s)
        print('%-32s n=%4d  median %.2f  p25 %.2f  p75 %.2f (sheet px)' % (os.path.basename(p), len(w), np.median(w),
                                                                         np.percentile(w, 25), np.percentile(w, 75)))
