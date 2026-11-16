"""Cecilia move sheet: reads her live game data (stance moves -> states -> animation data -> hitboxes),
prints a JSON of every move with frame data, and renders a GIF per move from her real sprites.
Run from tools/sprite_port:  python3 cec_sheet.py OUTDIR
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(HERE, '..', 'tools', 'sprite_port') if not os.path.exists(os.path.join(HERE, 'hitfit.py')) else HERE
sys.path.insert(0, SP)
from tres import Tres
import hitfit
from PIL import Image, ImageDraw
from build import rotated_layer

PROJ = os.path.abspath(os.path.join(SP, '..', '..'))
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
UPX = 27.5

def rf(res): return os.path.join(PROJ, res.replace('res://', ''))
def load(res): return Tres(open(rf(res), encoding='utf-8').read())
def rget(t, key):
    for l in t.res:
        if l.startswith(key + ' = '): return l.split(' = ', 1)[1]
def subs(t): return {s[0]: s for s in t.sub}
def sget(lines, key):
    for l in lines:
        if l.startswith(key + ' = '): return l.split(' = ', 1)[1]
def ext_path(t, ref):
    m = re.search(r'ExtResource\("([^"]+)"\)', ref or '')
    return t.ext_by_id(m.group(1))['path'] if m else None
def ids(v): return re.findall(r'(?:Sub|Ext)Resource\("([^"]+)"\)', v or '')

data = load('res://actors/cecilia/0_CEC_Data.tres')
STATES = [data.ext_by_id(i)['path'] for i in re.findall(r'ExtResource\("([^"]+)"\)', rget(data, 'States'))]
stance = load('res://actors/cecilia/Stances/CEC_Stance_Main.tres')
MOVES = [stance.ext_by_id(i)['path'] for i in re.findall(r'ExtResource\("([^"]+)"\)', rget(stance, 'Moves'))]
HITTYPE = {0: 'High', 1: 'Mid', 2: 'Low', 3: 'Unblockable'}

def script_of(t, lines):
    s = sget(lines, 'script'); p = ext_path(t, s) or ''
    return os.path.basename(p).replace('.cs', '')

def state_info(idx):
    p = STATES[idx]; t = load(p); S = subs(t)
    anim = ext_path(t, rget(t, 'AnimationData'))
    def events(key):
        out = []
        for eid in ids(rget(t, key)):
            body = S[eid][2]
            conds = [(script_of(t, S[c][2]), S[c][2]) for c in ids(sget(body, 'Conditions'))]
            acts = [(script_of(t, S[a][2]), S[a][2]) for a in ids(sget(body, 'Actions'))]
            out.append((conds, acts))
        return out
    return dict(path=p, name=(rget(t, 'StateName') or '').strip('"'), anim=anim,
                enter=events('OnEnterEvents'), tick=events('OnTickEvents'), trans=events('TransitionEvents'))

def anim_info(res):
    if not res: return None
    name = os.path.basename(res).replace('_AnimData.tres', '')
    t = load(res); S = subs(t)
    dur = int(rget(t, 'Duration') or 0)
    profs = []
    for pid in ids(rget(t, 'AttackProfiles')):
        b = S[pid][2]; profs.append(int(sget(b, 'BaseDamage') or 0))
    hs = []
    for hid in ids(rget(t, 'Hitboxes')):
        b = S[hid][2]; hd = ext_path(t, sget(b, 'HitboxData'))
        at = int(sget(b, 'AtFrame') or 0)
        atk = None
        if hd and os.path.exists(rf(hd)):
            ht = load(hd)
            for s in ht.sub:
                if sget(s[2], 'HitboxType') == '1':
                    pr = int(sget(s[2], 'Profile') or 0); hty = int(sget(s[2], 'HitType') or 0)
                    atk = dict(dmg=profs[pr] if pr < len(profs) else None, guard=HITTYPE.get(hty, '?'))
                    break
        hs.append((at, atk))
    hs.sort(key=lambda h: h[0])
    first = last_end = None; hits = 0; dmg = guard = None; prev = False
    for i, (at, atk) in enumerate(hs):
        end = hs[i + 1][0] if i + 1 < len(hs) else dur
        if atk:
            if first is None: first = at; dmg = atk['dmg']; guard = atk['guard']
            last_end = end
            if not prev: hits += 1
        prev = bool(atk)
    fd = dict(anim=name, total=dur)
    if first is not None:
        fd.update(startup=first + 1, active=last_end - first, recovery=max(0, dur - last_end), damage=dmg, guard=guard, hits=hits)
    return fd

def frame_of(conds):
    """None = every frame; (a, b) frame range; 'never' for conditions we don't simulate"""
    rng = None
    for k, b in conds:
        if k == 'AtFrameCondition': f = int(sget(b, 'Frame') or 0); rng = (f, f)
        elif k == 'AtFrameRangeCondition': rng = (int(sget(b, 'MinFrame') or 0), int(sget(b, 'MaxFrame') or 999))
        else: return 'never'
    return rng

def simulate(st, start, maxdur):
    x, y = start; vx = vy = 0.0; out = []; was_up = y > 0
    def apply(k, b):
        nonlocal vx, vy, x, y
        if k == 'MoveXAction': vx = float(sget(b, 'Velocity') or 0)
        elif k == 'MoveYAction': vy = float(sget(b, 'Velocity') or 0)
    for conds, acts in st['enter']:
        if frame_of(conds) != 'never':
            for k, b in acts: apply(k, b)
    for f in range(maxdur):
        for conds, acts in st['tick']:
            r = frame_of(conds)
            if r == 'never': continue
            if r is None or r[0] <= f <= r[1]:
                for k, b in acts:
                    if k == 'AddGravityAction': vy -= float(sget(b, 'Force') or 260000) / 60.0
                    elif r is None or r[0] == r[1]: apply(k, b)
                    elif f == r[0]: apply(k, b)
        x += vx / 60.0 / UPX; y += vy / 60.0 / UPX
        if y > 1: was_up = True
        if y < 0: y = 0.0; vy = 0.0
        out.append((x, y))
        if f > 3 and was_up and y <= 0: break
    return out

OPP = None
o = os.path.join(PROJ, 'actors', 'noah', 'Sprites', 'v2', 'idle_0_1.png')
if os.path.exists(o):
    OPP = Image.open(o).convert('RGBA').transpose(Image.FLIP_LEFT_RIGHT)
    OPP.putalpha(OPP.split()[3].point(lambda v: int(v * 0.7)))

X0, X1, Y0, Y1, SCALE, OPPX = -450, 1350, -40, 1250, 0.32, 560
def render(chain_idx, out, air=False):
    frames = []; start = (0.0, 330.0 if air else 0.0); W, H = int((X1 - X0) * SCALE), int((Y1 - Y0) * SCALE)
    VW, VH = X1 - X0, Y1 - Y0
    for si in chain_idx:
        st = state_info(si)
        if not st['anim']: continue
        an = hitfit.Anim('cecilia', os.path.basename(st['anim']).replace('_AnimData.tres', ''))
        dur = an.dur or 30
        path = simulate(st, start, dur)
        last = None
        for f, pos in enumerate(path):
            k = an.key_at(f); key = (id(k), round(pos[0]), round(pos[1]))
            if key == last: frames[-1][1] += 1; continue
            img = Image.new('RGBA', (W, H), (26, 24, 34, 255)); d = ImageDraw.Draw(img)
            fy = int(Y1 * SCALE); d.rectangle([0, fy, W, H], fill=(18, 17, 24, 255)); d.line([(0, fy), (W, fy)], fill=(232, 196, 92, 255), width=2)
            big = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
            if OPP is not None:
                big.paste(OPP, (OPPX - OPP.width // 2 - X0, Y1 - OPP.height), OPP)
            for md in (k[1] if k else []):
                if md['contact']: continue
                im = Image.fromarray(hitfit.png(md['tex']), 'RGBA')
                if md['flipx']: im = im.transpose(Image.FLIP_LEFT_RIGHT)
                ox, oy = md['off'][0] + pos[0], md['off'][1] + pos[1]
                if md['rot']:
                    r, left, top = rotated_layer(im, ox, oy, md['rot'], pos[0], pos[1])
                    big.paste(r, (int(round(left)) - X0, Y1 - int(round(top))), r)
                else:
                    big.paste(im, (int(ox) - X0, Y1 - (int(oy) + im.height)), im)
            img.alpha_composite(big.resize((W, H), Image.LANCZOS))
            frames.append([img, 1]); last = key
        start = path[-1] if path else start
        if start[1] <= 0: start = (start[0], 0.0)
    if not frames: return False
    frames[-1][1] += 30
    pal = [f[0].convert('RGB').quantize(colors=200, method=Image.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    durs = [max(20, int(round(f[1] * 1000 / 60 / 10)) * 10) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, disposal=1, optimize=True)
    still = frames[min(len(frames) - 1, max(0, len(frames) // 2))][0].convert('RGB')
    return True

cmd = json.load(open(os.path.join(PROJ, 'actors', 'cecilia', 'command_list.json'), encoding='utf-8'))
rows = []
for mp in MOVES:
    t = load(mp)
    name = (rget(t, 'MoveName') or '').strip('"')
    si = int(rget(t, 'MoveState') or -1)
    pri = int(rget(t, 'Priority') or 0)
    cost = int(rget(t, 'SuperGaugeRequired') or 0)
    inp = os.path.basename(ext_path(t, rget(t, 'Inputs')) or '').replace('.tres', '')
    seq = rget(t, 'IsSequenceFromStates') == 'true'
    air = rget(t, 'UseOnAir') == 'true' and rget(t, 'UseOnGround') != 'true'
    air = air or int(rget(t, 'MoveState') or -1) in (69, 70, 71, 108, 109, 110, 94, 116, 132)
    rows.append(dict(file=os.path.basename(mp), name=name, state=si, priority=pri, cost=cost, input=inp, seq=seq, air=air))

CHAINS = {82: [82, 120], 83: [83, 120], 84: [84, 121, 122, 123], 124: [124, 125, 126, 127, 128],
          93: [93], 94: [94, 114, 95], 108: [108, 111], 109: [109, 111], 110: [110, 112], 115: [115, 97], 85: [85, 92]}
result = []
done = set()
for r in rows:
    if r['priority'] < 6 or r['state'] < 0: continue
    if cmd['moves'].get(r['name'], {}).get('hide'): continue
    note = cmd['moves'].get(r['name'], {})
    chain = list(note.get('states') or [r['state']])
    if r['state'] not in chain: chain[0] = r['state']
    chain = CHAINS.get(r['state'], chain)
    key = (r['name'], r['input'], r['state'])
    if key in done: continue
    done.add(key)
    st = state_info(chain[0] if chain else r['state'])
    fd = [anim_info(state_info(s)['anim']) for s in chain]
    slug = re.sub(r'\W+', '_', (r['input'] + '_' + r['name'])).strip('_')
    ok = render(chain, os.path.join(OUT, slug + '.gif'), r['air'])
    result.append(dict(r, display=note.get('name', r['name']), desc=note.get('desc', ''), tags=note.get('tags', []),
                       hide=note.get('hide', False), chain=chain, state_name=st['name'], frames=fd, gif=slug + '.gif' if ok else None))
    print(slug, chain, fd[0], file=sys.stderr)
for ex in cmd.get('extra', []):
    slug = re.sub(r'\W+', '_', 'extra_' + ex['name']).strip('_')
    ok = render(ex['states'], os.path.join(OUT, slug + '.gif'))
    result.append(dict(name=ex['name'], display=ex['name'], input=ex.get('input'), after=ex.get('after'), desc=ex['desc'],
                       tags=ex.get('tags', []), chain=ex['states'], frames=[anim_info(state_info(s)['anim']) for s in ex['states']],
                       gif=slug + '.gif' if ok else None, extra=True))
json.dump(result, open(os.path.join(OUT, 'moves.json'), 'w', encoding='utf-8'), indent=1)
print(len(result), 'moves', file=sys.stderr)
