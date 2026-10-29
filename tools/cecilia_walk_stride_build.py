"""Cecilia walk v3: normal stride, planted feet.
- Each drawing: idle upper body + walk legs (same compositing as cecilia_walk_build.py), floor-aligned.
- Timing: every drawing has an ideal moment u_i (body travel when its standing foot is exactly in place);
  drawings switch halfway between ideal moments.
- Per game frame, the legs are leaned (horizontal shear pivoting at the hip) by s = u_i - u so the standing
  foot stays fixed on the floor while the body glides at constant speed.
- Backward walk = same cycle in reverse at the back-walk speed.
Usage: python tools/cecilia_walk_stride_build.py <sprites_root> <project_dir> <preview_dir>
"""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw
SRC, PROJ, PREV = sys.argv[1:4]; os.makedirs(PREV, exist_ok=True)
sys.argv = [sys.argv[0], SRC, PROJ, os.path.join(PREV, '_unused')]
os.makedirs(sys.argv[3], exist_ok=True)
import importlib.util
spec = importlib.util.spec_from_file_location('wb', os.path.join(PROJ, 'tools', 'cecilia_walk_build_lib.py'))
wb = importlib.util.module_from_spec(spec); spec.loader.exec_module(wb)
F = 'Cecilia/Forward/'
SEQ = [  # pose, file, standing foot side used for the ideal moment ('L' or 'R' shoe in the drawing), chain
    ('C_A', F + 'Cecilia_Walk_Forward_01.png', 'R', 'S'),
    ('P_A', F + 'Cecilia_Walk_Stride_W4_2.png', 'L', 'S'),
    ('C_B', F + 'Cecilia_Walk_Stride_W5_1.png', 'L', 'S'),
    ('D_B', F + 'Cecilia_Walk_Forward_02.png', 'R', 'R'),
    ('P_B', F + 'Cecilia_Walk_Stride_W7_1.png', 'L', 'R'),
    ('U_B', F + 'Cecilia_Walk_Stride_W8_1_extracted.png', 'L', 'R'),
]
HIP = 880
VF_UNITS, VB_UNITS = 32000, 21000
UNIT_TO_SRC = 1 / 120 / 55 / wb.SCALE      # velocity units -> source px per frame
comp, sh = {}, {}
for pose, path, side, ch in SEQ:
    full, info = wb.compose(path)
    comp[pose] = (full, info)
    sh[pose] = wb.shoe_contacts(full)
FOOT = sh['P_A'][0]['max'] - sh['P_A'][0]['min']       # flat standing shoe length
def ref(pose, idx): return wb.contact_ref(sh[pose][idx], FOOT)
u = {'C_A': 0.0}
sockF = ref('C_A', 1)
u['P_A'] = sockF - ref('P_A', 0); u['C_B'] = sockF - ref('C_B', 0)
ribF = ref('C_B', 1) + u['C_B']
u['D_B'] = ribF - ref('D_B', 1); u['P_B'] = ribF - ref('P_B', 0); u['U_B'] = ribF - ref('U_B', 0)
stride = ribF - ref('C_A', 0)   # ribbon foot reaches the next contact-A position
order = [p for p, *_ in SEQ]; us = [u[p] for p in order]
assert all(b > a for a, b in zip(us, us[1:] + [stride])), us
bounds = [(a + b) / 2 for a, b in zip(us, us[1:] + [stride])]   # end of each drawing's range
def drawing_at(x):
    x %= stride
    if x >= bounds[-1]: return order[0], us[0] + stride
    for p, b, ui in zip(order, bounds, us):
        if x < b: return p, ui
H, W = 1500, 1049
ys = np.arange(H, dtype=np.float32)
def shear(a, s, body_shift):
    hip = HIP + body_shift
    frac = np.clip((ys - hip) / (wb.FLOOR - hip), 0, 1)[:, None]
    xs = np.arange(W, dtype=np.float32)[None, :] - s * frac        # sample from x - shift
    x0 = np.floor(xs).astype(int); fx = (xs - x0)[..., None]
    yy = np.broadcast_to(np.arange(H)[:, None], (H, W))
    def g(xx):
        ok = (xx >= 0) & (xx < W)
        return a[yy, np.clip(xx, 0, W - 1)] * ok[..., None]
    return g(x0) * (1 - fx) + g(x0 + 1) * fx
spr = os.path.join(PROJ, 'actors', 'cecilia', 'Sprites')
report = {'stride_src_px': round(stride, 1), 'ideal_u': {p: round(u[p], 1) for p in order}}
for walk, units in (('F', VF_UNITS), ('B', -VB_UNITS)):
    vt = abs(units) * UNIT_TO_SRC
    T = max(2, round(stride / vt)); v = stride / T
    new_units = round(v / UNIT_TO_SRC / 10) * 10
    frames, imgs, maxs = [], [], 0
    for t in range(T):
        x = (t + 0.5) * v if walk == 'F' else stride - (t + 0.5) * v
        p, ui = drawing_at(x)
        s = ui - (x if x >= us[0] else x)            # lean so the standing foot stays put
        if p == order[0] and x < bounds[-1] and ui > stride - 1: s = ui - x
        if p == order[0] and x >= bounds[-1]: s = ui - x
        maxs = max(maxs, abs(s))
        full, info = comp[p]
        g = wb.to_game(shear(full, s, info['body_shift']))
        name = f'walk_v3_{walk}{t:02d}'; g.save(os.path.join(spr, name + '.png'))
        frames.append((name, t, 1)); imgs.append((g, p, s))
    json.dump(frames, open(os.path.join(PREV, f'timeline_{walk}.json'), 'w'))
    report[walk] = dict(frames=T, velocity_units=(new_units if walk == 'F' else -new_units), max_lean_src_px=round(maxs, 1),
                        poses=[im[1] for im in imgs])
    # previews: in place and moving at speed over a marked floor (every frame, 60 fps -> show at 30 by skipping)
    for mode in ('inplace', 'moving'):
        outs, X = [], 0.0
        step = v * wb.SCALE * (1 if walk == 'F' else -1)
        Wd = 300 if mode == 'inplace' else 720
        x0 = 30 if walk == 'F' else Wd - 330
        for rep in range(3):
            for i, (g, p, s) in enumerate(imgs):
                if i % 2 == 0:
                    bg = Image.new('RGBA', (Wd, 300), (235, 235, 235, 255)); d = ImageDraw.Draw(bg)
                    d.line([(0, 281), (Wd, 281)], fill=(120, 120, 120, 255))
                    for mx in range(0, Wd, 40): d.line([(mx, 281), (mx, 288)], fill=(120, 120, 120, 255))
                    bg.alpha_composite(g.crop((360, 340, 660, 640)), (int(x0 + (X if mode == 'moving' else 0)), 0))
                    outs.append(bg.convert('P', palette=Image.ADAPTIVE))
                X += step
        outs[0].save(os.path.join(PREV, f'stride_{walk}_{mode}.gif'), save_all=True, append_images=outs[1:], duration=33, loop=0, disposal=2)
json.dump(report, open(os.path.join(PREV, 'report.json'), 'w'), indent=1)
print(json.dumps(report))
