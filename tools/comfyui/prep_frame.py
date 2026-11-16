"""Get a sprite frame ready for the 'fix a frame' workflow.

    python tools/comfyui/prep_frame.py <frame.png> [--out folder]

Puts the frame on the grey background the LoRA knows, scales it so the figure is about 1100 px tall
(SDXL works badly on small pictures; the game's v2 frames are ~500 px), pads it to multiples of 64,
and writes <frame>_flat.png plus <frame>_flat.json (how to undo it: cutout.py --restore).
Load the _flat.png in the workflow's 'Frame to fix' node.
"""
import argparse, os, json
from netsu_comfy import load_rgba, make_flat, save_rgb

ap = argparse.ArgumentParser()
ap.add_argument("frame")
ap.add_argument("--out")
ap.add_argument("--height", type=int, default=1100, help="figure height to scale to")
a = ap.parse_args()

arr = load_rgba(a.frame)
canvas, box, s = make_flat(arr, a.height)
out_dir = a.out or os.path.dirname(os.path.abspath(a.frame))
base = os.path.join(out_dir, os.path.splitext(os.path.basename(a.frame))[0] + "_flat")
save_rgb(canvas, base + ".png")
json.dump({"source": os.path.abspath(a.frame), "orig_size": [arr.shape[1], arr.shape[0]], "scale": s,
           "height": a.height, "box": list(box)}, open(base + ".json", "w"), indent=1)
print(f"{base}.png  {canvas.shape[1]}x{canvas.shape[0]} (x{s:.2f})")
