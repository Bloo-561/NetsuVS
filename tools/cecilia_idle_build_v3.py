"""Cecilia idle v3 ("locked"): every frame is 01_ready, warped to breathe.
Only the eyes come from the blink drawings (aligned, feathered patch). Zero detail flicker.
Usage: python tools/cecilia_idle_build_v3.py <src_dir> <project_dir> <preview_dir>
"""
import sys, os, json, math
import numpy as np
from PIL import Image

SRC, PROJ, PREV = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(PREV, exist_ok=True)
ANCH_Y = {'head': 230, 'chest': 560, 'hem': 860}
ZERO_Y = 905
SCALE = 250 / 1433
SRC_FOOT, DST_FOOT, CANVAS = (94, 1446), (403, 621), 1024
EYE_BOX = (625, 205, 800, 295)   # x0,y0,x1,y1 in source px
EYE_FEATHER = 14
BLINK_ALIGN = {'HB': ('04_half_blink.png', -9, 0), 'B': ('05_blink.png', -10, 0)}  # measured head drift
BREATH = 60; KEY = 5           # 60f breath, a new pose every 5 frames
DY_MID, DY_AMP = -3.5, 8.5     # head dy range -12 (up) .. +5 (down), source px
BLINK = [(62, 65, 'HB'), (65, 69, 'B'), (69, 72, 'HB')]  # ticks in breath 2
TOTAL = BREATH * 2

def load(f):
    a = np.array(Image.open(os.path.join(SRC, f)).convert('RGBA')).astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a

def warp_rows(a, cx, cy):
    H, W = a.shape[:2]
    ys = np.broadcast_to(np.arange(H, dtype=np.float32)[:, None] + cy[:, None], (H, W))
    xs = np.broadcast_to(np.arange(W, dtype=np.float32)[None, :] + cx[:, None], (H, W))
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = (xs - x0)[..., None]; fy = (ys - y0)[..., None]
    def g(yy, xx):
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        return a[np.clip(yy, 0, H - 1), np.clip(xx, 0, W - 1)] * ok[..., None]
    return (g(y0, x0) * (1 - fx) * (1 - fy) + g(y0, x0 + 1) * fx * (1 - fy)
            + g(y0 + 1, x0) * (1 - fx) * fy + g(y0 + 1, x0 + 1) * fx * fy)

ref = load('01_ready.png'); H, W = ref.shape[:2]
yy = np.arange(H, dtype=np.float32)
def breath_profile(head_dy):  # sampling offset = -target displacement
    pts_y = [ANCH_Y['head'], ANCH_Y['chest'], ANCH_Y['hem'], ZERO_Y]
    pts_v = [-head_dy, -head_dy * 0.7, -head_dy * 0.25, 0.0]
    return (np.interp(yy, pts_y, pts_v) * (yy < ZERO_Y)).astype(np.float32)
zero = np.zeros(H, np.float32)

# eye patch mask
m = np.zeros((H, W), np.float32)
x0, y0, x1, y1 = EYE_BOX
m[y0:y1, x0:x1] = 1
for _ in range(EYE_FEATHER):  # cheap feather: box blur passes
    m = (m + np.roll(m, 1, 0) + np.roll(m, -1, 0) + np.roll(m, 1, 1) + np.roll(m, -1, 1)) / 5
m = m[..., None]
eyes = {}
for k, (f, dx, dy) in BLINK_ALIGN.items():
    b = load(f)
    b = warp_rows(b, np.full(H, dx, np.float32), np.full(H, dy, np.float32))  # undo head drift
    eyes[k] = ref * (1 - m) + b * m

def to_game(a):
    nw, nh = round(W * SCALE), round(H * SCALE)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA')
    s = np.array(img.resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255.0
    al = s[..., 3:4]; s[..., :3] = np.where(al > 1e-4, s[..., :3] / np.maximum(al, 1e-4), 0)
    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    out.paste(Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8), 'RGBA'),
              (round(DST_FOOT[0] - SRC_FOOT[0] * SCALE), round(DST_FOOT[1] - SRC_FOOT[1] * SCALE)))
    return out

def dy_at(tick):
    k = (tick % BREATH) // KEY
    phase = (k * KEY) / BREATH            # 0 = top of breath
    return round(DY_MID - DY_AMP * math.cos(2 * math.pi * phase), 1)

def eye_at(tick):
    for a, b, e in BLINK:
        if a <= tick < b: return e
    return 'O'

segs = []
for t in range(TOTAL):
    key = (eye_at(t), dy_at(t))
    if segs and segs[-1][0] == key: segs[-1][2] += 1
    else: segs.append([key, t, 1])

spr = os.path.join(PROJ, 'actors', 'cecilia', 'Sprites')
made, frames = {}, []
for (eye, dy), at, hold in segs:
    name = f'idle_v3_{eye}{dy:+.1f}'.replace('+', 'p').replace('-', 'm').replace('.', '_')
    if name not in made:
        src = ref if eye == 'O' else eyes[eye]
        g = to_game(warp_rows(src, zero, breath_profile(dy)))
        g.save(os.path.join(spr, name + '.png')); made[name] = g
    frames.append((name, at, hold))
json.dump(frames, open(os.path.join(PREV, 'timeline_v3.json'), 'w'))
print('unique', len(made), 'segments', len(frames), 'total', TOTAL)
seq = []
for name, _, hold in frames:
    im = made[name].crop((360, 340, 640, 640))
    bg = Image.new('RGBA', im.size, (235, 235, 235, 255)); bg.alpha_composite(im)
    seq.append((bg.resize((im.width * 2, im.height * 2), Image.NEAREST).convert('P', palette=Image.ADAPTIVE), hold))
seq[0][0].save(os.path.join(PREV, 'idle_v3_preview.gif'), save_all=True, append_images=[s[0] for s in seq[1:]],
               duration=[round(h * 1000 / 60) for _, h in seq], loop=0, disposal=2)
# eye-patch check at full res
for k in eyes:
    e = eyes[k]; c = e[150:350, 560:860]
    c = np.where(c[..., 3:4] > 1e-4, c[..., :3] / np.maximum(c[..., 3:4], 1e-4), 1)
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).resize((600, 400)).save(os.path.join(PREV, f'eyecheck_{k}.png'))
