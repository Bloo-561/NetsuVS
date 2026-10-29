"""LETICIA'S DERIVED PICTURES: effect layers made from her drawings by script (nothing is drawn by
hand). Written to tools/sprite_port/derived/leticia/ and used in manifests/leticia.json as
"src": "derived/leticia/<name>.png".

  super1_beam_a/b/c.png   the Super 1 beam (Super1_02_Beam.png ends at the picture's edge): the beam
                          from the muzzles on, made ~1600 px longer with pieces of its own far half
                          (cross-faded, a different mix in each picture), faded out at the tip;
                          b is 8% thicker, c 7% thinner, so alternating them makes the beam pulse.
                          Same canvas origin as Super1_02_Beam.png: the manifest places them with
                          "anchor": "like", "like": "s1_2", and s1_2 erases its own beam.
                          (Oct 24: the game stretches them to the far side of the screen: fx_reach in moves_leticia.py)
  photon_ext.png          (Oct 24) a short piece of the Photon Line laser (Leticia_Combined_02.png, x 1560-1600) on
                          that drawing's canvas; the game stretches it (fx_reach) so the laser runs across the whole
                          screen. cb_2 erases its own tip (x 1600 on).
  prism_ext.png           (Oct 24) the same for Prism Overdrive's big beam (Leticia_Combined_06.png, x 1200-1440);
                          cb_6 erases its arrow tip (x 1440 on).
  ricochet_long.png       (Oct 24 late) Ricochet Prism across the whole screen: the shot from the gun to the first
                          bounce, then the drawn down leg and its mirror image, bounce after bounce (RICOCHET below);
                          cb_4 erases its own beam (x 800 on).

    python derive_leticia.py            everything
    python derive_leticia.py --pieces   only photon_ext / prism_ext / ricochet_long
"""
import os, sys
import numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import cfg, source_root
OUT = os.path.join(HERE, 'derived', 'leticia')
BEAM_CUT = {'x_top': 700, 'y_split': 640, 'x_bottom': 880}   # the beam alone: right of the muzzles (above her front foot)

def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def super1_beams(root):
    src = np.array(Image.open(os.path.join(root, 'Leticia/14_Supers/Super1_02_Beam.png')).convert('RGBA')).astype(np.float32)
    H, W = src.shape[:2]
    pm = src.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0          # premultiplied, for blending
    keep = np.zeros((H, W), bool); c = BEAM_CUT
    keep[:c['y_split'], c['x_top']:] = True; keep[c['y_split']:, c['x_bottom']:] = True
    base = pm * keep[..., None]
    TILE, OVL, EXT, FADE = 360, 90, 1600, 260
    lo, hi = 1000, W - TILE
    Wt = W + EXT; xs = np.arange(Wt)
    al = src[:, W // 2:W, 3]; axis = float((al * np.arange(H)[:, None]).sum() / max(al.sum(), 1))
    res = {}
    for name, seed, sv in (('a', 1, 1.0), ('b', 2, 1.08), ('c', 3, 0.93)):
        rng = np.random.default_rng(seed)
        out = np.zeros((H, Wt, 4), np.float32); out[:, :W] = base
        pos = W - OVL
        while pos < Wt:
            x0 = int(rng.integers(lo, hi))
            t = pm[:, x0:x0 + TILE]
            w = min(TILE, Wt - pos)
            ramp = np.ones(w, np.float32); ramp[:OVL] = smooth(np.arange(OVL) / OVL)[:w] if w >= OVL else smooth(np.arange(w) / OVL)
            seg = out[:, pos:pos + w]
            out[:, pos:pos + w] = seg * (1 - ramp[None, :, None]) + t[:, :w] * ramp[None, :, None]
            pos += TILE - OVL
        tip = 1 - smooth((xs - (Wt - FADE)) / FADE)
        out *= tip[None, :, None]
        if sv != 1.0:
            s = 1 + (sv - 1) * smooth((xs - 1000) / 300)              # no change near the guns
            mapy = (axis + (np.arange(H)[:, None] - axis) / s[None, :]).astype(np.float32)
            mapx = np.repeat(xs[None, :].astype(np.float32), H, 0)
            out = cv2.remap(out, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = out[..., 3:4]; rgb = np.where(a > 1e-3, out[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
        res['super1_beam_' + name] = np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 255)])
    return res, {'axis_row': round(axis, 1), 'size': [Wt, H]}

# Oct 24 late: Ricochet Prism (214B, and the ricochet of 214C) across the whole screen. The drawing
# (Leticia_Combined_04.png) bounces once at the top and once low, and its last leg runs off the canvas; the
# derived picture keeps the shot from the gun to the first bounce, then repeats the drawn down leg and its mirror
# image (the up leg) bounce after bounce until RICOCHET['width'] (the far side of the screen at the widest camera).
# Same canvas origin as the drawing: the manifest places it "like" cb_4, and cb_4 erases its own beam (x >= start).
RICOCHET = dict(src='Leticia/10_214_Beams/Combined/Leticia_Combined_04.png', start=800, apex=(1142, 96), low=(1373, 387),
                r=52, width=8300)


def ricochet_long(root):
    c = RICOCHET
    src = np.array(Image.open(os.path.join(root, c['src'])).convert('RGBA')).astype(np.float32)
    pm = src.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0          # premultiplied (max-compositing the glows)
    H, W = pm.shape[:2]
    (ax, ay), (lx, ly), r = c['apex'], c['low'], c['r']
    yy, xx = np.mgrid[0:H, 0:W]
    near = lambda cx, cy: (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    Wt = c['width']
    out = np.zeros((H, Wt, 4), np.float32)
    # the shot from the gun to the first bounce (its diamond included)
    first = ((xx >= c['start']) & (xx <= ax)) | near(ax, ay)
    out[:, :W] = pm * first[..., None]
    # one down leg (first bounce -> low bounce, both diamonds), as a strip of columns ax - r .. lx + r
    # (each diamond only from the leg's side of it: the mirror image fills in the other half, and the drawn shot that
    # arrives at the first bounce, or the drawn up leg leaving the low one, doesn't show up at every bounce)
    leg_mask = ((xx >= ax) & (xx <= lx)) | (near(ax, ay) & (xx >= ax)) | (near(lx, ly) & (xx <= lx))
    c0, c1 = ax - r, lx + r + 1
    down = (pm * leg_mask[..., None])[:, c0:c1]
    up = down[:, ::-1]                                             # mirrored about the low bounce: the up leg
    period = 2 * (lx - ax)
    i = 0
    while True:
        d0 = c0 + i * period                                       # the down leg's columns
        u0 = 2 * lx - (c1 - 1) + i * period                        # the up leg's (mirror image of the down leg)
        if d0 >= Wt:
            break
        for strip, x0 in ((down, d0), (up, u0)):
            x1 = min(Wt, x0 + strip.shape[1])
            if x1 > x0:
                out[:, x0:x1] = np.maximum(out[:, x0:x1], strip[:, :x1 - x0])
        i += 1
    a = out[..., 3:4]
    rgb = np.where(a > 1e-3, out[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 255)])


# Oct 25: Ricochet Prism's two angles (after Hollow Point in the user's reference): B tapped bounces DOWN first
# (gun -> floor -> up high -> floor ...), B held goes UP first (the drawn shot to its first bounce, then floor -> high
# ...). Both zigzag between ZIG_HIGH and ZIG_FLOOR (rows of cb_4's canvas: ~1.6 m and ~0.13 m in the game) at the drawn
# legs' own slope, so a leg is the drawn down leg's line slid along itself (a piece of it repeated, no resampling: it
# stays as crisp as the drawing), up legs its mirror image, and every bounce gets the drawn low bounce's flash (flipped
# upside down for the high ones: its line stubs leave at the same angle). Same canvas origin as the drawing: the
# manifest places them "like" cb_4. zigzag_verts() gives the path (the game's attack boxes are worked out from it).
ZIG_HIGH, ZIG_FLOOR = 96, 900
ZIG_SLOPE = (1373 - 1142) / (387 - 96)          # the drawn legs: px across per px down

def zigzag_verts(kind, width=None):
    """the path on cb_4's canvas: 'down' (B tapped) from the muzzle down first, 'up' (B held) from the drawn first
    bounce on. The last point is past width."""
    c = RICOCHET; width = width or c['width']
    if kind == 'down':
        pts = [(float(c['start']), float(c.get('start_y', 168)))]
        y = ZIG_FLOOR
    else:
        pts = [(float(c['start']), float(c.get('start_y', 168))), (float(c['apex'][0]), float(c['apex'][1]))]
        y = ZIG_FLOOR
    while pts[-1][0] < width:
        x0, y0 = pts[-1]
        pts.append((x0 + abs(y - y0) * ZIG_SLOPE, float(y)))
        y = ZIG_HIGH if y == ZIG_FLOOR else ZIG_FLOOR
    return pts

def ricochet_paths(root):
    c = RICOCHET
    src = np.array(Image.open(os.path.join(root, c['src'])).convert('RGBA')).astype(np.float32)
    pm = src.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0
    H, W = pm.shape[:2]
    (ax, ay), (lx, ly), r = c['apex'], c['low'], c['r']
    yy, xx = np.mgrid[0:H, 0:W]
    L = float(np.hypot(lx - ax, ly - ay)); ux, uy = (lx - ax) / L, (ly - ay) / L
    along = (xx - ax) * ux + (yy - ay) * uy
    perp = np.abs((xx - ax) * -uy + (yy - ay) * ux)
    # a piece of the drawn down leg between the two bounces (its line and glow only)
    t0, t1 = 0.36, 0.62
    m = (perp <= 40) & (along >= L * t0) & (along <= L * t1)
    ys, xs = np.nonzero(m); bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    piece = (pm * m[..., None])[by0:by1, bx0:bx1]
    p0 = (ax + ux * L * t0 - bx0, ay + uy * L * t0 - by0)      # the piece's start point, in its own pixels
    step = L * (t1 - t0) * 0.45                                # copies overlap by half
    piece_up = piece[:, ::-1]; p0_up = (piece.shape[1] - 1 - p0[0], p0[1])
    # the low bounce's flash (and the stubs of its two legs), and the same upside down for the high bounces
    R, R_IN = 62, 30      # the flash fades out from R_IN to R (its leg stubs with it: the slid legs carry the line)
    d = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2)
    flash_w = 1 - smooth((d - R_IN) / (R - R_IN))
    flash = (pm * flash_w[..., None])[ly - R:ly + R + 1, lx - R:lx + R + 1]
    flash_hi = flash[::-1]
    Wt = c['width']
    def put(out, img, x, y):          # max-composite img with its top-left at (x, y), clipped to the canvas
        x, y = int(round(x)), int(round(y)); h, w = img.shape[:2]
        sx0, sy0 = max(0, -x), max(0, -y); dx0, dy0 = max(0, x), max(0, y)
        dx1, dy1 = min(Wt, x + w), min(H, y + h)
        if dx1 <= dx0 or dy1 <= dy0: return
        region = out[dy0:dy1, dx0:dx1]
        np.maximum(region, img[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0], out=region)
    res = {}
    for kind, name in (('down', 'ricochet_down'), ('up', 'ricochet_up')):
        out = np.zeros((H, Wt, 4), np.float32)
        pts = zigzag_verts(kind, Wt)
        legs = pts
        if kind == 'up':                 # the drawn shot from the gun to its first bounce, that bounce's flash included
            first = ((xx >= c['start']) & (xx <= ax)) | (((xx - ax) ** 2 + (yy - ay) ** 2 <= r * r))
            out[:, :W] = np.maximum(out[:, :W], pm * first[..., None])
            legs = pts[1:]
        plen = L * (t1 - t0)
        for (xa, ya), (xb, yb) in zip(legs[:-1], legs[1:]):
            down = yb > ya
            img, s0 = (piece, p0) if down else (piece_up, p0_up)
            ln = max(1.0, float(np.hypot(xb - xa, yb - ya)))
            # the piece runs down-right from its start point (the mirrored one down-left from it): a down leg puts it
            # at t = 0 .. 1 - plen / ln, an up leg at t = plen / ln .. 1, so no copy sticks out past a bounce
            lo, hi = (0.0, max(0.0, 1 - plen / ln)) if down else (min(1.0, plen / ln), 1.0)
            n = max(1, int(np.ceil((hi - lo) * ln / step)))
            for i in range(n + 1):
                t = lo + (hi - lo) * i / n
                px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
                put(out, img, px - s0[0], py - s0[1])
        for (x, y) in pts[1 if kind == 'down' else 2:]:
            put(out, flash if y == ZIG_FLOOR else flash_hi, x - R, y - R)
        a = out[..., 3:4]
        rgb = np.where(a > 1e-3, out[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
        res[name] = np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 255)])
    return res


# (drawing, x0, x1): the piece of a drawn beam the game stretches across the screen
BEAM_PIECES = {'photon_ext': ('Leticia/10_214_Beams/Combined/Leticia_Combined_02.png', 1560, 1600),
               'prism_ext': ('Leticia/10_214_Beams/Combined/Leticia_Combined_06.png', 1200, 1440)}

def beam_pieces(root):
    """each piece alone on its drawing's canvas (so the manifest can place it "like" that drawing)"""
    res = {}
    for name, (rel, x0, x1) in BEAM_PIECES.items():
        src = np.array(Image.open(os.path.join(root, rel)).convert('RGBA'))
        out = np.zeros_like(src); out[:, x0:x1] = src[:, x0:x1]
        res[name] = out.astype(np.float32)
    return res

def main():
    c = cfg('leticia'); root = source_root(c); os.makedirs(OUT, exist_ok=True)
    for name, img in beam_pieces(root).items():
        Image.fromarray(img.astype(np.uint8), 'RGBA').save(os.path.join(OUT, name + '.png'))
        print('wrote derived/leticia/%s.png' % name, img.shape[1::-1])
    img = ricochet_long(root)
    Image.fromarray(img.astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'ricochet_long.png'))
    print('wrote derived/leticia/ricochet_long.png', img.shape[1::-1])
    for name, img in ricochet_paths(root).items():
        Image.fromarray(img.astype(np.uint8), 'RGBA').save(os.path.join(OUT, name + '.png'))
        print('wrote derived/leticia/%s.png' % name, img.shape[1::-1])
    if '--pieces' in sys.argv: return   # only the beam pieces (the Super 1 beams use a random mix: kept as they are)
    pics, info = super1_beams(root)
    for name, img in pics.items():
        Image.fromarray(img.astype(np.uint8), 'RGBA').save(os.path.join(OUT, name + '.png'))
        print('wrote derived/leticia/%s.png' % name, img.shape[1::-1])
    print(info, 'erase in s1_2:', [[BEAM_CUT['x_top'], 0, 1774, BEAM_CUT['y_split']], [BEAM_CUT['x_bottom'], BEAM_CUT['y_split'], 1774, 887]])

if __name__ == '__main__':
    main()
