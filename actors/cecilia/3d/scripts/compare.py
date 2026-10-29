# Compose review renders next to the turnaround sheet at the same scale (run outside Blender with Pillow).
# usage: python compare.py <renders_dir> <sheet.png> <out.png> [prefix]
import sys, os
from PIL import Image, ImageDraw

SHEET_PPM = 1 / 0.00175          # sheet pixels per meter
SHEET_FEET = 932
def main(rdir, sheet, out, prefix="review", render_ppm=1100 / 1.80, render_feet=550 + 0.82 * 1100 / 1.80):
    sh = Image.open(sheet).convert("RGB")
    crops = {"front": (20, 400), "back": (390, 760), "side": (740, 990)}
    k = SHEET_PPM / render_ppm
    tiles = []
    def rend(v, half=380):
        im = Image.open(os.path.join(rdir, f"{prefix}_{v}.png")).convert("RGBA")
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        feet = render_feet * k; cx = im.width / 2
        top = feet - SHEET_FEET
        return bg.convert("RGB").crop((int(cx - half), int(top), int(cx + half), int(top + 960)))
    for name, kind in (("front", "sheet"), ("front", "r"), ("threequarter", "r"), ("side", "sheet"), ("side", "r"),
                       ("back", "sheet"), ("back", "r")):
        if kind == "sheet":
            x0, x1 = crops[name]; t = sh.crop((x0, 0, x1, 960))
        else:
            t = rend(name, 380 if name in ("front", "back") else 260)
        tiles.append((f"{'SHEET' if kind == 'sheet' else '3D'} {name}", t))
    W = sum(t.width for _, t in tiles) + 10 * len(tiles)
    canvas = Image.new("RGB", (W, 990), "white"); d = ImageDraw.Draw(canvas)
    x = 0
    for label, t in tiles:
        canvas.paste(t, (x, 30)); d.text((x + 6, 8), label, fill=(200, 0, 0)); x += t.width + 10
    for y in range(30, 990, 50):
        d.line([(0, y), (W, y)], fill=(220, 235, 255))
    canvas.save(out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(sys.argv[4:5]))
