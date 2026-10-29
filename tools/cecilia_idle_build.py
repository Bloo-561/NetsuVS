"""Build Cecilia's idle loop from the hand-made idle drawings.

- Locks the legs to 01_ready (removes ribbon/sock flicker).
- Measures each drawing's upper-body drift against 01_ready and warps it back
  into line, adding a designed breathing rise/fall instead (warp fades to 0 at the thighs).
- Downscales to the game's sprite scale (feet on y=621, same x as the old idle).
- Writes actors/cecilia/Sprites/idle_v2_XX.png and prints the timeline.

Usage: python tools/cecilia_idle_build.py <src_dir> <project_dir> [<preview_dir>]
"""
import sys, os, json
import numpy as np
from PIL import Image

SRC, PROJ = sys.argv[1], sys.argv[2]
PREV = sys.argv[3] if len(sys.argv) > 3 else None

DRAW = {  # key -> file
    'R': '01_ready.png', 'I': '02_inhale.png', 'P': '06_breath_peak_2.png',
    'S': '07_settle_1.png', 'E': '03_exhale.png', 'HB': '04_half_blink.png', 'B': '05_blink.png',
}
ANCH = {'head': (40, 420, 350, 950, 230), 'chest': (420, 700, 300, 900, 560), 'hem': (780, 880, 150, 1000, 860)}
ZERO_Y = 905          # warp displacement reaches 0 here
LOCK0, LOCK1 = 905, 945   # blend to 01_ready legs
SCALE = 250 / 1433
SRC_FOOT = (94, 1446)     # left shoe x, shoe bottom y in source
DST_FOOT = (403, 621)     # same points in the 1024 game canvas
CANVAS = 1024

# (drawing, head_dy in source px (negative = up), hold frames @60fps)
TIMELINE = [
    ('R', 0, 6), ('R', -2, 5), ('I', -5, 5), ('I', -8, 5), ('P', -11, 6), ('P', -12, 6),
    ('S', -9, 5), ('S', -5, 5), ('E', -1, 5), ('E', 3, 6), ('E', 5, 6),            # breath 1 = 60f
    ('R', 0, 4), ('HB', 0, 3), ('B', 0, 4), ('HB', -1, 3), ('I', -5, 5), ('P', -10, 5),
    ('P', -12, 6), ('S', -9, 5), ('S', -5, 5), ('E', -1, 5), ('E', 3, 5), ('E', 5, 5),  # breath 2 = 60f (blink)
]

def load(f):
    a = np.array(Image.open(os.path.join(SRC, f)).convert('RGBA')).astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]  # premultiply
    return a

def feat(a):  # alpha + luminance, for matching
    return a[..., 3] * 0.5 + (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) * 0.5

def measure(ref, a):
    fr, fa = feat(ref), feat(a)
    out = {}
    for k, (y0, y1, x0, x1, _) in ANCH.items():
        R = fr[y0:y1, x0:x1]
        def err(dx, dy):
            return np.abs(fa[y0 + dy:y1 + dy, x0 + dx:x1 + dx] - R).mean()
        best = min(((err(dx, dy), dx, dy) for dx in range(-18, 19, 2) for dy in range(-24, 25, 2)))
        _, bx, by = best
        best = min(((err(dx, dy), dx, dy) for dx in range(bx - 1, bx + 2) for dy in range(by - 1, by + 2)))
        out[k] = (best[1], best[2])
    return out

def warp(a, cx_of_y, cy_of_y):
    H, W = a.shape[:2]
    ys = np.arange(H, dtype=np.float32)[:, None] + cy_of_y[:, None]
    xs = np.arange(W, dtype=np.float32)[None, :] + cx_of_y[:, None]
    ys = np.broadcast_to(ys, (H, W)); xs = np.broadcast_to(xs, (H, W))
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = (xs - x0)[..., None]; fy = (ys - y0)[..., None]
    def g(yy, xx):
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        v = a[np.clip(yy, 0, H - 1), np.clip(xx, 0, W - 1)]
        return v * ok[..., None]
    return (g(y0, x0) * (1 - fx) * (1 - fy) + g(y0, x0 + 1) * fx * (1 - fy)
            + g(y0 + 1, x0) * (1 - fx) * fy + g(y0 + 1, x0 + 1) * fx * fy)

def profile(H, vals):  # vals: list of (y, value) incl. zero point; constant above first
    ys = [v[0] for v in vals]; vs = [v[1] for v in vals]
    y = np.arange(H, dtype=np.float32)
    return np.interp(y, ys, vs).astype(np.float32) * (y < ZERO_Y)

ref = load(DRAW['R'])
H, W = ref.shape[:2]
meas = {k: (measure(ref, load(f)) if k != 'R' else {a: (0, 0) for a in ANCH}) for k, f in DRAW.items()}
lockw = np.clip((np.arange(H) - LOCK0) / (LOCK1 - LOCK0), 0, 1).astype(np.float32)[:, None, None]

def build(key, head_dy):
    a = load(DRAW[key]); m = meas[key]
    tgt = {'head': head_dy, 'chest': head_dy * 0.7, 'hem': head_dy * 0.25}
    ptsx = [(ANCH[k][4], m[k][0]) for k in ('head', 'chest', 'hem')] + [(ZERO_Y, 0.0)]
    ptsy = [(ANCH[k][4], m[k][1] - tgt[k]) for k in ('head', 'chest', 'hem')] + [(ZERO_Y, 0.0)]
    w = warp(a, profile(H, ptsx), profile(H, ptsy))
    return w * (1 - lockw) + ref * lockw

def to_game(a):
    nw, nh = round(W * SCALE), round(H * SCALE)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA')  # still premultiplied
    small = np.array(img.resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255.0
    al = small[..., 3:4]
    small[..., :3] = np.where(al > 1e-4, small[..., :3] / np.maximum(al, 1e-4), 0)
    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    ox = round(DST_FOOT[0] - SRC_FOOT[0] * SCALE); oy = round(DST_FOOT[1] - SRC_FOOT[1] * SCALE)
    out.paste(Image.fromarray((np.clip(small, 0, 1) * 255).astype(np.uint8), 'RGBA'), (ox, oy))
    return out

print('measured drift (dx,dy) vs 01_ready:', json.dumps(meas))
spr = os.path.join(PROJ, 'actors', 'cecilia', 'Sprites')
cache, frames, t = {}, [], 0
for key, dy, hold in TIMELINE:
    name = f'idle_v2_{key}{dy:+d}'.replace('+', 'p').replace('-', 'm')
    if name not in cache:
        full = build(key, dy)
        g = to_game(full); g.save(os.path.join(spr, name + '.png'))
        cache[name] = g
        if PREV:
            Image.fromarray((np.clip(np.where(full[..., 3:4] > 1e-4, full[..., :3] / np.maximum(full[..., 3:4], 1e-4), 0), 0, 1) * 255).astype(np.uint8)).save(os.path.join(PREV, name + '_full.jpg'), quality=85) if False else None
    frames.append((name, t, hold)); t += hold
print('TOTAL', t)
print('TIMELINE', json.dumps(frames))
if PREV:
    os.makedirs(PREV, exist_ok=True)
    seq = []
    for name, _, hold in frames:
        im = cache[name].crop((360, 340, 640, 640))
        bg = Image.new('RGBA', im.size, (235, 235, 235, 255)); bg.alpha_composite(im)
        bg = bg.resize((im.width * 2, im.height * 2), Image.NEAREST).convert('P', palette=Image.ADAPTIVE)
        seq.append((bg, hold))
    seq[0][0].save(os.path.join(PREV, 'idle_v2_preview.gif'), save_all=True, append_images=[s[0] for s in seq[1:]],
                   duration=[round(h * 1000 / 60) for _, h in seq], loop=0, disposal=2)
    json.dump(frames, open(os.path.join(PREV, 'timeline.json'), 'w'))
