"""Tiny image I/O layer: numpy arrays in, PNGs out.

Inside Blender it uses OpenImageIO (bundled with Blender 5.x); outside
Blender it falls back to Pillow. Arrays are row 0 = top of the image.
"""
import numpy as np

try:
    import OpenImageIO as oiio  # Blender's bundled OIIO
except Exception:  # pragma: no cover - outside Blender
    oiio = None


def load(path, channels=None):
    """Return uint8 array (H, W, C)."""
    if oiio is not None:
        inp = oiio.ImageInput.open(path)
        if inp is None:
            raise IOError("cannot open %s: %s" % (path, oiio.geterror()))
        spec = inp.spec()
        px = inp.read_image(0, 0, 0, spec.nchannels, oiio.UINT8)
        inp.close()
        arr = np.asarray(px, dtype=np.uint8).reshape(spec.height, spec.width, spec.nchannels)
    else:
        from PIL import Image
        im = Image.open(path)
        if im.mode not in ("L", "RGB", "RGBA"):
            im = im.convert("RGBA")
        arr = np.asarray(im, dtype=np.uint8)
        if arr.ndim == 2:
            arr = arr[..., None]
    if channels is not None:
        c = arr.shape[2]
        if channels == 3 and c >= 3:
            arr = arr[..., :3]
        elif channels == 1 and c >= 3:
            arr = arr[..., :3].mean(axis=2, keepdims=True).astype(np.uint8)
        elif channels == 1 and c == 1:
            pass
        elif channels == 3 and c == 1:
            arr = np.repeat(arr, 3, axis=2)
    return np.ascontiguousarray(arr)


def save(path, arr):
    """Save uint8 (H, W) or (H, W, C) array as PNG."""
    arr = np.ascontiguousarray(np.asarray(arr))
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = arr[..., None]
    h, w, c = arr.shape
    if oiio is not None:
        spec = oiio.ImageSpec(w, h, c, oiio.UINT8)
        out = oiio.ImageOutput.create(path)
        if out is None:
            raise IOError("cannot create %s: %s" % (path, oiio.geterror()))
        out.open(path, spec)
        out.write_image(arr)
        out.close()
    else:
        from PIL import Image
        mode = {1: "L", 3: "RGB", 4: "RGBA"}[c]
        Image.fromarray(arr[..., 0] if c == 1 else arr, mode).save(path)


def save16(path, arr01):
    """Save a float 0..1 array as a 16-bit greyscale PNG."""
    a = np.clip(np.asarray(arr01, np.float64), 0.0, 1.0)
    a16 = np.ascontiguousarray((a * 65535.0 + 0.5).astype(np.uint16))
    h, w = a16.shape
    if oiio is not None:
        spec = oiio.ImageSpec(w, h, 1, oiio.UINT16)
        out = oiio.ImageOutput.create(path)
        out.open(path, spec)
        out.write_image(a16)
        out.close()
    else:
        from PIL import Image
        Image.fromarray(a16, "I;16").save(path)


def load16(path):
    """16-bit greyscale PNG -> float32 0..1."""
    if oiio is not None:
        inp = oiio.ImageInput.open(path)
        spec = inp.spec()
        px = inp.read_image(0, 0, 0, 1, oiio.UINT16)
        inp.close()
        a = np.asarray(px, dtype=np.uint16).reshape(spec.height, spec.width)
    else:
        from PIL import Image
        a = np.asarray(Image.open(path), dtype=np.uint16)
        if a.ndim == 3:
            a = a[..., 0]
    return a.astype(np.float32) / 65535.0


def load_mask(path):
    a = load(path)
    return a[..., 0] >= 128


def load_alpha(path):
    """Alpha channel of an RGBA render as float 0..1 (falls back to luminance)."""
    a = load(path)
    if a.shape[2] == 4:
        return a[..., 3].astype(np.float32) / 255.0
    return a[..., :3].astype(np.float32).mean(axis=2) / 255.0
