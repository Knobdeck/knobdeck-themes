"""Cut a painted blueprint (art/blueprint.py) back into a theme's image files.

    python3 art/cut.py <painted.png> <theme-id>

Writes themes/<id>/{plate,center,back,slice,slice-hover}.webp: magenta keyed out (with its fringe
de-spilled), discs masked round, and the slice placed in the 400 px ring frame the dial's slice
renderer expects (`tile` / `tileHover`, `tileSpan` 45, `tileFrame` 400). A sheet that came back at
another size is scaled to the blueprint's first.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: F401

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / "templates" / "blueprint.json").read_text())


def key_magenta(im, band=6):
    """Cut a part off the magenta. Inside the painted shape every pixel stays exactly as painted;
    only in a `band` px strip along its edge (and in soft shadows that fade into the magenta) is the
    alpha estimated and the magenta un-mixed out, so no pink fringe is left.

    For a pixel c = a·F + (1 − a)·magenta: 255 − r = a(255 − Fr), 255 − b = a(255 − Fb) and
    g = a·Fg, so a ≥ each of those; the largest is exact for shadows and dark or saturated edges.
    One pixel can't tell a mid brown from a magenta blend, which is why the interior is left alone."""
    import numpy as np
    c = np.asarray(im.convert("RGB"), dtype=np.float32)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    est = np.clip((np.maximum.reduce([255 - r, 255 - b, g]) / 255 - 0.05) / 0.95, 0, 1)
    solid = Image.fromarray(((est > 0.5) * 255).astype(np.uint8))
    interior = np.asarray(solid.filter(ImageFilter.MinFilter(2 * band + 1))) > 0
    alpha = np.where(interior, 1.0, est)
    safe = np.maximum(alpha, 1e-3)[..., None]
    mag = np.array([255.0, 0.0, 255.0])
    fg = np.where(interior[..., None], c, (c - (1 - alpha[..., None]) * mag) / safe)
    rgba = np.dstack([np.clip(fg, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def disc(im, r):
    m = Image.new("L", im.size, 0)
    cx, cy = im.size[0] / 2, im.size[1] / 2
    ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.0))
    im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
    return im


def crop(sheet, name):
    g = META["regions"][name]
    return sheet.crop((int(g["x"]), int(g["y"]), int(g["x"] + g["w"]), int(g["y"] + g["h"])))


def main(src, theme):
    out = HERE.parent / "themes" / theme
    out.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(src).convert("RGB")
    if sheet.size != (META["width"], META["height"]):
        sheet = sheet.resize((META["width"], META["height"]), Image.LANCZOS)
    s = META["scale"]

    plate = disc(key_magenta(crop(sheet, "plate")), META["plate_r"] * s - 2)
    plate.save(out / "plate.webp", quality=90)
    disc(key_magenta(crop(sheet, "center")), META["center_r"] * s + 4).save(out / "center.webp", quality=90)
    disc(key_magenta(crop(sheet, "back")), META["back_r"] * s + 3).save(out / "back.webp", quality=90)

    # The slices: back into a 400 px frame centred on the ring's centre (1600 image px at scale 4).
    frame = 400 * s
    for name, file in (("slice", "slice.webp"), ("slice_hover", "slice-hover.webp")):
        g = META["regions"][name]
        piece = key_magenta(crop(sheet, name))
        canvas = Image.new("RGBA", (frame, frame), (0, 0, 0, 0))
        # The piece's frame sits so the ring centre (ring_cx, ring_cy) lands at the canvas centre.
        ox = int(frame / 2 - (g["ring_cx"] - g["x"]))
        oy = int(frame / 2 - (g["ring_cy"] - g["y"]))
        canvas.alpha_composite(piece, (ox, oy))
        canvas.resize((frame // 2, frame // 2), Image.LANCZOS).save(out / file, quality=90)
    print(f"cut {src} into themes/{theme}/")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
