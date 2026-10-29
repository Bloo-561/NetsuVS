"""compose the Milestone 7 review sheet (plain Python + Pillow, outside Blender):
test poses next to the game's sprites, all-round views, deformation
close-ups, the sword sockets, the eye controls and the rig drawn over the
rest pose.
usage: m7_sheet.py renders_dir sprites_dir out.png [iou_json]"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

R, SP, out_path = sys.argv[1].rstrip('/') + '/', sys.argv[2].rstrip('/') + '/', sys.argv[3]
iou = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F, FB, FS = (ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT.replace('Sans', 'Sans-Bold'), 30),
             ImageFont.truetype(FONT, 17))
G = 14
BODY = dict(size=1.9, res=900, target=(0.0, 0.0, 0.74))      # = m7_review.BODY
SPRITE_H = 1.58 / 246.0                                       # m per sprite px (idle1: 246 px, sole to head top)


def openw(p):
    im = Image.open(p)
    if im.mode == 'RGBA':
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return im.convert('RGB')


def h_fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def _bbox(path):
    a = np.asarray(Image.open(path).convert('RGBA'))[..., 3]
    ys, xs = np.nonzero(a > 0)
    return xs.min(), xs.max(), ys.min(), ys.max()


def sprite(name, h):
    """the sprite at the scale where idle1's figure (ahoge to sole, 246 px)
    is as tall as the idle render's, feet on the render's floor line"""
    sp = Image.open(SP + name + '.png').convert('RGBA')
    x0, x1, y0, y1 = _bbox(SP + name + '.png')
    i0, i1, j0, j1 = _bbox(SP + 'idle1.png')
    r0, r1, s0, s1 = _bbox(R + 'm7_idle_cam.png')
    k = (s1 - s0) / float(j1 - j0)                 # render px per sprite px
    crop_h = BODY['res'] / k
    y_top = j1 - (s1 + 0.5) / k                    # sprite sole row <-> render sole row
    cx = 0.5 * (x0 + x1)
    w = max(crop_h, (x1 - x0) + 30)
    c = sp.crop((int(cx - w / 2), int(round(y_top)), int(cx + w / 2), int(round(y_top + crop_h))))
    bg = Image.new('RGBA', c.size, (255, 255, 255, 255))
    bg.alpha_composite(c)
    c = bg.convert('RGB')
    return c.resize((round(c.width * h / c.height), h), Image.NEAREST)


def r(name, h):
    return h_fit(openw(R + name + '.png'), h)


COLL = {'Body': (40, 90, 220), 'Fingers': (0, 160, 200), 'Hair': (150, 60, 200), 'Skirt': (240, 120, 0),
        'Cloth': (20, 160, 60), 'Sword': (200, 150, 0), 'Face': (230, 60, 150), 'Controls': (220, 20, 20)}


def bones_over(view, h):
    J = json.load(open(R + 'm7_bones.json'))
    cam = next(c for c in J['cams'] if c['name'] == view)
    im = openw(R + 'm7_rest_%s.png' % view)
    # fade the render so the bones read
    im = Image.blend(im, Image.new('RGB', im.size, (255, 255, 255)), 0.45)
    d = ImageDraw.Draw(im)
    rt, up, tg = np.array(cam['right']), np.array(cam['up']), np.array(cam['target'])
    s = cam['res'][0] / cam['size']

    def pr(p):
        q = np.array(p) - tg
        return (cam['res'][0] / 2 + q @ rt * s, cam['res'][1] / 2 - q @ up * s)
    order = ['Skirt', 'Cloth', 'Hair', 'Body', 'Fingers', 'Face', 'Sword', 'Controls']
    for cname in order:
        for b in J['bones']:
            if b['hidden'] or not b['coll'] or b['coll'][0] != cname:
                continue
            col = COLL.get(cname, (90, 90, 90))
            a, e = pr(b['head']), pr(b['tail'])
            d.line([a, e], fill=col, width=3)
            d.ellipse([a[0] - 3, a[1] - 3, a[0] + 3, a[1] + 3], fill=col)
    return h_fit(im, h)


def legend():
    im = Image.new('RGB', (230, 30 * len(COLL) + 10), 'white')
    d = ImageDraw.Draw(im)
    for i, (k, c) in enumerate(COLL.items()):
        d.line([(10, 20 + 30 * i), (50, 20 + 30 * i)], fill=c, width=4)
        d.text((60, 9 + 30 * i), k, fill=(40, 40, 40), font=FS)
    return im


H = 560
rows = []
rows.append(('Test poses at the sprite angle (camera 40 deg to her right-front, 5 deg up); the sprites scaled so idle1 is as tall as the idle render',
             [(sprite('idle1', H), 'Sprites/idle1.png'), (r('m7_idle_cam', H), 'idle'),
              (sprite('5m4', H), 'Sprites/5m4.png (5C: the cut)'), (r('m7_draw_slash_cam', H), 'two-handed draw-slash'),
              (r('m7_right_hand_cam', H), 'right-hand socket'), (r('m7_overhead_cam', H), 'overhead (shoulder test)')]))
rows.append(('The two test poses from the front, side and back',
             [(r('m7_idle_front', 430), 'idle front'), (r('m7_idle_side', 430), 'idle side'), (r('m7_idle_back', 430), 'idle back'),
              (r('m7_draw_slash_front', 430), 'slash front'), (r('m7_draw_slash_side', 430), 'slash side'),
              (r('m7_draw_slash_back', 430), 'slash back')]))
rows.append(('Deformation: shoulders',
             [(r('m7_idle_sh_cam', 330), 'idle'), (r('m7_idle_sh_back', 330), 'idle, back'),
              (r('m7_draw_slash_sh_cam', 330), 'slash'), (r('m7_draw_slash_sh_back', 330), 'slash, back'),
              (r('m7_overhead_sh_front', 330), 'arm up'), (r('m7_overhead_sh_back', 330), 'arm up, back'),
              (r('m7_overhead_sh_side', 330), 'arm up, side'), (r('m7_overhead_sh_pit', 330), 'arm up, from below')]))
rows.append(('Deformation: hips and skirt',
             [(r('m7_idle_hip_cam', 330), 'idle'), (r('m7_idle_hip_back', 330), 'idle, back-left'),
              (r('m7_idle_hip_front', 330), 'idle, front-left low'), (r('m7_idle_hip_low', 330), 'idle, from below'),
              (r('m7_draw_slash_hip_cam', 330), 'slash'), (r('m7_draw_slash_hip_back', 330), 'slash, back-left'),
              (r('m7_draw_slash_hip_front', 330), 'slash, front-left low'), (r('m7_draw_slash_hip_low', 330), 'slash, from below')]))
rows.append(('Sword sockets (sword: 0 sheath / 1 right hand / 2 both hands; sheath: 0 hip / 1 held; hand_L, hand_R: on hilt / on sheath)',
             [(r('m7_rest_sock_front', 330), 'sheathed at the hip'), (r('m7_idle_sock_cam', 330), 'sheath held (idle)'),
              (r('m7_right_hand_sock_cam', 330), 'right hand'), (r('m7_draw_slash_sock_cam', 330), 'both hands'),
              (r('m7_overhead_sock_cam', 330), 'right hand, raised')]))
eyes = [(r('m7_eyes_%s_front' % n, 300).crop((40, 60, 260, 230)), n) for n in ('ahead', 'left', 'right', 'up', 'down')]
eyes += [(r('m7_eyes_%s_q' % n, 300).crop((40, 60, 260, 230)), n + ', 3/4') for n in ('ahead', 'left')]
rows.append(('Eye controls: eyes_target moved 15 cm to each side / 8 cm up and down (both irises follow; clipped to the eye opening)',
             [(h_fit(im, 230), lab) for im, lab in eyes]))
rows.append(('The rig over the rest pose (deform bones, fingers, hair, skirt, cloth, sword, face, IK controls and poles)',
             [(bones_over('front', 700), 'front'), (bones_over('side', 700), 'side'), (legend(), '')]))

LAB = 24
W = max(sum(im.width for im, _ in ims) + G * (len(ims) + 1) for _, ims in rows)
Htot = 150 + sum(max(im.height for im, _ in ims) + 56 + LAB for _, ims in rows)
out = Image.new('RGB', (W, Htot), (255, 255, 255))
d = ImageDraw.Draw(out)
d.text((G, 16), 'Cecilia v2 - Milestone 7: rig, test poses and deformation', fill=(0, 0, 0), font=FB)
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
if iou:
    d.text((G, Htot - 60), 'Rest pose with the rig live: IoU front %.4f, back %.4f, side %.4f (M6: 0.9503 / 0.9503 / 0.9676).'
           % (iou['front']['iou'], iou['back']['iou'], iou['side']['iou']), fill=(60, 60, 60), font=FS)
d.text((G, Htot - 34), 'Sword: the sheet draws the tachi about 41 cm long (hilt 9.6 cm); the game sprites draw it about 1 m. '
       'The model follows the sheet (see notes).', fill=(60, 60, 60), font=FS)
out.save(out_path)
print(out_path, out.size)
