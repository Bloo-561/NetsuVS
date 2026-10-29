"""CECILIA'S DERIVED PICTURES (Oct 24): pictures made by script from her drawings, used by manifests/cecilia.json
as "derived/cecilia/...".

    python derive_cecilia.py

  5b_attack.png   07_Ground_5B/02_attack.png with the blade finished: the drawing's canvas cuts the glowing blade
                  off a hand's width past the guard, so in game it looked like a broken sword. The blade is carried
                  on along its own line (its last clean column, copied and shifted with the blade's slope) and
                  tapered to a point. The canvas grows to the right; nothing else changes.
  5c_arc.png      the big crescent slash of 09_Ground_5C/02_attack.png on its own (same canvas). 5C now shows the
                  follow-through body (03_recovery) with this arc on top at the hit, instead of the attack drawing
                  whose hand is still above her head while the slash is already at the floor.
"""
import os, sys
import numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import cfg, source_root, fx_mask

OUT = os.path.join(HERE, 'derived', 'cecilia')
B5 = 'Cecilia_Original_Idle_Style/07_Ground_5B/02_attack.png'
C5 = 'Cecilia_Original_Idle_Style/09_Ground_5C/02_attack.png'

# 5B blade: rows 395-462 hold the blade near the canvas edge; its centre rises 0.127 px per px to the right
BLADE_SEG = (985, 1046)   # a clean piece of the blade (no sparks), copied outwards along its line
BLADE_ROWS = (392, 466)
BLADE_SLOPE = -0.127
BLADE_EXTRA = 210         # px of blade added past the canvas edge
BLADE_TIP = 85            # the last px taper to a point
HILT_CUT = (852, 128)     # 5C: the arc's top-left corner up to here is the sword's hilt end, not the slash


def _pm(a):
    f = a.astype(np.float32) / 255.0; f[..., :3] *= f[..., 3:4]; return f
def _unpm(f):
    al = f[..., 3:4]; rgb = np.where(al > 1e-5, f[..., :3] / np.maximum(al, 1e-5), 0)
    return (np.clip(np.dstack([rgb, al]), 0, 1) * 255 + 0.5).astype(np.uint8)


def blade_5b(root):
    a = np.array(Image.open(os.path.join(root, B5)).convert('RGBA'))
    h, w = a.shape[:2]
    W = w + BLADE_EXTRA + 6
    out = np.zeros((h, W, 4), np.float32); out[:, :w] = _pm(a)
    y0, y1 = BLADE_ROWS; c0, c1 = BLADE_SEG
    seg = _pm(a[y0:y1, c0:c1])                                     # a clean piece of the blade, glow and all
    al = seg[..., 3]
    cy0 = (np.arange(y0, y1)[:, None] * al).sum() / max(al.sum(), 1e-5)   # the piece's centre line (at its middle column)
    half = 0.5 * (np.ptp(np.nonzero(al.max(1) > 0.12)[0]) + 1)
    seglen = c1 - c0
    acc = np.zeros((h, W, 4), np.float32); wsum = np.zeros((h, W, 1), np.float32)
    ramp = np.minimum(1.0, np.minimum(np.arange(seglen) + 1, seglen - np.arange(seglen)) / 10.0).astype(np.float32)
    xs = w - 14                                                    # start inside the cut, so there is no seam
    while xs < w + BLADE_EXTRA:
        dy = BLADE_SLOPE * (xs - c0)                                # keep the blade's line going
        M = np.float32([[1, 0, xs], [0, 1, y0 + dy]])
        piece = cv2.warpAffine(seg, M, (W, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        wcol = np.zeros(W, np.float32); x0 = max(0, xs); x1 = min(W, xs + seglen)
        wcol[x0:x1] = ramp[x0 - xs:x1 - xs]
        acc += piece * wcol[None, :, None]; wsum += wcol[None, :, None]
        xs += seglen - 10                                          # pieces overlap 10 px and cross-fade
    ext = np.where(wsum > 1e-4, acc / np.maximum(wsum, 1e-4), 0)
    # taper to a point over the last BLADE_TIP px (a wedge around the centre line), cut at the new end
    yy, xx = np.mgrid[0:h, 0:W].astype(np.float32)
    tip_end = w + BLADE_EXTRA
    cyx = cy0 + BLADE_SLOPE * (xx - (c0 + c1) / 2.0)
    k = np.clip((tip_end - xx) / float(BLADE_TIP), 0, 1)
    hw = half * (0.08 + 0.92 * np.sqrt(k))
    wedge = np.clip(hw + 1.0 - np.abs(yy - cyx), 0, 1) * (xx < tip_end)
    ext *= np.where(xx >= tip_end - BLADE_TIP, wedge, (xx < tip_end).astype(np.float32))[..., None]
    # cross-fade from the drawing into the new blade over the last 12 px of the drawing
    fade = np.clip((np.arange(W, dtype=np.float32) - (w - 12)) / 12.0, 0, 1)[None, :, None]
    band = np.zeros((h, 1, 1), np.float32); band[max(0, y0 - 10):y1 + 10] = 1     # only the blade's rows (the swirl below stays)
    fade = np.where(np.arange(W)[None, :, None] >= w, 1.0, fade * band)
    out = out * (1 - fade) + ext * fade
    Image.fromarray(_unpm(out)).save(os.path.join(OUT, '5b_attack.png'))
    return '5b_attack.png (%d px of blade added, canvas %dx%d)' % (BLADE_EXTRA, W, h)


def arc_5c(root):
    a = np.array(Image.open(os.path.join(root, C5)).convert('RGBA'))
    m = fx_mask(a, 'yellow') & (a[..., 3] > 8)
    # the slash: the big glow component(s) right of her torso, plus the sparks next to it
    n, lab, stats, cent = cv2.connectedComponentsWithStats(cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)), 8)
    big = max(range(1, n), key=lambda i: stats[i, cv2.CC_STAT_AREA])
    bx, by, bw, bh = stats[big, :4]
    keep = np.zeros(n, bool); keep[big] = True
    for i in range(1, n):          # sparks: small pieces within reach of the arc's box, right of the arc's left edge
        x, y, ww, hh, area = stats[i]
        if i != big and area >= 30 and x >= bx - 40 and x + ww <= bx + bw + 80 and y >= by - 40 and y + hh <= by + bh + 60:
            keep[i] = True
    sel = keep[lab] & m
    sel[:HILT_CUT[1], :HILT_CUT[0]] = False                        # the hilt end the hand held (the hand is elsewhere now)
    yy, xx = np.mgrid[0:sel.shape[0], 0:sel.shape[1]]
    start_fade = np.clip((np.hypot(xx - HILT_CUT[0], yy - HILT_CUT[1] + 20) - 10) / 70.0, 0, 1)   # the trail starts soft
    # soften: the glow's own alpha, cut where the mask ends (a 2 px feather)
    feather = cv2.GaussianBlur(sel.astype(np.float32), (0, 0), 1.2)
    out = a.copy()
    out[..., 3] = (a[..., 3].astype(np.float32) * np.clip(feather * 1.4, 0, 1) * start_fade).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    Image.fromarray(out).save(os.path.join(OUT, '5c_arc.png'))
    ys, xs = np.nonzero(out[..., 3] > 10)
    return '5c_arc.png (arc box x %d-%d, y %d-%d)' % (xs.min(), xs.max(), ys.min(), ys.max())


def main():
    root = source_root(cfg('cecilia'))
    os.makedirs(OUT, exist_ok=True)
    print('wrote derived/cecilia/' + blade_5b(root))
    print('wrote derived/cecilia/' + arc_5c(root))


if __name__ == '__main__':
    main()
