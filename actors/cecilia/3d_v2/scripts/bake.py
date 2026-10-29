"""Milestone 5: the sheet baked into UV textures, cleaned and flattened
(run in Blender; numpy only).

For every texel of the UV atlas (uv_unwrap.py) the bake knows where it is on
the model (rasterised UV triangles -> world position and normal). For each
reference view it then asks:
  * visible?   the texel's depth against a depth map of the whole model,
               rendered (numpy rasteriser) from that view's orthographic camera
  * reliable?  not within CONTOUR_PX of an outline of the model in that view
               (silhouette, an object in front of another, a depth jump):
               the sheet draws its outlines there, and the toon outlines
               (inverted hulls) take that job; nor outside the drawn figure
  * how square-on?  weight = max(0, n . view)^K_ANGLE
and samples the sheet there. The side view shows her right side; her left
side takes it mirrored, except where she isn't symmetric (NO_LEFT).

Flattening. Each part has a short list of the design's base colours
(PALETTE, families sampled from the sheet: lit + shadow tone). A sample is
assigned to the family whose shading line (deep shadow - shadow - lit -
highlight) it lies closest to, so the sheet's soft shading and highlights
all fold into one flat base colour per family; the views vote, weighted.
Line art is kept: thin dark strokes found in the sheet (darker than both
sides and a darkened version of one side, or near black) are removed from
the colour before classifying and come back as crisp lines, coloured per
family like the sheet's (LINE colours measured from the sheet).
Texels no view sees (soles, under the arms, inside the skirt, tops of the
shoulders) take the nearest seen texel's family, by a 3D voxel fill.

Outputs (textures/): body_base.png (flat lit colours + lines),
body_shade.png (the families' shadow tones, for M6), body_label.png
(family index), body_lineclr.png (the sheet's outline colour per family, M6),
body_sheen.png (where the sheet draws the jacket's sheen, M6), hair_mask.png
(purple fraction of the hair for the toon hair bands), plus bake_report.json.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\bake.py")["run"]()
"""
import importlib
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

importlib.reload(cfg)
importlib.reload(imgio)

P = cfg.PX
TEX_DIR = os.path.join(cfg.ROOT, "textures")
CACHE = os.path.join(cfg.REFS, "m5")
UV_NAME = "UVBake"
SIZE = {"body": 2048, "hair": 1024}
SS = 2                    # depth maps: pixels per sheet pixel
TOL = 0.0025              # m: a texel this far behind the nearest surface still counts as visible
JUMP = 0.015              # m: depth step between neighbouring depth-map pixels that makes an outline
CONTOUR_PX = 1.5          # sheet px: samples this close to an outline in a view are not used
# small parts are mostly "near an outline": with the full band they kept
# almost no samples and lost their drawn details (the bows' knots and folds)
CONTOUR_PX_SMALL = 0.5
SMALL_PARTS = ("bow_R", "bow_L", "brooch", "buckle_A", "buckle_B", "tie", "shirt_collar", "kashira", "tsuka",
               "tsuba", "saya_mouth", "saya_tip", "hanger_strap", "clip_R", "clip_L", "hand_R", "hand_L")
K_ANGLE = 4.0
SIDE_PRIORITY = 1.0       # side views' weight factor (1 = plain angle blend, the views meet at 45 deg)
W_MIN = 0.02              # weights below this (beyond ~68 deg from square-on) count as unseen
VOXEL = 0.004             # m: unseen-texel fill grid
MARGIN = 8                # texels of padding around every UV island

# --------------------------------------------------------------------------- palette
# (lit, shadow) in sRGB 0-255. Lit tones are the medians of plain areas of the
# sheet, shadows its shaded areas (sample boxes in M5_NOTES.md):
# skirt panel, thigh, cuff, sleeve, upper back of the jacket, stockings,
# loafers, soles, neckerchief, belts, buckles, glove, shirt collar, hilt
# wrap, clip; the vent's lining; headband from toon.BAND_RGB.
FAMILY = {
    "skin": ((254, 238, 227), (240, 199, 185)),
    "red": ((199, 72, 74), (143, 44, 47)),
    "white": ((250, 250, 250), (198, 195, 201)),
    "sleeve": ((122, 122, 124), (94, 93, 98)),
    "jacket": ((75, 77, 81), (55, 56, 60)),
    "lining": ((180, 75, 117), (130, 50, 85)),
    "legwear": ((95, 71, 66), (70, 50, 47)),
    "loafer": ((115, 79, 70), (89, 60, 54)),
    "sole": ((62, 48, 45), (41, 34, 33)),
    "gold": ((250, 201, 101), (198, 135, 55)),
    "maroon": ((168, 64, 75), (120, 40, 48)),
    "silver": ((235, 232, 235), (177, 157, 166)),
    "glove": ((68, 69, 68), (45, 45, 46)),
    "tie": ((76, 78, 79), (50, 51, 52)),
    "shirt": ((237, 238, 241), (168, 171, 183)),
    "hilt": ((165, 72, 58), (129, 39, 36)),
    "teal": ((108, 152, 167), (57, 76, 86)),
    "band": ((205, 62, 64), (150, 40, 45)),
    "steel": ((222, 226, 232), (160, 166, 176)),
    # hair families: only so the line-colour survey can tell hair from clothes
    "hairblack": ((60, 60, 66), (35, 32, 38)),
    "purple": ((157, 80, 140), (103, 44, 96)),
}
FAMILY_NAMES = list(FAMILY)
CLOTH_FAMILIES = [n for n in FAMILY_NAMES if n not in ("hairblack", "purple")]

PALETTE = {
    "leg_R": ("skin", "legwear", "red"),
    "leg_L": ("skin", "legwear"),
    "shoe_R": ("loafer", "sole", "legwear"),
    "shoe_L": ("loafer", "sole", "legwear"),
    "bow_R": ("red",), "bow_L": ("red",),
    "arm_R": ("sleeve", "red", "white", "skin"),
    "arm_L": ("sleeve", "red", "white", "skin"),
    "hand_R": ("glove", "skin"), "hand_L": ("glove", "skin"),
    "body": ("red", "white", "jacket"),     # top: shirt V + the lapels' undersides where the model's opening is wider
    "jacket": ("jacket", "lining"),   # lining: the back vent's pink (REGION keeps it there)
    "collar": ("jacket",),
    "neckerchief": ("gold",), "brooch": ("white",), "tie": ("tie",), "shirt_collar": ("shirt", "white"),
    "skirt": ("red", "white"), "lace": ("white",),
    "belt_A": ("maroon",), "belt_B": ("maroon",), "buckle_A": ("silver",), "buckle_B": ("silver",),
    "kashira": ("gold",), "tsuka": ("hilt", "gold"), "tsuba": ("gold",), "saya_mouth": ("hilt", "gold"),
    "saya": ("white",), "saya_tip": ("hilt", "gold"), "hanger_strap": ("gold", "hilt"),
    "blade": ("steel",), "headband": ("band", "gold"), "clip_R": ("teal",), "clip_L": ("teal",),
}
# Where on a part each family may appear, traced on the front view (the back
# agrees within 2-3 px), +-4 px tolerance: axis "row" = front-sheet row of the
# texel's height, "absx" = distance from the centre line in sheet px.
# A family is allowed for lo <= value < hi (None = open).
REGION = {
    ("body", "white"): ("row", None, 181), ("body", "red"): ("row", 179, None),       # shirt above the bodice (row 180)
    ("body", "jacket"): ("row", None, 181),
    # the back vent: a pink triangle at the back centre, front rows 227-247, |x| <= 6 px
    ("jacket", "lining"): [("row", 224, 250), ("absx", None, 8)],
    ("skirt", "white"): ("row", 325, None),        # the two stripes near the hem (buckles' white above them)
    # gloves: the glove covers wrist to knuckles (right hand cols 41-78), fingers are skin; the
    # front view draws her left arm ~8 px longer than the model's (front/back split), so its
    # forearm skin landed on the glove's cuff
    ("hand_R", "glove"): ("absx", None, 229), ("hand_R", "skin"): ("absx", 222, None),
    ("hand_L", "glove"): ("absx", None, 229), ("hand_L", "skin"): ("absx", 222, None),
    ("leg_R", "skin"): ("row", None, 420), ("leg_R", "legwear"): ("row", 412, None),  # stocking top: row 416
    ("leg_R", "red"): ("row", 412, None),
    ("leg_L", "skin"): ("row", None, 522), ("leg_L", "legwear"): ("row", 514, None),  # knee sock top: row 518
    ("shoe_R", "legwear"): ("row", None, 656), ("shoe_R", "loafer"): ("row", 645, 688),  # vamp from ~652, sole 685-692
    ("shoe_R", "sole"): ("row", 684, None),
    ("shoe_L", "legwear"): ("row", None, 656), ("shoe_L", "loafer"): ("row", 645, 688),
    ("shoe_L", "sole"): ("row", 684, None),
    # right arm: glove to col 78, forearm 79-125, cuff 125-145, sleeve, red band cols 178-185
    ("arm_R", "skin"): ("absx", 141, None), ("arm_R", "white"): ("absx", 121, 149),
    ("arm_R", "sleeve"): ("absx", None, 129), ("arm_R", "red"): ("absx", 81, 96),
    # left arm (drawn longer): cuff cols 402-421, forearm 421-469, red band 359-366
    ("arm_L", "skin"): ("absx", 147, None), ("arm_L", "white"): ("absx", 128, 155),
    ("arm_L", "sleeve"): ("absx", None, 136), ("arm_L", "red"): ("absx", 85, 100),
}
# Regular patterns drawn from measurements instead of projected (the views
# put them at slightly different places, so a projected pattern breaks up
# where one view hands over to the next).
#
# Stocking ribbons (right leg): the front, side and back views each draw an X
# at the same three heights, in the middle of the leg. A 3D pattern that
# shows an X on every face is a lattice: on each face the upper arms run
# z = h + up * m and the lower ones z = h - down * m, with m = min(|x_n|,
# |y_n|) in the leg's normalised cross-section (0 at a face's centre); the
# arms of neighbouring faces meet at the corners (diamonds at 45 deg).
# Parameters fitted to each view's red (fit_patterns.ribbons()), averaged:
# (crossing row, upper arm reach, lower arm reach) in front-sheet px.
RIBBON_BANDS = [(447.7, 24.3, 16.7), (527.0, 14.0, 18.7), (608.3, 16.7, 11.7)]
RIBBON_W = 6.8            # px, across the ribbon (lattice)
STOCKING_TOP = 416.0      # front row of the stocking's top edge
# M6: the sheet's own socks panel (refs/cecilia_ref_detail_socks.png, "wears
# crisscross sock") and the main render both draw a criss-cross wrap: two
# ribbons wound round the leg in opposite directions, crossing in front at
# the three RIBBON_BANDS rows and behind, half-way between. "helix" draws
# that; "lattice" is the M5 pattern (an X on every face at the same rows,
# which is what the side and back views draw, but at 3/4 it reads as a chain
# of diamonds that no view shows). Helix: in front each arm runs straight
# (sin of the wrap angle linear in the row) from the crossing to the leg's
# edge at the fitted reaches; behind, the angle runs on linearly. Width
# across the ribbon: the front view's horizontal red runs (median 7 / 6 / 5
# px per band) at the arms' ~45 deg slope
RIBBON_STYLE = "helix"
RIBBON_W_HELIX = 4.5
HELIX_C = 0.95            # front halves: angle = (pi/2) asin(C t) / asin(C), t linear in the row:
                          # near-straight arms from the front, without the ribbon turning flat
                          # round the leg's sides (C = 1: exactly straight, flat at the sides)
# Skirt stripes: two thin white lines at a fixed height above the hem in all
# three views (fit_patterns.stripes(): sub-pixel brightness peaks per column;
# front 8.9 / 14.5, back 8.6 / 14.2, side 8.3 / 13.7 px; 1.7 px wide at half
# height); drawn above the model's own hem
STRIPES = (8.6, 14.1)
STRIPE_W = 1.7
PROCEDURAL = ("leg_R", "skirt")
HAIR_OBJECTS = ("hair", "bangs", "skull", "ahoge")
NO_PROJECTION = ("blade",)             # inside the sheath on the sheet: flat steel, no lines
# M6: where the sheet draws the black jacket's light-grey sheen. The flat
# colours fold it into the jacket's black (it is light, not cloth); the
# shader puts it back as a highlight inside this mask (shade_bake: ILM-style
# specular mask). Sheet luminance from plain jacket (lo) to full sheen (hi);
# the views' weighted vote above SHEEN_CUT is the mask
SHEEN = {"jacket": ("jacket", 92.0, 116.0)}       # object -> (its family, lo, hi)
SHEEN_CUT = 0.5
# her left side takes the side view mirrored, except parts she doesn't wear
# symmetrically: the plain knee sock (the side view shows the right leg's
# ribboned stocking) and the tachi on her left hip (her right hip is bare)
NO_LEFT = ("leg_L", "leg_R", "kashira", "tsuka", "tsuba", "saya_mouth", "saya", "saya_tip", "hanger_strap")
# the legs' inner sides face the other leg: from the side cameras they are
# glimpsed past it, where the side view draws the other leg (or nothing)
NO_RIGHT = ("leg_L",)
# no texture lines on skin (the sheet draws none: strokes there are other
# parts' edges, e.g. the lace's scallops on the thighs) nor on the jacket's
# black (its cel-shading edges came out as specks); the saya's drawn shading
# strokes too
NO_LINE_FAMILIES = ("skin", "jacket", "loafer", "legwear")   # loafers / socks: their shading strokes came out as scribbles
NO_LINE_OBJECTS = ("saya", "lace", "leg_R", "headband")   # headband (M6): its lines were its own edges
LINE_MIN_STROKE = 16                  # px: line-art specks smaller than this (shading noise) are dropped
# families that don't spread into unseen texels: the ribbons stop where no
# view sees them instead of smearing round the leg's inner side
FILL_EXCLUDE = {"leg_R": {"red": "legwear"}}     # family -> what its seeds count as
# the belts cross her hips at different heights left and right: the mirrored
# side view's belt edges must not draw lines on the skirt / bodice
NO_LEFT_LINES = ("skirt", "body")

VIEWS = {
    "front": dict(img="front", d=(0.0, -1.0, 0.0)),
    "back": dict(img="back", d=(0.0, 1.0, 0.0)),
    "right": dict(img="side", d=(-1.0, 0.0, 0.0)),
    "left": dict(img="side", d=(1.0, 0.0, 0.0)),
}
YW = np.array([0.299, 0.587, 0.114], np.float32)


# --------------------------------------------------------------------------- 2D helpers
def shift(a, dy, dx):
    """a shifted by (dy, dx) with edge padding: out[y, x] = a[y + dy, x + dx]"""
    H, W = a.shape[:2]
    r = max(abs(dy), abs(dx))
    if r == 0:
        return a
    p = np.pad(a, ((r, r), (r, r)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    return p[r + dy:r + dy + H, r + dx:r + dx + W]


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx <= r * r + 0.5:
                out |= shift(m, dy, dx)
    return out


def erode(m, r):
    return ~dilate(~m, r)


def bilinear(a, u, v):
    """sample an (H, W[, C]) array at continuous coords (pixel centres at +0.5)"""
    H, W = a.shape[:2]
    x = np.clip(u - 0.5, 0, W - 1.001)
    y = np.clip(v - 0.5, 0, H - 1.001)
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    if a.ndim == 3:
        fx, fy = fx[:, None], fy[:, None]
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) +
            a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


# --------------------------------------------------------------------------- line art
def _darkened_of(c, X, smax=0.72, rmax=0.16):
    """c is X darkened: c ~ s * X with s < smax (residual relative to |X|)"""
    xx = (X * X).sum(-1) + 1e-6
    s = (c * X).sum(-1) / xx
    res = np.sqrt(((c - s[..., None] * X) ** 2).sum(-1) / xx)
    return (s < smax) & (res < rmax)


def detect_lines(rgb, fig):
    """thin dark strokes: darker than the pixels 2-3 px away on both sides
    (in one of four directions) and either a darkened version of one side or
    near black. A thin band of a base colour between two lighter ones (the
    skirt's red between its white stripes) is neither, so it stays colour."""
    Y = rgb @ YW
    line = np.zeros(Y.shape, bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for k in (2, 3):
            A, B = shift(rgb, dy * k, dx * k), shift(rgb, -dy * k, -dx * k)
            darker = (Y < 0.82 * (A @ YW)) & (Y < 0.82 * (B @ YW))
            line |= darker & (_darkened_of(rgb, A) | _darkened_of(rgb, B) | (Y < 0.2))
    return line & fig


def drop_specks(m, min_px):
    """remove 8-connected components smaller than min_px from a bool mask"""
    lab = np.zeros(m.shape, np.int32)
    out = m.copy()
    H, W = m.shape
    ys, xs = np.nonzero(m)
    cur = 0
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if lab[y0, x0]:
            continue
        cur += 1
        lab[y0, x0] = cur
        stack, comp = [(y0, x0)], [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur
                        stack.append((yy, xx))
                        comp.append((yy, xx))
        if len(comp) < min_px:
            for y, x in comp:
                out[y, x] = False
    return out


def inpaint(rgb, hole, it=8):
    """fill hole pixels from their known neighbours, ring by ring"""
    out = rgb.copy()
    known = ~hole
    for _ in range(it):
        acc = np.zeros_like(out)
        cnt = np.zeros(out.shape[:2], np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                k = shift(known, dy, dx)
                acc += shift(out, dy, dx) * k[..., None]
                cnt += k
        fill = (~known) & (cnt > 0)
        out[fill] = acc[fill] / cnt[fill, None]
        known = known | fill
        if known.all():
            break
    return out


_SHEET = {}


def sheet(img):
    """(lineless rgb 0-255 float, line mask float 0/1, figure mask eroded 1 px) of a crop"""
    if img in _SHEET:
        return _SHEET[img]
    rgb = imgio.load(cfg.ref_path(img), channels=3).astype(np.float32) / 255.0
    fig = imgio.load_mask(cfg.mask_path(img))
    line = drop_specks(detect_lines(rgb, fig), LINE_MIN_STROKE)
    clean = inpaint(rgb, dilate(line, 1) & fig)
    os.makedirs(CACHE, exist_ok=True)
    imgio.save(os.path.join(CACHE, "lineless_%s.png" % img), np.clip(clean * 255 + 0.5, 0, 255).astype(np.uint8))
    imgio.save(os.path.join(CACHE, "lines_%s.png" % img), (line * 255).astype(np.uint8))
    _SHEET[img] = (clean * 255.0, line.astype(np.float32), erode(fig, 1))
    return _SHEET[img]


# --------------------------------------------------------------------------- classification
def _polyline(name):
    lit, sh = (np.array(c, np.float32) for c in FAMILY[name])
    deep = sh * (sh / np.maximum(lit, 1.0))                 # one more shadow step
    hi = np.minimum(lit + (lit - sh) * 0.35, 255.0)        # highlights fold in too
    return [deep, sh, lit, hi]


def _seg_dist(c, a, b):
    ab = b - a
    t = np.clip(((c - a) @ ab) / max(float(ab @ ab), 1e-6), 0.0, 1.0)
    return np.sqrt(((c - (a + t[:, None] * ab)) ** 2).sum(-1))


def classify(c, names, allowed=None):
    """index into names of the family whose shading line is nearest to each
    colour (N, 3); allowed: optional (N, len(names)) bool mask"""
    if len(names) == 1:
        return np.zeros(len(c), np.int64)
    D = []
    for n in names:
        pl = _polyline(n)
        D.append(np.min([_seg_dist(c, pl[i], pl[i + 1]) for i in range(3)], axis=0))
    D = np.array(D).T
    if allowed is not None:
        D = np.where(allowed, D, np.inf)
    return np.argmin(D, axis=1)


def allowed_mask(name, fams, pos):
    """(N, len(fams)) bool: which families each texel may take (REGION)"""
    row = cfg.VIEWS["front"]["sole_v"] - pos[:, 2] / P
    absx = np.abs(pos[:, 0]) / P
    out = np.ones((len(pos), len(fams)), bool)
    for k, f in enumerate(fams):
        r = REGION.get((name, f))
        if r is None:
            continue
        for axis, lo, hi in (r if isinstance(r, list) else [r]):
            val = row if axis == "row" else absx
            if lo is not None:
                out[:, k] &= val >= lo
            if hi is not None:
                out[:, k] &= val < hi
    bad = ~out.any(1)                      # never leave a texel with nothing allowed
    out[bad] = True
    return out


SURVEY = [n for n in FAMILY_NAMES if n != "steel"]     # families that appear on the sheet
LINE_MIN_PX = 60          # fewer line pixels than this next to a family: lit colour x LINE_FALLBACK
LINE_FALLBACK = 0.55


CONTOUR_MIN_PX = 30       # fewer contour pixels than this next to a family: lit colour x CONTOUR_FALLBACK
CONTOUR_FALLBACK = 0.5
# families the sheet draws too few outer contours for; their inner line colour
# (line_colours) stands in
CONTOUR_FROM_LINES = ("lining", "tie", "hilt", "teal", "steel")


def outline_colours():
    """per family: the colour of the sheet's outer contour where that family
    meets the background (figure pixels within 3 px of the background that are
    darker than the line-free colour there, labelled by the family around them;
    mean of their 10th-40th percentile in luminance). The toon outlines
    (inverted hulls) take these, part by part, as GG tints its outlines."""
    acc = {n: [] for n in SURVEY}
    for img in ("front", "back", "side"):
        clean, line, fig = sheet(img)
        figfull = imgio.load_mask(cfg.mask_path(img))
        raw = imgio.load(cfg.ref_path(img), channels=3).astype(np.float32)
        lab = classify(clean.reshape(-1, 3), SURVEY).reshape(line.shape)
        Y = raw @ YW
        near_bg = dilate(~figfull, 3) & figfull
        inner = erode(figfull, 4)
        votes = np.zeros(Y.shape + (len(SURVEY),), np.int16)
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                ok = shift(inner, dy, dx)
                lb = shift(lab, dy, dx)
                for k in range(len(SURVEY)):
                    votes[..., k] += (ok & (lb == k)).astype(np.int16)
        around = votes.argmax(-1)
        sel = near_bg & (Y < 0.85 * (clean @ YW)) & (votes.max(-1) >= 6)
        for k, n in enumerate(SURVEY):
            m = sel & (around == k)
            if m.any():
                acc[n].append(raw[m])
    lines = line_colours()
    out = {}
    for n in FAMILY_NAMES:
        c = np.concatenate(acc[n]) if acc.get(n) else np.zeros((0, 3), np.float32)
        if n in CONTOUR_FROM_LINES or len(c) < CONTOUR_MIN_PX:
            out[n] = lines[n] if n in CONTOUR_FROM_LINES else \
                [int(round(x)) for x in np.array(FAMILY[n][0], np.float32) * CONTOUR_FALLBACK]
            continue
        y = c @ YW
        lo, hi = np.percentile(y, 10), np.percentile(y, 40)
        out[n] = [int(round(x)) for x in c[(y >= lo) & (y <= hi)].mean(axis=0)]
    return out


def line_colours():
    """per family: the colour the sheet draws its lines in next to that
    family. Line pixels whose surroundings (2 px) are >= 70 % one family;
    the stroke's core is their darker half without the darkest fifth
    (mean of the 20th-50th percentile in luminance)."""
    acc = {n: [] for n in SURVEY}
    for img in ("front", "back", "side"):
        clean, line, fig = sheet(img)
        raw = imgio.load(cfg.ref_path(img), channels=3).astype(np.float32)
        lab = classify(clean.reshape(-1, 3), SURVEY).reshape(line.shape)
        L = line > 0.5
        votes = np.zeros(L.shape + (len(SURVEY),), np.int16)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ok = shift(~L & fig, dy, dx)
                lb = shift(lab, dy, dx)
                for k in range(len(SURVEY)):
                    votes[..., k] += (ok & (lb == k)).astype(np.int16)
        around = votes.argmax(-1)
        pure = votes.max(-1) >= 0.7 * np.maximum(votes.sum(-1), 1)
        for k, n in enumerate(SURVEY):
            sel = L & (around == k) & pure & (votes.max(-1) > 0)
            if sel.any():
                acc[n].append(raw[sel])
    out = {}
    for n in FAMILY_NAMES:
        c = np.concatenate(acc[n]) if acc.get(n) else np.zeros((0, 3), np.float32)
        if len(c) >= LINE_MIN_PX:
            y = c @ YW
            lo, hi = np.percentile(y, 20), np.percentile(y, 50)
            core = c[(y >= lo) & (y <= hi)]
            out[n] = [int(round(x)) for x in core.mean(axis=0)]
        else:
            out[n] = [int(round(x)) for x in np.array(FAMILY[n][0], np.float32) * LINE_FALLBACK]
    return out


# --------------------------------------------------------------------------- geometry
def mesh_arrays(ob, evaluated=False, uv=False):
    """world-space triangles of an object: dict(pos (N,3,3), nrm (N,3,3)[, uv (N,3,2)])"""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    if evaluated:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
    else:
        ev, me = None, ob.data
    try:
        me.calc_loop_triangles()
    except AttributeError:
        pass
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tv)
    tv = tv.reshape(-1, 3)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    vn = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("normal", vn)
    vn = vn.reshape(-1, 3)
    mw = np.array(ob.matrix_world, np.float32)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    nm = np.linalg.inv(mw[:3, :3]).T
    vn = vn @ nm.T
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
    out = dict(pos=co[tv], nrm=vn[tv])
    if uv:
        tl = np.empty(nt * 3, np.int64)
        me.loop_triangles.foreach_get("loops", tl)
        lay = me.uv_layers[UV_NAME]
        u = np.empty(len(lay.data) * 2, np.float32)
        lay.data.foreach_get("uv", u)
        out["uv"] = u.reshape(-1, 2)[tl.reshape(-1, 3)]
    if ev is not None:
        ev.to_mesh_clear()
    return out


def raster(xy, chunk=2_000_000):
    """pixel centres (i + .5, j + .5) inside triangles xy (N, 3, 2):
    returns (i, j, tri, bary (M, 3))"""
    A, B, C = xy[:, 0], xy[:, 1], xy[:, 2]
    v0, v1 = B - A, C - A
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    lo = np.ceil(xy.min(1) - 0.5).astype(np.int64)
    hi = np.floor(xy.max(1) - 0.5).astype(np.int64)
    wh = hi - lo + 1
    ok = (np.abs(den) > 1e-12) & (wh[:, 0] > 0) & (wh[:, 1] > 0)
    size = wh.max(1)
    out_i, out_j, out_t, out_l = [], [], [], []
    s = 1
    while True:
        sel = np.where(ok & (size <= s) & (size > s // 2 if s > 1 else size >= 1))[0]
        if len(sel):
            oy, ox = np.mgrid[0:s, 0:s]
            ox, oy = ox.ravel(), oy.ravel()
            step = max(1, chunk // (s * s))
            for c0 in range(0, len(sel), step):
                t = sel[c0:c0 + step]
                px = lo[t, 0][:, None] + ox[None]
                py = lo[t, 1][:, None] + oy[None]
                inb = (ox[None] < wh[t, 0][:, None]) & (oy[None] < wh[t, 1][:, None])
                qx = px + 0.5 - A[t, 0][:, None]
                qy = py + 0.5 - A[t, 1][:, None]
                d = den[t][:, None]
                l1 = (qx * v1[t, 1][:, None] - v1[t, 0][:, None] * qy) / d
                l2 = (v0[t, 0][:, None] * qy - qx * v0[t, 1][:, None]) / d
                l0 = 1.0 - l1 - l2
                e = -1e-6
                inside = inb & (l0 >= e) & (l1 >= e) & (l2 >= e)
                r, k = np.nonzero(inside)
                out_i.append(px[r, k])
                out_j.append(py[r, k])
                out_t.append(t[r])
                out_l.append(np.stack([l0[r, k], l1[r, k], l2[r, k]], 1))
        if s >= size[ok].max(initial=1):
            break
        s *= 2
    if not out_i:
        z = np.zeros(0, np.int64)
        return z, z, z, np.zeros((0, 3))
    return (np.concatenate(out_i), np.concatenate(out_j), np.concatenate(out_t),
            np.concatenate(out_l).astype(np.float32))


def to_img(view, p):
    """world points (N, 3) -> (u, v) continuous sheet coords of the view's crop, depth (smaller = nearer)"""
    c = cfg.VIEWS[VIEWS[view]["img"]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    v = c["sole_v"] - z / P
    if view == "front":
        return c["centre_u"] + x / P, v, y
    if view == "back":
        return c["centre_u"] - x / P, v, -y
    if view == "right":
        return c["centre_u"] - y / P, v, x
    return c["centre_u"] - y / P, v, -x


def render_objects():
    import bpy
    return [o for o in bpy.data.collections["MODEL"].all_objects
            if o.type == "MESH" and not o.hide_render]


def view_buffers(view, objs):
    """depth map, object-id map and the (dilated) outline mask of the whole
    model seen from a view, at SS x the sheet's resolution"""
    import bpy
    hulls = [m for o in objs for m in o.modifiers if m.name == "GG_outline" and m.show_viewport]
    for m in hulls:
        m.show_viewport = False
    try:
        tri_xy, tri_d, tri_id = [], [], []
        for k, o in enumerate(objs):
            g = mesh_arrays(o, evaluated=True)
            pos = g["pos"].reshape(-1, 3)
            u, v, d = to_img(view, pos)
            tri_xy.append(np.stack([u * SS, v * SS], 1).reshape(-1, 3, 2))
            tri_d.append(d.reshape(-1, 3))
            tri_id.append(np.full(len(g["pos"]), k, np.int32))
    finally:
        for m in hulls:
            m.show_viewport = True
    xy = np.concatenate(tri_xy)
    dd = np.concatenate(tri_d)
    ids = np.concatenate(tri_id)
    c = cfg.VIEWS[VIEWS[view]["img"]]
    W, H = c["W"] * SS, c["H"] * SS
    i, j, t, l = raster(xy)
    keep = (i >= 0) & (i < W) & (j >= 0) & (j < H)
    i, j, t, l = i[keep], j[keep], t[keep], l[keep]
    z = (l * dd[t]).sum(1)
    idx = j * W + i
    order = np.lexsort((z, idx))
    idx, z, t = idx[order], z[order], t[order]
    first = np.r_[True, idx[1:] != idx[:-1]]
    depth = np.full(W * H, np.inf, np.float32)
    oid = np.full(W * H, -1, np.int32)
    depth[idx[first]] = z[first]
    oid[idx[first]] = ids[t[first]]
    depth, oid = depth.reshape(H, W), oid.reshape(H, W)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        nd, ni = shift(depth, dy, dx), shift(oid, dy, dx)
        both = np.isfinite(depth) & np.isfinite(nd)
        jump = np.zeros_like(edge)
        jump[both] = np.abs(depth[both] - nd[both]) > JUMP
        edge |= (ni != oid) | jump
    contour = dilate(edge, int(math.ceil(CONTOUR_PX * SS)))
    contour_small = dilate(edge, int(math.ceil(CONTOUR_PX_SMALL * SS)))
    return dict(depth=depth, oid=oid, contour=contour, contour_small=contour_small, W=W, H=H)


# --------------------------------------------------------------------------- texels
def texels(ob, size):
    """the object's texels: flat atlas index, world position, normal"""
    g = mesh_arrays(ob, uv=True)
    uvp = g["uv"] * size
    i, j, t, l = raster(uvp)
    keep = (i >= 0) & (i < size) & (j >= 0) & (j < size)
    i, j, t, l = i[keep], j[keep], t[keep], l[keep]
    idx = j * size + i
    _, first = np.unique(idx, return_index=True)
    i, j, t, l, idx = i[first], j[first], t[first], l[first], idx[first]
    pos = (l[:, :, None] * g["pos"][t]).sum(1)
    nrm = (l[:, :, None] * g["nrm"][t]).sum(1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    return idx, pos.astype(np.float32), nrm.astype(np.float32)


def view_samples(view, buf, pos, nrm, img_data, obj_index, small=False):
    """weights and sheet samples of texels in one view"""
    u, v, d = to_img(view, pos)
    W, H = buf["W"], buf["H"]
    ii = np.clip(np.floor(u * SS).astype(np.int64), 0, W - 1)
    jj = np.clip(np.floor(v * SS).astype(np.int64), 0, H - 1)
    inside = (u * SS >= 0) & (u * SS < W) & (v * SS >= 0) & (v * SS < H)
    vis = inside & (d <= buf["depth"][jj, ii] + TOL)
    ok = vis & ~buf["contour_small" if small else "contour"][jj, ii]
    clean, line, fig = img_data
    fh, fw = fig.shape
    fu = np.clip(np.floor(u).astype(np.int64), 0, fw - 1)
    fv = np.clip(np.floor(v).astype(np.int64), 0, fh - 1)
    ok &= fig[fv, fu]
    dvec = np.array(VIEWS[view]["d"], np.float32)
    w = np.maximum(nrm @ dvec, 0.0) ** K_ANGLE
    w = np.where(ok & (w >= W_MIN), w, 0.0).astype(np.float32)
    if view in ("right", "left"):
        w *= SIDE_PRIORITY
    return w, u, v


def voxel_fill(pos, label, seen, n_labels):
    """labels of unseen texels: the most common label among the seen texels of
    the nearest voxel that has any (grown outward through empty voxels)"""
    if seen.all() or not seen.any():
        return label
    lo = pos.min(0) - VOXEL
    q = np.floor((pos - lo) / VOXEL).astype(np.int64)
    dims = q.max(0) + 2
    flat = (q[:, 0] * dims[1] + q[:, 1]) * dims[2] + q[:, 2]
    counts = np.zeros((int(np.prod(dims)), n_labels), np.int32)
    np.add.at(counts, (flat[seen], label[seen]), 1)
    grid = np.where(counts.sum(1) > 0, counts.argmax(1), -1).reshape(tuple(dims))
    for _ in range(int(dims.max())):
        empty = grid < 0
        if not empty.any():
            break
        changed = False
        for ax in range(3):
            for s in (1, -1):
                nb = np.roll(grid, s, axis=ax)
                put = empty & (nb >= 0) & (grid < 0)
                if put.any():
                    grid[put] = nb[put]
                    changed = True
        if not changed:
            break
    out = label.copy()
    out[~seen] = grid.reshape(-1)[flat[~seen]]
    return np.maximum(out, 0)


def voxel_fill_value(pos, value, seen):
    """same for a scalar (hair mask): mean of the seen texels per voxel, grown outward"""
    if seen.all() or not seen.any():
        return value
    lo = pos.min(0) - VOXEL
    q = np.floor((pos - lo) / VOXEL).astype(np.int64)
    dims = q.max(0) + 2
    flat = (q[:, 0] * dims[1] + q[:, 1]) * dims[2] + q[:, 2]
    n = int(np.prod(dims))
    s = np.zeros(n, np.float64)
    c = np.zeros(n, np.float64)
    np.add.at(s, flat[seen], value[seen])
    np.add.at(c, flat[seen], 1.0)
    grid = np.where(c > 0, s / np.maximum(c, 1), np.nan).reshape(tuple(dims))
    for _ in range(int(dims.max())):
        empty = np.isnan(grid)
        if not empty.any():
            break
        acc = np.zeros_like(grid)
        cnt = np.zeros_like(grid)
        for ax in range(3):
            for sh in (1, -1):
                nb = np.roll(grid, sh, axis=ax)
                ok = ~np.isnan(nb)
                acc[ok] += nb[ok]
                cnt[ok] += 1
        put = empty & (cnt > 0)
        if not put.any():
            break
        grid[put] = acc[put] / cnt[put]
    out = value.copy()
    out[~seen] = np.nan_to_num(grid.reshape(-1)[flat[~seen]], nan=0.0)
    return out


MAJORITY_IT = 2           # 3x3 majority passes over each part's family labels (texel space)


def majority(idx, label, k, S, allow, it=MAJORITY_IT):
    """smooth a part's family labels in UV space: each texel takes the most
    common family among itself (weighted 1.5) and its 8 neighbours of the
    same part, within what REGION allows there. Removes single-texel noise
    and stair-steps along boundaries; 3x3 keeps the ribbons and stripes."""
    n = len(idx)
    order = np.argsort(idx)
    sidx = idx[order]
    nb = []
    for o in (-S - 1, -S, -S + 1, -1, 1, S - 1, S, S + 1):
        q = idx + o
        p = np.clip(np.searchsorted(sidx, q), 0, n - 1)
        nb.append(np.where(sidx[p] == q, order[p], -1))
    nb = np.stack(nb, 1)
    rows = np.arange(n)
    for _ in range(it):
        counts = np.zeros((n, k), np.float32)
        counts[rows, label] += 1.5
        for c in range(nb.shape[1]):
            v = nb[:, c] >= 0
            np.add.at(counts, (rows[v], label[nb[v, c]]), 1.0)
        label = np.where(allow, counts, -1.0).argmax(1)
    return label


def _leg_rings(side="R"):
    with open(os.path.join(cfg.REFS, "profiles_m2.json")) as fh:
        rings = json.load(fh)["legs"][side]
    r = np.array(sorted(rings, key=lambda q: q[0]), np.float64)
    return r


def ribbon_phase(row):
    """helix wrap angle (rad, 0 = front) of ribbon 1 at each front-sheet row;
    ribbon 2 is its mirror (-angle). 2 pi k at the k-th front crossing,
    -+ pi / 2 where the arms reach the leg's edges (front view)"""
    row = np.asarray(row, np.float64)
    out = np.empty_like(row)
    b = RIBBON_BANDS
    # front halves: sin(angle) ~linear in the row between h - up and h + down (HELIX_C)
    done = np.zeros(row.shape, bool)
    for k, (h, up, dn) in enumerate(b):
        t = np.where(row < h, (row - h) / up, (row - h) / dn)
        on = np.abs(t) <= 1.0 + 1e-9
        tc = np.clip(t[on], -1.0, 1.0)
        out[on] = 2 * math.pi * k + 0.5 * math.pi * np.arcsin(HELIX_C * tc) / math.asin(HELIX_C)
        done |= on
    # back halves: linear from 2 pi k + pi / 2 to 2 pi (k + 1) - pi / 2
    for k in range(len(b) - 1):
        r0, r1 = b[k][0] + b[k][2], b[k + 1][0] - b[k + 1][1]
        on = ~done & (row > r0) & (row < r1)
        out[on] = 2 * math.pi * k + math.pi / 2 + math.pi * (row[on] - r0) / (r1 - r0)
        done |= on
    # above the first and below the last band: the back-half rate of the
    # nearest gap carries on round the leg
    g0 = math.pi / ((b[1][0] - b[1][1]) - (b[0][0] + b[0][2]))
    g1 = math.pi / ((b[-1][0] - b[-1][1]) - (b[-2][0] + b[-2][2]))
    top = ~done & (row < b[0][0])
    out[top] = -math.pi / 2 - g0 * ((b[0][0] - b[0][1]) - row[top])
    bot = ~done & (row > b[-1][0])
    out[bot] = 2 * math.pi * (len(b) - 1) + math.pi / 2 + g1 * (row[bot] - (b[-1][0] + b[-1][2]))
    return out


def ribbon_mask(pos):
    """True where the ribbons cover the right stocking (RIBBON_STYLE)"""
    if RIBBON_STYLE == "helix":
        return helix_mask(pos)
    return lattice_mask(pos)


def helix_mask(pos):
    r = _leg_rings("R")
    z = pos[:, 2]
    x0, x1, y0, y1 = (np.interp(z, r[:, 0], r[:, k]) for k in (1, 2, 3, 4))
    xc, yc = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    hx, hy = np.maximum(0.5 * (x1 - x0), 1e-4) / P, np.maximum(0.5 * (y1 - y0), 1e-4) / P   # px
    xn, yn = (pos[:, 0] - xc) / P / hx, (pos[:, 1] - yc) / P / hy
    th = np.arctan2(xn, -yn)                                  # 0 = front, +pi/2 = her left (+x)
    row = cfg.VIEWS["front"]["sole_v"] - z / P
    phi = ribbon_phase(row)
    # slope of the ribbon in (arc length, row): d(arc)/d(row), numerically
    dphi = (ribbon_phase(row + 0.25) - ribbon_phase(row - 0.25)) / 0.5
    hit = np.zeros(len(pos), bool)
    for sgn in (1.0, -1.0):
        d = np.abs((th - sgn * phi + math.pi) % (2 * math.pi) - math.pi)   # wrap-angle offset
        R = np.sqrt((hx * np.cos(th)) ** 2 + (hy * np.sin(th)) ** 2)     # px of arc per radian
        perp = d * R / np.sqrt(1.0 + (R * dphi) ** 2)
        hit |= perp < 0.5 * RIBBON_W_HELIX
    return hit & (row > STOCKING_TOP + 1.0)


def lattice_mask(pos):
    """True where the lattice ribbons cover the right stocking"""
    r = _leg_rings("R")
    z = pos[:, 2]
    x0, x1, y0, y1 = (np.interp(z, r[:, 0], r[:, k]) for k in (1, 2, 3, 4))
    xc, yc = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    hx, hy = np.maximum(0.5 * (x1 - x0), 1e-4), np.maximum(0.5 * (y1 - y0), 1e-4)
    xn, yn = np.abs((pos[:, 0] - xc) / hx), np.abs((pos[:, 1] - yc) / hy)
    m = np.clip(np.minimum(xn, yn), 0.0, 1.0)
    hw = np.where(xn <= yn, hx, hy) / P                      # the face's half-width in px
    row = cfg.VIEWS["front"]["sole_v"] - z / P
    hit = np.zeros(len(pos), bool)
    for h, up, dn in RIBBON_BANDS:
        du = np.abs(row - (h - up * m)) / np.sqrt(1.0 + (up / hw) ** 2)
        dl = np.abs(row - (h + dn * m)) / np.sqrt(1.0 + (dn / hw) ** 2)
        hit |= (np.minimum(du, dl) < 0.5 * RIBBON_W)
    return hit & (row > STOCKING_TOP + 1.0)


def stripe_mask(ob, pos, axis=(0.0, 0.005)):
    """True on the skirt's two stripes: STRIPES px above the hem below each point"""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    mw = np.array(ob.matrix_world, np.float32)
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    th_v = np.arctan2(co[:, 0] - axis[0], -(co[:, 1] - axis[1]))
    nb = 88                       # 2 of the skirt's 176 columns per bin: every bin holds hem vertices
    bins = np.clip(((th_v + np.pi) / (2 * np.pi) * nb).astype(np.int64), 0, nb - 1)
    hem = np.full(nb, np.inf)
    np.minimum.at(hem, bins, co[:, 2])
    ok = np.isfinite(hem)
    centres = (np.arange(nb) + 0.5) / nb * 2 * np.pi - np.pi
    hem = np.interp(centres, centres[ok], hem[ok], period=2 * np.pi)
    th = np.arctan2(pos[:, 0] - axis[0], -(pos[:, 1] - axis[1]))
    zh = np.interp(th, centres, hem, period=2 * np.pi)
    d = (pos[:, 2] - zh) / P
    hit = np.zeros(len(pos), bool)
    for off in STRIPES:
        hit |= np.abs(d - off) < 0.5 * STRIPE_W
    return hit


SMOOTH_CELL = 0.006       # m: voxel of smooth3d
SMOOTH_IT = 2


def smooth3d(pos, val, w, cell=SMOOTH_CELL, it=SMOOTH_IT):
    """val averaged (weights w) over 3x3x3 voxel neighbourhoods, it passes:
    smooths a per-texel value across the model's surface regardless of how
    the UV islands are cut. Texels with w = 0 take the average around them."""
    q = np.floor((pos - pos.min(0)) / cell).astype(np.int64) + 1
    dims = q.max(0) + 2
    key = (q[:, 0] * dims[1] + q[:, 1]) * dims[2] + q[:, 2]
    uk, inv = np.unique(key, return_inverse=True)
    s = np.bincount(inv, weights=val * w)
    c = np.bincount(inv, weights=w)
    offs = [(dx * dims[1] + dy) * dims[2] + dz for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for _ in range(it):
        s2, c2 = np.zeros_like(s), np.zeros_like(c)
        for o in offs:
            p = np.clip(np.searchsorted(uk, uk + o), 0, len(uk) - 1)
            ok = uk[p] == uk + o
            s2[ok] += s[p[ok]]
            c2[ok] += c[p[ok]]
        s, c = s2, c2
    return np.where(c[inv] > 0, s[inv] / np.maximum(c[inv], 1e-9), 0.0)


def pad_islands(arrs, filled, it=MARGIN):
    """grow every island's border texels outward into the empty texels"""
    filled = filled.copy()
    for _ in range(it):
        grow = np.zeros_like(filled)
        src = {}
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = shift(filled, dy, dx)
            new = nb & ~filled & ~grow
            if new.any():
                for name, a in arrs.items():
                    sa = shift(a, dy, dx)
                    a[new] = sa[new]
                grow |= new
        if not grow.any():
            break
        filled |= grow
    return filled


# --------------------------------------------------------------------------- bake
def bake_body(report):
    import bpy
    S = SIZE["body"]
    objs = render_objects()
    buffers = {v: view_buffers(v, objs) for v in VIEWS}
    lines = line_colours()
    contours = outline_colours()
    report["line_colours"] = lines
    report["outline_colours"] = contours
    base = np.zeros((S * S, 3), np.uint8)
    lineclr = np.zeros((S * S, 3), np.uint8)
    shade = np.zeros((S * S, 3), np.uint8)
    lab_img = np.zeros(S * S, np.uint8)
    line_img = np.zeros(S * S, np.uint8)
    sheen_img = np.zeros(S * S, np.uint8)
    filled = np.zeros(S * S, bool)
    for name, fams in PALETTE.items():
        ob = bpy.data.objects.get(name)
        if ob is None or ob.data.uv_layers.get(UV_NAME) is None:
            continue
        t0 = time.time()
        idx, pos, nrm = texels(ob, S)
        n = len(idx)
        if n == 0:
            continue
        k = len(fams)
        allow = allowed_mask(name, fams, pos)
        score = np.zeros((n, k), np.float32)
        best_w = np.zeros(n, np.float32)
        best_line = np.zeros(n, np.float32)
        sheen = np.zeros(n, np.float32)
        if name not in NO_PROJECTION:
            for view, vd in VIEWS.items():
                if (view == "left" and name in NO_LEFT) or (view == "right" and name in NO_RIGHT):
                    continue
                data = sheet(vd["img"])
                w, u, v = view_samples(view, buffers[view], pos, nrm, data, objs.index(ob) if ob in objs else -1,
                                       small=name in SMALL_PARTS)
                on = w > 0
                if not on.any():
                    continue
                col = bilinear(data[0], u[on], v[on])
                lab = classify(col, fams, allow[on])
                score[np.where(on)[0], lab] += w[on]
                if name in SHEEN:
                    _, lo, hi = SHEEN[name]
                    sheen[on] += w[on] * np.clip((col @ YW - lo) / (hi - lo), 0.0, 1.0)
                ln = bilinear(data[1], u[on], v[on])
                if view == "left" and name in NO_LEFT_LINES:
                    ln = np.zeros_like(ln)
                wo = w[on]
                upd = wo > best_w[on]
                sel = np.where(on)[0][upd]
                best_w[sel] = wo[upd]
                best_line[sel] = ln[upd]
        seen = score.sum(1) > 0
        label = score.argmax(1)
        excl = FILL_EXCLUDE.get(name, {})
        if excl:
            seed = label.copy()
            for f, g in excl.items():                       # seeds of excluded families count as another family
                seed[seed == fams.index(f)] = fams.index(g)
            fill_lab = voxel_fill(pos, seed, seen, k)
            label = np.where(seen, label, fill_lab)
        else:
            label = voxel_fill(pos, label, seen, k)
        bad = ~allow[np.arange(n), label]              # a fill that crossed into a family's no-go zone
        label[bad] = allow[bad].argmax(1)
        if k > 1:
            label = majority(idx, label, k, S, allow)
        if name == "leg_R":
            sk, lw, rd = fams.index("skin"), fams.index("legwear"), fams.index("red")
            rib = ribbon_mask(pos)
            cloth = label != sk
            label = np.where(cloth, np.where(rib, rd, lw), label)
        elif name == "skirt":
            rd, wh = fams.index("red"), fams.index("white")
            label = np.where(stripe_mask(ob, pos), wh, rd)
        is_line = (best_line > 0.5) & seen & (name not in NO_LINE_OBJECTS)
        for i, f in enumerate(fams):
            if f in NO_LINE_FAMILIES:
                is_line &= label != i
        fam_idx = np.array([FAMILY_NAMES.index(f) for f in fams])
        lit = np.array([FAMILY[f][0] for f in fams], np.uint8)
        shd = np.array([FAMILY[f][1] for f in fams], np.uint8)
        lcol = np.array([lines[f] for f in fams], np.uint8)
        b = lit[label]
        b[is_line] = lcol[label[is_line]]
        s_ = shd[label]
        # lines in shadow: the line colour darkened like the family's shadow
        ratio = np.array([np.array(FAMILY[f][1], np.float32) / np.maximum(np.array(FAMILY[f][0], np.float32), 1)
                          for f in fams])
        s_[is_line] = np.clip(lcol[label[is_line]] * ratio[label[is_line]], 0, 255).astype(np.uint8)
        base[idx], shade[idx] = b, s_
        lineclr[idx] = np.array([contours[f] for f in fams], np.uint8)[label]
        lab_img[idx] = fam_idx[label] + 1
        line_img[idx] = is_line * 255
        if name in SHEEN:
            wsum = score.sum(1)
            frac = np.where(seen, sheen / np.maximum(wsum, 1e-9), 0.0)
            frac = smooth3d(pos, frac, wsum)
            on = ((frac > SHEEN_CUT) & (label == fams.index(SHEEN[name][0]))).astype(np.int64)
            on = majority(idx, on, 2, S, np.ones((n, 2), bool))
            sheen_img[idx] = on * 255
            report.setdefault("sheen", {})[name] = round(float(on.mean()), 3)
        filled[idx] = True
        report["objects"][name] = dict(texels=int(n), seen=round(float(seen.mean()), 3),
                                       labels={f: round(float((label == i).mean()), 3) for i, f in enumerate(fams)},
                                       lines=round(float(is_line.mean()), 3), t=round(time.time() - t0, 1))
    arrs = dict(base=base.reshape(S, S, 3), shade=shade.reshape(S, S, 3), lab=lab_img.reshape(S, S),
                line=line_img.reshape(S, S), lineclr=lineclr.reshape(S, S, 3), sheen=sheen_img.reshape(S, S))
    pad_islands(arrs, filled.reshape(S, S))
    os.makedirs(TEX_DIR, exist_ok=True)
    flip = lambda a: a[::-1]                                   # UV v goes up, image rows go down
    imgio.save(os.path.join(TEX_DIR, "body_base.png"), flip(arrs["base"]))
    imgio.save(os.path.join(TEX_DIR, "body_shade.png"), flip(arrs["shade"]))
    imgio.save(os.path.join(TEX_DIR, "body_label.png"), flip(arrs["lab"]))
    imgio.save(os.path.join(TEX_DIR, "body_line.png"), flip(arrs["line"]))
    imgio.save(os.path.join(TEX_DIR, "body_lineclr.png"), flip(arrs["lineclr"]))
    imgio.save(os.path.join(TEX_DIR, "body_sheen.png"), flip(arrs["sheen"]))
    report["body_fill"] = round(float(filled.mean()), 3)
    return buffers


def bake_hair(report, buffers):
    """the purple fraction of the hair (layers.hair_purple) baked the same way;
    the toon hair cuts it into flat bands"""
    import bpy
    S = SIZE["hair"]
    objs = render_objects()
    masks = {img: imgio.load(os.path.join(cfg.REFS, "layers", "hairp_%s.png" % img), channels=1)[..., 0]
             .astype(np.float32) / 255.0 for img in ("front", "back", "side")}
    out = np.zeros(S * S, np.float32)
    filled = np.zeros(S * S, bool)
    shell = None                                   # the hair shell's seen texels (pos, value)
    for name in HAIR_OBJECTS:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.data.uv_layers.get(UV_NAME) is None:
            continue
        idx, pos, nrm = texels(ob, S)
        n = len(idx)
        acc = np.zeros(n, np.float64)
        wsum = np.zeros(n, np.float64)
        for view, vd in VIEWS.items():
            data = sheet(vd["img"])
            w, u, v = view_samples(view, buffers[view], pos, nrm, data, objs.index(ob) if ob in objs else -1)
            on = w > 0
            if on.any():
                acc[on] += w[on] * bilinear(masks[vd["img"]], u[on], v[on])
                wsum[on] += w[on]
        seen = wsum > 0
        val = np.where(seen, acc / np.maximum(wsum, 1e-9), 0.0)
        if name == "hair":
            shell = (pos[seen], val[seen])
        if name == "skull" and shell is not None:
            # the skull filler shows only through gaps in the hair: it takes the
            # nearest hair shell colour (purple at the tips, dark above)
            ap = np.concatenate([shell[0], pos])
            av = np.concatenate([shell[1], np.zeros(n)])
            sn = np.concatenate([np.ones(len(shell[0]), bool), np.zeros(n, bool)])
            val = voxel_fill_value(ap, av, sn)[len(shell[0]):]
        else:
            val = voxel_fill_value(pos, val, seen)
        out[idx] = val
        filled[idx] = True
        report["objects"][name] = dict(texels=int(n), seen=round(float(seen.mean()), 3),
                                       purple=round(float(val.mean()), 3))
    arrs = dict(m=out.reshape(S, S))
    pad_islands(arrs, filled.reshape(S, S))
    g = np.clip(arrs["m"] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    imgio.save(os.path.join(TEX_DIR, "hair_mask.png"), g[::-1])
    report["hair_fill"] = round(float(filled.mean()), 3)


def run(hair=True):
    t0 = time.time()
    report = dict(objects={})
    buffers = bake_body(report)
    if hair:
        bake_hair(report, buffers)
    report["t"] = round(time.time() - t0, 1)
    with open(os.path.join(TEX_DIR, "bake_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    return report


# --------------------------------------------------------------------------- materials
def _img(path, colorspace="sRGB"):
    import bpy
    name = os.path.basename(path)
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.load(path, check_existing=True)
        im.name = name
    else:
        im.filepath = path
        im.reload()
    im.colorspace_settings.name = colorspace
    return im


def tex_material(ob, image, name=None):
    """UV-textured emission (toon.toonify wraps it like the projection previews)"""
    import bpy
    name = name or "TEX_" + ob.name
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = UV_NAME
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = image
    t.interpolation = "Linear"
    t.extension = "EXTEND"
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(t.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me = ob.data
    keep = [m for m in me.materials if m and m.name.startswith("GG_Outline")]
    me.materials.clear()
    me.materials.append(mat)
    for m in keep:
        me.materials.append(m)
    return mat


def apply_materials():
    """every atlas part gets its baked texture"""
    import bpy
    im = _img(os.path.join(TEX_DIR, "body_base.png"))
    done = []
    for name in PALETTE:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.data.uv_layers.get(UV_NAME) is None:
            continue
        tex_material(ob, im)
        done.append(name)
    return done


if __name__ == "__main__":
    print(run())
