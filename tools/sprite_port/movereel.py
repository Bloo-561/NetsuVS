"""MOVE REEL: GIF preview of a fighter's moves WITH their movement (rising kicks rise, rushes
travel, teleports jump around a stand-in opponent), simulated from the move tables in
moves_<char>.py (movex / movey / gravity / teleport). Physics like the engine: two half-steps a frame,
so position += speed / 60 every frame; gravity takes force / 60 off the speed every frame.
Animations not in the table play in place. A grey stand-in opponent is drawn for scale.

    python movereel.py leticia out.gif 78_LET_623A 98_LET_DPLAND 95_LET_S2 97_LET_S2_hit [--x1=1900 --scale=0.35 --opp=520]
    --chain   each move starts where the one before ended (a move into a follow-up state, played as one)
"""
import sys, os, importlib
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from build import Port, rotated_layer
import hitfit
from analyze import font as _font
FONT = _font(18, bold=True)
UPX = 27.5
AIR_START = 330          # px: air moves start from about a jump's height

def kind(o): return os.path.basename(o.script).replace('.cs', '') if hasattr(o, 'script') else ''

def motion(m, dur, opp_x, start=None, chain=False):
    """per-tick (x, y) of the fighter's origin in world px; the opponent stands at opp_x facing her.
    start: (x, y) to begin from (--chain: where the previous move ended); chain also stops a move that
    leads into another state on hit (hit_confirm) when it reaches the opponent."""
    acts = {}
    for f, a in m.get('tick', []): acts.setdefault(f, []).append(a)
    ranges = list(m.get('tick_ranges', []))
    x = 0.0; y = AIR_START if m.get('air') else 0.0; vx = vy = 0.0; out = []
    if start is not None: x, y = start
    lands = m.get('air_land') or m.get('flux_land') or m.get('air_land_normal') or m.get('meteor_land'); was_up = y > 0
    def apply(a):
        nonlocal x, y, vx, vy
        k = kind(a); fl = a.fields
        if k == 'MoveXAction': vx = float(fl.get('Velocity') or 0)
        elif k == 'MoveYAction': vy = float(fl.get('Velocity') or 0)
        elif k == 'TeleportAction':
            t = fl['TargetPosition']
            if fl.get('xRelativeTo') == 2: x = opp_x - t.x / UPX          # in front of the opponent = towards her side
            else: x += t.x / UPX
            if fl.get('yRelativeTo') == 2: y = t.y / UPX                 # (stand-in opponent stands on the floor)
            elif fl.get('yRelativeTo') == 0: y = t.y / UPX
            else: y += t.y / UPX
    for a in m.get('enter', []): apply(a)
    for f in range(dur):
        for a in acts.get(f, []): apply(a)
        for (a0, b0), a in ranges:
            if a0 <= f <= b0 and kind(a) == 'AddGravityAction':
                g = a.fields.get('Force') or 260000; vy -= g / 60.0
        x += vx / 60.0 / UPX; y += vy / 60.0 / UPX     # (Oct 24 fix: was / 120, half the game's speed)
        if y > 1: was_up = True
        if y < 0 and f > 3: y = 0.0; vy = 0.0
        out.append((x, y))
        if lands and was_up and y <= 0 and f > 3: break      # the game switches to the landing state here
        if chain and m.get('hit_confirm') and x >= opp_x - 200: break   # connected: the hit state takes over
    return out

def render(p, name, moves, X0, X1, Y0, Y1, scale, opp_x, opp_img, start=None, chain=False):
    an = hitfit.Anim(p.char, name); dur = an.dur or 60
    mk = name.split('_', 2)[2] if name.count('_') >= 2 else None
    m = moves.get(mk) if moves else None
    path = motion(m, dur, opp_x, start, chain) if m else [start or (0.0, 0.0)] * dur
    dur = len(path)
    W, H = int((X1 - X0) * scale), int((Y1 - Y0) * scale)
    frames = []; last = None
    for tick in range(dur):
        k = an.key_at(tick); pos = path[tick]
        state = (id(k), round(pos[0]), round(pos[1]))
        if last is not None and state == last: frames[-1][1] += 1; continue
        img = Image.new('RGBA', (W, H), (54, 54, 64, 255)); d = ImageDraw.Draw(img)
        fy = int(Y1 * scale); d.rectangle([0, fy, W, H], fill=(40, 40, 48, 255)); d.line([(0, fy), (W, fy)], fill=(90, 160, 170, 255), width=2)
        VW, VH = X1 - X0, Y1 - Y0
        def layer(im, ox, oy, rot=0, cx=0.0, cy=0.0):
            big = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
            if rot:   # turned about her origin like the engine; the sprite itself is turned, so nothing is cut off first
                r, left, top = rotated_layer(im, ox, oy, rot, cx, cy)
                big.paste(r, (int(round(left)) - X0, Y1 - int(round(top))), r)
            else:
                big.paste(im, (int(ox) - X0, Y1 - (int(oy) + im.height)), im)
            img.alpha_composite(big.resize((W, H), Image.LANCZOS))
        if opp_img is not None:   # stand-in opponent on the floor, facing her
            layer(opp_img, opp_x - opp_img.width // 2, 0)
        for md in (k[1] if k else []):
            if md['contact']: continue
            im = Image.fromarray(hitfit.png(md['tex']), 'RGBA')
            if md['flipx']: im = im.transpose(Image.FLIP_LEFT_RIGHT)
            layer(im, md['off'][0] + pos[0], md['off'][1] + pos[1], md['rot'], pos[0], pos[1])
        d.text((12, 10), (m['name'] if m else name.split('_', 2)[-1].replace('_', ' ')), fill=(255, 230, 120, 255), font=FONT)
        frames.append([img, 1]); last = state
    render.end = path[-1] if path else (0.0, 0.0)
    return frames

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = dict(a[2:].split('=') for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    char, out = args[0], args[1]
    X0, X1 = int(opt.get('x0', -500)), int(opt.get('x1', 1300)); Y0, Y1 = int(opt.get('y0', -40)), int(opt.get('y1', 900))
    scale = float(opt.get('scale', 0.4)); opp_x = int(opt.get('opp', 520))
    p = Port(char)
    try: moves = importlib.import_module('moves_' + char).MOVES
    except Exception: moves = {}
    opp_img = None
    o = os.path.join(HERE, '..', '..', 'actors', 'cecilia', 'Sprites', 'v2', 'idle_O0.png')
    if os.path.exists(o) and char != 'cecilia':
        opp_img = Image.open(o).convert('RGBA').transpose(Image.FLIP_LEFT_RIGHT)
        opp_img.putalpha(opp_img.split()[3].point(lambda v: int(v * 0.55)))
    allf = []; chain = '--chain' in sys.argv; start = None
    for n in args[2:]:
        allf += render(p, n, moves, X0, X1, Y0, Y1, scale, opp_x, opp_img, start if chain else None, chain)
        allf[-1][1] += 4 if chain else 24
        start = (render.end[0], 0.0) if render.end[1] <= 0 else render.end
    pal = [f[0].convert('RGB').quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE) for f in allf]
    durs = [max(20, int(round(f[1] * 1000 / 60 / 10)) * 10) for f in allf]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, disposal=1)
    print(out, len(allf), 'frames', sum(durs) / 1000, 's')

if __name__ == '__main__':
    main()
