"""Noah's select portrait (drawn on black): the black around him made transparent (flood from the edges)."""
import sys, numpy as np, cv2
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
im = np.array(Image.open(src).convert('RGB')).astype(np.int16)
mx = im.max(axis=2)
bg = (mx <= int(sys.argv[3]) if len(sys.argv) > 3 else mx <= 12).astype(np.uint8)
n, lab = cv2.connectedComponents(bg, connectivity=4)
edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
outside = np.isin(lab, list(edge)) & (bg > 0)
# soft edge: alpha ramps with brightness in a 3px band next to the outside
near = cv2.dilate(outside.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
alpha = np.where(outside, 0, 255).astype(np.float32)
band = near & ~outside
alpha[band] = np.clip((mx[band] - 4) / 30.0, 0, 1) * 255
a = alpha.astype(np.uint8)
rgba = np.dstack([im.astype(np.uint8), a])
Image.fromarray(rgba, 'RGBA').save(dst)
print('transparent px', int(outside.sum()), 'of', outside.size)
