"""GG-style face texture (numpy only; runs in Blender or plain Python).

The turnaround's face is about 60 px wide, too blurry to carry a cel-shaded
face. The eyes come instead from the sheet's high-resolution eyes panel
(refs/cecilia_ref_detail_eyes.png, about 6.3x the turnaround's scale),
registered onto the front view; everything else is flat base skin plus the
sheet's nose and mouth redrawn as clean anti-aliased lines at their traced
positions. Shading is left to the toon shader.

Texture space = front-view image coordinates (u, v) of the front crop,
TEX_SCALE texture pixels per sheet pixel, covering U_RANGE x V_RANGE; the
face mesh gets matching front-planar UVs (build_head.face_mesh).

Panel registration (normalised cross-correlation of the panel, box-filtered
to the turnaround's scale, against the front crop, scale and sub-pixel offset
searched; NCC 0.82): panel pixel (px, py) <-> front
  u = PANEL_U0 + (px - PANEL_BOX[0]) / PANEL_SCALE
  v = PANEL_V0 + (py - PANEL_BOX[1]) / PANEL_SCALE
Writes refs/face/face_tex.png and refs/face/face_tex_check.png (the texture
next to the sheet's face at the same scale).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\face_texture.py", run_name="__main__")
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

TEX_SCALE = 8                       # texture px per sheet px
U_RANGE = (226.0, 314.0)            # front-crop columns covered (face +-, generous)
V_RANGE = (70.0, 152.0)             # front-crop rows covered (forehead under the bangs .. below the chin)
PANEL_BOX = (8, 30, 440, 200)       # panel interior used (inside its frame and title)
PANEL_SCALE = 6.34                  # panel px per sheet px
PANEL_U0, PANEL_V0 = 236.875, 91.25  # front coords of the panel box's top-left corner
FEATHER = 2.0                       # sheet px over which the panel fades into the base skin
OUT_DIR = os.path.join(cfg.REFS, "face")

# features traced from the front crop (sheet px)
MOUTH = [(263.8, 126.7), (265.2, 127.6), (267.0, 128.25), (268.8, 128.0), (270.0, 127.45),
         (271.2, 128.0), (273.0, 128.25), (274.8, 127.6), (276.2, 126.7)]   # cat-mouth smile
MOUTH_W = 0.42                      # line width, sheet px
MOUTH_RGB = (150, 88, 84)
NOSE = (270.05, 118.6)              # small nose dot
NOSE_R = 0.55
NOSE_RGB = (222, 168, 158)
BLUSH = [((247.5, 117.5), (6.5, 2.2)), ((292.5, 117.5), (6.5, 2.2))]       # centre, radii (sheet px)
BLUSH_RGB = (247, 190, 185)
BLUSH_A = 0.35


def tex_path(name="face_tex.png"):
    return os.path.join(OUT_DIR, name)


def grid():
    """front coords (u, v) at the centre of every texture pixel"""
    w = int(round((U_RANGE[1] - U_RANGE[0]) * TEX_SCALE))
    h = int(round((V_RANGE[1] - V_RANGE[0]) * TEX_SCALE))
    u = U_RANGE[0] + (np.arange(w) + 0.5) / TEX_SCALE
    v = V_RANGE[0] + (np.arange(h) + 0.5) / TEX_SCALE
    return np.meshgrid(u, v)


def bilinear(img, x, y):
    H, W = img.shape[:2]
    x = np.clip(x - 0.5, 0, W - 1.001)
    y = np.clip(y - 0.5, 0, H - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) +
            img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def skin_colour(panel):
    """base skin: median of the panel's light warm pixels"""
    r, g, b = panel[..., 0], panel[..., 1], panel[..., 2]
    m = (r > 225) & (g > 195) & (b > 180) & (r - b > 12) & (r - b < 45)
    return np.median(panel[m], axis=0)


# eye outlines traced on the eyes panel (panel px): lashes, lid crease, white,
# iris and lower lashes inside; hair locks, brows and skin outside
EYE_POLYS = [
    [(25, 110), (26, 99), (40, 84), (60, 77), (85, 73), (110, 73), (136, 81), (156, 96), (161, 112),
     (157, 128), (150, 145), (138, 160), (125, 171), (100, 173), (80, 171), (64, 162), (51, 150),
     (39, 136), (29, 121)],
    [(277, 121), (283, 106), (300, 91), (320, 81), (345, 75), (370, 75), (393, 83), (408, 95),
     (410, 105), (404, 121), (396, 140), (381, 158), (361, 169), (335, 173), (311, 171), (297, 161),
     (287, 146), (280, 133)],
]


def poly_mask(h, w, poly, ox=0.0, oy=0.0):
    """even-odd point-in-polygon for every pixel centre (polygon in panel px,
    image origin at (ox, oy) in the same units)"""
    y, x = np.mgrid[0:h, 0:w]
    x = x + 0.5 + ox
    y = y + 0.5 + oy
    inside = np.zeros((h, w), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cross = ((y0 > y) != (y1 > y))
        xint = x0 + (y - y0) * (x1 - x0) / ((y1 - y0) if y1 != y0 else 1e-9)
        inside ^= cross & (x < xint)
    return inside


def clean_panel(panel, skin):
    """keep the eyes (traced outlines), flatten everything else to the base
    skin; inside the outlines, skin-like pixels (the sheet's soft shading)
    are flattened too"""
    p = panel.astype(np.float32)
    h, w = p.shape[:2]
    eyes = np.zeros((h, w), bool)
    for poly in EYE_POLYS:
        eyes |= poly_mask(h, w, poly, PANEL_BOX[0], PANEL_BOX[1])
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    lum = p.mean(axis=2)
    # skin: light, warm, and not yellow (the iris's gold bottom and highlight stay)
    skinlike = (lum > 200) & (r - b > 10) & (r - b < 45) & (r >= g) & (b > 0.84 * r)
    out = p.copy()
    out[~eyes | skinlike] = skin
    return out, eyes, skinlike


def draw_polyline(img, U, V, pts, width, rgb, alpha=1.0):
    """anti-aliased polyline (width in sheet px) composited onto img"""
    a = np.zeros(U.shape, np.float32)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip(((U - x0) * dx + (V - y0) * dy) / max(L2, 1e-9), 0, 1)
        d = np.hypot(U - (x0 + t * dx), V - (y0 + t * dy)) * TEX_SCALE      # texture px
        a = np.maximum(a, np.clip(width * TEX_SCALE / 2.0 + 0.5 - d, 0, 1))
    # taper the two ends
    for (x, y) in (pts[0], pts[-1]):
        d = np.hypot(U - x, V - y)
        a *= np.clip(d / 0.8, 0.35, 1.0)
    a = a[..., None] * alpha
    img[:] = img * (1 - a) + np.array(rgb, np.float32) * a


def draw_ellipse(img, U, V, c, rad, rgb, alpha):
    d = np.hypot((U - c[0]) / rad[0], (V - c[1]) / rad[1])
    a = np.clip(1.0 - d, 0, 1) ** 1.2 * alpha
    a = a[..., None]
    img[:] = img * (1 - a) + np.array(rgb, np.float32) * a


def build():
    panel_full = imgio.load(os.path.join(cfg.REFS, "cecilia_ref_detail_eyes.png"), channels=3).astype(np.float32)
    x0, y0, x1, y1 = PANEL_BOX
    panel = panel_full[y0:y1, x0:x1]
    skin = skin_colour(panel)
    clean, hair, skinlike = clean_panel(panel, skin)
    U, V = grid()
    tex = np.empty(U.shape + (3,), np.float32)
    tex[:] = skin
    # blush under the eyes (under the panel's own content)
    for c, rad in BLUSH:
        draw_ellipse(tex, U, V, c, rad, BLUSH_RGB, BLUSH_A)
    # the panel, mapped into texture space, faded in over FEATHER at its border
    px = (U - PANEL_U0) * PANEL_SCALE
    py = (V - PANEL_V0) * PANEL_SCALE
    inside = (px >= 0) & (py >= 0) & (px < panel.shape[1]) & (py < panel.shape[0])
    samp = bilinear(clean, px, py)
    du = np.minimum(U - PANEL_U0, PANEL_U0 + panel.shape[1] / PANEL_SCALE - U)
    dv = np.minimum(V - PANEL_V0, PANEL_V0 + panel.shape[0] / PANEL_SCALE - V)
    w = np.clip(np.minimum(du, dv) / FEATHER, 0, 1) * inside
    # only where the panel differs from flat skin (keeps the blush showing through)
    diff = np.abs(samp - skin).max(axis=-1)
    w = w * np.clip(diff / 18.0, 0, 1)
    tex = tex * (1 - w[..., None]) + samp * w[..., None]
    draw_ellipse(tex, U, V, NOSE, (NOSE_R, NOSE_R * 1.3), NOSE_RGB, 0.9)
    draw_polyline(tex, U, V, MOUTH, MOUTH_W, MOUTH_RGB, 0.95)
    return np.clip(tex, 0, 255), skin, (clean, hair, skinlike)


def check_image(tex):
    """texture next to the sheet's face at the same scale (for review)"""
    front = imgio.load(cfg.ref_path("front"), channels=3).astype(np.float32)
    U, V = grid()
    ref = bilinear(front, U, V)
    gap = np.full((tex.shape[0], 12, 3), 255, np.float32)
    return np.concatenate([ref, gap, tex, gap, 0.5 * ref + 0.5 * tex], axis=1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tex, skin, _ = build()
    imgio.save(tex_path(), (tex + 0.5).astype(np.uint8))
    imgio.save(tex_path("face_tex_check.png"), (check_image(tex) + 0.5).astype(np.uint8))
    return dict(path=tex_path(), size=tex.shape[:2], skin=[round(float(c), 1) for c in skin])


if __name__ == "__main__":
    print(main())
