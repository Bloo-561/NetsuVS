"""Cecilia walk build (shuffle step): idle upper body + walk-drawing legs.

Every frame = 01_ready (idle) for head/arms/sword/upper skirt, blended along a line that follows
the skirt stripes, with the walk drawing for lower skirt, lace and legs (so lace and thighs always
match). Walk drawings are aligned to the idle upper body, legs lightly stretched / body shifted so
the planted foot sits on the floor. Same canvas placement as the idle (no pop idle<->walk).
Usage: python tools/cecilia_walk_build.py <sprites_root> <project_dir> <preview_dir>
"""
import sys, os, json, numpy as np
from PIL import Image
SRC, PROJ, PREV = sys.argv[1:4]; os.makedirs(PREV, exist_ok=True)
FLOOR = 1446; STRETCH0 = 880; KMAX = 0.05
SCALE = 250 / 1433; SRC_FOOT = (94, 1446); DST_FOOT = (403, 621); CANVAS = 1024
IDLE = 'Cecilia_Original_Idle_Style/01_Idle/01_ready.png'
WALKS = {
  'F': {'speed': 32000, 'frames': [  # key, file, hold
        ('F01', 'Cecilia/Forward/Cecilia_Walk_Forward_01.png', 7),
        ('F05', 'Cecilia/Forward/Cecilia_Walk_Forward_05_1.png', 6),
        ('F03', 'Cecilia/Forward/Cecilia_Walk_Forward_03.png', 7),
        ('F04', 'Cecilia/Forward/Cecilia_Walk_Forward_04.png', 6),
        ('F06', 'Cecilia/Forward/Cecilia_Walk_Forward_06_1.png', 6)]},
  'B': {'speed': -21000, 'frames': [
        ('B01', 'Cecilia/Backward/Cecilia_Walk_Backward_01.png', 7),
        ('B03', 'Cecilia/Backward/Cecilia_Walk_Backward_03.png', 7),
        ('B06', 'Cecilia/Backward/Cecilia_Walk_Backward_06_1.png', 7),
        ('B02', 'Cecilia/Backward/Cecilia_Walk_Backward_02.png', 8),
        ('B05', 'Cecilia/Backward/Cecilia_Walk_Backward_05_2.png', 7)]},
}
def load(p):
    a = np.array(Image.open(os.path.join(SRC, p)).convert('RGBA')).astype(np.float32) / 255; a[..., :3] *= a[..., 3:4]; return a
def unpm(a): return np.where(a[..., 3:4] > 1e-4, a[..., :3] / np.maximum(a[..., 3:4], 1e-4), 1.0)
def feat(a): return a[..., 3] * .5 + a[..., :3].mean(-1) * .5
def sole_y(a):
    c = unpm(a); r, g, b = c[..., 0], c[..., 1], c[..., 2]
    m = (a[..., 3] > 0.8) & (r < 0.51) & (g < 0.37) & (b < 0.33) & (r >= g - 0.02); m[:1200] = False
    return int(np.where(m)[0].max())
idle = load(IDLE); H, W = idle.shape[:2]; ys = np.arange(H, dtype=np.float32)
def align(a):  # offset of walk upper body vs idle upper body
    R = feat(idle)[40:700, 250:1000]; P = np.pad(feat(a), ((80, 80), (120, 120)))
    def e(dx, dy): return np.abs(P[120 + dy:780 + dy, 370 + dx:1120 + dx] - R).mean()
    best = min((e(dx, dy), dx, dy) for dx in range(-110, 111, 4) for dy in range(-60, 61, 4))
    best = min((e(dx, dy), dx, dy) for dx in range(best[1] - 3, best[1] + 4) for dy in range(best[2] - 3, best[2] + 4))
    return best[1], best[2]
# blend band following the idle's stripe line
c = unpm(idle); stripe = np.full(W, np.nan)
for x in range(W):
    col = np.where((c[650:900, x].min(-1) > 0.84) & (idle[650:900, x, 3] > 0.9))[0]
    if len(col): stripe[x] = 650 + col[0]
good = ~np.isnan(stripe); xs = np.arange(W)
fit = np.polyfit(xs[(xs > 260) & (xs < 760) & good], stripe[(xs > 260) & (xs < 760) & good], 1)
line = np.polyval(fit, xs)                        # straight slanted line along the stripe top
B0 = line - 55; B1 = line - 12                    # band: idle fully above B0, walk fully below B1
t = np.clip((B1[None, :] - ys[:, None]) / (B1 - B0)[None, :], 0, 1); wI = (t * t * (3 - 2 * t))[..., None]
def vremap(a, src):
    y0 = np.clip(np.floor(src).astype(int), 0, H - 1); y1 = np.clip(y0 + 1, 0, H - 1); f = (src - np.floor(src))[:, None, None]
    return (a[y0] * (1 - f) + a[y1] * f) * ((src >= 0) & (src < H - 1))[:, None, None]
def compose(path):
    w = load(path); dx, dy = align(w)
    w = np.roll(np.roll(w, -dy, 0), -dx, 1)
    if dx < 0: w[:, :-dx] = 0
    if dx > 0: w[:, W - dx:] = 0
    s = sole_y(w)
    k = float(np.clip((FLOOR - STRETCH0) / (s - STRETCH0) - 1, -KMAX, KMAX))
    w = vremap(w, np.where(ys >= STRETCH0, STRETCH0 + (ys - STRETCH0) / (1 + k), ys))
    shift = FLOOR - (STRETCH0 + (s - STRETCH0) * (1 + k))
    # cross-fade in the band, but where the walk skirt is narrower keep the idle skirt solid (no haze)
    extra = idle * (1 - w[..., 3:4]) * np.sqrt(wI)
    out = vremap(idle * wI + (1 - wI) * (w + extra), ys - shift)
    return out, dict(dx=dx, dy=dy, sole=s, stretch=round(k, 3), body_shift=round(float(shift), 1))
def to_game(a):
    nw, nh = round(W * SCALE), round(H * SCALE)
    s = np.array(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA').resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255
    al = s[..., 3:4]; s[..., :3] = np.where(al > 1e-4, s[..., :3] / np.maximum(al, 1e-4), 0)
    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    out.paste(Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8), 'RGBA'),
              (round(DST_FOOT[0] - SRC_FOOT[0] * SCALE), round(DST_FOOT[1] - SRC_FOOT[1] * SCALE)))
    return out
report = {}
spr = os.path.join(PROJ, 'actors', 'cecilia', 'Sprites')
for wk, spec in WALKS.items():
    frames, t, imgs = [], 0, []
    for key, path, hold in spec['frames']:
        full, info = compose(path); g = to_game(full)
        name = f'walk_v2_{key}'; g.save(os.path.join(spr, name + '.png'))
        report[key] = info; frames.append((name, t, hold)); t += hold; imgs.append((g, hold))
        Image.fromarray((np.clip(unpm(full) * full[..., 3:4] + (1 - full[..., 3:4]), 0, 1) * 255).astype(np.uint8)).resize((525, 750)).save(os.path.join(PREV, f'full_{key}.jpg'))
    json.dump(frames, open(os.path.join(PREV, f'timeline_{wk}.json'), 'w'))
    # preview GIF: in place, and moving at the real walk speed over a floor with marks
    px_per_frame = spec['speed'] / 120 / 55
    for mode in ('inplace', 'moving'):
        seq, x = [], 0.0
        for rep in range(3):
            for g, hold in imgs:
                for _ in range(hold):
                    seq.append((g, x)); x += px_per_frame if mode == 'moving' else 0
        frames_out = []
        Wd = 700 if mode == 'moving' else 300
        x0 = 60 if px_per_frame > 0 else Wd - 300
        for i, (g, xx) in enumerate(seq[::2]):
            bg = Image.new('RGBA', (Wd, 300), (235, 235, 235, 255))
            from PIL import ImageDraw
            d = ImageDraw.Draw(bg); d.line([(0, 281), (Wd, 281)], fill=(120, 120, 120, 255))
            for mx in range(0, Wd, 40): d.line([(mx, 281), (mx, 287)], fill=(120, 120, 120, 255))
            bg.alpha_composite(g.crop((360, 340, 660, 640)), (int(x0 + xx * (1 if mode == 'moving' else 0)), 0))
            frames_out.append(bg.convert('P', palette=Image.ADAPTIVE))
        frames_out[0].save(os.path.join(PREV, f'walk_{wk}_{mode}.gif'), save_all=True, append_images=frames_out[1:], duration=33, loop=0, disposal=2)
print(json.dumps(report, indent=0))
