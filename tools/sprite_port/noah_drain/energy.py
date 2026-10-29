"""Noah drain energy: from the opponent (in front) arcing over his hood into the crystal claw. 8 frames.
Coordinates are Noah's sprite space relative to his origin, y up (same as AnimData offsets)."""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]
FAR = len(sys.argv) > 2 and sys.argv[2] == "far"   # Void Devour: she's already launched, energy streams in from off-frame
SS = 3                                   # supersampling
X0, Y0, CW, CH = -95, 245, 480, 255      # canvas: left, bottom (y up), width, height (sprite px)
SRC = (400.0, 345.0) if FAR else (318.0, 300.0)   # inside the opponent's chest / past the canvas edge
CTRL1 = (250.0, 470.0)
CTRL2 = (70.0, 470.0)
CLAW = (-33.0, 392.0)
N = 8

VIOLET = (110, 40, 210)
MAGENTA = (190, 80, 255)
PINK = (245, 200, 255)
WHITE = (255, 248, 255)


def bez(t):
    u = 1 - t
    x = u**3 * SRC[0] + 3 * u * u * t * CTRL1[0] + 3 * u * t * t * CTRL2[0] + t**3 * CLAW[0]
    y = u**3 * SRC[1] + 3 * u * u * t * CTRL1[1] + 3 * u * t * t * CTRL2[1] + t**3 * CLAW[1]
    return x, y


def tangent(t, e=1e-3):
    a, b = bez(max(0, t - e)), bez(min(1, t + e))
    dx, dy = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dy) or 1
    return dx / l, dy / l


def px(p):  # sprite coords (y up) -> canvas pixels (supersampled)
    return ((p[0] - X0) * SS, (CH - (p[1] - Y0)) * SS)


def layer():
    return Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))


def strand_points(t0, t1, phase, amp, waves, side):
    pts = []
    steps = 90
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        x, y = bez(t)
        tx, ty = tangent(t)
        nx, ny = -ty, tx
        t = min(1.0, max(0.0, t)); a = amp * (1 - t) ** 0.8 * (0.35 + 0.65 * min(1, t * 6))   # wide near her, tight at the claw
        o = side * a * math.sin(2 * math.pi * (waves * t - phase))
        pts.append((x + nx * o, y + ny * o, t))
    return pts


def draw_strand(d, pts, width0, width1, color, alpha):
    for (x1, y1, ta), (x2, y2, tb) in zip(pts, pts[1:]):
        w = width0 + (width1 - width0) * ta
        d.line([px((x1, y1)), px((x2, y2))], fill=color + (int(alpha * 255),), width=max(1, int(w * SS)))
        r = w * SS / 2
        cx, cy = px((x2, y2))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (int(alpha * 255),))


def diamond(d, c, size, ang, color, a=255):
    cx, cy = px(c)
    s = size * SS
    pts = []
    for k, rr in enumerate((s, s * 0.32, s, s * 0.32)):
        th = ang + k * math.pi / 2
        pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
    d.polygon(pts, fill=color + (a,))


def frame(f):
    rnd = random.Random(1234)            # same particles every frame, moved by f
    # reach of the stream: grows out of her (f0-2), full (f2-5), tail sucked in (f6-7)
    head = [0.45, 0.78, 1, 1, 1, 1, 1, 1][f]
    tail = [0, 0, 0, 0, 0.05, 0.18, 0.5, 0.82][f]
    strength = [0.8, 0.95, 1, 1, 1, 1, 0.85, 0.6][f]
    if FAR:   # already flowing when the pose starts, then the last of it is sucked in
        head = [0.6, 0.9, 1, 1, 1, 1, 1, 1][f]
        tail = [0, 0, 0, 0.08, 0.2, 0.38, 0.6, 0.85][f]
        strength = [0.9, 1, 1, 1, 1, 0.95, 0.85, 0.6][f]
    phase = f * 0.38

    glow, body, core, fx = layer(), layer(), layer(), layer()
    dg, db, dc, dfx = ImageDraw.Draw(glow), ImageDraw.Draw(body), ImageDraw.Draw(core), ImageDraw.Draw(fx)

    # three twisting strands
    for s, (amp, waves, side, ph) in enumerate(((22, 2.2, 1, 0.0), (18, 2.2, -1, 0.33), (13, 3.1, 1, 0.66))):
        pts = strand_points(tail, head, phase + ph, amp, waves, side)
        draw_strand(dg, pts, 26, 12, VIOLET, 0.6 * strength)
        draw_strand(db, pts, 11, 5.0, MAGENTA, 0.95 * strength)
        draw_strand(dc, pts, 4.0, 2.2, PINK if s else WHITE, 1.0 * strength)

    # a straight-ish bright spine the strands wind around
    spine = strand_points(tail, head, 0, 0, 1, 1)
    draw_strand(dg, spine, 34, 14, VIOLET, 0.45 * strength)
    draw_strand(db, spine, 6, 3, MAGENTA, 0.7 * strength)
    draw_strand(dc, spine, 2.6, 1.6, WHITE, 0.95 * strength)

    # shards and sparks riding the stream toward the claw
    for i in range(26):
        t = (rnd.random() + f * 0.085 * (0.8 + rnd.random() * 0.5)) % 1.0
        if not (tail <= t <= head):
            continue
        x, y = bez(t)
        tx, ty = tangent(t)
        spread = (1 - t) * 30 + 4
        x += -ty * rnd.uniform(-spread, spread)
        y += tx * rnd.uniform(-spread, spread)
        if i % 3 == 0:
            ang = math.atan2(-ty, tx) + rnd.uniform(-0.3, 0.3)
            diamond(dfx, (x, y), rnd.uniform(7, 11) * (1 - 0.4 * t), ang, VIOLET)
            diamond(dfx, (x, y), rnd.uniform(5, 7) * (1 - 0.4 * t), ang, MAGENTA)
            diamond(dfx, (x, y), rnd.uniform(2.2, 3.2), ang, WHITE)
        else:
            r = rnd.uniform(1.8, 3.2) * SS
            cx, cy = px((x, y))
            dfx.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PINK + (230,))

    # energy being torn out of her: a burst at the source while the pull runs
    if tail < 0.1 and not FAR:
        for k in range(7):
            ang = rnd.uniform(0, 2 * math.pi)
            ln = rnd.uniform(22, 44) * strength
            a = (SRC[0] + math.cos(ang) * 4, SRC[1] + math.sin(ang) * 4)
            b = (SRC[0] + math.cos(ang) * ln, SRC[1] + math.sin(ang) * ln)
            dg.line([px(a), px(b)], fill=VIOLET + (170,), width=10 * SS)
            db.line([px(a), px(b)], fill=MAGENTA + (240,), width=3 * SS)
            dc.line([px(a), px((SRC[0] + math.cos(ang) * ln * 0.6, SRC[1] + math.sin(ang) * ln * 0.6))], fill=WHITE + (255,), width=1 * SS)
        r = (17 + 3 * math.sin(f)) * SS
        cx, cy = px(SRC)
        dg.ellipse([cx - r * 1.8, cy - r * 1.8, cx + r * 1.8, cy + r * 1.8], fill=VIOLET + (110,))
        db.ellipse([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=MAGENTA + (220,))
        dc.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], fill=WHITE + (255,))

    # the orb forming in the claw, then swallowed (last frame: flash ring, small core)
    orb_r = [0, 7, 11, 15, 18, 20, 22, 9][f]
    if orb_r:
        cx, cy = px(CLAW)
        R = orb_r * SS
        dg.ellipse([cx - R * 2, cy - R * 2, cx + R * 2, cy + R * 2], fill=VIOLET + (120,))
        db.ellipse([cx - R, cy - R, cx + R, cy + R], fill=MAGENTA + (245,))
        # swirl
        for arm in range(3):
            pts = []
            for k in range(40):
                s = k / 39
                th = arm * 2 * math.pi / 3 + s * 4.2 + f * 0.9
                rr = R * (0.95 - 0.85 * s)
                pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
            dc.line(pts, fill=PINK + (255,), width=max(1, int(R * 0.22)))
        dc.ellipse([cx - R * 0.38, cy - R * 0.38, cx + R * 0.38, cy + R * 0.38], fill=WHITE + (255,))
    if f == 7:
        cx, cy = px(CLAW)
        # absorbed: a short star flare out of the claw
        for k in range(10):
            th = k * 2 * math.pi / 10 + 0.2
            ln = (46 if k % 2 == 0 else 26) * SS
            tip = (cx + ln * math.cos(th), cy + ln * math.sin(th))
            sideA = (cx + 5 * SS * math.cos(th + math.pi / 2), cy + 5 * SS * math.sin(th + math.pi / 2))
            sideB = (cx + 5 * SS * math.cos(th - math.pi / 2), cy + 5 * SS * math.sin(th - math.pi / 2))
            dg.polygon([sideA, tip, sideB], fill=VIOLET + (200,))
            db.polygon([sideA, tip, sideB], fill=MAGENTA + (235,))
            tip2 = (cx + ln * 0.6 * math.cos(th), cy + ln * 0.6 * math.sin(th))
            dc.line([(cx, cy), tip2], fill=WHITE + (255,), width=2 * SS)

    glow = glow.filter(ImageFilter.GaussianBlur(5 * SS))
    body = body.filter(ImageFilter.GaussianBlur(0.8 * SS))
    img = layer()
    for l in (glow, body, core, fx):
        img = Image.alpha_composite(img, l)
    img = img.convert("RGBa").resize((CW, CH), Image.LANCZOS).convert("RGBA")
    if FAR:   # fade the far end out instead of a hard cut at the frame edge
        arr = np.array(img).astype(np.float32)
        ramp = np.clip((CW - 1 - np.arange(CW)) / 90.0, 0, 1) ** 1.3
        arr[..., 3] *= ramp[None, :]
        for ch, v in enumerate(MAGENTA):   # the fading end goes violet, not grey
            arr[..., ch] = arr[..., ch] * ramp[None, :] + v * (1 - ramp[None, :])
        img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return img


for f in range(N):
    frame(f).save(f"{OUT}/fx_drain_{'far_' if FAR else ''}{f + 1}.png")
print("offset", (X0, Y0), "size", (CW, CH))
