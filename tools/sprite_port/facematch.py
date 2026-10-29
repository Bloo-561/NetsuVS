"""FACE MATCH: a second opinion on a drawing's scale, for poses where analyze.py's SIFT match is
weak or missing.  Searches the reference face (scaled + rotated) in the drawing and reports the
best scale.  Works when the face is visible (front or 3/4 view); not for back views.

    python facematch.py leticia [file-substring ...]
"""
import os, sys, json, cv2, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import cfg, source_root

def gray(p):
    a = np.array(Image.open(p).convert('RGBA')).astype(np.float32)
    al = a[..., 3:4] / 255
    rgb = a[..., :3] * al + 128 * (1 - al)
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY), (a[..., 3] > 128).astype(np.uint8)

def main(char, subs, face_box):
    c = cfg(char); root = source_root(c)
    an = json.load(open(os.path.join(HERE, 'analysis', char + '.json')))['frames']
    rg, ra = gray(os.path.join(root, c['reference']))
    x0, y0, x1, y1 = face_box
    T = rg[y0:y1, x0:x1]; TM = ra[y0:y1, x0:x1]
    D = 4.0   # coarse search at 1/4 size
    out = {}
    for rel in an:
        if subs and not any(s in rel for s in subs): continue
        g, m = gray(os.path.join(root, rel))
        gs = cv2.resize(g, None, fx=1 / D, fy=1 / D, interpolation=cv2.INTER_AREA)
        best = (-1, 0, 0, None)
        for s in np.arange(0.55, 1.65, 0.03):
            t = cv2.resize(T, None, fx=s / D, fy=s / D, interpolation=cv2.INTER_AREA)
            tm = cv2.resize(TM, None, fx=s / D, fy=s / D, interpolation=cv2.INTER_NEAREST)
            h, w = t.shape
            for r in range(-45, 46, 5):
                M = cv2.getRotationMatrix2D((w / 2, h / 2), r, 1.0)
                tr = cv2.warpAffine(t, M, (w, h), borderValue=128); mr = cv2.warpAffine(tm, M, (w, h))
                if mr.sum() < 20 or gs.shape[0] < h or gs.shape[1] < w: continue
                res = cv2.matchTemplate(gs, tr, cv2.TM_CCOEFF_NORMED, mask=mr * 255)
                res = np.nan_to_num(res, nan=-1, posinf=-1, neginf=-1)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > best[0]: best = (mv, s, r, ml)
        # refine at 1/2 size around the best
        sc, s0, r0, ml = best
        D2 = 2.0; g2 = cv2.resize(g, None, fx=1 / D2, fy=1 / D2, interpolation=cv2.INTER_AREA)
        ref = (-1, s0, r0, None)
        for s in np.arange(s0 - 0.04, s0 + 0.041, 0.01):
            t = cv2.resize(T, None, fx=s / D2, fy=s / D2, interpolation=cv2.INTER_AREA)
            tm = cv2.resize(TM, None, fx=s / D2, fy=s / D2, interpolation=cv2.INTER_NEAREST)
            h, w = t.shape
            for r in range(r0 - 6, r0 + 7, 2):
                M = cv2.getRotationMatrix2D((w / 2, h / 2), r, 1.0)
                tr = cv2.warpAffine(t, M, (w, h), borderValue=128); mr = cv2.warpAffine(tm, M, (w, h))
                cx, cy = int(ml[0] * D / D2), int(ml[1] * D / D2)
                X0, Y0 = max(0, cx - 40), max(0, cy - 40)
                win = g2[Y0:cy + h + 40, X0:cx + w + 40]
                if win.shape[0] < h or win.shape[1] < w: continue
                res = cv2.matchTemplate(win, tr, cv2.TM_CCOEFF_NORMED, mask=mr * 255)
                res = np.nan_to_num(res, nan=-1, posinf=-1, neginf=-1)
                _, mv, _, l2 = cv2.minMaxLoc(res)
                if mv > ref[0]: ref = (mv, s, r, (X0 + l2[0], Y0 + l2[1]))
        a = an[rel]; sift = a.get('scale')
        out[rel] = {'face_scale': round(float(ref[1]), 3), 'face_rot': ref[2], 'score': round(float(ref[0]), 3),
                    'face_at': [int(ref[3][0] * D2), int(ref[3][1] * D2)] if ref[3] else None}
        print('%-62s face %.3f rot %4d score %.3f   sift %s' % (rel.split('/', 1)[1], ref[1], ref[2], ref[0], ('%.3f' % sift) if sift else None), flush=True)
    p = os.path.join(HERE, 'analysis', char + '_face.json')
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(out); json.dump(old, open(p, 'w'), indent=1)

if __name__ == '__main__':
    char = sys.argv[1]
    box = json.load(open(os.path.join(HERE, 'manifests', char + '.json'))).get('face_box', [540, 60, 740, 300])
    main(char, sys.argv[2:], box)
