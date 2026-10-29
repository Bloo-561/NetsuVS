"""PALETTE PREVIEW: what a fighter's colours look like, without opening Godot. Reads each colour's
ShaderMaterial (sprite_color_swap / sprite_hue_shift parameters) from its skin scene and applies
the same maths to a sprite.   python palette_preview.py leticia [sprite.png] -> checks/<char>/palettes.png"""
import os, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
try: FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
except Exception: FONT = ImageFont.load_default()

def rgb2hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx, mn = c.max(-1), c.min(-1); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-10
    rr = (mx == r) & m; gg = (mx == g) & m & ~rr; bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6; h[gg] = (b - r)[gg] / d[gg] + 2; h[bb] = (r - g)[bb] / d[bb] + 4
    h = h / 6.0; s = np.where(mx > 1e-10, d / np.maximum(mx, 1e-10), 0); return np.stack([h, s, mx], -1)
def hsv2rgb(c):
    h, s, v = c[..., 0], c[..., 1], c[..., 2]
    k = np.stack([(5 + h * 6) % 6, (3 + h * 6) % 6, (1 + h * 6) % 6], -1)
    return v[..., None] - v[..., None] * s[..., None] * np.clip(np.minimum(k, 4 - k), 0, 1)
def ss(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def color_swap(rgb, P):
    hsv = rgb2hsv(rgb); h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    ht = (h + P.get('hue_offset', 0)) % 1.0
    trim = ss(P['trim_hue_min'] - .01, P['trim_hue_min'] + .01, ht) * (1 - ss(P['trim_hue_max'] - .01, P['trim_hue_max'] + .01, ht)) \
         * ss(P['trim_min_sat'] - .04, P['trim_min_sat'] + .04, s) * ss(.08, .15, v)
    o = hsv.copy(); o[..., 0] = np.where(trim > 0, P['target_hue'], h)
    o[..., 1] = s + (s * P['target_sat'] - s) * trim; o[..., 2] = v + (np.clip(v * P['target_val'], 0, 1) - v) * trim
    dark = (1 - ss(P['dark_max_sat'] - .05, P['dark_max_sat'] + .05, s)) * (1 - ss(P['dark_max_val'] - .05, P['dark_max_val'] + .05, v)) * (1 - trim)
    o[..., 0] = np.where(dark > .01, P['dark_hue'], o[..., 0])
    o[..., 1] = o[..., 1] + (P['dark_sat'] - o[..., 1]) * dark; o[..., 2] = o[..., 2] + (np.clip(o[..., 2] * P['dark_lift'], 0, 1) - o[..., 2]) * dark
    out = np.clip(hsv2rgb(np.clip(o, 0, 1)), 0, 1); st = P.get('strength', 1.0)
    return rgb + (out - rgb) * st
def hue_shift(rgb, P):
    hsv = rgb2hsv(rgb); rr = P.get('red_range', 0.05)
    dist = np.minimum(hsv[..., 0], 1 - hsv[..., 0])
    is_red = (1 - ss(rr, rr + .02, dist)) * (hsv[..., 1] >= P.get('min_saturation', .45))
    hsv[..., 0] = (hsv[..., 0] + P.get('hue_shift', .62) * is_red) % 1.0; return hsv2rgb(hsv)

def material_of(scene):
    t = open(scene, encoding='utf-8').read()
    m = re.search(r'\[ext_resource type="Material"[^\]]*path="([^"]+)"', t)
    if not m: return None, {}
    mt = open(os.path.join(PROJ, m.group(1).replace('res://', '')), encoding='utf-8').read()
    sh = re.search(r'path="([^"]+\.gdshader)"', mt).group(1)
    P = {k: float(v) for k, v in re.findall(r'shader_parameter/(\w+) = (-?[\d.]+)', mt)}
    return os.path.basename(sh), P

def main(char, sprite=None):
    inst = os.path.join(PROJ, 'actors', char, 'Instances')
    scenes = sorted(f for f in os.listdir(inst) if f.endswith('.tscn'))
    sprite = sprite or os.path.join(PROJ, 'actors', char, 'Sprites', 'v2', 'idle_O0.png')
    a = np.array(Image.open(sprite).convert('RGBA')).astype(np.float32) / 255
    cells = []
    for sc in scenes:
        shader, P = material_of(os.path.join(inst, sc)); rgb = a[..., :3]
        if shader == 'sprite_color_swap.gdshader': rgb = color_swap(rgb, P)
        elif shader == 'sprite_hue_shift.gdshader': rgb = hue_shift(rgb, P)
        im = Image.fromarray((np.dstack([np.clip(rgb, 0, 1), a[..., 3:]]) * 255).astype(np.uint8), 'RGBA')
        bg = Image.new('RGBA', im.size, (70, 70, 80, 255)); bg.alpha_composite(im)
        ImageDraw.Draw(bg).text((8, 8), sc.replace('.tscn', ''), fill=(255, 230, 120, 255), font=FONT); cells.append(bg)
    W = sum(c.width for c in cells); out = Image.new('RGB', (W, max(c.height for c in cells))); x = 0
    for c in cells: out.paste(c.convert('RGB'), (x, 0)); x += c.width
    od = os.path.join(HERE, 'checks', char); os.makedirs(od, exist_ok=True)
    p = os.path.join(od, 'palettes.png'); out.save(p); print(p)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
