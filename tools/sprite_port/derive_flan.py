"""FLAN'S DERIVED PICTURES (Oct 24): pictures made by script from her drawings, used by manifests/flan.json
as "derived/flan/...".

    python derive_flan.py

  radiant_burst.png   09_236236_Super/.../Radiant_Burst.png repaired: the file on the PC is damaged (the picture
                      stops at row 810 of 1024, everything below is empty). The burst is a fan around a
                      horizontal axis (y = 512), so the missing bottom is the top half mirrored, blended into
                      what is left of the real bottom. Replace the drawing with an undamaged copy and run this
                      again (it then only copies the drawing).
"""
import os, sys
import numpy as np
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import cfg, source_root

OUT = os.path.join(HERE, 'derived', 'flan')
BURST = 'Flan_All_Sprites/09_236236_Super/Flan_236236_Locked/PNG/Radiant_Burst.png'
AXIS = 512          # the burst's horizontal axis (its bright core sits on it)
BLEND = (770, 808)  # rows where the real bottom fades into the mirrored top

def premul(a):
    f = a.astype(np.float32) / 255.0; f[..., :3] *= f[..., 3:4]; return f
def unpremul(f):
    al = f[..., 3:4]; rgb = np.where(al > 1e-5, f[..., :3] / np.maximum(al, 1e-5), 0)
    return (np.clip(np.dstack([rgb, al]), 0, 1) * 255 + 0.5).astype(np.uint8)

def radiant_burst(root):
    src = os.path.join(root, BURST)
    a = np.array(Image.open(src).convert('RGBA'))
    h = a.shape[0]
    rows = np.nonzero(a[..., 3].max(1) > 10)[0]
    last = int(rows.max())
    if last > h - 30:                       # complete picture: use it as it is
        Image.fromarray(a).save(os.path.join(OUT, 'radiant_burst.png')); return 'radiant_burst.png (drawing is complete, copied)'
    f = premul(a); out = f.copy()
    b0, b1 = BLEND; b1 = min(b1, last - 2)
    for y in range(b0, h):
        ym = 2 * AXIS - y
        mir = f[ym] if 0 <= ym < h else np.zeros_like(f[0])
        if y < b1:
            t = (y - b0) / float(b1 - b0); t = t * t * (3 - 2 * t)     # smooth fade
            out[y] = f[y] * (1 - t) + mir * t
        else:
            out[y] = mir
    Image.fromarray(unpremul(out)).save(os.path.join(OUT, 'radiant_burst.png'))
    return 'radiant_burst.png (rows %d-%d rebuilt from the mirrored top)' % (b0, h - 1)

def main():
    root = source_root(cfg('flan'))
    os.makedirs(OUT, exist_ok=True)
    print('wrote derived/flan/' + radiant_burst(root))

if __name__ == '__main__':
    main()
