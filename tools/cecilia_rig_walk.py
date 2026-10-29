"""Cecilia cut-out rig walk (prototype).
One drawing (idle 01_ready) cut into parts: upper body (+skirt, sword, sheath), and per leg thigh / shin / shoe.
Legs are posed with 2-bone IK from foot paths (planted stance, heel-strike and toe-off roll, arced swing),
hips glide at the walk speed with a small bob, then each 60 fps frame is rendered as a sprite.
Usage: python tools/cecilia_rig_walk.py <sprites_root> <out_dir> [forward|backward]
"""
import sys, os, math, json, numpy as np
from PIL import Image, ImageDraw
SRC, OUT = sys.argv[1], sys.argv[2]; MODE = sys.argv[3] if len(sys.argv) > 3 else 'forward'
os.makedirs(OUT, exist_ok=True)
IDLE = os.path.join(SRC, 'Cecilia_Original_Idle_Style/01_Idle/01_ready.png')
FLOOR = 1446
SCALE = 250 / 1433; SRC_FOOT = (94, 1446); DST_FOOT = (403, 621); CANVAS = 1024
# rest skeleton (source px, measured on 01_ready)
J = {'ribbon': dict(hip=(450, 790), knee=(300, 1050), ankle=(175, 1290)),
     'sock':   dict(hip=(616, 790), knee=(850, 1000), ankle=(952, 1290))}
KNEE_R, ANKLE_R = 58, 34
KNEE_R_LEG = {'ribbon': 44, 'sock': 56}
HIP_Y = 770                                        # walk hip height (idle hips are at 790)
# walk parameters
SPEED_UNITS = 32000 if MODE == 'forward' else -21000
V = SPEED_UNITS / 120 / 55 / SCALE              # source px per frame (signed)
T = 32 if MODE == 'forward' else 40              # frames per cycle
STRIDE = abs(V) * T
BETA = 0.56                                       # fraction of the cycle a foot is planted
FOOT_OFFSET = 15                                  # stance centre slightly ahead of the hip
LIFT = 62                                         # swing foot height (source px)
BOB = 9                                           # hip bob amplitude (source px)
STRIKE_ANG, TOEOFF_ANG = -12, 28                  # degrees (negative = toe up)

def load():
    a = np.array(Image.open(IDLE).convert('RGBA')).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    return a
A = load(); H, W = A.shape[:2]
alpha = A[..., 3] > 0.02
c = np.where(A[..., 3:4] > 1e-4, A[..., :3] / np.maximum(A[..., 3:4], 1e-4), 1)
mx, mn = c.max(-1), c.min(-1)
lace = (A[..., 3] > 0.5) & (mn > 0.66) & (mx - mn < 0.12) & (c[..., 2] >= c[..., 0] - 0.03); lace[:650] = False; lace[1000:] = False  # cool white/grey only (skin is warm)
env = np.full(W, -1)
for x in range(W):
    ys = np.where(lace[:, x])[0]
    if len(ys) >= 3: env[x] = ys.max()
env2 = env.copy()
for x in range(W):
    seg = env[max(0, x - 14):x + 15]; seg = seg[seg >= 0]; env2[x] = seg.max() if len(seg) else -1
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
below = (YY > np.where(env2 >= 0, env2, 820)[None, :]) & (YY > 820)
sheath = (YY < 912) & (XX < 328)
legs = alpha & below & ~sheath
leg_mask = {'ribbon': legs & (XX < 560), 'sock': legs & (XX >= 560)}
upper_mask = alpha & ~legs

def axis(p, q):
    d = np.array(q, np.float32) - np.array(p, np.float32); L = float(np.hypot(*d)); return d / L, L
def proj(p, u):  # signed distance along u from p, and across
    dx, dy = XX - p[0], YY - p[1]
    return dx * u[0] + dy * u[1], -dx * u[1] + dy * u[0]
def piece(mask):
    out = A * mask[..., None].astype(np.float32)
    ys, xs = np.where(mask)
    return out, (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)

def sample(img, px, py):
    ix = np.floor(px).astype(int); iy = np.floor(py).astype(int); fx = (px - ix)[..., None]; fy = (py - iy)[..., None]
    def g(yy, xx):
        ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
        return img[np.clip(yy, 0, H - 1), np.clip(xx, 0, W - 1)] * ok[..., None]
    return g(iy, ix) * (1 - fx) * (1 - fy) + g(iy, ix + 1) * fx * (1 - fy) + g(iy + 1, ix) * (1 - fx) * fy + g(iy + 1, ix + 1) * fx * fy

def strip(leg_img, p, q, half_w, v_top, v_bot):
    """Resample the segment p->q into a straight strip: rows = distance along the bone from p, cols = across."""
    u, L = axis(p, q); n = (-u[1], u[0])
    vs = np.arange(v_top, v_bot, dtype=np.float32)[:, None]; ws = np.arange(-half_w, half_w, dtype=np.float32)[None, :]
    px = p[0] + vs * u[0] + ws * n[0]; py = p[1] + vs * u[1] + ws * n[1]
    return sample(leg_img, px, py), L, (-v_top)  # image, length, row of p

def cap(img, row_cut, keep_above, r):
    """Cut the strip at row_cut and keep one side plus a round cap of radius r centred on the joint."""
    h, w = img.shape[:2]; yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); cx = w / 2
    side = (yy <= row_cut) if keep_above else (yy >= row_cut)
    disc = (yy - row_cut) ** 2 + (xx - cx) ** 2 <= r * r
    m = (side | disc).astype(np.float32)[..., None]
    return img * m

def extrude_top(img, prow, L):
    """Find the first row where both thigh edges are the real contour (no longer cut by the skirt),
    and replace everything above it with that row (a clean tube under the skirt)."""
    h, w = img.shape[:2]; a = img[..., 3] > 0.85
    xl = np.full(h, np.nan); xr = np.full(h, np.nan)
    for r in range(h):
        xs = np.where(a[r])[0]
        if len(xs) >= 12: xl[r], xr[r] = xs.min(), xs.max()
    r_end = int(prow + 0.85 * L)
    r_full = None
    for r in range(int(prow), r_end - 25):
        if np.isnan(xl[r]) or np.isnan(xl[r + 25]): continue
        if (xl[r + 25] - xl[r]) > -5 and (xr[r + 25] - xr[r]) < 5 and (xr[r] - xl[r]) > 40:
            r_full = r; break
    out = img.copy()
    if r_full is None: return out
    out[:r_full] = img[r_full][None, :, :]
    return out

parts = {}
for leg, j in J.items():
    limg = A * leg_mask[leg][..., None]
    # thigh strip: from 110 px above the hip to past the knee
    th, L1, prow = strip(limg, j['hip'], j['knee'], 150, -110, 0)
    _, L1 = axis(j['hip'], j['knee'])
    th, _, prow = strip(limg, j['hip'], j['knee'], 150, -110, int(L1) + KNEE_R + 4)
    if leg == 'ribbon':
        cc = np.where(th[..., 3:4] > 1e-4, th[..., :3] / np.maximum(th[..., 3:4], 1e-4), 0)
        skin = (th[..., 3] > 0.85) & (cc[..., 0] > 0.85) & (cc[..., 1] > 0.72) & (cc[..., 0] - cc[..., 2] > 0.06)
        rows = range(int(prow), int(prow + 0.4 * L1))
        r_skin = max(rows, key=lambda r: skin[r].sum())
        cols = np.where(skin[r_skin])[0]
        tube = np.zeros_like(th[r_skin]); tube[cols] = th[r_skin][cols]
        # keep the outline: darken the two edge columns of the tube
        for e in (cols.min(), cols.max()):
            tube[max(e - 2, 0):e + 3] = th[r_skin + 6][max(e - 2, 0):e + 3] if th[r_skin + 6][e, 3] > 0.5 else tube[max(e - 2, 0):e + 3]
        th[:r_skin] = tube[None]
    else:
        th = extrude_top(th, prow, L1)
    th = cap(th, prow + L1, True, KNEE_R_LEG[leg])
    parts[leg + '_thigh'] = dict(img=th, pivot=(150.0, float(prow)), rest=math.pi / 2, strip=True)
    _, L2 = axis(j['knee'], j['ankle'])
    sh, _, krow = strip(limg, j['knee'], j['ankle'], 130, -KNEE_R - 4, int(L2) + ANKLE_R + 4)
    sh = cap(sh, krow, False, KNEE_R_LEG[leg])
    sh = cap(sh, krow + L2, True, ANKLE_R)
    parts[leg + '_shin'] = dict(img=sh, pivot=(130.0, float(krow)), rest=math.pi / 2, strip=True)
# shoe: from the sock leg (it faces forward); used for both feet
j = J['sock']; u2, L2 = axis(j['knee'], j['ankle']); v2, _ = proj(j['knee'], u2)
shoe = leg_mask['sock'] & (v2 >= L2 - 22)
parts['shoe'] = dict(img=piece(shoe)[0], pivot=j['ankle'], rest=0.0)
SOLE_Y = float(np.where(shoe & (A[..., 3] > 0.5))[0].max())
sy, sx = np.where(shoe & (A[..., 3] > 0.5) & (YY > SOLE_Y - 8))
TOE = (float(sx.max()) - 18, SOLE_Y); HEEL = (float(sx.min()) + 10, SOLE_Y)
print('shoe sole', SOLE_Y, 'heel', HEEL, 'toe', TOE)
parts['upper'] = dict(img=A * upper_mask[..., None], pivot=(0, 0), rest=0.0)

def place(img, pivot_src, pivot_dst, ang, canvas, dark=1.0):
    """Draw img rotated by ang (radians, image coords) about pivot_src, moved to pivot_dst (premultiplied over)."""
    ys, xs = np.where(img[..., 3] > 0.003)
    if not len(xs): return
    corners = np.array([[xs.min(), ys.min()], [xs.max(), ys.min()], [xs.min(), ys.max()], [xs.max(), ys.max()]], np.float32) - pivot_src
    ca, sa = math.cos(ang), math.sin(ang)
    rc = np.stack([corners[:, 0] * ca - corners[:, 1] * sa, corners[:, 0] * sa + corners[:, 1] * ca], 1) + pivot_dst
    x0, y0 = np.floor(rc.min(0)).astype(int) - 2; x1, y1 = np.ceil(rc.max(0)).astype(int) + 2
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0: return
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = gx - pivot_dst[0], gy - pivot_dst[1]
    sxf = dx * ca + dy * sa + pivot_src[0]; syf = -dx * sa + dy * ca + pivot_src[1]
    ix = np.floor(sxf).astype(int); iy = np.floor(syf).astype(int); fx = (sxf - ix)[..., None]; fy = (syf - iy)[..., None]
    ih, iw = img.shape[:2]
    def g(yy, xx):
        ok = (xx >= 0) & (xx < iw) & (yy >= 0) & (yy < ih)
        return img[np.clip(yy, 0, ih - 1), np.clip(xx, 0, iw - 1)] * ok[..., None]
    s = (g(iy, ix) * (1 - fx) * (1 - fy) + g(iy, ix + 1) * fx * (1 - fy) + g(iy + 1, ix) * (1 - fx) * fy + g(iy + 1, ix + 1) * fx * fy)
    if dark != 1.0: s[..., :3] *= dark
    reg = canvas[y0:y1, x0:x1]
    canvas[y0:y1, x0:x1] = s + reg * (1 - s[..., 3:4])

def rot(v, ang):
    ca, sa = math.cos(ang), math.sin(ang); return (v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca)
def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

ANK_REST = J['sock']['ankle']
def foot_pose(leg, ph):
    """ph in [0,1): 0 = heel strike. Returns (ankle position relative to own hip x, foot angle)."""
    fwd = 1 if V > 0 else -1
    half = BETA * STRIDE / 2
    front, back = FOOT_OFFSET + half * fwd, FOOT_OFFSET - half * fwd       # ground anchor (ankle-rest x) positions rel. hip
    if ph < BETA:      # stance: anchor moves from front to back (hip passes over)
        s = ph / BETA
        gx = front + (back - front) * s
        if fwd > 0 and s < 0.12:  ang = math.radians(STRIKE_ANG) * (1 - smooth(s / 0.12)); piv = HEEL
        elif s > 0.72:            ang = math.radians(TOEOFF_ANG) * smooth((s - 0.72) / 0.28); piv = TOE
        else:                     ang = 0.0; piv = HEEL
        if fwd < 0:   # walking backward: land on the toe, roll to flat, lift the heel... mirrored roll
            if s < 0.15: ang = math.radians(TOEOFF_ANG) * (1 - smooth(s / 0.15)); piv = TOE
            elif s > 0.8: ang = math.radians(STRIKE_ANG) * smooth((s - 0.8) / 0.2); piv = HEEL
            else: ang = 0.0; piv = HEEL
        # ankle from the pivot staying on the ground
        rest_vec = (ANK_REST[0] - piv[0], ANK_REST[1] - piv[1])
        rv = rot(rest_vec, ang)
        piv_x = gx + (piv[0] - ANK_REST[0])
        ankle = (piv_x + rv[0], FLOOR + rv[1])
        return ankle, ang
    s = (ph - BETA) / (1 - BETA)        # swing
    e = smooth(s)
    a0 = foot_pose(leg, BETA - 1e-6)[0]; a1 = foot_pose(leg, 0.0)[0]
    ax = a0[0] + (a1[0] - a0[0]) * e
    ay = a0[1] + (a1[1] - a0[1]) * e - LIFT * math.sin(math.pi * s)
    ang0 = math.radians(TOEOFF_ANG) if V > 0 else math.radians(STRIKE_ANG)
    ang1 = math.radians(STRIKE_ANG) if V > 0 else math.radians(TOEOFF_ANG)
    ang = ang0 + (ang1 - ang0) * smooth(s * 1.2) + (math.radians(12) * math.sin(math.pi * s) if V > 0 else 0)
    return (ax, ay), ang

def ik(hip, ank, L1, L2, knee_fwd=1):
    dx, dy = ank[0] - hip[0], ank[1] - hip[1]; d = math.hypot(dx, dy)
    d = min(d, (L1 + L2) * 0.9995); d = max(d, abs(L1 - L2) + 1)
    a = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    s = math.sin(a) * knee_fwd; cs = math.cos(a)
    kx = hip[0] + L1 * (ux * cs + uy * s); ky = hip[1] + L1 * (-ux * s + uy * cs)
    return (kx, ky)

LEN = {leg: (axis(j['hip'], j['knee'])[1], axis(j['knee'], j['ankle'])[1]) for leg, j in J.items()}
def hip_y_raw(t):
    ph_s = (t / T) % 1.0; ph_r = (ph_s + 0.5) % 1.0
    poses = {'sock': foot_pose('sock', ph_s), 'ribbon': foot_pose('ribbon', ph_r)}
    bob = -BOB * math.cos(4 * math.pi * (ph_s - BETA / 2))
    hy = HIP_Y + BOB + bob
    for leg in J:
        hx = J[leg]['hip'][0]; (ax, ay), _ = poses[leg]; ax += hx
        L = sum(LEN[leg]) * 0.997; dxa = ax - hx
        if dxa * dxa < L * L: hy = max(hy, ay - math.sqrt(L * L - dxa * dxa))
    return hy, poses
_HY = [hip_y_raw(t)[0] for t in range(T)]
_HY = [max(_HY[t], _HY[(t + T // 2) % T]) for t in range(T)]                 # both steps dip the same
for _ in range(3):
    _HY = [(_HY[(t - 2) % T] + 2 * _HY[(t - 1) % T] + 3 * _HY[t] + 2 * _HY[(t + 1) % T] + _HY[(t + 2) % T]) / 9 for t in range(T)]  # smooth
def frame(t):
    _, poses = hip_y_raw(t)
    hy = _HY[t % T]
    dyb = hy - 790
    canvas = np.zeros((H, W, 4), np.float32); info = {}
    for leg, dark in (('ribbon', 0.86), ('sock', 1.0)):
        hip = (J[leg]['hip'][0], J[leg]['hip'][1] + dyb)
        (ax, ay), fang = poses[leg]; ank = (ax + J[leg]['hip'][0], ay)
        L1, L2 = LEN[leg]
        knee = ik(hip, ank, L1, L2, 1)
        a_th = math.atan2(knee[1] - hip[1], knee[0] - hip[0]); a_sh = math.atan2(ank[1] - knee[1], ank[0] - knee[0])
        th, sh = parts[leg + '_thigh'], parts[leg + '_shin']
        place(sh['img'], sh['pivot'], knee, a_sh - sh['rest'], canvas, dark)
        place(parts['shoe']['img'], parts['shoe']['pivot'], ank, fang, canvas, dark)
        place(th['img'], th['pivot'], hip, a_th - th['rest'], canvas, dark)
        info[leg] = dict(ankle=ank, knee=knee, foot=fang)
    place(parts['upper']['img'], (0, 0), (0, dyb), 0.0, canvas)
    return canvas, info, dyb

def to_game(a):
    nw, nh = round(W * SCALE), round(H * SCALE)
    s = np.array(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA').resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255
    al = s[..., 3:4]; s[..., :3] = np.where(al > 1e-4, s[..., :3] / np.maximum(al, 1e-4), 0)
    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    out.paste(Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8), 'RGBA'),
              (round(DST_FOOT[0] - SRC_FOOT[0] * SCALE), round(DST_FOOT[1] - SRC_FOOT[1] * SCALE)))
    return out

if __name__ == '__main__':
    games, fulls, infos = [], [], []
    for t in range(T):
        cv, info, dyb = frame(t); infos.append((info, dyb))
        g = to_game(cv); games.append(g)
        if t % 4 == 0: fulls.append(cv)
        g.save(os.path.join(OUT, f'rig_{MODE[0].upper()}{t:02d}.png'))
    # planted-foot check: ground anchors in world space
    rep = []
    for t, (info, dyb) in enumerate(infos):
        rep.append({leg: round(info[leg]['ankle'][0] + V * t, 1) for leg in info} | {'bob': round(dyb, 1)})
    json.dump(dict(T=T, V=V, stride=STRIDE, frames=rep), open(os.path.join(OUT, f'rig_{MODE}_report.json'), 'w'), indent=0)
    # previews
    for kind in ('inplace', 'moving'):
        seq, X = [], 0.0
        Wd = 300 if kind == 'inplace' else 760; x0 = 30 if V > 0 else Wd - 330
        for rep_i in range(3):
            for t, g in enumerate(games):
                if t % 2 == 0:
                    bg = Image.new('RGBA', (Wd, 300), (235, 235, 235, 255)); d = ImageDraw.Draw(bg)
                    d.line([(0, 281), (Wd, 281)], fill=(120, 120, 120, 255))
                    for mxx in range(0, Wd, 40): d.line([(mxx, 281), (mxx, 288)], fill=(120, 120, 120, 255))
                    bg.alpha_composite(g.crop((360, 340, 660, 640)), (int(x0 + (X if kind == 'moving' else 0)), 0))
                    seq.append(bg.convert('P', palette=Image.ADAPTIVE))
                X += V * SCALE * 1
                X += V * SCALE * 0
        seq[0].save(os.path.join(OUT, f'rig_{MODE}_{kind}.gif'), save_all=True, append_images=seq[1:], duration=33, loop=0, disposal=2)
    # contact sheet of full-res poses
    sh = Image.new('RGB', (262 * len(fulls), 375), 'white')
    for i, cv in enumerate(fulls):
        im = Image.fromarray((np.clip(np.where(cv[..., 3:4] > 1e-4, cv[..., :3] / np.maximum(cv[..., 3:4], 1e-4), 1) * cv[..., 3:4] + (1 - cv[..., 3:4]), 0, 1) * 255).astype(np.uint8))
        sh.paste(im.resize((262, 375)), (262 * i, 0))
    sh.save(os.path.join(OUT, f'rig_{MODE}_sheet.png'))
    print('T', T, 'V src/f', round(V, 2), 'stride', round(STRIDE), 'done')
