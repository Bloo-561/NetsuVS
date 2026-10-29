"""FIGHTER ARTWORK: makes the menu / HUD / cut-in pictures a fighter needs from the drawings.

    python make_artwork.py leticia

Reads the "artwork" block of manifests/<char>.json:
    "artwork": {"name": "Leticia",
                "icon": "<drawing: head-and-shoulders, square>",
                "fullbody": "<drawing: full body, select screen>",
                "cutin_ex": "<drawing: EX cut-in>",
                "victory": "<drawing: win screen pose>",
                "hud_eyes": [x, y], "hud_size": 1000}       (in the icon drawing's pixels)
Writes actors/<char>/Artwork/:
    <Name>_Select_Icon.png      the icon as drawn
    <Name>_Select_Portrait.png  840x840 icon (Profile -> Portrait, character select)
    <Name>_Select_FullBody.png  full body trimmed, 1500 tall (Profile -> Render, character select)
    CutIn_Super.png             same picture, slides in for supers (battle_hud/netsu_cut_in.gd)
    CutIn_EX.png                the EX cut-in trimmed (EX banner)
    HUD_Portrait.png            512x512, eyes in the middle (battle HUD corner)
    <Name>_WinRender.png        victory pose trimmed (Profile -> VictoryRender, win screen)
    <Name>_Icon_Small.png       160x160 (Profile -> OnlineIcon)
Existing files are overwritten (they are made from the drawings; edit the drawings or this block).
"""
import os, sys, json
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from analyze import cfg, source_root

def trim(im, pad=0.03):
    bb = im.getbbox(); im = im.crop(bb)
    p = int(round(max(im.size) * pad))
    out = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0)); out.paste(im, (p, p)); return out

def to_height(im, h):
    k = h / im.height; return im.resize((max(1, round(im.width * k)), h), Image.LANCZOS)

def main(char):
    c = cfg(char); root = source_root(c); a = c['artwork']; name = a['name']
    out = os.path.join(PROJ, 'actors', char, 'Artwork'); os.makedirs(out, exist_ok=True)
    load = lambda k: Image.open(os.path.join(HERE, a[k]) if a[k].startswith('derived/') else os.path.join(root, a[k])).convert('RGBA')   # derived/ = made by a script (Noah)
    made = []
    def save(im, fn): im.save(os.path.join(out, fn)); made.append('%s %dx%d' % (fn, im.width, im.height))
    icon = load('icon')
    save(icon, '%s_Select_Icon.png' % name)
    save(icon.resize((840, 840), Image.LANCZOS), '%s_Select_Portrait.png' % name)
    save(icon.resize((160, 160), Image.LANCZOS), '%s_Icon_Small.png' % name)
    ex, ey = a['hud_eyes']; s = a.get('hud_size', 1000)
    sq = Image.new('RGBA', (s, s), (0, 0, 0, 0)); sq.paste(icon, (s // 2 - ex, s // 2 - ey))
    save(sq.resize((512, 512), Image.LANCZOS), 'HUD_Portrait.png')
    body = to_height(trim(load('fullbody')), 1500)
    save(body, '%s_Select_FullBody.png' % name); save(body, 'CutIn_Super.png')
    save(trim(load('cutin_ex'), 0.0), 'CutIn_EX.png')
    # "victory_canvas": true keeps the drawing's canvas (a picture laid out for the win screen, e.g. Noah's landscape pose)
    vic = load('victory') if a.get('victory_canvas') else trim(load('victory'))
    save(to_height(vic, 1500), '%s_WinRender.png' % name)
    for m in made: print('wrote Artwork/' + m)

if __name__ == '__main__':
    main(sys.argv[1])
