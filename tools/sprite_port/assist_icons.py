"""ASSIST ICONS (Oct 29 2026): the assists' face pictures (select-screen assist card, VS screen, battle HUD assist gauge)
cut from their Netsu iF card art (E:/Netsu Projects/Netsu iF Beta/img/CGC/art, copies kept in derived/assist_icons/).

    python tools/sprite_port/assist_icons.py           # all four
    python tools/sprite_port/assist_icons.py harie     # one

CROPS: card picture and the square cut from it (x, y, side) in card pixels (cards are 224x384; the title bar ends at
y ~72 and the text box starts at y ~270, keep the square between them). Written as actors/assists/<name>/Artwork/Icon.png
(256x256). assists.py keeps an existing Icon.png unless run with --force. The previous icons: derived/assist_icons/old_icons/.
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(HERE, 'derived', 'assist_icons')

# Oct 29 (later): switched to the full-body standing art in derived/assist_icons/full/ (transparent PNGs, ~1040x1510);
# each square is centred on the face and takes in head + shoulders, so the picture sits centred in the select-screen
# tile, the locked assist card, the VS screen chip and the HUD hexagon. The old card crops are kept below.
CROPS = {
    'mary':  ('full/mary.png',  (310, 25, 340)),
    'adin':  ('full/adin.png',  (345, 15, 340)),
    'eren':  ('full/eren.png',  (360, 10, 320)),
    'harie': ('full/harie.png', (290, 20, 340)),
}
CARD_CROPS = {
    'mary':  ('GentleMelody.png',      (50, 77, 134)),   # violin
    'adin':  ('GuardStance.png',       (38, 84, 168)),   # shield
    'eren':  ('ThinkingofHer.png',     (30, 77, 124)),
    'harie': ('EnduranceTraining.png', (40, 77, 108)),   # swimsuit
}

def make(k):
    f, (x, y, s) = CROPS[k]
    im = Image.open(os.path.join(SRC, f)).convert('RGBA').crop((x, y, x + s, y + s)).resize((256, 256), Image.LANCZOS)
    out = os.path.join(PROJ, 'actors', 'assists', k, 'Artwork', 'Icon.png')
    im.save(out); print('wrote', os.path.relpath(out, PROJ))

if __name__ == '__main__':
    for k in (sys.argv[1:] or CROPS): make(k)
