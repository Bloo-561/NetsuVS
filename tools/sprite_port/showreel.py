"""One GIF that plays several animations in a row, same camera for all (for showing the port).
   python showreel.py <char> <out.gif> <anim> [<anim> ...]"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import Port, HERE
import hitfit
from analyze import font as _font
FONT = _font(18, bold=True)
def render(p, name, X0=-700, X1=900, Y0=-40, Y1=760, scale=0.5, loops=1):
    an = hitfit.Anim(p.char, name)
    dur = an.dur or 60
    W, H = int((X1 - X0) * scale), int((Y1 - Y0) * scale)
    frames = []
    for loop in range(loops):
        last = None
        for tick in range(dur):
            k = an.key_at(tick)
            if last is not None and k is last: frames[-1][1] += 1; continue
            img = Image.new('RGBA', (W, H), (54, 54, 64, 255)); d = ImageDraw.Draw(img)
            fy = int(Y1 * scale); d.rectangle([0, fy, W, H], fill=(40, 40, 48, 255)); d.line([(0, fy), (W, fy)], fill=(90, 160, 170, 255), width=2)
            for md in k[1]:
                if md['contact']: continue
                c = hitfit.png(md['tex']); im = Image.fromarray(c, 'RGBA')
                if md['flipx']: im = im.transpose(Image.FLIP_LEFT_RIGHT)
                R = 1800; big = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0))
                big.paste(im, (int(md['off'][0]) + R, R - (int(md['off'][1]) + c.shape[0])), im)
                if md['rot']: big = big.rotate(md['rot'], resample=Image.BICUBIC, center=(R, R))
                big = big.crop((R + X0, R - Y1, R + X1, R - Y0)).resize((W, H), Image.LANCZOS)
                img.alpha_composite(big)
            d.text((12, 10), name.split('_', 2)[-1].replace('_', ' '), fill=(255, 230, 120, 255), font=FONT)
            frames.append([img, 1]); last = k
    return frames
if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = dict(a[2:].split('=') for a in sys.argv[1:] if a.startswith('--') and '=' in a)   # --x0= --x1= --y1= --scale=
    cam = {k: (float(v) if k == 'scale' else int(v)) for k, v in opt.items() if k in ('x0', 'x1', 'y0', 'y1', 'scale')}
    cam = {{'x0': 'X0', 'x1': 'X1', 'y0': 'Y0', 'y1': 'Y1'}.get(k, k): v for k, v in cam.items()}
    char, out = args[0], args[1]
    p = Port(char); allf = []
    for n in args[2:]:
        loops = 2 if n.endswith(('Neutral', 'MoveF', 'MoveB')) else 1
        allf += render(p, n, loops=loops, **cam)
        allf[-1][1] += 20
    pal = [f[0].convert('RGB').quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE) for f in allf]
    durs = [max(20, int(round(f[1] * 1000 / 60 / 10)) * 10) for f in allf]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, disposal=1)
    print(out, len(allf), 'frames', sum(durs) / 1000, 's')
