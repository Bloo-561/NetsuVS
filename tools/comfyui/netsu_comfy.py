"""Shared helpers for the Netsu VS ComfyUI tools (tools/comfyui/)."""
import numpy as np
from PIL import Image

BG = (160, 160, 160)          # flat grey the LoRA is trained on and the workflows ask for
GEN_W, GEN_H = 832, 1216       # SDXL portrait bucket used by the workflows


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0


def save_rgba(arr, path):
    Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(path)


def bbox(alpha, thr=0.5):
    ys, xs = np.nonzero(alpha > thr)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def resize_rgba(arr, w, h):
    """Lanczos resize in premultiplied alpha (no dark/grey fringes)."""
    pm = arr.copy()
    pm[..., :3] *= pm[..., 3:4]
    out = np.stack([np.asarray(Image.fromarray(pm[..., c]).resize((w, h), Image.LANCZOS)) for c in range(4)], -1)
    out = np.clip(out, 0, 1)
    a = out[..., 3:4]
    out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
    return np.clip(out, 0, 1)


def flatten(arr, bg=BG):
    bgc = np.array(bg, np.float32) / 255.0
    a = arr[..., 3:4]
    return arr[..., :3] * a + bgc * (1 - a)


def save_rgb(rgb, path):
    Image.fromarray(np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8), "RGB").save(path)


def checker(h, w, s=16):
    yy, xx = np.mgrid[0:h, 0:w]
    c = ((yy // s + xx // s) % 2).astype(np.float32)
    return np.stack([0.75 + 0.15 * c] * 3, -1)


def make_flat(arr, height=1100, pad=64):
    """The picture prep_frame.py feeds to the fix workflow: frame on the grey background, upscaled so the
    figure is about `height` px tall, padded to multiples of 64. Deterministic, so cutout.py can rebuild it."""
    oh, ow = arr.shape[:2]
    s = max(1.0, height / oh)
    w, h = round(ow * s), round(oh * s)
    big = resize_rgba(arr, w, h) if s > 1 else arr.copy()
    big[..., 3] = (big[..., 3] > 0.5)
    cw, ch = -(-(w + pad) // 64) * 64, -(-(h + pad) // 64) * 64
    x, y = (cw - w) // 2, (ch - h) // 2
    canvas = np.ones((ch, cw, 3), np.float32) * (np.array(BG, np.float32) / 255)
    canvas[y:y + h, x:x + w] = flatten(big)
    return canvas, (x, y, w, h), s
