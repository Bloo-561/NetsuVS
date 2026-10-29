"""Cut silhouette masks from the reference crops (numpy only; runs in Blender).

Mask = everything that is not near-white background:
 1. Background = near-white pixels (min channel >= 239) 4-connected to the
    crop border (flood fill). Enclosed white parts of the figure (lace,
    shirt, cuffs, sheath) are inside the line art, so they stay figure.
 2. Edge refinement to 50 % coverage: a figure pixel touching background is
    an anti-aliased mix of line ink and background. Its coverage is
    (bg - value) / (bg - ink), ink = darkest figure pixel within 2 px.
    Pixels under 50 % coverage are dropped, so the mask edge sits where a
    rendered silhouette thresholded at alpha 0.5 would put it.

Output: refs/masks/mask_<view>.png (white figure on black),
        refs/masks/cov_<view>.png (16-bit coverage of boundary pixels, for
        sub-pixel edges in profiles.py) and
        refs/masks/check_<view>.png (background tinted blue, for eyeballing).
Run in Blender:  import runpy; runpy.run_path(r"...\\scripts\\ref_masks.py", run_name="__main__")
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import imgio  # noqa: E402

NEAR_WHITE = 16      # background if 255 - min(R,G,B) <= 16
BG_LEVEL = 253.5     # measured background level (border pixels 252-255)

# Background pockets fully enclosed by the figure (the flood fill can't reach
# them). Checked by eye; every other enclosed near-white region is white
# clothing (lace, shirt, cuffs, sheath) or a skin highlight.
#   side: the inside of the ahoge's loop, which touches down on the head.
BG_SEEDS = {"side": [(145, 28)]}    # (column u, row v)


def flood_background(cand, seeds=()):
    """4-connected geodesic fill of `cand` from the image border (+ extra seeds)."""
    bg = np.zeros_like(cand)
    bg[0, :] = cand[0, :]
    bg[-1, :] = cand[-1, :]
    bg[:, 0] |= cand[:, 0]
    bg[:, -1] |= cand[:, -1]
    for (u, v) in seeds:
        if not cand[v, u]:
            raise ValueError("background seed %s is not near-white" % ((u, v),))
        bg[v, u] = True
    while True:
        prev = bg
        for _ in range(16):
            g = bg.copy()
            g[1:, :] |= bg[:-1, :]
            g[:-1, :] |= bg[1:, :]
            g[:, 1:] |= bg[:, :-1]
            g[:, :-1] |= bg[:, 1:]
            bg = g & cand
        if np.array_equal(bg, prev):
            return bg


def dilate3(m):
    p = np.pad(m, 1, constant_values=False)
    out = np.zeros_like(m)
    h, w = m.shape
    for dy in range(3):
        for dx in range(3):
            out |= p[dy:dy + h, dx:dx + w]
    return out


def min_filter5(a, fill=255.0):
    p = np.pad(a, 2, constant_values=fill)
    win = np.lib.stride_tricks.sliding_window_view(p, (5, 5))
    return win.min(axis=(2, 3))


def make_mask(rgb, view=None, return_coverage=False):
    mn = rgb[..., :3].min(axis=2).astype(np.float32)
    cand = (255.0 - mn) <= NEAR_WHITE
    bg = flood_background(cand, BG_SEEDS.get(view, ()))
    fig = ~bg
    edge = fig & dilate3(bg)
    ink = min_filter5(np.where(fig, mn, 255.0))
    cov = np.clip((BG_LEVEL - mn) / np.maximum(BG_LEVEL - ink, 1.0), 0.0, 1.0)
    mask = fig & ~(edge & (cov < 0.5))
    if not return_coverage:
        return mask
    # Coverage map for sub-pixel edges: 1 inside, the ink-model coverage on the
    # anti-aliased boundary pixels (kept >= 0.5, dropped < 0.5), and a small
    # value on background pixels touching the figure (soft halo), 0 elsewhere.
    C = np.zeros(mask.shape, np.float32)
    C[mask] = 1.0
    C[edge] = cov[edge]
    halo = bg & dilate3(fig)
    C[halo] = np.minimum(cov[halo], 0.49)
    return mask, C


def main():
    os.makedirs(cfg.MASKS, exist_ok=True)
    report = {}
    for view in cfg.VIEW_ORDER:
        rgb = imgio.load(cfg.ref_path(view), channels=3)
        m, C = make_mask(rgb, view, return_coverage=True)
        imgio.save(cfg.mask_path(view), (m * 255).astype(np.uint8))
        imgio.save16(os.path.join(cfg.MASKS, "cov_%s.png" % view), C)
        chk = rgb.astype(np.float32)
        chk[~m] = chk[~m] * 0.3 + np.array([0, 80, 255], np.float32) * 0.7
        imgio.save(os.path.join(cfg.MASKS, "check_%s.png" % view), chk.astype(np.uint8))
        rows = np.where(m.any(axis=1))[0]
        report[view] = dict(area=int(m.sum()), top_row=int(rows.min()), bottom_row=int(rows.max()),
                            height_px=int(rows.max() + 1 - rows.min()))
    return report


if __name__ == "__main__":
    print(main())
