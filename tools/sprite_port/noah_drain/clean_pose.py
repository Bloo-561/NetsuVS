"""Remove the energy (beam, orb, haze, sparkles) from Tamaki's Noah drain pose, keep body + crystal arm."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

src, out, dbg = sys.argv[1], sys.argv[2], sys.argv[3]
im = np.array(Image.open(src).convert("RGBA")).astype(np.int32)
R, G, B, A = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
H, W = A.shape
V = np.maximum(np.maximum(R, G), B)

solid = A >= 250

# 1. orb in the claw: bright, pink/white (G clearly raised), inside a disk around the claw's grip
cx, cy, rad = 637, 147, 58
yy, xx = np.mgrid[0:H, 0:W]
disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= rad ** 2
orb = disk & (G > 85) & (V > 170)
# grow a little into its own halo (still bright-ish, purple, not outline-dark)
orb = ndi.binary_dilation(orb, iterations=2) & disk & (V > 120) & (G > 55)
solid &= ~orb
# the open space inside the claw: clear what's left of the orb's swirl (anything not dark outline)
from PIL import ImageDraw
poly = Image.new("L", (W, H), 0)
ImageDraw.Draw(poly).polygon([(597, 112), (640, 108), (684, 120), (684, 172), (640, 184), (600, 182), (595, 150)], fill=255)
inner = (np.array(poly) > 0) & (V > 75)
solid &= ~inner
orb |= inner

# 2. keep only the big connected shapes (body + crystal arm); the beam and sparkles are separate pieces
lab, n = ndi.label(solid, structure=np.ones((3, 3)))
sizes = ndi.sum(solid, lab, range(1, n + 1))
keep_ids = [int(np.argmax(sizes)) + 1]   # body + crystal arm only (the beam core is the 2nd biggest piece)
keep = np.isin(lab, keep_ids)
print("components", n, "kept sizes", sorted([int(sizes[i - 1]) for i in keep_ids], reverse=True))

# fill pinholes inside kept shapes that were opaque before (not the orb hole)
filled = ndi.binary_fill_holes(keep) & (A >= 250) & ~orb
keep |= filled

# 3. anti-aliased rim: semi-transparent pixels touching the kept art, unless they are glow-coloured
near = ndi.binary_dilation(keep, iterations=2) & ~keep & (A > 0)
purple_glow = (B > G + 40) & (R > G + 15) & (V > 110)
rim = near & ~purple_glow & ~orb

alpha = np.where(keep, A, 0)
alpha = np.where(rim, A, alpha)
# soften the cut edge where glow was removed next to the arm: 1px feather
edge = keep & ~ndi.binary_erosion(keep, iterations=1)
cut = edge & ndi.binary_dilation(near & purple_glow, iterations=1)
alpha = np.where(cut, (alpha * 0.6).astype(np.int32), alpha)

res = im.copy()
# 4. the orb's purple rim light on the coat / hood (not the crystal arm, not the hair streak) -> neutral rim light
coat = ((yy > 240) & (xx > 598)) | (yy > 430)
hair = (xx > 835) & (yy < 450)
spill = coat & ~hair & (B > G + 25) & (R > G + 8) & (alpha > 0)
Y = (0.30 * R + 0.59 * G + 0.11 * B)
lum = np.clip(Y * 1.15, 0, 255)
for ch, k in ((0, 0.97), (1, 0.95), (2, 1.08)):
    res[..., ch] = np.where(spill, np.clip(lum * k, 0, 255), res[..., ch])
print("spill px", int(spill.sum()))
res[..., 3] = alpha
res[alpha == 0, :3] = 0
img = Image.fromarray(res.astype(np.uint8), "RGBA")
bb = img.getchannel("A").point(lambda v: 255 if v > 0 else 0).getbbox()
print("bbox", bb)
img.save(out)

bg = Image.new("RGBA", img.size, (60, 160, 60, 255))
Image.alpha_composite(bg, img).save(dbg)
