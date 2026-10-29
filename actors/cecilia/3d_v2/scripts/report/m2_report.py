"""Milestone 2 report figures (plain Python + numpy + Pillow, not Blender).

    python m2_report.py [tag]        (default tag: m2_final)

Reads renders/sil/<tag>_*.png (+ _iou.json) and renders/m2_review_*.png,
writes renders/m2_silhouettes.png, renders/m2_overlay.png, renders/m2_review_sheet.png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cfg  # noqa: E402

VIEWS = cfg.VIEW_ORDER


def font(size):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def silhouettes(tag, renders):
    sil = os.path.join(renders, "sil")
    with open(os.path.join(sil, "%s_iou.json" % tag)) as fh:
        iou = json.load(fh)
    cols = []
    for v in VIEWS:
        ref = Image.open(cfg.ref_path(v)).convert("RGB")
        a = np.asarray(Image.open(os.path.join(sil, "%s_%s.png" % (tag, v))).convert("RGBA"))[..., 3]
        model = Image.fromarray(np.where(a >= 128, 255, 0).astype(np.uint8)).convert("RGB")
        diff = Image.open(os.path.join(sil, "%s_%s_diff.png" % (tag, v))).convert("RGB")
        cols.append((v, ref, model, diff))
    gap, head = 10, 70
    W = sum(3 * c[1].width + 2 * gap for c in cols) + gap * 4 * (len(cols) - 1)
    H = cols[0][1].height + head
    out = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(out)
    x = 0
    for v, ref, model, diff in cols:
        r = iou[v]
        ok = r["iou"] >= r["target"]
        d.text((x, 6), "%s   IoU %.4f  (target %.2f)  %s" % (v.upper(), r["iou"], r["target"], "OK" if ok else "BELOW"),
               fill=(0, 120, 0) if ok else (200, 0, 0), font=font(18))
        d.text((x, 32), "reference | model silhouette | diff: red = ref only %d px, blue = model only %d px"
               % (r["ref_only_px"], r["model_only_px"]), fill=(0, 0, 0), font=font(13))
        for im in (ref, model, diff):
            out.paste(im, (x, head))
            x += im.width + gap
        x += 3 * gap
    return out


def overlay(tag, renders):
    sil = os.path.join(renders, "sil")
    tiles = []
    for v in VIEWS:
        ref = np.asarray(Image.open(cfg.ref_path(v)).convert("RGB")).astype(np.float32)
        a = np.asarray(Image.open(os.path.join(sil, "%s_%s.png" % (tag, v))).convert("RGBA"))[..., 3] >= 128
        out = ref * 0.5 + 255 * 0.5                                    # faded reference
        tint = np.array([40, 120, 255], np.float32)
        out[a] = ref[a] * 0.5 + tint * 0.5                              # 50 % blue model over it
        edge = a & ~(np.pad(a, 1)[2:, 1:-1] & np.pad(a, 1)[:-2, 1:-1] & np.pad(a, 1)[1:-1, 2:] & np.pad(a, 1)[1:-1, :-2])
        out[edge] = (0, 40, 160)
        tiles.append(Image.fromarray(out.clip(0, 255).astype(np.uint8)))
    W = sum(max(t.width, 300) for t in tiles) + 20 * (len(tiles) - 1)
    img = Image.new("RGB", (W, tiles[0].height + 48), (255, 255, 255))
    d = ImageDraw.Draw(img)
    x = 0
    for v, t in zip(VIEWS, tiles):
        img.paste(t, (x, 48))
        d.text((x + 4, 4), v.upper(), fill=(0, 0, 0), font=font(16))
        d.text((x + 4, 26), "model silhouette (blue, 50 %) over the reference", fill=(0, 0, 0), font=font(12))
        x += max(t.width, 300) + 20
    return img


def review(renders, names=("front", "q_front_right", "side_right", "q_back_right", "back", "q_front_left"),
           prefix="m2_review", scale=0.5):
    ims = []
    for n in names:
        p = os.path.join(renders, "%s_%s.png" % (prefix, n))
        im = Image.open(p).convert("RGB")
        ims.append((n, im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)))
    W = sum(i.width for _, i in ims) + 10 * (len(ims) - 1)
    out = Image.new("RGB", (W, ims[0][1].height + 26), (255, 255, 255))
    d = ImageDraw.Draw(out)
    x = 0
    for n, i in ims:
        out.paste(i, (x, 26))
        d.text((x + 4, 5), n, fill=(0, 0, 0), font=font(14))
        x += i.width + 10
    return out


def main(tag="m2_final", renders=None):
    renders = renders or cfg.RENDERS
    silhouettes(tag, renders).save(os.path.join(renders, "m2_silhouettes.png"))
    overlay(tag, renders).save(os.path.join(renders, "m2_overlay.png"))
    review(renders).save(os.path.join(renders, "m2_review_sheet.png"))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["m2_final"]))
