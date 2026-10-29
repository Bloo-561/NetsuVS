# Depths of the Old Schoolhouse - procedural texture generator (numpy + Pillow).
#   python make_textures.py <out_dir>
# floor_tiles.png   4 x 4 m repeat (2 x 2 polished slabs), blue-grey stone with veins and dark seams
# floor_carpet.png  the ornate inlay in front of the dais (24 x 14 m): teal field, cream-gold filigree
# glyph.png         knotwork panel for the glowing pillar lanterns (white lines on black; shader colours it)
# circle.png        rune ring for the teleport circle on the dais (white on black, polar)
import sys, math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)

def vnoise_periodic(n, cells, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((cells, cells)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) / n * cells
    i0 = np.floor(t).astype(int); f = t - i0; f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells; i0 %= cells
    a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
    b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]

def fbm(n, base, octaves, seed):
    s = np.zeros((n, n), np.float32); a = 0.5; tot = 0
    for o in range(octaves):
        s += a * vnoise_periodic(n, base * 2 ** o, seed + o); tot += a; a *= 0.5
    return s / tot

def to_img(a):
    return Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

# ---------------------------------------------------------------- floor tiles
def floor_tiles(n=2048):
    rng = np.random.default_rng(3)
    base = fbm(n, 4, 6, 10)
    vein_n = fbm(n, 3, 5, 40)
    veins = np.abs(np.sin((vein_n * 9.0 + base * 3.0) * math.pi))
    veins = 1 - np.clip((veins - 0.0) / 0.10, 0, 1)                # thin bright veins
    grain = fbm(n, 64, 3, 70)
    yy, xx = np.mgrid[0:n, 0:n]
    slab = (yy // (n // 2)) * 2 + (xx // (n // 2))
    tint = np.array([[0.0, 0.0, 0.0], [0.04, 0.03, 0.02], [-0.03, -0.02, 0.0], [0.02, 0.0, -0.02]], np.float32)
    c0, c1 = hexc("#6f7f8c"), hexc("#a3b2bd")
    col = c0 + (c1 - c0) * (0.35 + 0.5 * base[..., None]) + tint[slab] * 1.0
    col += (grain[..., None] - 0.5) * 0.06
    col = col * (1 - 0.18 * veins[..., None]) + hexc("#dce6ec") * 0.18 * veins[..., None]
    # seams: dark grooves around each 2 m slab, with a thin bevel highlight
    m = n // 2; d = np.minimum(np.minimum(xx % m, m - 1 - xx % m), np.minimum(yy % m, m - 1 - yy % m))
    seam = np.clip(1 - d / 5.0, 0, 1)
    bevel = np.clip(1 - np.abs(d - 7) / 3.0, 0, 1) * 0.08
    col = col * (1 - 0.75 * seam[..., None]) + bevel[..., None]
    to_img(col).save(os.path.join(OUT, "floor_tiles.png"))

# ---------------------------------------------------------------- carpet inlay
def carpet(W=2400, H=1400, ss=2):
    w, h = W * ss, H * ss
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
    lw = int(5 * ss)
    def line(pts, width=lw):
        d.line(pts, fill=255, width=width, joint="curve")
    def spiral(cx, cy, r0, turns, dirn, start, width=lw, sx=1, sy=1):
        pts = []
        for k in range(int(60 * turns)):
            t = k / (60 * turns)
            a = start + dirn * t * turns * 2 * math.pi
            r = r0 * (1 - 0.85 * t)
            pts.append((cx + sx * r * math.cos(a), cy + sy * r * math.sin(a)))
        line(pts, width)
    def scroll(x0, y0, x1, y1, r, sx, sy, width=lw):
        """S-shaped acanthus scroll from (x0,y0) to (x1,y1) ending in curls."""
        pts = []
        for k in range(80):
            t = k / 79
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + math.sin(t * math.pi * 2) * r * 0.5 * sy
            pts.append((x, y))
        line(pts, width)
        spiral(x1, y1 - r * 0.5 * sy, r * 0.5, 1.6, sx * sy, math.pi / 2 * sy, width)
        spiral(x0, y0 + r * 0.5 * sy, r * 0.45, 1.5, -sx * sy, -math.pi / 2 * sy, width)
    # outer frame: double border with a running knot band between
    m = 40 * ss
    for off in (0, 22 * ss, 78 * ss, 100 * ss):
        d.rectangle([m + off, m + off, w - m - off, h - m - off], outline=255, width=lw)
    band0, band1 = m + 22 * ss, m + 78 * ss
    step = 56 * ss
    def knot_band(horizontal, fixed0, fixed1, a0, a1):
        mid = (fixed0 + fixed1) / 2; amp = (fixed1 - fixed0) / 2 - 8 * ss
        for ph in (0, math.pi):
            pts = []
            n = int((a1 - a0) / (2 * ss))
            for k in range(n + 1):
                a = a0 + (a1 - a0) * k / n
                o = mid + amp * math.sin((a - a0) / step * math.pi + ph)
                pts.append((a, o) if horizontal else (o, a))
            line(pts)
    knot_band(True, band0, band1, band1, w - band1); knot_band(True, h - band1, h - band0, band1, w - band1)
    knot_band(False, band0, band1, band1, h - band1); knot_band(False, w - band1, w - band0, band1, h - band1)
    # inner field: central lozenge medallion + scrolls, mirrored into the four quadrants
    cx, cy = w / 2, h / 2
    fx0, fy0 = m + 130 * ss, m + 130 * ss
    for s in (1.0, 0.82, 0.55, 0.3):
        rx, ry = (cx - fx0) * 0.42 * s, (cy - fy0) * 0.78 * s
        d.polygon([(cx - rx, cy), (cx, cy - ry), (cx + rx, cy), (cx, cy + ry)], outline=255, width=lw)
    d.ellipse([cx - 60 * ss, cy - 60 * ss, cx + 60 * ss, cy + 60 * ss], outline=255, width=lw)
    for sx in (-1, 1):
        for sy in (-1, 1):
            # scrolls flowing from the medallion tips toward the corners
            ax, ay = cx + sx * (cx - fx0) * 0.42, cy
            for k, (u, v, r) in enumerate(((0.08, 0.30, 120), (0.30, 0.55, 140), (0.55, 0.82, 110))):
                x0 = ax + sx * (cx - fx0) * 0.58 * u; x1 = ax + sx * (cx - fx0) * 0.58 * v
                y0 = cy + sy * (cy - fy0) * (0.10 + 0.25 * k); y1 = cy + sy * (cy - fy0) * (0.35 + 0.25 * k)
                scroll(x0, y0, x1, y1, r * ss, sx, sy)
            # corner fans
            ccx, ccy = (fx0 if sx < 0 else w - fx0), (fy0 if sy < 0 else h - fy0)
            for k in range(5):
                a = math.radians(10 + k * 17.5)
                ex, ey = ccx - sx * math.cos(a) * 230 * ss, ccy - sy * math.sin(a) * 230 * ss
                line([(ccx, ccy), (ex, ey)])
                spiral(ex, ey, 34 * ss, 1.3, 1 if (sx * sy) > 0 else -1, a, lw)
            a0 = {(-1, -1): 0, (1, -1): 90, (1, 1): 180, (-1, 1): 270}[(sx, sy)]
            for rr in (260, 236):
                d.arc([ccx - rr * ss, ccy - rr * ss, ccx + rr * ss, ccy + rr * ss], a0, a0 + 90, fill=255, width=lw)
            # tips of the medallion: little spiral pairs
            spiral(cx, cy + sy * (cy - fy0) * 0.78 + sy * 40 * ss, 40 * ss, 1.4, sx, 0, lw)
    # faint all-over damask behind the main ornament (the painting's inlay is densely filled)
    fa = Image.new("L", (w, h), 0); fd = ImageDraw.Draw(fa)
    sp = 150 * ss; fw = 3 * ss
    for j, y in enumerate(range(int(fy0), int(h - fy0), int(sp * 0.6))):
        for x in range(int(fx0) + (j % 2) * sp // 2, int(w - fx0), sp):
            for sgn in (-1, 1):
                pts = [(x + sgn * (12 + 40 * t) * ss, y - 26 * ss * math.sin(t * math.pi)) for t in [k / 20 for k in range(21)]]
                fd.line(pts, fill=255, width=fw)
                ex, ey = pts[-1]
                spts = [(ex + sgn * 14 * ss * (1 - t) * math.cos(t * 9), ey + 14 * ss * (1 - t) * math.sin(t * 9)) for t in [k / 30 for k in range(31)]]
                fd.line(spts, fill=255, width=fw)
            fd.ellipse([x - 5 * ss, y - 5 * ss, x + 5 * ss, y + 5 * ss], outline=255, width=fw)
    fmask = Image.new("L", (w, h), 0); ImageDraw.Draw(fmask).rectangle([fx0 - 20 * ss, fy0 - 20 * ss, w - fx0 + 20 * ss, h - fy0 + 20 * ss], fill=255)
    faint = np.asarray(fa, np.float32) * (np.asarray(fmask, np.float32) / 255)
    main = np.asarray(im, np.float32)
    mainblur = np.asarray(im.filter(ImageFilter.GaussianBlur(14 * ss)), np.float32)
    faint *= np.clip(1 - mainblur / 40.0, 0, 1)                  # keep the damask out of the main ornament
    comb = Image.fromarray(np.clip(np.maximum(main, faint * 0.5), 0, 255).astype(np.uint8))
    lines = np.asarray(comb.filter(ImageFilter.GaussianBlur(ss * 0.8)).resize((W, H), Image.LANCZOS), np.float32) / 255
    # colour: dark teal field with mottling, cream-gold lines with a soft halo, worn in places
    n = fbm(1024, 6, 5, 5)
    nn = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    field = hexc("#2c5f62")[None, None] * (0.8 + 0.35 * nn[..., None])
    gold = hexc("#d8cf98")
    halo = np.asarray(Image.fromarray((lines * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    col = field * (1 - 0.25 * halo[..., None]) + hexc("#7fb7ad") * 0.25 * halo[..., None]
    wear = np.clip(0.75 + 0.5 * nn, 0, 1)[..., None]
    col = col * (1 - lines[..., None] * wear) + gold * lines[..., None] * wear
    to_img(col).save(os.path.join(OUT, "floor_carpet.png"))

# ---------------------------------------------------------------- glowing panel glyphs
def glyph(W=256, H=512, ss=4):
    w, h = W * ss, H * ss
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im); lw = 6 * ss
    m = 14 * ss
    d.rectangle([m, m, w - m, h - m], outline=255, width=lw)
    d.rectangle([m + 18 * ss, m + 18 * ss, w - m - 18 * ss, h - m - 18 * ss], outline=200, width=3 * ss)
    # interlaced diagonal knot lattice
    cell = (w - 2 * m - 36 * ss) / 2
    x0, y0 = m + 18 * ss, m + 18 * ss
    rows = int(round((h - 2 * y0) / cell))
    cell_y = (h - 2 * y0) / rows
    for r in range(rows):
        for c in range(2):
            ax, ay = x0 + c * cell, y0 + r * cell_y
            d.line([(ax, ay), (ax + cell, ay + cell_y)], fill=255, width=lw)
            d.line([(ax + cell, ay), (ax, ay + cell_y)], fill=255, width=lw)
            d.ellipse([ax + cell * 0.3, ay + cell_y * 0.3, ax + cell * 0.7, ay + cell_y * 0.7], outline=255, width=lw // 2)
    im = im.filter(ImageFilter.GaussianBlur(ss * 0.7)).resize((W, H), Image.LANCZOS)
    im.save(os.path.join(OUT, "glyph.png"))

# ---------------------------------------------------------------- rune ring (polar strip: x = angle, y = radius)
def circle(W=2048, H=256, ss=2):
    w, h = W * ss, H * ss
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im); lw = 4 * ss
    for y in (12, 40, 216, 244):
        d.line([(0, y * ss), (w, y * ss)], fill=255, width=lw)
    rnd = random.Random(9)
    x = 0
    while x < w - 40 * ss:
        gw = rnd.randint(40, 70) * ss
        y0, y1 = 70 * ss, 186 * ss
        for k in range(rnd.randint(2, 4)):          # rune strokes
            a = (x + rnd.random() * gw, rnd.choice((y0, y1, (y0 + y1) / 2)))
            b = (x + rnd.random() * gw, rnd.choice((y0, y1, (y0 + y1) / 2)))
            d.line([a, b], fill=255, width=lw)
        if rnd.random() < 0.5:
            r = gw * 0.25
            d.ellipse([x + gw / 2 - r, (y0 + y1) / 2 - r, x + gw / 2 + r, (y0 + y1) / 2 + r], outline=255, width=lw)
        x += gw + rnd.randint(14, 30) * ss
    im = im.filter(ImageFilter.GaussianBlur(ss * 0.7)).resize((W, H), Image.LANCZOS)
    im.save(os.path.join(OUT, "circle.png"))

if __name__ == "__main__":
    floor_tiles(); carpet(); glyph(); circle()
    print("ok")
