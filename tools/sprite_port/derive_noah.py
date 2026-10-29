"""NOAH: pictures made from his drawings by script (Oct 25 evening), into tools/sprite_port/derived/noah/.

    python derive_noah.py

* The standing normals (Normals/Standing/*_Active.png) were cut from one sheet: 5C's devil fist runs past its
  canvas into 6C's (6C has the fist tip at its left edge), and 5A's front boot tip sits at 5B's left edge. The bits
  that aren't the canvas's own figure go back where they belong (5C / 5A get a wider canvas); the sheet's labels
  under the feet are cleared.
* The crouching normals carry a "2A" / "2B" / "2C" label under the feet: cleared.
"""
import os, sys
import numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import cfg, source_root
OUT = os.path.join(HERE, 'derived', 'noah')

def comps(a, min_area=40):
    n, lab, st, _ = cv2.connectedComponentsWithStats((a[..., 3] > 10).astype(np.uint8), 8)
    big = 1 + int(np.argmax(st[1:, 4])) if n > 1 else 0
    return lab, st, big

def main():
    root = source_root(cfg('noah')); os.makedirs(OUT, exist_ok=True)
    S = os.path.join(root, 'Noah_Complete', 'Normals', 'Standing')
    load = lambda f: np.array(Image.open(os.path.join(S, f)).convert('RGBA'))
    a5, b5, c5, d6 = load('5A_Active.png'), load('5B_Active.png'), load('5C_Active.png'), load('6C_Active.png')
    def strays(a, xmax):
        """pixels left of xmax that aren't part of the canvas's main figure"""
        lab, st, big = comps(a)
        m = (lab != big) & (lab != 0)
        m[:, xmax:] = False
        return m
    def move(src, dst, xmax):
        m = strays(src, xmax)
        h, w = dst.shape[:2]
        out = np.zeros((h, w + xmax, 4), np.uint8); out[:, :w] = dst
        piece = np.zeros_like(src); piece[m] = src[m]
        out[:, w:w + xmax] = np.maximum(out[:, w:w + xmax], piece[:, :xmax])
        src[m] = 0
        return out
    c5w = move(d6, c5, 110)    # 5C's fist tip from 6C's canvas
    a5w = move(b5, a5, 40)     # 5A's boot tip from 5B's canvas
    for img in (a5w, b5, c5w, d6):
        img[689:] = 0          # the sheet's labels under the feet
    for name, img in [('5A_Active.png', a5w), ('5B_Active.png', b5), ('5C_Active.png', c5w), ('6C_Active.png', d6)]:
        Image.fromarray(img).save(os.path.join(OUT, name)); print('wrote derived/noah/' + name, img.shape[1::-1])
    C = os.path.join(root, 'Noah_Complete', 'Normals', 'Crouching')
    for f in ('2A_Active.png', '2B_Active.png', '2C_Active.png'):
        a = np.array(Image.open(os.path.join(C, f)).convert('RGBA')); a[628:] = 0
        Image.fromarray(a).save(os.path.join(OUT, f)); print('wrote derived/noah/' + f)

if __name__ == '__main__':
    main()
