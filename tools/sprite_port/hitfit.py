"""HITBOX FIT: fits a fighter's hitboxes to the sprites its animations show now.

    python hitfit.py <character> [animation ...]            look only: draws checks/<char>/fit_<anim>.png
    python hitfit.py <character> [animation ...] --write    also updates the hitbox files

It reads what the game shows (each AnimationData's sprites, offsets, rotations) and, for every
hitbox state, fits that state's hitbox file to the pose on screen during it:
  hurtboxes  (green)  head / body / legs bands of the body silhouette (thin things like the blade
                      or hair strands don't count), plus an arm or leg box when a limb sticks out
                      on active and recovery frames. A file with no hurtboxes (invincible) stays so.
  attack     (red)    the slash trail / effect drawn during the active frames, or the limb that
                      sticks out when nothing is drawn (hilt jabs, kicks). Damage, hitstun,
                      knockback and every other property stay exactly as they were.
  proximity  (blue)   moved and stretched with the attack box (keeps its old margins).
  pushbox    (yellow) never changed (shared templates).
Files are updated in place: same file, same uid, nothing that points at them changes. The first
time a file is changed its old copy is saved in _backup_stage_select/pre_sprite_port/Hitboxes/.
Hand edits are safe: a file changed since hitfit last wrote it is skipped (use --force to refit),
unless the change was a moves_<fighter>.py run putting new attack values into it.

Manifest options (manifests/<char>.json, key "hitfit", all optional):
  "skip":     ["100_Hitbox_Burst", ...]            files to leave alone
  "attack_part": {"<file or animation>": "auto" | "trail" | "trail_all" | "weapon" | "edge" | "top" | "keep"}
              what the attack box covers: the effect in front (trail), effects on both sides
              (trail_all), the held weapon (weapon), the body's leading edge (edge), the top of the pose
              (top: fist pumps, uppercuts), or nothing new (keep)
  "min_fx":   600                                  smallest effect area (px) counted as a trail (thin lasers)
  (the effect colour is the manifest's "fx": yellow (Cecilia), cyan (Leticia), radiant (Flan's soft golden glow))
  "hair":     {"hsv": [[h0, h1, s_min, v_min]], "head_frac": 0.24}   hair colour below the head
              doesn't count as body for hurtboxes (long twin tails)
  "fit_from": {"1_Hitbox_Crouch": ["7_CEC_Crouching", 0]}   file -> animation + frame to fit it to
  "fresh_size": true | ["<file or animation>", ...]   attack boxes sized from the drawing only (normally an attack
              box stays at least as big as the old one, the move's design; boxes copied from another fighter's
              moves, e.g. Flan's from Cecilia's sword, shouldn't keep that size)
  "boxes":    {"5_Hitbox_5A_2": {"attack": [[x0, y0, x1, y1]], "hurt": [...]}}
              hand-made boxes in world pixels (x forward from the character origin, y up from
              the floor; the check images have a 50 px grid), used instead of the fitted ones.
"""
import sys, os, re, json, math, hashlib
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from tres import Tres
from analyze import fx_mask, radiant_mask
BODY_BOX_LIMIT = 16   # PhysicsBody.HitboxesLimit (the fighters' scenes keep the default): boxes past it are ignored

try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
except Exception:
    FONT = ImageFont.load_default()

def res_file(res): return os.path.join(PROJ, res.replace('res://', ''))
def md5(s): return hashlib.md5(s.encode('utf-8')).hexdigest()
def _kit_record(res):
    """the md5 fdk.py recorded when it last wrote this file (a moves_<fighter>.py run), or None"""
    import fdk
    return fdk._state().get(res)

# ------------------------------------------------------------------ reading what the game shows
class Anim:
    def __init__(self, char, name):
        self.name = name
        self.path = os.path.join(PROJ, 'actors', char, 'AnimationData', name + '_AnimData.tres')
        t = Tres(open(self.path, encoding='utf-8').read())
        self.dur = int(t.res_get('Duration') or 0)
        self.keys = []
        for aid in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Animations') or ''):
            body = t.sub_get(aid)[2]; at = 0; mods = []
            for l in body:
                m = re.match(r'AtFrame = (\d+)', l)
                if m: at = int(m.group(1))
                m = re.match(r'Modifiers = \[(.*)\]', l)
                if m: mods = re.findall(r'SubResource\("([^"]+)"\)', m.group(1))
            ms = []
            for mid in mods:
                d = {'off': (0.0, 0.0), 'rot': 0, 'flipx': False, 'contact': False, 'tex': None, 'sx': 1.0}
                for l in t.sub_get(mid)[2]:
                    m = re.match(r'Sprite = ExtResource\("([^"]+)"\)', l)
                    if m: d['tex'] = t.ext_by_id(m.group(1))['path']
                    m = re.match(r'Offset = Vector2\((-?[\d.]+), (-?[\d.]+)\)', l)
                    if m: d['off'] = (float(m.group(1)), float(m.group(2)))
                    m = re.match(r'Rotation = (-?\d+)', l)
                    if m: d['rot'] = int(m.group(1))
                    if l.strip() == 'FlipX = true': d['flipx'] = True
                    if l.strip() == 'OnlyOnContact = true': d['contact'] = True
                    m = re.match(r'Scale = Vector2\((-?[\d.]+), (-?[\d.]+)\)', l)
                    if m: d['sx'] = float(m.group(1))   # stretched layer (build.py fx_sx / fx_reach)
                if d['tex']: d['layer'] = len(ms); ms.append(d)   # layer 0 = the body, 1 = its effect layer (build.py 'fx')
            self.keys.append((at, ms))
        self.keys.sort(key=lambda k: k[0])
        self.states = []
        for hid in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or ''):
            body = '\n'.join(t.sub_get(hid)[2])
            hd = re.search(r'HitboxData = ExtResource\("([^"]+)"\)', body)
            if not hd: continue
            at = re.search(r'AtFrame = (\d+)', body); st = re.search(r'animationStage = (\d+)', body)
            self.states.append((int(at.group(1)) if at else 0, int(st.group(1)) if st else 0, t.ext_by_id(hd.group(1))['path']))
        self.states.sort(key=lambda s: s[0])
    def span(self, i):
        a = self.states[i][0]
        b = self.states[i + 1][0] if i + 1 < len(self.states) else max(self.dur, a + 1)
        return a, max(b, a + 1)
    def keys_in(self, a, b):
        out = []
        for j, (at, ms) in enumerate(self.keys):
            nxt = self.keys[j + 1][0] if j + 1 < len(self.keys) else 10 ** 9
            if at < b and nxt > a: out.append((at, ms))
        return out
    def key_at(self, f):
        cur = self.keys[0] if self.keys else None
        for k in self.keys:
            if k[0] <= f: cur = k
        return cur

_png = {}
def png(res):
    if res not in _png: _png[res] = np.array(Image.open(res_file(res)).convert('RGBA'))
    return _png[res]

def world(rows, cols, h, w, md):
    """sprite pixel centres -> world px (x forward, y up from the floor), like the engine draws them"""
    x = (md['off'][0] + ((w - 1 - cols) if md['flipx'] else cols) + 0.5) * md.get('sx', 1.0)
    y = md['off'][1] + (h - 1 - rows) + 0.5
    if md['rot']:
        t = math.radians(md['rot']); c, s = math.cos(t), math.sin(t)
        x, y = c * x - s * y, s * x + c * y
    return np.stack([x, y], 1).astype(np.float32)

def trail_mask(a, kind, min_area):
    """slash trails / energy effects: the bright effect colour plus its white-hot core, in pieces
    big enough to be an effect (the yellow neckerchief or headband V never count)."""
    if kind == 'radiant':   # Flan: soft golden glow (her opaque yellow frills don't count)
        return radiant_mask(a, min_area=min_area)
    r, g, b, al = [a[..., i].astype(np.int16) for i in range(4)]
    vis = al > 60
    if kind == 'yellow':   hi1, hi2, lo = r, g, b
    elif kind == 'cyan':   hi1, hi2, lo = b, g, r
    elif kind == 'gold':   hi1, hi2, lo = r, g, b
    else: return np.zeros(a.shape[:2], bool)
    hiA, hiB = np.maximum(hi1, hi2), np.minimum(hi1, hi2)
    col = vis & (hiA > 215) & (hiB > 170) & (lo < 150) & ((hiB - lo) > 60)
    core = vis & (hi1 > 235) & (hi2 > 235) & ((hi2 - lo) > 28)
    m = col | core
    if not m.any(): return m
    # white-hot middles of thick trails: near-white pixels right next to the effect colour
    near = cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))).astype(bool)
    white = vis & (np.minimum(np.minimum(r, g), b) > 200)
    n, lab, st, _ = cv2.connectedComponentsWithStats(white.astype(np.uint8), 8)
    if n > 1:
        touch = np.bincount(lab[near & white], minlength=n) > 0.5 * np.maximum(st[:, cv2.CC_STAT_AREA], 1)
        touch[0] = False
        m |= touch[lab]
    grown = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(grown, 8)
    cnt = np.bincount(lab[m], minlength=n)
    keep = cnt >= min_area; keep[0] = False
    return keep[lab] & m

_masks = {}
HAIR = {}   # manifest hitfit "hair": {"hsv": [[h0, h1, s_min, v_min], ...], "head_frac": 0.24} (OpenCV hue 0-179)
def masks(md, fxkind, open_px, step=2, min_area=1500):
    key = (md['tex'], fxkind, open_px)
    if key not in _masks:
        a = png(md['tex']); al = a[..., 3] > 128
        fx = trail_mask(a, fxkind, min_area)
        solid = al & ~fx
        def big_parts(mk, frac):
            n, lab, st, _ = cv2.connectedComponentsWithStats(mk.astype(np.uint8), 8)
            if n <= 2: return mk
            keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > frac * st[1:, cv2.CC_STAT_AREA].max()
            return keep[lab] & mk
        solid = big_parts(solid, 0.01)   # drop specks
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_px, open_px))
        body = solid
        if HAIR and HAIR.get('hsv'):   # long hair below the head isn't hurtable
            hsv = cv2.cvtColor(np.ascontiguousarray(a[..., :3]), cv2.COLOR_RGB2HSV).astype(np.int16)
            hm = np.zeros(al.shape, bool)
            for h0, h1, s0, v0 in HAIR['hsv']:
                hm |= (hsv[..., 0] >= h0) & (hsv[..., 0] <= h1) & (hsv[..., 1] >= s0) & (hsv[..., 2] >= v0)
            rows = np.where(solid.any(1))[0]
            if len(rows):
                top, hh = rows.min(), rows.max() - rows.min() + 1
                hm[:top + int(HAIR.get('head_frac', 0.24) * hh)] = False
                body = solid & ~hm
        core = big_parts(cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool), 0.04)
        _masks[key] = (a.shape[0], a.shape[1], solid, core, fx)
    h, w, solid, core, fx = _masks[key]
    def pts(mk):
        sub = np.zeros_like(mk); sub[::step, ::step] = mk[::step, ::step]
        r, c = np.where(sub)
        return world(r, c, h, w, md) if len(r) else np.zeros((0, 2), np.float32)
    return {'solid': pts(solid), 'core': pts(core), 'fx': pts(fx)}

# ------------------------------------------------------------------ hitbox files
ALIAS = {}   # res path of a split copy that doesn't exist yet -> the file it will be copied from
def read_text(res):
    path = res_file(res)
    if not os.path.exists(path) and res in ALIAS: path = res_file(ALIAS[res])
    return open(path, encoding='utf-8').read()

def new_uid():
    """a fresh Godot resource uid (same text form Godot writes)"""
    import random
    v = random.getrandbits(62) | (1 << 61); txt = ''
    while v:
        c = v % 35; txt = (chr(97 + c) if c < 26 else chr(48 + c - 26)) + txt; v //= 35
    return 'uid://' + txt

def read_hitbox(res):
    t = Tres(read_text(res))
    els = []
    for i in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or ''):
        body = t.sub_get(i)[2]; txt = '\n'.join(body)
        c = re.search(r'Center = Vector2i\((-?\d+), (-?\d+)\)', txt); z = re.search(r'Size = Vector2i\((-?\d+), (-?\d+)\)', txt)
        ty = re.search(r'HitboxType = (\d+)', txt)
        cx, cy = (int(c.group(1)), int(c.group(2))) if c else (0, 0); w, h = (int(z.group(1)), int(z.group(2))) if z else (0, 0)
        els.append({'id': i, 'type': int(ty.group(1)) if ty else 0, 'box_u': (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 'body': body})
    pb = None
    v = t.res_get('Pushbox')
    if v:
        e = t.ext_by_id(re.search(r'ExtResource\("([^"]+)"\)', v).group(1))
        if e and os.path.exists(res_file(e['path'])):
            txt = open(res_file(e['path']), encoding='utf-8').read()
            c = re.search(r'Center = Vector2i\((-?\d+), (-?\d+)\)', txt); z = re.search(r'Size = Vector2i\((-?\d+), (-?\d+)\)', txt)
            if c and z:
                cx, cy, w, h = int(c.group(1)), int(c.group(2)), int(z.group(1)), int(z.group(2))
                pb = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return t, els, pb

_types = {}
def hit_types(res):
    if res not in _types: _types[res] = [e['type'] for e in read_hitbox(res)[1]]
    return _types[res]

def write_hitbox(res, t, els, new, upx):
    """new: {type: [world px boxes]} for the types being refitted; other elements stay as they are."""
    def r100(v): return int(round(v / 100.0)) * 100
    def body_for(tmpl, b):
        x0, y0, x1, y1 = [v * upx for v in b]
        cx, cy, w, h = r100((x0 + x1) / 2), r100((y0 + y1) / 2), max(100, r100(x1 - x0)), max(100, r100(y1 - y0))
        rest = [l for l in tmpl if not l.startswith('Center = ') and not l.startswith('Size = ')]
        return rest[:1] + ['Center = Vector2i(%d, %d)' % (cx, cy), 'Size = Vector2i(%d, %d)' % (w, h)] + rest[1:]
    order = []; old_ids = {e['id'] for e in els}
    taken = set()
    prefix = {0: 'H', 2: 'P', 1: 'A'}
    for ty in (0, 2, 1):
        if ty not in new: continue
        tmpl = next(e['body'] for e in els if e['type'] == ty)
        for n, b in enumerate(new[ty]):
            i = '%s%d' % (prefix[ty], n)
            while i in taken: i += '_'
            taken.add(i); order.append((i, body_for(tmpl, b)))
    keep = [e for e in els if e['type'] not in new]
    for e in keep:
        i = e['id']
        while i in taken: i = 'K_' + i
        taken.add(i); order.append((i, e['body']))
    t.sub = [s for s in t.sub if s[0] not in old_ids]
    for i, body in order: t.sub.append([i, 'Resource', body])
    t.res_set('Hitboxes', '[%s]' % ', '.join('SubResource("%s")' % i for i, _ in order))
    return t.text()

# ------------------------------------------------------------------ fitting
def pct_box(P, lo=2, hi=98):
    return [float(np.percentile(P[:, 0], lo)), float(np.percentile(P[:, 1], lo)), float(np.percentile(P[:, 0], hi)), float(np.percentile(P[:, 1], hi))]
def area(b): return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
def union(bs): return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]

def fit_hurt(core, n):
    """band boxes over the body (core = silhouette without thin parts)."""
    if len(core) < 150: return None, None
    xs, ys = core[:, 0], core[:, 1]
    top, bot = float(np.percentile(ys, 99.6)), float(np.percentile(ys, 0.4)); H = top - bot
    if H < 30: return None, None
    if n >= 3: bands = [(top - 0.22 * H, top), (bot + 0.40 * H, top - 0.20 * H), (bot, bot + 0.44 * H)]
    elif n == 2: bands = [(bot + 0.46 * H, top), (bot, bot + 0.54 * H)]
    else: bands = [(bot, top)]
    lims = {3: [(5, 95), (4, 96), (2, 98)], 2: [(4, 96), (2, 98)], 1: [(2, 98)]}[len(bands)]
    out = []
    for (y0, y1), (lo, hi) in zip(bands, lims):
        sel = (ys >= y0) & (ys <= y1)
        if sel.sum() < 20: continue
        bx = xs[sel]
        out.append([float(np.percentile(bx, lo)), y0, float(np.percentile(bx, hi)), y1])
    return out, {'bot': bot, 'top': top, 'H': H, 'cx': float(np.median(xs))}

def front_at(boxes, ys):
    f = np.full(len(ys), -1e9, np.float32)
    for x0, y0, x1, y1 in boxes:
        f = np.where((ys >= y0) & (ys <= y1), np.maximum(f, x1), f)
    return f

def sticking_out(P, boxes, H, margin=0.02):
    if not len(P): return P
    f = front_at(boxes, P[:, 1])
    return P[(f > -1e8) & (P[:, 0] > f + margin * H)]

def fit_limb(core, boxes, H):
    """an extra hurtbox for each arm / leg that sticks out in front of its band's box."""
    out = []
    for x0, y0, x1, y1 in boxes:
        sel = (core[:, 1] >= y0) & (core[:, 1] <= y1) & (core[:, 0] > x1 + 0.02 * H)
        S = core[sel]
        if len(S) < 30: continue
        b = pct_box(S, 2, 98)
        if b[2] - x1 < 0.08 * H: continue
        b[0] = min(b[0], x1 - 0.03 * H)   # overlap the body box so there is no gap
        out.append(b)
    for b in out:   # limbs are at least ~7% of the height thick
        if b[3] - b[1] < 0.07 * H:
            c = (b[1] + b[3]) / 2; b[1], b[3] = c - 0.035 * H, c + 0.035 * H
    merged = []
    for b in sorted(out, key=lambda b: b[1]):
        if merged and b[1] <= merged[-1][3] + 0.02 * H and min(b[2], merged[-1][2]) > max(b[0], merged[-1][0]):
            merged[-1] = union([merged[-1], b])
        else: merged.append(b)
    return merged

def fronts(P, y0, y1, step=4.0):
    """front edge (max x) of P per row bin between y0 and y1"""
    nb = max(1, int((y1 - y0) / step) + 1); f = np.full(nb, -1e9, np.float32)
    if len(P):
        bi = ((P[:, 1] - y0) / step).astype(int); ok = (bi >= 0) & (bi < nb)
        np.maximum.at(f, bi[ok], P[ok, 0])
    return f

def split2(P):
    """two boxes for a curved trail (2-means along its long axis)."""
    c = P.mean(0); u, s, vt = np.linalg.svd(P - c, full_matrices=False)
    proj = (P - c) @ vt[0]
    lab = proj > np.median(proj)
    for _ in range(10):
        m0, m1 = P[~lab].mean(0), P[lab].mean(0)
        nl = ((P - m1) ** 2).sum(1) < ((P - m0) ** 2).sum(1)
        if (nl == lab).all() or nl.all() or (~nl).all(): break
        lab = nl
    if lab.sum() < 30 or (~lab).sum() < 30: return None
    return [pct_box(P[~lab], 1, 99), pct_box(P[lab], 1, 99)]

def pad(b, p): return [b[0] - p, b[1] - p, b[2] + p, b[3] + p]
def sized(x1, y0, y1, old_px, cx, H, lo):
    """attack box ending at x1 over rows y0..y1, at least as big as the old box (the move's design)"""
    x0 = x1 - 0.22 * H
    if old_px:
        ow = max(b[2] - b[0] for b in old_px); oh = max(b[3] - b[1] for b in old_px)
        x0 = min(x0, x1 - ow)
        if y1 - y0 < oh:
            c = (y0 + y1) / 2; y0, y1 = c - oh / 2, c + oh / 2
    if y1 - y0 < 0.12 * H:
        c = (y0 + y1) / 2; y0, y1 = c - 0.06 * H, c + 0.06 * H
    if y0 < lo - 0.01 * H: y1 += (lo - 0.01 * H) - y0; y0 = lo - 0.01 * H
    return [max(x0, cx - 0.02 * H), y0, x1, y1]

def raster_clusters(P, cell=4.0):
    """label points by 8-connected cells of a coarse grid"""
    if not len(P): return np.zeros(0, int)
    q = np.floor(P / cell).astype(int); q -= q.min(0)
    g = np.zeros(q.max(0)[::-1] + 1, np.uint8); g[q[:, 1], q[:, 0]] = 1
    g = cv2.dilate(g, np.ones((3, 3), np.uint8))
    n, lab = cv2.connectedComponents(g, connectivity=8)
    return lab[q[:, 1], q[:, 0]]

def fit_weapon(SOL, CORE, boxes, info, old_px):
    """the weapon held out in front (hilt jabs, pokes): thin parts beyond the body boxes"""
    H, cx = info['H'], info['cx']
    T = sticking_out(SOL, boxes, H)
    if len(T): T = T[T[:, 1] > float(SOL[:, 1].min()) + 0.2 * H]   # not the feet
    if len(T) < 15: return None
    lab = raster_clusters(T)
    best = max(set(lab.tolist()), key=lambda l: T[lab == l, 0].max())
    C = T[lab == best]
    tip = float(np.percentile(C[:, 0], 99.5))
    front = C[C[:, 0] >= tip - 0.08 * H]
    yc = float(np.median(front[:, 1]))
    return sized(tip + 0.03 * H, yc - 0.06 * H, yc + 0.06 * H, old_px, cx, H, float(SOL[:, 1].min()))

def fit_edge(SOL, info, old_px):
    """the leading edge of the body (kicks, slides, body checks)"""
    H, cx = info['H'], info['cx']
    lo, hi = float(SOL[:, 1].min()), float(SOL[:, 1].max())
    fa = fronts(SOL, lo, hi, 4.0)
    sel = fa >= fa.max() - 0.05 * H
    ys = lo + np.where(sel)[0] * 4.0
    return sized(float(fa.max()) + 0.03 * H, float(ys.min()) - 0.02 * H, float(ys.max()) + 4 + 0.02 * H, old_px, cx, H, lo)

def fit_attack(FX, SOL, boxes, info, old_px, START=np.zeros((0, 2), np.float32), part='auto', CORE=np.zeros((0, 2), np.float32)):
    H, cx = info['H'], info['cx']; n_old = len(old_px)
    if part == 'weapon':
        b = fit_weapon(SOL, CORE, boxes, info, old_px)
        return ([b], 'weapon') if b else (None, 'no weapon found')
    if part == 'edge':
        return [fit_edge(SOL, info, old_px)], 'leading edge'
    if part == 'top':      # upward strikes (fist pumps, uppercuts): the top of the pose
        hi = float(SOL[:, 1].max()); T = SOL[(SOL[:, 1] >= hi - 0.28 * H) & (SOL[:, 0] >= cx - 0.04 * H)]
        if len(T) < 15: return None, 'no top'
        b = pct_box(T, 1, 99)
        if b[2] - b[0] < 0.16 * H: c = (b[0] + b[2]) / 2; b[0], b[2] = c - 0.08 * H, c + 0.08 * H
        return [pad(b, 0.02 * H)], 'top'
    if len(FX) and part in ('auto', 'trail', 'trail_all'):
        # an all-effect body hits with all of it; 'trail_all' = effects on both sides (shots fired backwards too)
        F = FX if (info.get('fx_body') or part == 'trail_all') else FX[FX[:, 0] > cx - 0.05 * H]
        if len(F) >= (40 if part in ('trail', 'trail_all') else 120):   # asked for a trail: thin lasers count too
            b = pct_box(F, 1, 99)
            out = [b]; how = 'trail'
            sp = split2(F)
            if sp and (n_old >= 2 or sum(area(x) for x in sp) < 0.6 * area(b)):
                out = sp; how = 'trail x2'
            return [pad(q, 0.01 * H) for q in out], how
    if not len(SOL): return None, 'no pose'
    # the part that reached forward the most from the move's first pose (fist, hilt, foot)
    lo, hi = float(min(SOL[:, 1].min(), START[:, 1].min() if len(START) else 1e9)), float(max(SOL[:, 1].max(), START[:, 1].max() if len(START) else -1e9))
    step = 4.0
    fa = fronts(SOL, lo, hi, step); fs = fronts(START, lo, hi, step)
    fs = np.where(fs < -1e8, cx, fs)
    d = np.where(fa > -1e8, fa - fs, -1e9)
    dmax = float(d.max())
    if dmax < 0.04 * H:   # nothing moved forward: use the leading edge
        sel = fa >= fa.max() - 0.04 * H; how = 'leading edge'
    else:
        sel = (d >= 0.6 * dmax) & (fa >= fa.max() - 0.25 * H); how = 'limb'
    if not sel.any():
        sel = fa >= fa.max() - 0.04 * H; how = 'leading edge'
    if not sel.any(): return None, 'no pose'
    ys = lo + np.where(sel)[0] * step
    y0, y1 = float(ys.min()) - 0.03 * H, float(ys.max()) + step + 0.03 * H
    tip = float(fa[sel].max())
    base = float(np.median(front_at(boxes, ys.astype(np.float32)))) if boxes else cx
    if base < -1e8: base = cx
    return [sized(tip + 0.03 * H, max(y0, lo), min(y1, hi + 0.01 * H), old_px, cx, H, lo)], how

def as_written(b, upx):
    """a world-px box the way write_hitbox stores it (centre and size rounded to 100 units), back in px"""
    def r100(v): return int(round(v / 100.0)) * 100
    x0, y0, x1, y1 = [v * upx for v in b]
    cx, cy, w, h = r100((x0 + x1) / 2), r100((y0 + y1) / 2), max(100, r100(x1 - x0)), max(100, r100(y1 - y0))
    return [(cx - w / 2) / upx, (cy - h / 2) / upx, (cx + w / 2) / upx, (cy + h / 2) / upx]

def edges_moved(old_u, cx, old_ref_u, new_ref_px, upx):
    """move/stretch an old box (units) by how much the attack box edges moved (old->new)."""
    o = [v / upx for v in old_u]; ra = [v / upx for v in old_ref_u]; rn = new_ref_px
    d = [rn[i] - ra[i] for i in range(4)]
    b = [o[0] + d[0], o[1] + d[1], o[2] + d[2], o[3] + d[3]]
    b = [min(b[0], rn[0]), min(b[1], rn[1]), max(b[2], rn[2]), max(b[3], rn[3])]
    b[0] = max(b[0], min(rn[0], cx))          # never reaches behind her
    b[1] = max(b[1], min(rn[1], o[1], 0.0))   # never below the floor (unless the attack is)
    if o[1] <= 1: b[1] = min(o[1], rn[1])     # a proximity box that started on the floor stays on it
    return b

# ------------------------------------------------------------------ main
class Fitter:
    def __init__(self, char):
        self.char = char
        self.m = json.load(open(os.path.join(HERE, 'manifests', char + '.json'), encoding='utf-8'))
        g = self.m['game']; self.upx = g['pixel_size'] * 10000.0
        self.fxkind = self.m.get('fx', 'none')
        self.open_px = max(3, int(round(0.026 * g['height_px'])) | 1)
        self.cfg = self.m.get('hitfit', {})
        # smallest effect (px) that counts as a trail; manifest "min_fx" lowers it for thin lasers
        self.min_fx = int(self.cfg.get('min_fx', 1500 * (g['height_px'] / 500.0) ** 2))
        HAIR.clear(); HAIR.update(self.cfg.get('hair', {})); _masks.clear()
        self.state_path = os.path.join(HERE, 'analysis', char + '_hitfit.json')
        self.state = json.load(open(self.state_path)) if os.path.exists(self.state_path) else {}
        self.anims = {}; self.scale = 0.45
    def anim(self, name):
        if name not in self.anims: self.anims[name] = Anim(self.char, name)
        return self.anims[name]
    def pose(self, mods, use_contact):
        P = {'solid': [], 'core': [], 'fx': []}
        for md in mods:
            if md['contact'] and not use_contact: continue
            mk = masks(md, self.fxkind, self.open_px, min_area=self.min_fx)
            for k in P:
                if (md['contact'] or md.get('layer', 0) > 0) and k != 'fx':   # effect layers: all of it is trail
                    P['fx'].append(mk[k]); continue
                P[k].append(mk[k])
        return {k: (np.concatenate(v) if v else np.zeros((0, 2), np.float32)) for k, v in P.items()}
    def fit_file(self, res, anim, i, at=None):
        name = os.path.basename(res).replace('.tres', '')
        t, els, pb = read_hitbox(res)
        a, b = anim.span(i); stage = anim.states[i][1]
        k0 = anim.key_at(a if at is None else at)
        if not k0: return None
        P0 = self.pose(k0[1], False); fx_body = False
        if len(P0['core']) < 150 and len(P0['fx']) >= 150:   # she is all effect here (lightning form)
            P0 = dict(P0); P0['core'] = P0['fx']; P0['solid'] = P0['fx']; fx_body = True
        types = {}
        for e in els: types.setdefault(e['type'], []).append(e)
        new = {}; notes = []
        man = self.cfg.get('boxes', {}).get(name, {})
        is_attack_move = any(1 in hit_types(s[2]) for s in anim.states)
        # hurtboxes
        info = None; bands = None
        if 0 in types:
            n = len(types[0])
            hb, info = fit_hurt(P0['core'], min(n, 3))
            if hb:
                bands = list(hb)
                if (stage >= 1 and is_attack_move) or n >= 4:
                    hb = hb + fit_limb(P0['core'], hb, info['H'])
                new[0] = hb
            else: notes.append('hurt kept (pose has no body)')
            if 'hurt' in man: new[0] = man['hurt']; notes.append('hurt from manifest')
        if info is None:
            _, info = fit_hurt(P0['core'], 3)
        if info: info['fx_body'] = fx_body
        # attack boxes
        if 1 in types:
            FX = []; SOL = []
            for kat, ms in anim.keys_in(a, b):
                Pk = self.pose(ms, True); FX.append(Pk['fx']); SOL.append(Pk['solid'] if len(Pk['solid']) >= 150 else Pk['fx'])
            FX = np.concatenate(FX) if FX else np.zeros((0, 2)); SOL = np.concatenate(SOL) if SOL else np.zeros((0, 2))
            hb = bands or (fit_hurt(P0['core'], 3)[0] if info else None) or []
            ks = anim.key_at(0)
            START = self.pose(ks[1], False)['solid'] if ks else np.zeros((0, 2), np.float32)
            old_px = [[v / self.upx for v in e['box_u']] for e in types[1]]
            fresh = self.cfg.get('fresh_size', False)   # boxes copied from another fighter: don't keep their size
            if fresh is True or (isinstance(fresh, list) and (name in fresh or anim.name in fresh)): old_px = []
            parts = self.cfg.get('attack_part', {})
            part = parts.get(name, parts.get(anim.name, 'auto'))
            if part == 'keep': ab, how = None, 'kept (manifest)'
            else:
                CORE = []
                for kat, ms in anim.keys_in(a, b): CORE.append(self.pose(ms, True)['core'])
                CORE = np.concatenate(CORE) if CORE else np.zeros((0, 2), np.float32)
                ab, how = (fit_attack(FX, SOL, hb, info, old_px, START, part, CORE) if info else (None, 'no pose'))
            if 'attack' in man: ab, how = man['attack'], 'manifest'
            if ab: new[1] = ab
            notes.append('attack: ' + how)
        return {'name': name, 'res': res, 't': t, 'els': els, 'pb': pb, 'new': new, 'notes': notes, 'anim': anim.name, 'at': a, 'stage': stage, 'key': k0, 'info': info}
    def hb_res(self, name): return 'res://actors/%s/Hitboxes/%s.tres' % (self.char, name)
    def apply_splits(self, write):
        """'split': {"<shared file>": {"<new file>": [animations that should use the new file]}}
        gives those animations their own copy (new uid), so each pose gets its own fit."""
        done = []
        for orig, news in self.cfg.get('split', {}).items():
            ores = self.hb_res(orig)
            for newname, anims in news.items():
                nres = self.hb_res(newname); npath = res_file(nres)
                if not os.path.exists(npath):
                    ALIAS.setdefault(nres, ores)
                    if write:
                        txt = open(res_file(ores), encoding='utf-8').read().replace('\r\n', '\n')
                        uid = new_uid()
                        txt = re.sub(r'^(\[gd_resource[^\]]*?)uid="[^"]*"', lambda m: m.group(1) + 'uid="%s"' % uid, txt, count=1)
                        open(npath, 'w', encoding='utf-8', newline='\n').write(txt); ALIAS.pop(nres, None)
                        done.append('created %s (copy of %s)' % (newname, orig))
                uid = None
                if os.path.exists(npath):
                    m = re.search(r'uid="([^"]+)"', open(npath, encoding='utf-8').readline()); uid = m.group(1) if m else None
                for an_name in anims:
                    an = self.anim(an_name)
                    if not any(st[2] == ores for st in an.states): continue
                    an.states = [(a0, sg, nres if r0 == ores else r0) for a0, sg, r0 in an.states]
                    if write:
                        t = Tres(open(an.path, encoding='utf-8').read())
                        for e in t.ext:
                            if e.get('path') == ores:
                                e['path'] = nres
                                if uid: e['uid'] = uid
                                else: e.pop('uid', None)
                        bk = an.path + '.bak_hitfit'
                        if not os.path.exists(bk): open(bk, 'w', encoding='utf-8').write(open(an.path, encoding='utf-8').read())
                        open(an.path, 'w', encoding='utf-8', newline='\n').write(t.text())
                        done.append('%s now uses %s' % (an_name, newname))
        return done
    def run(self, names, write=False, force=False):
        skip = set(self.cfg.get('skip', []))
        fit_from = self.cfg.get('fit_from', {})
        names = names or list(self.m['animations'])
        split_report = self.apply_splits(write)
        fits = {}; order = []
        def add(anim, i):
            res = anim.states[i][2]; name = os.path.basename(res).replace('.tres', '')
            if name in skip or res in fits: return
            at = None
            if name in fit_from:
                fa = self.anim(fit_from[name][0]); fr = fit_from[name][1]
                qs = [q for q, s in enumerate(fa.states) if s[2] == res]
                if not qs: return
                before = [q for q in qs if fa.states[q][0] <= fr]
                anim, i, at = fa, (before[-1] if before else qs[0]), fr
            try:
                r = self.fit_file(res, anim, i, at)
            except Exception as e:   # one odd pose shouldn't stop the rest
                print('   hitfit: %s (%s @%d) not fitted: %s' % (name, anim.name, anim.states[i][0], e)); return
            if r: fits[res] = r; order.append(res)
        for n in names:
            an = self.anim(n)
            for i in range(len(an.states)): add(an, i)
        # proximity boxes follow the attack box of their move
        for n in names:
            an = self.anim(n); ref = None
            for i, s in enumerate(an.states):
                r = fits.get(s[2])
                if r and 1 in r['new']:
                    old_att = [e['box_u'] for e in r['els'] if e['type'] == 1]
                    ref = (union(old_att), union([as_written(b, self.upx) for b in r['new'][1]])); break
            for i, s in enumerate(an.states):
                r = fits.get(s[2])
                if not r or r['anim'] != an.name: continue
                prox = [e for e in r['els'] if e['type'] == 2]
                if not prox: continue
                own = [e['box_u'] for e in r['els'] if e['type'] == 1]
                # compared as written (rounded), so a refit of an unchanged pose doesn't creep the box each run
                rr = (union(own), union([as_written(b, self.upx) for b in r['new'][1]])) if (own and 1 in r['new']) else ref
                if not rr: r['notes'].append('prox kept'); continue
                cx = r['info']['cx'] if r.get('info') else 0.0
                r['new'][2] = [edges_moved(p['box_u'], cx, rr[0], rr[1], self.upx) for p in prox]
        # draw + write
        out_dir = os.path.join(HERE, 'checks', self.char); os.makedirs(out_dir, exist_ok=True)
        for n in names:
            an = self.anim(n)
            cells = [self.cell(an, i, fits.get(s[2]), self.scale) for i, s in enumerate(an.states)]
            if cells:
                W = sum(c.width for c in cells); img = Image.new('RGB', (W, cells[0].height)); x = 0
                for c in cells: img.paste(c, (x, 0)); x += c.width
                img.save(os.path.join(out_dir, 'fit_%s.png' % n))
        report = list(split_report)
        for res in order:
            r = fits[res]
            report.append('%-34s from %s @%d  %s' % (r['name'], r['anim'], r['at'], '; '.join(r['notes'])))
            if not write or not r['new']: continue
            path = res_file(res); cur = open(path, encoding='utf-8').read(); h = md5(cur.replace('\r\n', '\n'))
            # changed since the last fit, and not by the kit either (a moves_<fighter>.py run updates attack values)
            if r['name'] in self.state and self.state[r['name']] != h and _kit_record(res) != h and not force:
                report[-1] += '  [SKIPPED: edited by hand since the last fit; --force to refit]'; continue
            sub = 'Hitboxes' if self.char == 'cecilia' else os.path.join(self.char, 'Hitboxes')   # (cecilia's first backups predate the per-fighter folders)
            bk = os.path.join(PROJ, '_backup_stage_select', 'pre_sprite_port', sub, os.path.basename(path) + '.bak')
            if not os.path.exists(bk):
                os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(cur)
            txt = write_hitbox(res, r['t'], r['els'], r['new'], self.upx)
            n_boxes = txt.count('\nCenter = ')
            if n_boxes > BODY_BOX_LIMIT:   # the fighter's body only takes its first 16 boxes: the rest never hit
                report[-1] += '  [WARNING: %d boxes, the game uses only the first %d]' % (n_boxes, BODY_BOX_LIMIT)
            open(path, 'w', encoding='utf-8', newline='\n').write(txt)
            self.state[r['name']] = md5(txt)
        if write:
            json.dump(self.state, open(self.state_path, 'w'), indent=1)
        return report
    # -------------------------------------------------------------- check image
    def cell(self, an, i, r, scale=0.45):
        X0, X1, Y0, Y1 = -700, 900, -60, 800
        Wd, Ht = int((X1 - X0) * scale), int((Y1 - Y0) * scale)
        img = Image.new('RGBA', (Wd, Ht + 32), (70, 70, 78, 255)); d = ImageDraw.Draw(img, 'RGBA')
        for gx in range(-700, 901, 50):
            d.line([((gx - X0) * scale, 0), ((gx - X0) * scale, Ht)], fill=(255, 255, 255, 10 if gx % 100 else 20))
        for gy in range(-50, 801, 50):
            d.line([(0, (Y1 - gy) * scale), (Wd, (Y1 - gy) * scale)], fill=(255, 255, 255, 10 if gy % 100 else 20))
        a, b = an.span(i); k = an.key_at(a)
        if k:
            for md in k[1]:
                c = png(md['tex']); im = Image.fromarray(c, 'RGBA')
                if md['flipx']: im = im.transpose(Image.FLIP_LEFT_RIGHT)
                if md['contact']: im.putalpha(im.getchannel('A').point(lambda v: v // 2))
                R = 1800; big = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0))
                big.paste(im, (int(md['off'][0]) + R, R - (int(md['off'][1]) + c.shape[0])), im)
                if md['rot']: big = big.rotate(md['rot'], resample=Image.BICUBIC, center=(R, R))
                big = big.crop((R + X0, R - Y1, R + X1, R - Y0)).resize((Wd, Ht), Image.LANCZOS)
                img.alpha_composite(big)
        fy = int(Y1 * scale); d.line([(0, fy), (Wd, fy)], fill=(0, 210, 210, 255)); d.line([(int(-X0 * scale), fy - 10), (int(-X0 * scale), fy + 10)], fill=(255, 70, 70, 255))
        COL = {0: (0, 255, 0), 1: (255, 40, 40), 2: (80, 120, 255), 9: (255, 230, 0)}
        def rect(bx, col, fill=45, w=2):
            x0, y0, x1, y1 = bx
            lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            dl.rectangle([int((x0 - X0) * scale), int((Y1 - y1) * scale), int((x1 - X0) * scale), int((Y1 - y0) * scale)], outline=col + (230,), fill=col + (fill,) if fill else None, width=w)
            img.alpha_composite(lay)
        res = an.states[i][2]
        t, els, pb = read_hitbox(res) if not r else (r['t'], r['els'], r['pb'])
        if pb: rect([v / self.upx for v in pb], COL[9], 0, 1)
        newt = r['new'] if r else {}
        for e in els:
            if e['type'] in newt:   # old box: thin white outline
                rect([v / self.upx for v in e['box_u']], (235, 235, 235), 0, 1)
            else:
                rect([v / self.upx for v in e['box_u']], COL.get(e['type'], (255, 255, 255)))
        for ty in (0, 2, 1):
            for bx in newt.get(ty, []): rect(bx, COL.get(ty, (255, 255, 255)), 45 if ty != 2 else 25)
        name = os.path.basename(res).replace('.tres', '')
        d.text((3, Ht + 2), '@%d st%d %s' % (a, an.states[i][1], name), fill=(255, 255, 0, 255), font=FONT)
        d.text((3, Ht + 16), ('fitted' if r and r['new'] else 'unchanged') + ('' if not r or r['anim'] == an.name else ' (from %s)' % r['anim']), fill=(200, 200, 200, 255), font=FONT)
        return img

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; flags = [a for a in sys.argv[1:] if a.startswith('--')]
    f = Fitter(args[0])
    for fl in flags:
        if fl.startswith('--scale='): f.scale = float(fl.split('=')[1])
    for line in f.run(args[1:], write='--write' in flags, force='--force' in flags): print(line)
