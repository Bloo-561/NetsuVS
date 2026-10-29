"""Milestone 6 review sheet (plain Python 3 + numpy + Pillow, outside Blender):
sheet | model | 50% overlay | silhouette diff per view, 3/4 views, head
close-ups, part close-ups (sheet | model), the shading palette and the
control maps. Needs the renders of m6_preview.run(tag, names=None, sil=True).
usage: python m6_sheet.py m6_final ../renders/m6_review.png "note line"
"""
import ast
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import os
_ROOT = os.environ.get('CECILIA_V2', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(_ROOT, 'renders') + os.sep
T = os.path.join(_ROOT, 'textures') + os.sep
REF = os.path.join(_ROOT, 'refs') + os.sep
SRC = os.path.dirname(os.path.abspath(__file__)) + os.sep
txt = open(SRC + 'review_body.py').read()
REG = ast.literal_eval(txt[txt.index('REGIONS = {') + len('REGIONS = '):txt.index('}\n', txt.index('REGIONS = {')) + 1])
tag, out_path = sys.argv[1], sys.argv[2]
lines_note = sys.argv[3] if len(sys.argv) > 3 else ''
iou = json.load(open(os.path.join(R, 'sil', '%s_iou.json' % tag)))
def _font(size, bold=False):
    for name in (('DejaVuSans-Bold.ttf', 'arialbd.ttf') if bold else ('DejaVuSans.ttf', 'arial.ttf')):
        for d in ('/usr/share/fonts/truetype/dejavu/', 'C:/Windows/Fonts/', ''):
            try:
                return ImageFont.truetype(d + name, size)
            except OSError:
                pass
    return ImageFont.load_default()


F, FB, FS, FT = _font(22), _font(30, True), _font(17), _font(14)
G = 14


def openw(p):
    im = Image.open(p)
    if im.mode == 'RGBA':
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return im.convert('RGB')


def h_fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def region_pair(name):
    view, u0, v0, w, h, s = REG[name]
    mod = openw(R + '%s_%s.png' % (tag, name))
    ref = Image.open(REF + 'cecilia_ref_%s.png' % view).convert('RGB').crop((u0, v0, u0 + w, v0 + h)).resize(mod.size, Image.LANCZOS)
    return ref, mod


def diff(view, size):
    d = Image.open(os.path.join(R, 'sil', '%s_%s_diff.png' % (tag, view))).convert('RGB')
    return d.resize(size, Image.NEAREST)


# ------------------------------------------------------------------ palette
def consts(path, names):
    src = open(path).read()
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n in names:
                try:
                    out[n] = ast.literal_eval(node.value)
                except ValueError:          # dict(...) calls in our own constants
                    out[n] = eval(compile(ast.Expression(node.value), path, 'eval'), {'__builtins__': {}, 'dict': dict})
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
            for t, v in zip(node.targets[0].elts, node.value.elts if isinstance(node.value, ast.Tuple) else []):
                if isinstance(t, ast.Name) and t.id in names:
                    out[t.id] = ast.literal_eval(v)
    return out


BK = consts(SRC + 'bake.py', ('FAMILY',))
TN = consts(SRC + 'toon.py', ('SPEC_METAL', 'SPEC_HAIR', 'SPEC_OBJ', 'HAIR_BANDS', 'HAIR_SHADE', 'SKIN_RGB', 'NECK_SHADE',
                              'EAR_RGB', 'EAR_SHADE'))


def lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb(c):
    c = np.clip(c, 0, 1)
    return tuple(int(round(v)) for v in 255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055))


def deep(base, shade):
    b, s = lin(base), lin(shade)
    return srgb(np.minimum(s * s / np.maximum(b, 0.02), s))


rows_pal = []
fam = BK['FAMILY']
for name in ('skin', 'red', 'white', 'jacket', 'sleeve', 'legwear', 'loafer', 'gold', 'maroon', 'glove', 'teal', 'band'):
    lit, sh = fam[name]
    spec = None
    if name == 'jacket':
        spec = TN['SPEC_OBJ']['jacket']['color']
    elif name == 'gold':
        spec = TN['SPEC_METAL']['color']
    rows_pal.append((name, lit, sh, deep(lit, sh), spec))
for (p, lit), (_, sh) in zip(TN['HAIR_BANDS'], TN['HAIR_SHADE']):
    rows_pal.append(('hair %.2f' % p, lit, sh, deep(lit, sh), TN['SPEC_HAIR']['color'] if p == 0.0 else None))
rows_pal.append(('neck', TN['SKIN_RGB'], TN['NECK_SHADE'], deep(TN['SKIN_RGB'], TN['NECK_SHADE']), None))
rows_pal.append(('neckerchief', fam['gold'][0], fam['gold'][1], deep(*fam['gold']), TN['SPEC_OBJ']['neckerchief']['color']))

SW = 46
pal = Image.new('RGB', (175 + 4 * (SW + 6), 30 + len(rows_pal) * (SW // 2 + 6)), (255, 255, 255))
dp = ImageDraw.Draw(pal)
for k, lab in enumerate(('lit', 'shadow', 'deep', 'spec')):
    dp.text((175 + k * (SW + 6), 2), lab, fill=(60, 60, 60), font=FT)
for i, (name, *cols) in enumerate(rows_pal):
    y = 24 + i * (SW // 2 + 6)
    dp.text((4, y + 3), name, fill=(40, 40, 40), font=FT)
    for k, c in enumerate(cols):
        x = 175 + k * (SW + 6)
        if c is None:
            dp.line((x, y + SW // 2, x + SW, y), fill=(200, 200, 200))
            continue
        dp.rectangle((x, y, x + SW, y + SW // 2), fill=tuple(int(v) for v in c), outline=(150, 150, 150))


def chan(path, k, size=340):
    a = np.asarray(Image.open(path).convert('RGBA'))[..., k]
    return Image.fromarray(a).convert('RGB').resize((size, size), Image.LANCZOS)


rows = []
for view in ('front', 'back', 'side'):
    ref, mod = region_pair('full_' + view)
    H = 640
    ref, mod = h_fit(ref, H), h_fit(mod, H)
    ov = Image.blend(ref, mod, 0.5)
    df = diff(view, ref.size)
    v = iou[view]
    lab = '%s   IoU %.4f (target %.2f)   bands: %s' % (
        view, v['iou'], v['target'], ', '.join('%s %.3f' % (b['band'], b['iou']) for b in v['bands']))
    rows.append((lab, [(ref, 'sheet'), (mod, 'model'), (ov, 'overlay'), (df, 'diff')]))
qs = [('q_front_right', 'front-right 40 deg'), ('idle', 'idle sprite angle (62 deg)'),
      ('q_front_left', 'front-left 40 deg'), ('q_back_right', 'back-right 140 deg')]
rows.append(('3/4 views (no sheet counterpart). One fixed key light: her right-front, 30 deg up',
             [(h_fit(openw(R + '%s_%s.png' % (tag, n)), 640), lab) for n, lab in qs]))
heads = [('front', 'front'), ('q_right', '3/4 right'), ('q_idle', 'idle angle'), ('side', 'side'), ('q_left', '3/4 left'),
         ('back', 'back')]
rows.append(('Head close-ups', [(h_fit(openw(R + '%s_%s.png' % (tag, n)), 330), lab) for n, lab in heads]))
close = []
for name, lab in (('torso_front', 'torso front'), ('torso_side', 'torso side'), ('torso_back', 'jacket back + vent'),
                  ('skirt_front', 'skirt front'), ('feet_side', 'stocking ribbons + loafer'), ('sword_front', 'tachi front')):
    ref, mod = region_pair(name)
    H = 300
    close.append((h_fit(ref, H), 'sheet: ' + lab))
    close.append((h_fit(mod, H), 'model: ' + lab))
rows.append(('Close-ups, same framing (sheet | model)', close[:4]))
rows.append(('', close[4:8]))
rows.append(('', close[8:]))
socks = Image.open(REF + 'cecilia_ref_detail_socks.png').convert('RGB')
rows.append(('Shading: palette (all from the sheet) | control maps (body_ctrl R occlusion, G threshold, B specular; hair_ctrl B strands) | socks panel',
             [(pal, 'lit | 1st shadow | 2nd (shadow^2/lit) | spec'),
              (chan(T + 'body_ctrl.png', 0), 'occlusion (R)'), (chan(T + 'body_ctrl.png', 1), 'threshold (G)'),
              (chan(T + 'body_ctrl.png', 2), 'specular mask (B)'), (chan(T + 'hair_ctrl.png', 2), 'hair strands (B)'),
              (h_fit(socks, 340), 'sheet: socks detail panel')]))

LAB = 24                                             # label strip under every image
W = max(sum(im.width for im, _ in ims) + G * (len(ims) + 1) for _, ims in rows)
Htot = 140 + sum(max(im.height for im, _ in ims) + 56 + LAB for _, ims in rows)
out = Image.new('RGB', (W, Htot), (255, 255, 255))
d = ImageDraw.Draw(out)
d.text((G, 16), 'Cecilia v2 - Milestone 6: Guilty Gear Xrd style toon shading', fill=(0, 0, 0), font=FB)
y = 70
for title, ims in rows:
    if title:
        d.text((G, y + 4), title, fill=(30, 30, 30), font=F)
    x = G
    for im, lab in ims:
        out.paste(im, (x, y + 34))
        d.text((x + 2, y + 34 + im.height + 3), lab, fill=(70, 70, 70), font=FS)
        x += im.width + G
    y += max(im.height for im, _ in ims) + 56 + LAB
d.text((G, Htot - 60), 'diff: white = both, red = sheet only, blue = model only.  ' + lines_note, fill=(60, 60, 60), font=FS)
d.text((G, Htot - 34), 'Shader: light = ((N.L + 1) x occlusion) / 2 + (2 x threshold - 1); shadow 1 below 0.5; shadow 2 where occlusion '
       'or threshold < 0.1; specular where N.H > 1 - size inside the mask, on lit areas (ASW / GG Xrd model).',
       fill=(60, 60, 60), font=FS)
out.save(out_path)
print(out_path, out.size)
