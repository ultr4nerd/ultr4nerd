"""Build art/avatar.png: the 1-bit wizard portrait tinted like the banner (lavender ink on black, pink crystal ball).

GitHub shows avatars as circles, so the art is inset and nothing lives in the corners.

One-off. Needs: pip install pillow numpy
    python scripts/art/build_avatar.py art/avatar-source.png [--size 800]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from dither import BAYER8, dither, paper_to_black  # noqa: E402
from PIL import ImageOps  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INK = (0xCF, 0xC3, 0xFF)
BG = (0x05, 0x03, 0x08)
PINK = (0xFF, 0x5F, 0xD2)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("--width", type=int, default=200, help="dither resolution (pixels across)")
    p.add_argument("--size", type=int, default=800, help="output size")
    p.add_argument("--contrast", type=float, default=1.6)
    p.add_argument("--gamma", type=float, default=1.3)
    p.add_argument("--ball", default=None, help="x,y of a point inside the crystal ball (source pixels) to tint it pink")
    p.add_argument("--inset", type=float, default=0.9, help="art scale inside the square, so a circular crop keeps it")
    args = p.parse_args()

    img = paper_to_black(Image.open(args.src).convert("RGB"))
    bits = dither(img, args.width, BAYER8, args.gamma, args.contrast)
    h, w = bits.shape
    rgb = np.where(bits[..., None], np.array(INK, np.uint8), np.array(BG, np.uint8))
    if args.ball:
        # flood-fill the bright ball in the source, downsample that mask, recolor its ink pixels
        g = np.asarray(ImageOps.grayscale(img))
        sx, sy = (int(v) for v in args.ball.split(","))
        seen, stack = np.zeros(g.shape, bool), [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= g.shape[1] or y >= g.shape[0] or seen[y, x] or g[y, x] < 200:
                continue
            seen[y, x] = True
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        small = np.asarray(Image.fromarray(seen.astype(np.uint8) * 255).resize((w, h), Image.BILINEAR)) > 100
        rgb[small & bits] = PINK
    art = Image.fromarray(rgb.astype(np.uint8))
    side = round(args.size * args.inset)
    art = art.resize((side, round(side * h / w)), Image.NEAREST)
    out = Image.new("RGB", (args.size, args.size), BG)
    out.paste(art, ((args.size - art.width) // 2, (args.size - art.height) // 2))
    dest = ROOT / "art" / "avatar.png"
    out.save(dest, optimize=True)
    print(f"{dest}: {out.size[0]}x{out.size[1]}, ink {bits.mean():.0%}")


if __name__ == "__main__":
    main()
