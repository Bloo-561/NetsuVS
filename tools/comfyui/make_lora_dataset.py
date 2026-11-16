"""Turn a fighter's finished drawings into a LoRA training set for ComfyUI / kohya / OneTrainer.

    python tools/comfyui/make_lora_dataset.py <drawings folder> [more folders] --name netsu_cecilia
           [--subject "1girl"] [--tags "black hair, red headband, katana"] [--out tools/comfyui/datasets]

Each drawing goes on the flat grey background the workflows use, scaled into an 832x1216 portrait
(the SDXL size the workflows generate at), with a caption file:  <trigger>, <subject>, solo, full body,
<pose tags from the file name>, grey background, simple background, <your tags>.
Effects on their own (beams, arcs, bursts: no dark hair/outline pixels), tiny pictures and near-duplicates (idle breathing frames) are skipped.
Output: <out>/<name>/<repeats>_<name>/ (the folder name kohya and OneTrainer read) + a contact sheet.

Best source: the artist's full-size drawings (Fighting_Game_All_Sprites/<fighter>). The game's
actors/<fighter>/Sprites/v2 frames also work (about 500 px tall, so they get upscaled about 2x).
"""
import argparse, os, re, glob
import numpy as np
from PIL import Image
from netsu_comfy import load_rgba, bbox, resize_rgba, flatten, save_rgb, BG, GEN_W, GEN_H

SKIP = r"(fx|arc|beam|trail|effect|spark|ricochet|aura|shadow|icon|portrait|cutin|cut_in|select|hud|_flat)"
POSE_TAGS = [  # (regex on file name, tags)
    (r"^(2[abc]|crouch|duck)", "crouching, attack"),
    (r"^j", "midair, jumping"),
    (r"^5[abc]|^[46][abc]", "standing, attack, fighting stance"),
    (r"walk", "walking"),
    (r"dash|run", "dashing, running"),
    (r"idle|ready|stand", "standing, fighting stance"),
    (r"hurt|hit|damage", "hurt, recoil"),
    (r"block|guard", "guarding, defensive stance"),
    (r"down|lying|knock", "lying, on back"),
    (r"win|victory", "victory pose, smile"),
    (r"intro", "standing, looking at viewer"),
    (r"super|236|214|623|special", "attack, action pose, dynamic pose"),
]


def pose_tags(fname):
    n = os.path.basename(fname).lower()
    for rx, tags in POSE_TAGS:
        if re.search(rx, n):
            return tags
    return "action pose"


def signature(arr):
    a = Image.fromarray((arr[..., 3] * 255).astype(np.uint8)).resize((24, 32), Image.BILINEAR)
    g = Image.fromarray((flatten(arr).mean(-1) * 255).astype(np.uint8)).resize((24, 32), Image.BILINEAR)
    return np.concatenate([np.asarray(a, np.float32), np.asarray(g, np.float32)]).ravel() / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="+")
    ap.add_argument("--name", required=True, help="trigger word, e.g. netsu_cecilia")
    ap.add_argument("--subject", default="1girl")
    ap.add_argument("--tags", default="", help="look tags added to every caption")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets"))
    ap.add_argument("--repeats", type=int, default=0, help="0 = pick so one epoch is about 300 steps")
    ap.add_argument("--min-height", type=int, default=200, help="skip pictures shorter than this (px)")
    ap.add_argument("--dedup", type=float, default=0.012, help="skip a picture this close to one kept")
    ap.add_argument("--skip", default=SKIP)
    ap.add_argument("--min-dark", type=float, default=0.05,
                    help="skip pictures with less than this share of dark pixels (effects without the fighter)")
    ap.add_argument("--trail-tags", default="lightning, yellow slash trail",
                    help="added to captions of frames with a lot of effect colour, so trails stay prompt-controlled")
    a = ap.parse_args()

    files = []
    for s in a.src:
        files += sorted(glob.glob(os.path.join(s, "**", "*.png"), recursive=True)) if os.path.isdir(s) else [s]
    kept, sigs, skipped = [], [], {"effect": 0, "small": 0, "duplicate": 0}
    for f in files:
        if re.search(a.skip, os.path.basename(f).lower()) or re.search(r"[\\/](archive|fx)[\\/]", f.lower()):
            skipped["effect"] += 1; continue
        arr = load_rgba(f)
        bb = bbox(arr[..., 3])
        if bb is None or bb[3] - bb[1] < a.min_height:
            skipped["small"] += 1; continue
        arr = arr[bb[1]:bb[3], bb[0]:bb[2]]
        op = arr[..., 3] > 0.5
        rgb = arr[..., :3][op]
        if (rgb.max(1) < 0.3).mean() < a.min_dark:   # no hair / jacket / outline: an effect on its own
            skipped["effect"] += 1; continue
        trail = ((rgb[:, 0] > 0.75) & (rgb[:, 1] > 0.6) & (rgb[:, 2] < 0.55)).mean() > 0.08
        sg = signature(arr)
        if sigs and min(np.abs(np.array(sigs) - sg).mean(1)) < a.dedup:
            skipped["duplicate"] += 1; continue
        sigs.append(sg); kept.append((f, arr, trail))

    n = len(kept)
    if n == 0:
        raise SystemExit("no usable drawings found")
    rep = a.repeats or max(1, min(20, round(300 / n)))
    folder = os.path.join(a.out, a.name, f"{rep}_{a.name}")
    os.makedirs(folder, exist_ok=True)
    bgc = np.array(BG, np.float32) / 255
    thumbs = []
    for i, (f, arr, trail) in enumerate(kept):
        h, w = arr.shape[:2]
        s = min((GEN_H - 96) / h, (GEN_W - 64) / w)
        nw, nh = max(1, round(w * s)), max(1, round(h * s))
        fig = resize_rgba(arr, nw, nh)
        canvas = np.ones((GEN_H, GEN_W, 3), np.float32) * bgc
        x0, y0 = (GEN_W - nw) // 2, GEN_H - 48 - nh
        canvas[y0:y0 + nh, x0:x0 + nw] = flatten(fig)
        base = f"{a.name}_{i:03d}_{os.path.splitext(os.path.basename(f))[0]}"
        save_rgb(canvas, os.path.join(folder, base + ".png"))
        cap = f"{a.name}, {a.subject}, solo, full body, {pose_tags(f)}, grey background, simple background"
        if trail:
            cap += ", " + a.trail_tags
        if a.tags:
            cap += ", " + a.tags
        open(os.path.join(folder, base + ".txt"), "w", encoding="utf-8").write(cap + "\n")
        thumbs.append(Image.fromarray((canvas * 255).astype(np.uint8)).resize((104, 152)))
    cols = 12
    sheet = Image.new("RGB", (cols * 104, ((n + cols - 1) // cols) * 152), (40, 40, 40))
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % cols) * 104, (i // cols) * 152))
    sheet.save(os.path.join(a.out, a.name, "contact_sheet.png"))
    print(f"{n} images ({skipped}) -> {folder}  (repeats {rep}, about {n * rep} steps per epoch)")
    print("Check contact_sheet.png, delete any picture that is off-model, and edit captions if you like.")


if __name__ == "__main__":
    main()
