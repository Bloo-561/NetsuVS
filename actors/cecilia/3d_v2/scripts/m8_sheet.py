"""compose the Milestone 8 review sheet (plain Python + Pillow, outside Blender):
the sprite test next to idle1.png (zoomed, overlay, silhouette diff, full
frames with the framing guides), a second frame through the same camera next
to 5m4.png, the live skirt shadow before / after, the camera fit.
usage: m8_sheet.py renders_dir sprites_dir out.png"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

R, SP, out_path = sys.argv[1].rstrip('/') + '/', sys.argv[2].rstrip('/') + '/', sys.argv[3]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F, FB, FS = (ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT.replace('Sans', 'Sans-Bold'), 30),
             ImageFont.truetype(FONT, 17))
G = 14
FRAME = dict(bottom=620, rear_x=403)


def rgba(p):
    return Image.open(p).convert('RGBA')


def onw(im, bg=(255, 255, 255)):
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def mask(im):
    return np.asarray(im)[..., 3] >= 128


def iou(a, b):
    return float((a & b).sum()) / max(int((a | b).sum()), 1)


def diff(a, b):
    """white = both, red = sprite only, blue = model only"""
    img = np.zeros(a.shape + (3,), np.uint8)
    img[a & b] = (255, 255, 255)
    img[b & ~a] = (255, 0, 0)
    img[a & ~b] = (0, 90, 255)
    return Image.fromarray(img)


def zoom(im, box, s):
    c = im.crop(box)
    return c.resize((c.width * s, c.height * s), Image.NEAREST)


def guides(im):
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.line([(0, FRAME['bottom'] + 0.5), (im.width, FRAME['bottom'] + 0.5)], fill=(0, 170, 220), width=1)
    d.line([(FRAME['rear_x'] - 0.5, 0), (FRAME['rear_x'] - 0.5, im.height)], fill=(0, 170, 220), width=1)
    return im


def h_fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


idle1 = rgba(SP + 'idle1.png')
test = rgba(R + 'idle_test.png')
smooth = rgba(R + 'idle_test_smooth.png')
m4 = rgba(SP + '5m4.png')
slash = rgba(R + '5m4_test.png')
mi, ms = mask(idle1), mask(test)
iou_idle = iou(ms, mi)
m54, msl = mask(m4), mask(slash)
iou_slash = iou(msl, m54)

rows = []
box = (385, 362, 615, 630)
s = 3
ov = Image.blend(onw(idle1), onw(test), 0.5)
rows.append(('Sprite test: renders/idle_test.png next to Sprites/idle1.png (3x, nearest).  Silhouette IoU %.3f' % iou_idle,
             [(zoom(onw(idle1), box, s), 'idle1.png'), (zoom(onw(test), box, s), 'idle_test.png (alpha cut at 50 %)'),
              (zoom(onw(smooth), box, s), 'idle_test_smooth.png (anti-aliased alpha)'),
              (zoom(ov, box, s), '50 % overlay'), (zoom(diff(ms, mi), box, s), 'silhouettes: red idle1 only, blue model only')]))
full = 470
rows.append(('The full 1024 x 1024 frames (shown at 46 %); guides: row 620 (feet) and column 403 (rear foot)',
             [(h_fit(guides(onw(idle1, (235, 235, 235))), full), 'idle1.png'),
              (h_fit(guides(onw(test, (235, 235, 235))), full), 'idle_test.png'),
              (h_fit(guides(onw(m4, (235, 235, 235))), full), '5m4.png'),
              (h_fit(guides(onw(slash, (235, 235, 235))), full), 'renders/5m4_test.png (same camera)')]))
box2 = (385, 375, 800, 630)
rows.append(('A second frame through the same, unmoved camera: the two-handed draw-slash next to 5m4.png, rear foot planted '
             'where the idle\'s stands.  IoU %.3f' % iou_slash,
             [(zoom(onw(m4), box2, 2), '5m4.png'), (zoom(onw(slash), box2, 2), '5m4_test.png'),
              (zoom(diff(msl, m54), box2, 2), 'silhouettes: red 5m4 only, blue model only')]))
sk = []
for v, lab in (('cam', 'idle, sprite side'), ('back', 'idle, back-left'), ('front', 'idle, front-left low'), ('low', 'idle, from below')):
    sk.append((h_fit(onw(rgba(R + 'm8_before_idle_%s.png' % v)), 300), 'M7: ' + lab))
    sk.append((h_fit(onw(rgba(R + 'm8_after_idle_%s.png' % v)), 300), 'M8: ' + lab))
rows.append(('The skirt\'s shadow on the legs now follows the skirt (M7 known issue 3): baked rest-pose shadow (M7) | live (M8)',
             sk[:4]))
rows.append(('', sk[4:]))
rows.append(('', [(h_fit(onw(rgba(R + 'm8_before_rest_%s.png' % v)), 300), 'M7 rest: ' + v) for v in ('front', 'back')] +
             [(h_fit(onw(rgba(R + 'm8_after_rest_%s.png' % v)), 300), 'M8 rest: ' + v) for v in ('front', 'back')]))
v2 = json.load(open(R + 'checks/sprite_fit_v2.json'))
v3 = json.load(open(R + 'checks/sprite_fit_v3.json'))
fit_dbg = Image.open(R + 'checks/fit_debug_diff.png').convert('RGB')
rows.append(('Fitting the camera and the stance to idle1 (silhouette IoU, same framing): M7 stance + camera %.2f -> fitted %.2f '
             '-> face and sword fixed by hand %.2f -> final sprite %.3f' % (v2['start'], v2['score'], v3['score'], iou_idle),
             [(zoom(fit_dbg, box, 2), 'M7 idle at the M7 camera (40 deg, 5 deg up)'),
              (zoom(diff(ms, mi), box, 2), 'final: camera 80 deg round to her right, level')]))

LAB = 24
W = max(sum(im.width for im, _ in ims) + G * (len(ims) + 1) for _, ims in rows)
Htot = 150 + sum(max(im.height for im, _ in ims) + 56 + LAB for _, ims in rows)
out = Image.new('RGB', (W, Htot), (255, 255, 255))
d = ImageDraw.Draw(out)
d.text((G, 16), 'Cecilia v2 - Milestone 8: sprite test', fill=(0, 0, 0), font=FB)
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
d.text((G, Htot - 60), 'Camera (SPRITE scene, CAM_sprite): orthographic, 80 deg round to her right from her front, level; '
       '5.23 mm per pixel; 1 px outlines; 4x supersampled.', fill=(60, 60, 60), font=FS)
d.text((G, Htot - 34), 'idle_test.png: 247 px tall incl. the ahoge (rows 374-620), feet on row 620, rear foot on column 403. '
       'The sword follows the sheet (41 cm); the sprites draw it about 1 m.', fill=(60, 60, 60), font=FS)
out.save(out_path)
print(out_path, out.size, 'iou idle %.4f slash %.4f' % (iou_idle, iou_slash))
