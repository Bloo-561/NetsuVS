"""ASSIST REEL: GIF previews of the assists' moves, played the way the game runs them: the caller
(grey Leticia) stands at x 0 facing right, the opponent (grey Cecilia) at --opp px; the assist
appears where its move says, runs its states (movement, jumps, turning, Mary's note), its attack
boxes are drawn red while active (counter box: blue), and a hit launches the stand-in opponent
with the hit's knockback and gravity.  Physics like the engine: position += speed / 60 a frame.

    python assistreel.py eren 5S [--opp=700] [--walk=-150] [--attack=20] [--out=file.gif]
    (assists.py --preview writes every move of an assist to checks/assists/)
--attack=N: the stand-in opponent swings at frame N (to see Adin's counter work).
--walk=V: the stand-in opponent walks V px a second until it is hit (negative = toward the caller: Harie's trap).
"""
import sys, os, re, json, math
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hitfit
from tres import Tres
PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
except Exception:
    FONT = ImageFont.load_default()
UPX = 27.5
OPP_BOX = (-115, 0, 115, 500)      # the stand-in opponent's body (px around its feet)

def kind(o): return os.path.basename(o.script).replace('.cs', '') if hasattr(o, 'script') else ''

class Actor:
    def __init__(self, k, a, states, x, y, side, start):
        self.k, self.a, self.states = k, a, states
        self.x, self.y, self.vx, self.vy, self.g = float(x), float(y), 0.0, 0.0, 260000.0
        self.side = side; self.active = True; self.state = None; self.frame = -1; self.hits = set(); self.contact = False
        self.hitstop = 0; self.spawned = []; self.pending = None
        self.play(start)
    def play(self, idx):
        self.state = idx; self.frame = 0; self.hits = set(); self.contact = False
        for act in self.states[idx]['enter']: self.do(act)
    def do(self, act):
        k, f = kind(act), act.fields
        if k == 'MoveXAction': self.vx = float(f.get('Velocity') or 0) * self.side
        elif k == 'MoveYAction': self.vy = float(f.get('Velocity') or 0)
        elif k == 'AddGravityAction':
            if f.get('SetValue'): self.g = 260000.0 if f.get('UseDefault') else float(f.get('Force') or 0)
            self.vy -= self.g / 60.0
        elif k == 'PlayStateAction': self.pending = int(f.get('StateIndex') or 0)
        elif k == 'SetActiveAction': self.active = bool(f.get('Active'))
        elif k == 'ChangeSideAction':
            if f.get('Forced'): self.side = -self.side
        elif k == 'NetsuPlaceAction':
            tx = self.target_x(f.get('Target', 2)); off = f.get('Offset')
            self.x = tx + (off.x / UPX if off else 0) * self.side
            if f.get('FaceBack'): self.side = -self.side
        elif k == 'NetsuAimAction':
            tx = self.target_x(f.get('Target', 2)) + (f.get('OffsetX') or 0) / UPX * self.side
            fr = f.get('Frames') or 30; fwd = (tx - self.x) * self.side * UPX
            sp = fwd * 60 / fr; sp = max(f.get('MinSpeed') or 0, min(f.get('MaxSpeed') or 400000, sp))
            self.vx = sp * self.side
        elif k == 'SpawnActorAction':
            t = f.get('TargetPosition'); self.spawned.append((self.x + t.x / UPX * self.side, self.y + t.y / UPX, self.side, f.get('InitialState') or 0))
        elif k == 'NetsuAssistBuffAction': self.buffed = True
        elif k == 'ResetHitAction': self.hits = set()
    def target_x(self, t):
        return {2: SCENE['opp_x'], 3: 0.0, 1: self.x}.get(t, 0.0)
    def check(self, c):
        k, f = kind(c), c.fields
        if k == 'AtFrameCondition':
            r = self.frame == (f.get('Frame') or 0)
        elif k == 'AtFrameRangeCondition': r = (f.get('MinFrame') or 0) <= self.frame <= (f.get('MaxFrame') or 0)
        elif k == 'StateEndedCondition': r = self.frame >= self.states[self.state]['duration']
        elif k == 'OnGroundCondition': r = self.y <= 0
        elif k == 'NetsuRelativeXCondition':
            d = (self.x - self.target_x(f.get('Target', 2))) * self.side * UPX
            r = (f.get('MinDistance') if f.get('MinDistance') is not None else -1e9) <= d <= (f.get('MaxDistance') if f.get('MaxDistance') is not None else 1e9)
        else: r = True
        return (not r) if f.get('Not') else r
    def events(self, evs):
        for e in evs:
            conds = e.fields.get('Conditions') or []
            if all(self.check(c) for c in conds):
                for act in e.fields.get('Actions') or []: self.do(act)
    def step(self):
        """one game frame: PreTick (frame++, transitions), Tick (tick events), physics"""
        if not self.active: return
        if self.hitstop > 0:
            self.hitstop -= 1; return
        self.frame += 1; self.pending = None
        self.events(self.states[self.state]['trans'])
        if self.pending is not None: self.play(self.pending); self.pending = None
        if not self.active: return
        self.events(self.states[self.state]['tick'])
        if self.pending is not None: self.play(self.pending); self.pending = None
        self.x += self.vx / 60.0 / UPX; self.y = max(0.0, self.y + self.vy / 60.0 / UPX)

def load_states(k, a, owner):
    import assists
    from fdk import ev, at, at_range
    out = {}
    sl = assists.state_list(k, a)
    for idx, tag, s, o in sl:
        if o != owner: continue
        st = assists.state_obj(k, a, idx, tag, s, o)
        f = st.fields
        anim = assists.anim_name(idx, tag, s)
        def lst(key):
            v = f.get(key); return v if isinstance(v, list) else []
        out[idx] = {'enter': lst('OnEnterEvents'), 'trans': lst('TransitionEvents'), 'tick': lst('OnTickEvents'),
                    'confirm': lst('OnHitConfirmEvents'), 'duration': s['duration'], 'anim': anim, 'name': s['name']}
    return out

SCENE = {}
_anims = {}
def anim_of(char, anim):
    if (char, anim) not in _anims: _anims[(char, anim)] = hitfit.Anim(char, anim)
    return _anims[(char, anim)]
_boxes = {}
def boxes_now(char, anim, frame):
    an = anim_of(char, anim)
    cur = None
    for i, (a0, stage, res) in enumerate(an.states):
        if a0 <= max(frame, 0): cur = res
    if not cur: return []
    if cur not in _boxes:
        t, els, pb = hitfit.read_hitbox(cur)
        _boxes[cur] = [(e['type'], [v / UPX for v in e['box_u']], e['body']) for e in els]
    return _boxes[cur]

def prop(body, key, default=0):
    for l in body:
        if l.startswith(key + ' = '):
            v = l.split(' = ', 1)[1]
            m = re.match(r'Vector2i\((-?\d+), (-?\d+)\)', v)
            if m: return (int(m.group(1)), int(m.group(2)))
            try: return int(v)
            except ValueError: return v
    return default

def reel(k, move_name, opp_px=700, attack_at=None, out=None, X0=-700, X1=1700, Y0=-40, Y1=900, scale=0.38, opp_walk=0):
    import assists
    a = assists.ASSISTS[k]; char = assists.char_of(k)
    mv = next(m for m in a['moves'] if m['name'] == move_name)
    states = load_states(k, a, 'main')
    sl = {s['key']: i for i, t, s, o in assists.state_list(k, a) if o == 'main'}
    spw = {sk: load_states(k, a, sk) for sk in a.get('spawnables', {})}
    SCENE['opp_x'] = float(opp_px)
    actor = Actor(k, a, states, mv['spawn'][0], 0, 1, sl[mv['state']]); actor.frame = -1
    actors = [actor]
    opp = {'x': float(opp_px), 'y': 0.0, 'vx': 0.0, 'vy': 0.0, 'g': 0.0, 'stun': 0, 'flash': 0}
    W, H = int((X1 - X0) * scale), int((Y1 - Y0) * scale)
    def grey(p, flip):
        im = Image.open(os.path.join(PROJ, 'actors', p, 'Sprites', 'v2', 'idle_O0.png')).convert('RGBA')
        if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        im.putalpha(im.split()[3].point(lambda v: int(v * 0.5))); return im
    caller_img = grey('leticia', False); opp_img = grey('cecilia', True)
    aura = []
    art = os.path.join(PROJ, 'actors', 'assists', k, 'Artwork')
    for n in ['BuffAura_1.png', 'BuffAura_2.png', 'BuffAura_3.png', 'BuffPulse.png']:
        if os.path.exists(os.path.join(art, n)):
            im = Image.open(os.path.join(art, n)).convert('RGBA'); im.putalpha(im.split()[3].point(lambda v: int(v * 0.8))); aura.append(im)
    buff_t = None
    frames = []; last = None; hits = 0
    for t in range(240):
        for ac in list(actors):
            ac.step()
            for sx, sy, side, st in ac.spawned:
                sk = list(spw)[0]
                n = Actor(k, a, spw[sk], sx, sy, side, st); n.frame = -1; n.note = True; actors.append(n)
            ac.spawned = []
        # the stand-in opponent: walks (opp_walk px a second, until hit), launched by hits, falls with the hit's gravity
        if opp_walk and not hits and opp['y'] <= 0: opp['x'] += opp_walk / 60.0
        if opp['stun'] > 0: opp['stun'] -= 1
        opp['x'] += opp['vx'] / 60.0 / UPX; opp['y'] += opp['vy'] / 60.0 / UPX; opp['vy'] -= opp['g'] / 60.0
        if opp['y'] <= 0: opp['y'] = 0.0; opp['vy'] = 0.0; opp['vx'] *= 0.7
        SCENE['opp_x'] = opp['x']
        if opp['flash'] > 0: opp['flash'] -= 1
        # hits: an attack box over the opponent's body
        for ac in actors:
            if not ac.active: continue
            st = ac.states[ac.state]
            for ty, b, body in boxes_now(char, st['anim'], ac.frame):
                x0, x1 = sorted([ac.x + b[0] * ac.side, ac.x + b[2] * ac.side]); y0, y1 = ac.y + b[1], ac.y + b[3]
                ox0, ox1 = opp['x'] + OPP_BOX[0], opp['x'] + OPP_BOX[2]; oy0, oy1 = opp['y'] + OPP_BOX[1], opp['y'] + OPP_BOX[3]
                over = x0 <= ox1 and x1 >= ox0 and y0 <= oy1 and y1 >= oy0
                if ty in (1, 3) and over and 'opp' not in ac.hits:
                    ac.hits.add('opp'); ac.contact = True; hits += 1
                    kb = prop(body, 'AirHitKnockback' if opp['y'] > 0 else 'GroundHitKnockback', (0, 0))
                    grav = prop(body, 'AirHitKnockbackGravity' if opp['y'] > 0 else 'GroundHitKnockbackGravity', 0) or 200000
                    opp['vx'] = -kb[0] * ac.side; opp['vy'] = kb[1]; opp['g'] = grav; opp['flash'] = 6
                    ac.hitstop = prop(body, 'SelfHitStopDuration', 0)
                    ac.pending = None; ac.events(st['confirm'])
                    if ac.pending is not None: ac.play(ac.pending); ac.pending = None
                    ac.hits.add('opp')      # like the engine: the target is marked as hit after the hit-confirm events
        # the opponent swings (to trigger a counter)
        swing = attack_at is not None and attack_at <= t < attack_at + 6
        if swing:
            sx0, sx1 = opp['x'] - 330, opp['x'] - 60
            for ac in actors:
                if not ac.active: continue
                st = ac.states[ac.state]
                for ty, b, body in boxes_now(char, st['anim'], ac.frame):
                    if ty != 5: continue
                    x0, x1 = sorted([ac.x + b[0] * ac.side, ac.x + b[2] * ac.side])
                    if x0 <= sx1 and x1 >= sx0 and 'counter' not in ac.hits:
                        ac.hits.add('counter'); ac.hitstop = prop(body, 'SelfHitStopDuration', 0)
                        ac.pending = None; ac.events(st['confirm'])
                        if ac.pending is not None: ac.play(ac.pending); ac.pending = None
        if not any(ac.active for ac in actors) and opp['y'] <= 0 and t > 20: break
        if t % 2: continue          # 30 pictures a second (GIFs can't show 60)
        # draw
        img = Image.new('RGBA', (W, H), (54, 54, 64, 255)); d = ImageDraw.Draw(img)
        fy = int(Y1 * scale); d.rectangle([0, fy, W, H], fill=(40, 40, 48, 255)); d.line([(0, fy), (W, fy)], fill=(90, 160, 170, 255), width=2)
        VW, VH = X1 - X0, Y1 - Y0
        def layer(im, ox, oy, flipx=False):
            if flipx: im = im.transpose(Image.FLIP_LEFT_RIGHT)
            big = Image.new('RGBA', (VW, VH), (0, 0, 0, 0)); big.paste(im, (int(ox) - X0, Y1 - (int(oy) + im.height)), im)
            img.alpha_composite(big.resize((W, H), Image.LANCZOS))
        layer(caller_img, -caller_img.width // 2, 0)
        if buff_t is None and any(getattr(ac, 'buffed', False) for ac in actors): buff_t = t
        if buff_t is not None and len(aura) == 4:      # Mary's buff on the caller (drawn by the engine's NetsuAssist)
            dt = t - buff_t; im = aura[3] if dt < 12 else aura[(dt // 5) % 3]
            al = im.split()[3]; ys = [y for y in range(im.height) if al.crop((0, y, im.width, y + 1)).getbbox()]
            bottom = im.height - 1 - (ys[-1] if ys else im.height - 1)
            layer(im, -im.width // 2, -bottom - 8)
        oi = opp_img
        if opp['flash']:
            oi = oi.copy(); r, g, b, al = oi.split(); oi = Image.merge('RGBA', (r.point(lambda v: min(255, v + 90)), g, b, al))
        layer(oi, opp['x'] - oi.width // 2, opp['y'])
        for ac in actors:
            if not ac.active: continue
            st = ac.states[ac.state]; an = anim_of(char, st['anim']); key = an.key_at(max(ac.frame, 0))
            for md in (key[1] if key else []):
                if md['contact'] and not ac.contact: continue
                im = Image.fromarray(hitfit.png(md['tex']), 'RGBA')
                if md['flipx']: im = im.transpose(Image.FLIP_LEFT_RIGHT)
                if ac.side > 0: layer(im, ac.x + md['off'][0], ac.y + md['off'][1])
                else: layer(im, ac.x - md['off'][0] - im.width, ac.y + md['off'][1], flipx=True)
            for ty, b, body in boxes_now(char, st['anim'], ac.frame):
                x0, x1 = sorted([ac.x + b[0] * ac.side, ac.x + b[2] * ac.side]); y0, y1 = ac.y + b[1], ac.y + b[3]
                col = {1: (255, 60, 60, 255), 3: (255, 120, 40, 255), 5: (80, 160, 255, 255)}.get(ty)
                if col: d.rectangle([(x0 - X0) * scale, (Y1 - y1) * scale, (x1 - X0) * scale, (Y1 - y0) * scale], outline=col, width=2)
        if swing:
            d.rectangle([(opp['x'] - 330 - X0) * scale, (Y1 - 380) * scale, (opp['x'] - 60 - X0) * scale, (Y1 - 200) * scale], outline=(255, 255, 0, 255), width=2)
        d.text((12, 10), '%s %s  %s' % (a['name'], mv['name'], mv['display']), fill=(255, 230, 120, 255), font=FONT)
        d.text((12, 34), 'frame %d' % t, fill=(210, 210, 220, 255), font=FONT)
        frames.append(img)
    out = out or os.path.join(HERE, 'checks', 'assists', '%s_%s.gif' % (k, move_name))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pal = [f.convert('RGB').quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=[33] * (len(pal) - 1) + [700], loop=0, disposal=1)
    print(out, len(frames), 'frames', 'hits', hits)
    return out

def reel_all(k):
    import assists
    a = assists.ASSISTS[k]
    for m in a['moves']:
        r = m.get('reel', {})       # per move: opp = where the stand-in opponent starts, walk = px a second
        reel(k, m['name'], attack_at=22 if (k == 'adin' and m['name'] == '5S') else None, opp_px=r.get('opp', 700),
             opp_walk=r.get('walk', 0))

if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    opt = dict(x[2:].split('=') for x in sys.argv[1:] if x.startswith('--') and '=' in x)
    if len(args) == 1: reel_all(args[0])
    else: reel(args[0], args[1], opp_px=int(opt.get('opp', 700)), attack_at=int(opt['attack']) if 'attack' in opt else None, out=opt.get('out'),
               opp_walk=float(opt.get('walk', 0)))
