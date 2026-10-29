"""Quick look: every frame of a character placed in game pixels (origin = red tick, floor = cyan).
    python lineup.py assists/eren out.png"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from build import Port
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14) if os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') else ImageFont.load_default()
def main(char, out, only=None):
    p = Port(char)
    fids = [f for f in p.m['frames'] if (only is None or f.startswith(only))]
    cells = []
    for f in fids:
        crop, off, info = p.frame(f)
        cells.append((f, crop, off, info))
    X0 = min(min(o[0] for _, _, o, _ in cells), -100) - 20; X1 = max(max(o[0] + c.shape[1] for _, c, o, _ in cells), 100) + 20
    Y1 = max(o[1] + c.shape[0] for _, c, o, _ in cells) + 20; Y0 = min(min(o[1] for _, _, o, _ in cells), 0) - 30
    W, H = X1 - X0, Y1 - Y0; cols = 6; sc = 0.5
    cw, ch = int(W * sc), int(H * sc) + 18
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cw * cols, ch * rows), (40, 40, 48)); d = ImageDraw.Draw(sheet)
    for i, (f, crop, off, info) in enumerate(cells):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        img = Image.new('RGBA', (W, H), (70, 70, 80, 255)); dd = ImageDraw.Draw(img)
        for gx in range(-1000, 2000, 100):
            x = gx - X0
            if 0 <= x < W: dd.line([(x, 0), (x, H)], fill=(85, 85, 96, 255))
        fy = Y1 - 0; dd.line([(0, fy), (W, fy)], fill=(0, 200, 200, 255), width=2)
        im = Image.fromarray(crop, 'RGBA'); img.alpha_composite(im, (int(off[0] - X0), int(Y1 - (off[1] + crop.shape[0]))))
        ox = -X0; dd.line([(ox, fy - 20), (ox, fy + 10)], fill=(255, 60, 60, 255), width=3)
        b = info.get('body')
        if b: dd.rectangle([b['x0'] - X0, Y1 - b['y1'], b['x1'] - X0, Y1 - b['y0']], outline=(255, 220, 0, 255))
        img = img.convert('RGB').resize((cw, ch - 18))
        sheet.paste(img, (cx, cy)); d.text((cx + 4, cy + ch - 17), '%s %dx%d off%s' % (f, crop.shape[1], crop.shape[0], off), fill=(255, 255, 255), font=FONT)
    sheet.save(out); print(out, sheet.size, 'world x', X0, X1, 'y', Y0, Y1)
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
