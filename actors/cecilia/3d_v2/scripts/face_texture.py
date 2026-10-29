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
import math
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


def eye_extents():
    """front-crop u of each eye's inner and outer end (the traced outlines'
    horizontal extent): {"R": (u_inner, u_outer), "L": (...)}; R = her right
    eye = screen left in the front view"""
    out = {}
    for name, poly in zip(("R", "L"), EYE_POLYS):
        xs = [PANEL_U0 + (p[0] - PANEL_BOX[0]) / PANEL_SCALE for p in poly]
        ys = [PANEL_V0 + (p[1] - PANEL_BOX[1]) / PANEL_SCALE for p in poly]
        inner, outer = (max(xs), min(xs)) if name == "R" else (min(xs), max(xs))
        out[name] = dict(inner=inner, outer=outer, top=min(ys), bottom=max(ys))
    return out


def build():
    """-> combined texture, base (skin, blush, nose, mouth), eyes RGBA
    (colour + coverage, for the view-dependent eyes of gg_face), skin colour"""
    panel_full = imgio.load(os.path.join(cfg.REFS, "cecilia_ref_detail_eyes.png"), channels=3).astype(np.float32)
    x0, y0, x1, y1 = PANEL_BOX
    panel = panel_full[y0:y1, x0:x1]
    skin = skin_colour(panel)
    clean, hair, skinlike = clean_panel(panel, skin)
    U, V = grid()
    base = np.empty(U.shape + (3,), np.float32)
    base[:] = skin
    # blush under the eyes (under the panel's own content)
    for c, rad in BLUSH:
        draw_ellipse(base, U, V, c, rad, BLUSH_RGB, BLUSH_A)
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
    draw_ellipse(base, U, V, NOSE, (NOSE_R, NOSE_R * 1.3), NOSE_RGB, 0.9)
    draw_polyline(base, U, V, MOUTH, MOUTH_W, MOUTH_RGB, 0.95)
    tex = base * (1 - w[..., None]) + samp * w[..., None]
    # eyes layer: the panel's colour (skin where flattened, so filtering at the
    # coverage edge never pulls in a foreign colour) + coverage as alpha
    eyes_rgb = np.where(inside[..., None], samp, skin)
    eyes = np.concatenate([eyes_rgb, 255.0 * w[..., None]], axis=-1)
    return np.clip(tex, 0, 255), np.clip(base, 0, 255), np.clip(eyes, 0, 255), skin, (clean, hair, skinlike, w)


# ----------------------------------------------------------------------------- moving irises (Milestone 7)
# The eyes layer split in three, so the eye bones can move the irises:
#   frame  the eyes with each iris painted over in the sclera's own colour
#          (row by row, so the grey shadow under the lid stays)
#   iris   each iris as a full ellipse (fitted to its visible edge; the part
#          hidden under the lashes is filled down from the visible iris)
#   open   where the eyeball shows (sclera + visible iris): the moved iris is
#          clipped to it, so it slides under the lids and lashes
# At rest, frame + iris x open = the eyes layer.
IRIS_TOP_SKIP = 0.30                 # top share of the visible iris left out of the ellipse fit (lashes cut it)


def _shift(m, dy, dx):
    out = np.zeros_like(m)
    H, W = m.shape
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    out[yd, xd] = m[ys, xs]
    return out


def _dilate(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= _shift(m, dy, dx)
    return out


def _erode(m, r=1):
    return ~_dilate(~m, r)


def _component(mask, seed):
    """4-connected region of mask containing seed (y, x)"""
    out = np.zeros_like(mask)
    if not mask[seed]:
        return out
    stack = [seed]
    H, W = mask.shape
    out[seed] = True
    while stack:
        y, x = stack.pop()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not out[yy, xx]:
                out[yy, xx] = True
                stack.append((yy, xx))
    return out


def _classes(p):
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    lum = p.mean(axis=2)
    maroon = (b > g + 8) & (r > 55) & (r < 205) & (lum < 150)           # the iris's red-violet (B > G)
    gold = (r > 225) & (g > 190) & (b < 205) & (g - b > 18)              # its gold lower half and pupil
    lash = (lum < 125) & (b <= g + 4)                                     # lashes, lid lines (brown, B <= G)
    sclera = (lum > 165) & ((r - b) < 24)                                 # white / grey-blue, not skin
    return maroon, gold, lash, sclera


def fit_iris(iris_px):
    """upright ellipse (cx, cy, a, b) from a mask of visible iris pixels,
    fitted to its half-widths row by row below the lash line"""
    ys = np.nonzero(iris_px.any(axis=1))[0]
    y0, y1 = int(ys.min()), int(ys.max())
    rows, hw, mid = [], [], []
    for y in range(y0, y1 + 1):
        xs = np.nonzero(iris_px[y])[0]
        if len(xs) < 2:
            continue
        rows.append(y + 0.5)
        hw.append(0.5 * (xs.max() - xs.min() + 1))
        mid.append(0.5 * (xs.max() + xs.min() + 1))
    rows, hw, mid = np.array(rows), np.array(hw), np.array(mid)
    use = rows >= y0 + IRIS_TOP_SKIP * (y1 - y0)
    best = None
    for cy in np.arange(y0, y1 + 1, 0.5):
        for bb in np.arange(0.35 * (y1 - y0), 1.2 * (y1 - y0), 0.5):
            t = np.clip(1.0 - ((rows[use] - cy) / bb) ** 2, 0.0, None)
            s = np.sqrt(t)
            if s.sum() < 1e-6:
                continue
            a = float((s * hw[use]).sum() / (s * s).sum())          # least squares a for this (cy, b)
            err = float(((a * s - hw[use]) ** 2).sum())
            if best is None or err < best[0]:
                best = (err, cy, bb, a)
    _, cy, bb, a = best
    wide = hw >= 0.8 * hw.max()
    cx = float(mid[wide].mean())
    return dict(cx=cx, cy=float(cy), a=float(a), b=float(bb), rms=float(math.sqrt(best[0] / max(use.sum(), 1))))


IRIS_RIM = 4.5                       # panel px added round the fitted colour ellipse: the iris's own dark outline


def _lid_lines(band, lower, inside, cols, max_run=16):
    """over the iris's columns: the bottom of the upper lash band (first
    `band` run from the top) and the top of the lower lash line (first
    `lower` run from the bottom), each fitted with a parabola across the
    columns (the lids are smooth curves; a column where the iris's own
    outline runs into the lashes is left out of the fit)"""
    h, w = band.shape
    pts_t, pts_b = [], []
    for x in cols:
        col = np.nonzero(inside[:, x])[0]
        if len(col) < 3:
            continue
        y0, ye = col.min(), col.max()
        y = y0
        while y <= ye and not band[y, x]:          # skin above the lashes
            y += 1
        if y <= ye:
            ys = y
            while y <= ye and band[y, x]:          # the lash band
                y += 1
            if 2 <= y - ys <= max_run:
                pts_t.append((x + 0.5, y))
        y = ye
        while y >= y0 and not lower[y, x]:
            y -= 1
        if y >= y0:
            ys = y
            while y >= y0 and lower[y, x]:
                y -= 1
            if 1 <= ys - y <= max_run:
                pts_b.append((x + 0.5, y + 1))
    xs = np.arange(w) + 0.5
    def fit(pts, default):
        if len(pts) < 5:
            return np.full(w, default)
        a = np.array(pts, float)
        c = np.polyfit(a[:, 0], a[:, 1], 2)
        return np.polyval(c, xs)
    return fit(pts_t, 0.0), fit(pts_b, float(h))


def eye_layers(clean):
    """panel-space layers from the cleaned panel: frame RGB, iris RGBA,
    opening (0..1), and the fitted ellipses (panel px, origin = PANEL_BOX)"""
    p = clean.astype(np.float32)
    h, w = p.shape[:2]
    maroon, gold, lash, sclera = _classes(p)
    yy, xx = np.mgrid[0:h, 0:w]
    xc, yc = xx + 0.5, yy + 0.5
    frame = p.copy()
    iris_rgb = np.zeros_like(p)
    iris_a = np.zeros((h, w), np.float32)
    opening = np.zeros((h, w), np.float32)
    fits = []
    for poly in EYE_POLYS:
        inside = poly_mask(h, w, poly, PANEL_BOX[0], PANEL_BOX[1])
        vis = (maroon | gold) & inside
        ys, xs = np.nonzero(vis)
        seed = (int(np.median(ys)), int(np.median(xs)))
        blob = _component(_dilate(vis, 1), seed) & inside
        f = fit_iris(blob)
        f["a"] += IRIS_RIM
        f["b"] += IRIS_RIM
        fits.append(f)
        rho = np.sqrt(((xc - f["cx"]) / f["a"]) ** 2 + ((yc - f["cy"]) / f["b"]) ** 2)
        E = rho <= 1.0
        ell_a = np.clip(0.5 + (1.0 - rho) * min(f["a"], f["b"]), 0.0, 1.0)
        band = _dilate(_erode(lash & inside, 2), 2)                   # thick lash band only (thin outlines drop out)
        cols = np.unique(np.nonzero(E & inside)[1])
        top, bot = _lid_lines(band, lash & inside, inside, cols)
        bot[:] = h          # no lower cut: the iris's own dark rim sits on the lower lid line (it moves with the iris)
        between = (yc >= top[None, :]) & (yc < bot[None, :])          # below the upper lashes, above the lower line
        V = E & inside & between                                       # visible iris (with its outline)
        S = inside & ~E & sclera
        O = _component(_dilate(V | S, 1) & inside & (between | ~E), (int(f["cy"]), int(f["cx"])))
        O = _erode(_dilate(O, 2), 2) & inside | V
        # sclera colour per row, from this eye's visible sclera
        rows_c = {}
        for y in range(h):
            m = S[y]
            if m.sum() >= 2:
                rows_c[y] = np.median(p[y][m], axis=0)
        ks = np.array(sorted(rows_c))
        for y in np.unique(np.nonzero(V)[0]):
            k = ks[np.argmin(np.abs(ks - y))]
            frame[y][V[y]] = rows_c[k]
        # iris colour: visible pixels as drawn; hidden ones filled from the nearest visible one in the column
        col = np.where(V[..., None], p, 0.0)
        fill = E & ~V
        core = V & (maroon | gold)
        mean_iris = p[V & maroon].mean(axis=0)
        for x in np.unique(np.nonzero(E)[1]):
            ysV = np.nonzero(core[:, x])[0]
            for y in np.nonzero(fill[:, x])[0]:
                col[y, x] = p[ysV[np.argmin(np.abs(ysV - y))], x] if len(ysV) else mean_iris
        ring = (ell_a > 0) & ~E
        col[ring] = col[ring] * 0 + mean_iris
        sel = ell_a > 0
        iris_rgb[sel] = col[sel]
        iris_a = np.maximum(iris_a, ell_a * inside)
        opening = np.maximum(opening, O.astype(np.float32))
    iris_rgb[iris_a <= 0] = iris_rgb[iris_a > 0.99].mean(axis=0)
    return frame, iris_rgb, iris_a, opening, fits


def eye_textures(clean, w_cover):
    """map the panel layers into face-texture space (as build() maps the
    panel): frame RGBA (coverage = the eyes layer's), iris RGBA, opening L"""
    frame, iris_rgb, iris_a, opening, fits = eye_layers(clean)
    U, V = grid()
    px = (U - PANEL_U0) * PANEL_SCALE
    py = (V - PANEL_V0) * PANEL_SCALE
    inside = (px >= 0) & (py >= 0) & (px < clean.shape[1]) & (py < clean.shape[0])
    skin = clean[0, 0]
    fr = np.where(inside[..., None], bilinear(frame, px, py), skin)
    ir = bilinear(iris_rgb, px, py)
    ia = bilinear(iris_a[..., None], px, py)[..., 0] * inside
    op = bilinear(opening[..., None], px, py)[..., 0] * inside
    frame_t = np.concatenate([fr, 255.0 * w_cover[..., None]], axis=-1)
    iris_t = np.concatenate([ir, 255.0 * ia[..., None]], axis=-1)
    # fitted ellipses in front-crop coordinates (sheet px)
    fits_f = [dict(cu=PANEL_U0 + (f["cx"]) / PANEL_SCALE, cv=PANEL_V0 + (f["cy"]) / PANEL_SCALE,
                   a=f["a"] / PANEL_SCALE, b=f["b"] / PANEL_SCALE, rms_panel_px=f["rms"]) for f in fits]
    return np.clip(frame_t, 0, 255), np.clip(iris_t, 0, 255), np.clip(255.0 * op, 0, 255), fits_f


def check_image(tex):
    """texture next to the sheet's face at the same scale (for review)"""
    front = imgio.load(cfg.ref_path("front"), channels=3).astype(np.float32)
    U, V = grid()
    ref = bilinear(front, U, V)
    gap = np.full((tex.shape[0], 12, 3), 255, np.float32)
    return np.concatenate([ref, gap, tex, gap, 0.5 * ref + 0.5 * tex], axis=1)


def main(irises=True):
    os.makedirs(OUT_DIR, exist_ok=True)
    tex, base, eyes, skin, extra = build()
    imgio.save(tex_path(), (tex + 0.5).astype(np.uint8))
    imgio.save(tex_path("face_base.png"), (base + 0.5).astype(np.uint8))
    imgio.save(tex_path("face_eyes.png"), (eyes + 0.5).astype(np.uint8))
    imgio.save(tex_path("face_tex_check.png"), (check_image(tex) + 0.5).astype(np.uint8))
    out = dict(path=tex_path(), size=tex.shape[:2], skin=[round(float(c), 1) for c in skin],
               eyes={k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in eye_extents().items()})
    if irises:
        clean, w = extra[0], extra[3]
        frame_t, iris_t, open_t, fits = eye_textures(clean, w)
        imgio.save(tex_path("face_eye_frame.png"), (frame_t + 0.5).astype(np.uint8))
        imgio.save(tex_path("face_eye_iris.png"), (iris_t + 0.5).astype(np.uint8))
        imgio.save(tex_path("face_eye_open.png"), np.repeat((open_t + 0.5).astype(np.uint8)[..., None], 3, axis=-1))
        out["iris_fits"] = [{k: round(v, 3) for k, v in f.items()} for f in fits]
    return out


if __name__ == "__main__":
    print(main())
