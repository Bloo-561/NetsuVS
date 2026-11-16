"""Cut a ComfyUI picture off its flat background, ready for the sprite port tools.

    python tools/comfyui/cutout.py <png> [<png> ...] --out <folder> [--name 5d_1] [--flip] [--preview]
    python tools/comfyui/cutout.py <fixed.png> --restore <frame>_flat.json --out <folder>   (after a fix)

The background is found from the picture's border (any flat colour works; the workflows ask for grey) and
removed where it touches the border, plus large flat gaps of the same colour inside the figure (between arm
and body). Alpha is made binary like the rest of the sprite set, the picture is trimmed, and --preview writes
<name>_check.png (on a checkerboard) so you can see that nothing of the character was eaten.
--restore undoes prep_frame.py's padding and scaling, so a fixed frame has the exact size of the original.
Then add the PNG to the art folder and the manifest (frames) like any drawing: build.py, hitfit.py.
"""
import argparse, os, json
import numpy as np
import cv2
from PIL import Image
from netsu_comfy import load_rgba, save_rgba, bbox, checker, flatten, make_flat


def cut(rgb, tol=0.11, hole_area=0.002, keep_holes=False):
    h, w = rgb.shape[:2]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bgc = np.median(border, 0)
    diff = np.abs(rgb - bgc).max(-1)
    cand = (diff < tol).astype(np.uint8)
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(cand, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    bg = np.zeros((h, w), bool)
    for i in range(1, nlab):
        region = lab == i
        if i in edge:
            bg |= region
        elif not keep_holes and stats[i, cv2.CC_STAT_AREA] >= hole_area * h * w:
            # an enclosed gap: only if it is as flat as the background (shaded cloth isn't)
            if diff[region].mean() < tol * 0.5 and rgb[region].std(0).max() < 0.02:
                bg |= region
    # anti-aliased fringe: pixels next to the background that are still close to its colour
    near = cv2.dilate(bg.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~bg
    bg |= near & (diff < tol * 2)
    # drop specks of "figure" floating in the background
    fg = (~bg).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n2 > 1:
        biggest = st2[1:, cv2.CC_STAT_AREA].max()
        for i in range(1, n2):
            if st2[i, cv2.CC_STAT_AREA] < max(30, biggest * 0.002):
                fg[lab2 == i] = 0
    return fg.astype(bool), bgc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", help="output name (one input only)")
    ap.add_argument("--tol", type=float, default=0.11, help="how far from the background colour still counts as background (0-1)")
    ap.add_argument("--keep-holes", action="store_true", help="don't clear enclosed gaps")
    ap.add_argument("--flip", action="store_true", help="mirror (the game's drawings face right)")
    ap.add_argument("--restore", help="<frame>_flat.json written by prep_frame.py")
    ap.add_argument("--changed-tol", type=float, default=0.08, help="--restore: colour change that counts as fixed")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for p in a.png:
        rgb = np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255
        fg, bgc = cut(rgb, a.tol, keep_holes=a.keep_holes)
        rgba = np.dstack([rgb, fg.astype(np.float32)])
        name = a.name or os.path.splitext(os.path.basename(p))[0]
        keep = None
        if a.restore:
            info = json.load(open(a.restore))
            x, y, w, h = info["box"]
            rgba = rgba[y:y + h, x:x + w]
            ow, oh = info["orig_size"]
            if (w, h) != (ow, oh):
                rgba = cv2.resize(rgba, (ow, oh), interpolation=cv2.INTER_AREA)
                rgba[..., 3] = (rgba[..., 3] > 0.5)
            if os.path.exists(info["source"]):
                # keep every pixel of the original that the fix didn't change: no drift outside the mask
                flat, _, _ = make_flat(load_rgba(info["source"]), info.get("height", 1100))
                if flat.shape == rgb.shape:
                    big = (np.abs(rgb - flat).max(-1) > a.changed_tol).astype(np.uint8)
                    big = cv2.dilate(big, np.ones((5, 5), np.uint8))[y:y + h, x:x + w]
                    changed = cv2.resize(big.astype(np.float32), (ow, oh), interpolation=cv2.INTER_AREA) > 0
                    changed = cv2.dilate(changed.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
                    print(f"  changed area: {changed.mean():.1%} of the frame; the rest is the original's pixels")
                else:
                    changed = np.ones((oh, ow), bool)
                    print("  picture size differs from the prepared frame: keeping the whole cut-out result")
                keep = (~changed, np.asarray(Image.open(info["source"]).convert("RGBA")))
        else:
            bb = bbox(rgba[..., 3])
            if bb is None:
                print(p, ": nothing left after removing the background, try a lower --tol"); continue
            x0, y0, x1, y1 = bb
            rgba = rgba[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2]
        rgba = np.ascontiguousarray(rgba, dtype=np.float32)
        rgba[..., :3] *= rgba[..., 3:4]
        u8 = np.clip(rgba * 255 + 0.5, 0, 255).astype(np.uint8)
        if keep is not None:   # untouched pixels: the original's bytes, soft edges and all
            u8 = np.where(keep[0][..., None], keep[1], u8)
        if a.flip:
            u8 = u8[:, ::-1]
        out = os.path.join(a.out, name + ".png")
        Image.fromarray(np.ascontiguousarray(u8), "RGBA").save(out)
        cov = rgba[..., 3].mean()
        print(f"{out}  {rgba.shape[1]}x{rgba.shape[0]}  background {np.round(bgc * 255).astype(int).tolist()}  figure {cov:.0%} of the box")
        if a.preview:
            ch = checker(*rgba.shape[:2])
            comp = rgba[..., :3] + ch * (1 - rgba[..., 3:4])
            Image.fromarray((np.clip(comp, 0, 1) * 255).astype(np.uint8)).save(os.path.join(a.out, name + "_check.png"))


if __name__ == "__main__":
    main()
