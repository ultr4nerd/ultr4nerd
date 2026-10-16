"""Convert an illustration to a chunky 1-bit Bayer-dithered PNG.

usage: dither.py IN OUT --width 300 --scale 3 [--crop L,T,R,B] [--gamma 1.0] [--contrast 1.0]
"""
import argparse
import base64
import io

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

BAYER8 = (
    np.array(
        [
            [0, 32, 8, 40, 2, 34, 10, 42],
            [48, 16, 56, 24, 50, 18, 58, 26],
            [12, 44, 4, 36, 14, 46, 6, 38],
            [60, 28, 52, 20, 62, 30, 54, 22],
            [3, 35, 11, 43, 1, 33, 9, 41],
            [51, 19, 59, 27, 49, 17, 57, 25],
            [15, 47, 7, 39, 13, 45, 5, 37],
            [63, 31, 55, 23, 61, 29, 53, 21],
        ]
    )
    + 0.5
) / 64.0

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


def dither(img: Image.Image, width: int, matrix: np.ndarray, gamma: float, contrast: float) -> np.ndarray:
    g = ImageOps.grayscale(img)
    h = round(g.height * width / g.width)
    g = g.resize((width, h), Image.LANCZOS)
    g = ImageEnhance.Contrast(g).enhance(contrast)
    a = np.asarray(g, dtype=np.float32) / 255.0
    a = a**gamma
    n = matrix.shape[0]
    tiled = np.tile(matrix, (h // n + 1, width // n + 1))[:h, :width]
    return a > tiled  # True = ink/white pixel


def paper_to_black(img: Image.Image, thr: int = 150) -> Image.Image:
    """AI illustrations often come on a cream 'paper' border; ink outlines stop the fill"""
    from PIL import ImageDraw
    g = ImageOps.grayscale(img)
    a = np.asarray(g)
    w, h = g.size
    seen = np.zeros((h, w), dtype=bool)
    stack = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y, x] or a[y, x] < thr:
            continue
        seen[y, x] = True
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    out = np.asarray(img).copy()
    out[seen] = 0
    return Image.fromarray(out)


def to_png(bits: np.ndarray, scale: int) -> bytes:
    im = Image.fromarray((bits * 255).astype(np.uint8), mode="L").convert("1")
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--width", type=int, default=300)
    p.add_argument("--scale", type=int, default=3)
    p.add_argument("--crop", default=None, help="L,T,R,B in source pixels")
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--contrast", type=float, default=1.0)
    p.add_argument("--matrix", choices=["4", "8"], default="8")
    p.add_argument("--b64", action="store_true", help="also write OUT.b64")
    p.add_argument("--paper-to-black", action="store_true", help="flood-fill light paper touching the image corners to black")
    args = p.parse_args()

    img = Image.open(args.src).convert("RGB")
    if args.crop:
        l, t, r, b = (int(v) for v in args.crop.split(","))
        img = img.crop((l, t, r, b))
    if args.paper_to_black:
        img = paper_to_black(img)
    bits = dither(img, args.width, BAYER8 if args.matrix == "8" else BAYER4, args.gamma, args.contrast)
    png = to_png(bits, args.scale)
    with open(args.out, "wb") as f:
        f.write(png)
    if args.b64:
        with open(args.out + ".b64", "w") as f:
            f.write(base64.b64encode(png).decode())
    print(f"{args.out}: {bits.shape[1]}x{bits.shape[0]} @x{args.scale} -> {len(png)} bytes, ink {bits.mean():.0%}")


if __name__ == "__main__":
    main()
