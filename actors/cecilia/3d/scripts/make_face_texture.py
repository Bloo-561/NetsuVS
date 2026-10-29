# Paints Cecilia's face decal (eyes, brows, mouth, blush, nose) as a transparent PNG.
# UV mapping on the head is a front projection: u = (x + 0.09) / 0.18, v = (z - 1.27) / 0.18  (meters).
# Run with plain Python + Pillow (outside Blender):  python make_face_texture.py out.png
import sys, math
from PIL import Image, ImageDraw, ImageFilter

S = 2048
PPM = S / 0.18

def px(x, z):
    return ((x + 0.09) * PPM, (1 - (z - 1.27) / 0.18) * S)

def lerp(a, b, t): return a + (b - a) * t

def spline(ctrl, n=80):
    c = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(c) - 2):
        p0, p1, p2, p3 = c[i - 1], c[i], c[i + 1], c[i + 2]
        for s in range(n):
            t = s / n
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                                   + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in (0, 1)))
    out.append(c[-2])
    return out


def draw_eye(W, H):
    """Eye on its own canvas, inner corner at left. Normalized eye box 0..1 maps to W x H with 25% margins."""
    from PIL import ImageChops
    m = 0.25
    cw, ch = int(W * (1 + 2 * m)), int(H * (1 + 2 * m))
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    P = lambda x, y: (m * W + x * W, m * H + y * H)
    upper = spline([P(0.0, 0.50), P(0.18, 0.18), P(0.45, 0.04), P(0.78, 0.08), P(0.98, 0.36)])
    lower = spline([P(0.98, 0.36), P(0.85, 0.80), P(0.55, 0.97), P(0.22, 0.90), P(0.0, 0.50)])
    shape = upper + lower
    mask = Image.new("L", (cw, ch), 0); ImageDraw.Draw(mask).polygon(shape, fill=255)
    img.paste((255, 255, 255, 255), (0, 0), mask)
    d = ImageDraw.Draw(img)
    # iris gradient
    icx, icy = P(0.52, 0.56); irx, iry = 0.30 * W, 0.44 * H
    grad = Image.new("RGBA", (cw, ch)); gd = ImageDraw.Draw(grad)
    stops = [(0.0, (58, 12, 26)), (0.40, (140, 34, 52)), (0.72, (206, 96, 66)), (1.0, (248, 200, 92))]
    for y in range(ch):
        t = min(max((y - (icy - iry)) / (2 * iry), 0), 1)
        for k in range(len(stops) - 1):
            if stops[k][0] <= t <= stops[k + 1][0]:
                f = (t - stops[k][0]) / (stops[k + 1][0] - stops[k][0])
                c = tuple(int(lerp(stops[k][1][i], stops[k + 1][1][i], f)) for i in range(3))
        gd.line([(0, y), (cw, y)], fill=c + (255,))
    def em(box, w=0):
        mm = Image.new("L", (cw, ch), 0)
        if w: ImageDraw.Draw(mm).ellipse(box, outline=255, width=w)
        else: ImageDraw.Draw(mm).ellipse(box, fill=255)
        return ImageChops.multiply(mm, mask)
    img.paste(grad, (0, 0), em([icx - irx, icy - iry, icx + irx, icy + iry]))
    img.paste((64, 16, 28, 255), (0, 0), em([icx - irx, icy - iry, icx + irx, icy + iry], int(W * 0.03)))
    img.paste((44, 8, 20, 255), (0, 0), em([icx - 0.14 * W, icy - 0.30 * H, icx + 0.14 * W, icy + 0.14 * H]))
    img.paste((250, 208, 106, 255), (0, 0), em([icx - 0.06 * W, icy - 0.14 * H, icx + 0.06 * W, icy + 0.10 * H]))
    img.paste((255, 255, 255, 255), (0, 0), em([icx - 0.24 * W, icy - 0.34 * H, icx - 0.07 * W, icy - 0.15 * H]))
    img.paste((255, 255, 255, 255), (0, 0), em([icx + 0.09 * W, icy + 0.18 * H, icx + 0.17 * W, icy + 0.27 * H]))
    # upper-lid shadow on the eye white
    sh = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(sh).polygon(upper + [(x, y + 0.12 * H) for x, y in reversed(upper)], fill=110)
    img.paste((150, 90, 110, 255), (0, 0), ImageChops.multiply(sh, mask))
    # upper lash band (thick, growing toward the outer corner) + flick
    n = len(upper)
    top = []
    for i, (x, y) in enumerate(upper):
        t = i / (n - 1)
        th = H * (0.04 + 0.13 * math.sin(math.pi * min(t * 1.1, 1.0)) ** 0.6 + 0.04 * t)
        top.append((x, y - th))
    ox, oy = upper[-1]
    lash = upper + [(ox + 0.02 * W, oy + 0.03 * H), (ox + 0.16 * W, oy - 0.12 * H)] + list(reversed(top))
    d.polygon(lash, fill=(36, 16, 22, 255))
    # lower lash: thin line on the outer half
    d.line(lower[:len(lower) // 2], fill=(118, 58, 60, 255), width=max(2, int(H * 0.028)))
    # double-lid crease
    cr = [(x, y - 0.30 * H) for x, y in upper[len(upper) // 5: int(len(upper) * 0.9)]]
    d.line(cr, fill=(176, 116, 110, 255), width=max(2, int(H * 0.014)))
    return img, None


def main(out):
    tex = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    W = H = 0.042 * PPM
    eye, _ = draw_eye(W, H * 0.92)
    for sx in (1, -1):
        cx, cz = sx * 0.047, 1.377
        e = eye if sx == 1 else eye.transpose(Image.FLIP_LEFT_RIGHT)
        X, Y = px(cx, cz)
        # eye canvas: inner corner at left for her left eye (+x); mirrored for the other
        tex.alpha_composite(e, (int(X - eye.width * 0.5), int(Y - eye.height * 0.5)))
    d = ImageDraw.Draw(tex)
    # brows
    for sx in (1, -1):
        pts = []
        for i in range(21):
            t = i / 20
            x = sx * lerp(0.026, 0.068, t); z = 1.421 + 0.006 * math.sin(math.pi * t) - 0.004 * t
            pts.append(px(x, z))
        d.line(pts, fill=(60, 36, 42, 255), width=int(0.0016 * PPM))
    # nose
    d.line([px(0.0015, 1.351), px(-0.001, 1.346)], fill=(214, 150, 140, 255), width=int(0.0012 * PPM))
    # mouth (small calm smile)
    pts = [px(lerp(-0.010, 0.010, i / 20), 1.329 - 0.0028 * math.sin(math.pi * i / 20)) for i in range(21)]
    d.line(pts, fill=(140, 62, 70, 255), width=int(0.0011 * PPM))
    # blush
    a = Image.new("L", (S, S), 0); bd = ImageDraw.Draw(a)
    for sx in (1, -1):
        X, Y = px(sx * 0.051, 1.350)
        bd.ellipse([X - 0.015 * PPM, Y - 0.0055 * PPM, X + 0.015 * PPM, Y + 0.0055 * PPM], fill=90)
    a = a.filter(ImageFilter.GaussianBlur(0.004 * PPM))
    bl = Image.new("RGBA", (S, S), (244, 140, 140, 0)); bl.putalpha(a)
    tex = Image.alpha_composite(bl, tex)
    tex = tex.resize((1024, 1024), Image.LANCZOS)
    tex.save(out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "face.png")
