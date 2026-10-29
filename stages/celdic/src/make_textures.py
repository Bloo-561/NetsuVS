# Celdic - procedural textures (numpy + Pillow).   python make_textures.py <out_dir>
# cobble.png  4 x 4 m seamless cobblestones: rounded grey-brown stones, dark gaps, moss and grass in the cracks
import sys, os, math
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)

def vnoise_periodic(n, cells, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((cells, cells)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) / n * cells
    i0 = np.floor(t).astype(int); f = t - i0; f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells; i0 %= cells
    a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
    b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]

def fbm(n, base, octaves, seed):
    s = np.zeros((n, n), np.float32); a = 0.5; tot = 0
    for o in range(octaves):
        s += a * vnoise_periodic(n, base * 2 ** o, seed + o); tot += a; a *= 0.5
    return s / tot

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def cobble(n=2048, cells=12, seed=4):
    rng = np.random.default_rng(seed)
    jit = rng.random((cells, cells, 2)).astype(np.float32) * 0.8 + 0.1
    tint = rng.random((cells, cells)).astype(np.float32)
    # domain warp so the stones are irregular, not a grid
    wx = (fbm(n, 6, 3, 21) - 0.5) * 0.35; wy = (fbm(n, 6, 3, 22) - 0.5) * 0.35
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n * cells
    px, py = xx + wx * 1.0, yy + wy * 1.0
    cx0, cy0 = np.floor(px).astype(int), np.floor(py).astype(int)
    f1 = np.full((n, n), 9.0, np.float32); f2 = np.full((n, n), 9.0, np.float32); idx = np.zeros((n, n, 2), int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = cx0 + dx, cy0 + dy
            j = jit[cy % cells, cx % cells]
            d = np.hypot(px - (cx + j[..., 0]), py - (cy + j[..., 1]))
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            idx[..., 0] = np.where(closer, cx % cells, idx[..., 0]); idx[..., 1] = np.where(closer, cy % cells, idx[..., 1])
            f1 = np.where(closer, d, f1)
    edge = f2 - f1                                       # 0 on the gaps between stones
    gap = 1 - np.clip((edge - 0.03) / 0.07, 0, 1)        # 1 in the mortar gaps
    dome = np.clip(edge / 0.35, 0, 1) ** 0.5             # rounded stone tops
    t = tint[idx[..., 1], idx[..., 0]]
    base = fbm(n, 24, 4, 30)
    c_a, c_b, c_c = hexc("#8a7e72"), hexc("#a39684"), hexc("#6e6a66")
    stone = c_a + (c_b - c_a) * t[..., None]
    stone = stone * (1 - 0.35 * (t[..., None] < 0.25)) + c_c * 0.35 * (t[..., None] < 0.25)   # some cool grey stones
    stone *= (0.78 + 0.3 * dome[..., None]) * (0.9 + 0.2 * base[..., None])
    moss_n = fbm(n, 5, 4, 40)
    gapc = hexc("#3a3128") * (1 - moss_n[..., None]) + hexc("#4e5a2a") * moss_n[..., None]
    col = stone * (1 - gap[..., None]) + gapc * gap[..., None]
    # occasional moss creeping onto stones
    moss = np.clip((moss_n - 0.62) * 4, 0, 1) * (1 - dome) ** 2
    col = col * (1 - 0.6 * moss[..., None]) + hexc("#5d6b2e") * 0.6 * moss[..., None]
    # RGB only: an alpha channel (gap mask) made Godot's importer black out the "transparent" stones
    Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(OUT, "cobble.png"))

if __name__ == "__main__":
    cobble(); print("ok")
