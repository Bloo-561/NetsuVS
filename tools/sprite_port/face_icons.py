"""FACE ICONS (Oct 26 2026, TamaDeez): the character-select slot picture (Profile -> Portrait, 840x840) and the battle HUD
corner picture (HUD_Portrait.png, 512x512) cut from a picture's face, so every fighter's face sits in the same place.

    python tools/sprite_port/face_icons.py            # all fighters in FACES
    python tools/sprite_port/face_icons.py noah       # one

The select screen shows the same part of every Portrait (character_select.gd PORTRAIT_CROP: x 0.24-0.92, y 0.03-0.63);
its middle is x 487 of 840. Here each face is scaled so the eyes are EYE_GAP px apart and their midpoint lands on EYES.
FACES: source picture (in the fighter's Artwork folder, or a path from the project folder starting with tools/), the two eye centres in it, and which pictures
to write. Measure the eyes in the source picture (pixels). Re-running make_artwork.py overwrites these: run this after it.
"""
import os, sys, math
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))

PORTRAIT = dict(size=840, eyes=(487, 345), gap=145)   # character select slot
HUD = dict(size=512, eyes=(262, 285), gap=135)        # battle HUD corner (netsu_hud.gd centres the picture there)

FACES = {
    # Oct 26: Cecilia and Leticia take the face from their standing select render (the big picture on the select screen)
    'cecilia': dict(src='Cecilia_Select_FullBody.png', eyes=((513, 192), (590, 240)),
                    write={'Cecilia_Select_Portrait.png': PORTRAIT, 'HUD_Portrait.png': HUD}),
    'leticia': dict(src='Leticia_Select_FullBody.png', eyes=((533, 285), (600, 305)),
                    write={'Leticia_Select_Portrait.png': PORTRAIT, 'HUD_Portrait.png': HUD}),
    # Noah keeps his select portrait drawing (the old one, kept as tools/sprite_port/derived/noah/Noah_Select_Portrait_src.png), only centred and sized
    # like the others (it was small and to the left)
    'noah': dict(src='tools/sprite_port/derived/noah/Noah_Select_Portrait_src.png', eyes=((405, 218), (475, 232)),
                 write={'Noah_Select_Portrait.png': PORTRAIT}),
}


def face_crop(src, eyes, size, target, gap):
    (x1, y1), (x2, y2) = eyes
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    k = gap / math.hypot(x2 - x1, y2 - y1)
    big = src.resize((max(1, round(src.width * k)), max(1, round(src.height * k))), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(big, (round(target[0] - cx * k), round(target[1] - cy * k)), big)
    return out


def main(names):
    for name in names:
        f = FACES[name]
        art = os.path.join(PROJ, 'actors', name, 'Artwork')
        src = Image.open(os.path.join(PROJ, f['src']) if f['src'].startswith('tools/') else os.path.join(art, f['src'])).convert('RGBA')
        for fn, spec in f['write'].items():
            im = face_crop(src, f['eyes'], spec['size'], spec['eyes'], spec['gap'])
            im.save(os.path.join(art, fn))
            print('wrote actors/%s/Artwork/%s' % (name, fn))


if __name__ == '__main__':
    main(sys.argv[1:] or list(FACES))
