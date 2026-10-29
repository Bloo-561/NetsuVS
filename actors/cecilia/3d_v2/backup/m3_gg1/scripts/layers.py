"""Milestone 3: per-class colour layers of the reference crops (numpy only).

Projection paints each head part from the drawing, but a part must only take
its own colours: hair from hair pixels, the face from skin, the headband from
the band, and so on. Otherwise the side view's eye lands on the side locks,
background white lands on bang tips, the ahoge turns grey, etc.

For every view and class this writes refs/layers/<class>_<view>.png: the crop
with each pixel that isn't that class replaced by the nearest class colours
(filled outward ring by ring from the class pixels, then softened). The class
pixels themselves are untouched, so a view looks exactly like the sheet
wherever the model's surface lines up with the drawing.

Classes (see head_profiles.classes):
  hair : hair colours (purple, or dark above the jacket line), minus band,
         clips, face and ear
  skin : face region (eyes, brows, mouth included), ear, visible neck;
         filled from plain skin only, so the forehead under the bangs and
         the cheek sides come out skin coloured
  skinnoeye : the same with the eyes filled in with skin
  band : red / yellow headband;  clip : teal clips
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\layers.py", run_name="__main__")
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402
import head_profiles as hp  # noqa: E402

LAYER_DIR = os.path.join(cfg.REFS, "layers")
HEAD_ROWS = 205                       # front rows computed; rows below copy the last one
FACE_SEED = {"front": (270, 125), "side": (158, 125)}
NECK_ROWS = (138, 158)                # front rows where the neck shows
SOFTEN = 3                            # blur passes over the filled pixels


def layer_path(cls, view):
    return os.path.join(LAYER_DIR, "%s_%s.png" % (cls, view))


def front_rows(shape, view):
    return np.arange(shape[0])[:, None] - hp.OFF[view] + np.zeros((1, shape[1]), int)


def masks(view):
    """valid pixels and fill sources per class for one view"""
    C = hp.classes(view)
    shape = C["mask"].shape
    rows = front_rows(shape, view)
    skinpx = C["skin"] | C["skin_light"]
    face = hp.face_region(view, FACE_SEED[view]) if view in FACE_SEED else np.zeros(shape, bool)
    ear = C["ear"]
    neck = skinpx & (rows >= NECK_ROWS[0]) & (rows < NECK_ROWS[1])
    if view != "side":
        cu = cfg.VIEWS[view]["centre_u"]
        cols = np.arange(shape[1])[None, :] + np.zeros((shape[0], 1), int)
        neck &= np.abs(cols + 0.5 - cu) < 24
    out = {}
    hair = C["hair"] & ~C["band"] & ~C["clip"] & ~face & ~ear & (rows < 152)
    out["hair"] = (hair, hp.erode3(hair) | (hair & ~hp.dilate3(~hair & C["mask"])))
    skin = face | ear | neck
    out["skin"] = (skin, skinpx & hp.erode3(skin))
    # the same without the eyes (filled with the skin around them): for the
    # face's sides, where the front and side drawings of the eye disagree
    noeye = skin & ~hp.dilate3(hp.dilate3(C["eye"]))
    out["skinnoeye"] = (noeye, skinpx & hp.erode3(noeye))
    band = C["band"] & (rows < 92)
    out["band"] = (band, band)
    clip = C["clip"] & (rows < 80)
    out["clip"] = (clip, clip)
    return C["rgb"], out


def fill(rgb, sources, max_iter=400):
    """onion-peel fill: every unknown pixel takes the mean of its known
    8-neighbours, ring by ring outward from the sources"""
    h, w, _ = rgb.shape
    known = sources.copy()
    val = np.where(known[..., None], rgb, 0.0).astype(np.float32)
    if not known.any():
        return val
    for _ in range(max_iter):
        if known.all():
            break
        pv = np.pad(val, ((1, 1), (1, 1), (0, 0)))
        pk = np.pad(known, 1).astype(np.float32)
        s = np.zeros_like(val)
        c = np.zeros((h, w), np.float32)
        for dy in range(3):
            for dx in range(3):
                if dy == 1 and dx == 1:
                    continue
                k = pk[dy:dy + h, dx:dx + w]
                s += pv[dy:dy + h, dx:dx + w] * k[..., None]
                c += k
        new = (~known) & (c > 0)
        if not new.any():
            break
        val[new] = s[new] / c[new][:, None]
        known |= new
    if not known.all():
        val[~known] = val[known].mean(axis=0)
    return val


def soften(val, keep, passes=SOFTEN):
    """3x3 box blur applied only to the filled (not kept) pixels"""
    h, w, _ = val.shape
    for _ in range(passes):
        pv = np.pad(val, ((1, 1), (1, 1), (0, 0)), mode="edge")
        b = np.zeros_like(val)
        for dy in range(3):
            for dx in range(3):
                b += pv[dy:dy + h, dx:dx + w]
        b /= 9.0
        val = np.where(keep[..., None], val, b)
    return val


def make_layers(view):
    rgb, M = masks(view)
    H = min(rgb.shape[0], HEAD_ROWS + hp.OFF[view])
    out = {}
    for cls, (valid, src) in M.items():
        if not src.any():
            src = valid
        if not valid.any():
            continue
        sub = rgb[:H].astype(np.float32)
        val = fill(sub, src[:H])
        val = soften(val, valid[:H])
        val = np.where(valid[:H, :, None], sub, val)
        full = np.empty(rgb.shape, np.float32)
        full[:H] = val
        full[H:] = val[H - 1]
        out[cls] = (full, valid)
    return out


def main(views=cfg.VIEW_ORDER):
    os.makedirs(LAYER_DIR, exist_ok=True)
    written = {}
    for v in views:
        for cls, (img, valid) in make_layers(v).items():
            p = layer_path(cls, v)
            imgio.save(p, np.clip(img + 0.5, 0, 255).astype(np.uint8))
            written["%s_%s" % (cls, v)] = int(valid.sum())
    return written


if __name__ == "__main__":
    print(main())
