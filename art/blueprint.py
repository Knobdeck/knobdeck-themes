"""The theme blueprint: one sheet with the wireframe of every part a sliced dial theme needs, at
exact scale, on flat magenta. Paint the parts in place (an image generator, or by hand), keep the
magenta everywhere else, and `art/cut.py` cuts the painted sheet back into the theme's files.

    python3 art/blueprint.py                 # writes art/templates/blueprint.png + blueprint.json
    python3 art/cut.py <painted.png> <theme-id>

Geometry is the dial's (CSS px): the plate's edge r = 196, the item ring r = 64..128 (items centred
at r = 96), the centre piece r = 56. Every part is drawn at SCALE image px per CSS px.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "templates"
SCALE = 4
MAGENTA = (255, 0, 255)
INK = (255, 255, 255)
GUIDE = (40, 40, 40)

PLATE_R, OUTER_IN = 196, 168
RING_IN, RING_OUT = 64, 128
CENTER_R = 56
BACK_R = 22
SPAN = 45  # the slice is drawn for a ring of 8


def font(size):
    for f in ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


GAP = 4.5  # the joint between two slices (CSS px, constant along the ring), as in Forge


def wedge_points(cx, cy, r_in, r_out, half_deg, steps=48, scale=1.0):
    """The slice's outline, leaving half a joint on each side."""
    half = math.radians(half_deg)
    def side(r):
        h = half - (GAP * scale / 2) / r
        return [(cx + r * math.sin(-h + 2 * h * k / steps), cy - r * math.cos(-h + 2 * h * k / steps)) for k in range(steps + 1)]
    return side(r_out) + side(r_in)[::-1]


def main():
    s = SCALE
    plate_box = 2 * PLATE_R * s + 64                  # 1632
    W, H = plate_box + 1200, plate_box + 330
    img = Image.new("RGB", (W, H), MAGENTA)
    d = ImageDraw.Draw(img)
    title, label, small = font(46), font(30), font(24)
    regions = {}

    def outline_circle(cx, cy, r, width=4, color=INK, dash=False):
        if not dash:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)
            return
        for k in range(0, 360, 6):
            d.arc([cx - r, cy - r, cx + r, cy + r], k, k + 3, fill=color, width=width)

    def frame(name, x, y, w, h, caption, notes):
        d.rectangle([x, y, x + w, y + h], outline=GUIDE, width=2)
        d.text((x, y - 44), caption, fill=INK, font=label)
        for i, line in enumerate(notes):
            d.text((x, y + h + 10 + i * 30), line, fill=INK, font=small)
        regions[name] = {"x": x, "y": y, "w": w, "h": h}

    d.text((40, 18), "KnobDeck dial theme blueprint", fill=INK, font=title)
    d.text((40, 74), "Paint each part inside its wireframe. Keep everything else flat magenta #FF00FF. Leave no text or guide lines.", fill=INK, font=label)

    # 1. The backplate: everything behind the items.
    bx, by = 40, 180
    frame("plate", bx, by, plate_box, plate_box, "1  BACKPLATE (static, under everything)",
          ["Edge r=196. Decorate freely outside the item ring (sockets, rim, notches).",
           "Item ring r=58..134 (dashed): a plain recessed channel the slices sit in.",
           "Centre r<60: plain, the centre piece covers it."])
    cx, cy = bx + plate_box / 2, by + plate_box / 2
    outline_circle(cx, cy, PLATE_R * s, 6)
    outline_circle(cx, cy, OUTER_IN * s, 2, dash=True)
    outline_circle(cx, cy, (RING_OUT + 6) * s, 3, dash=True)
    outline_circle(cx, cy, (RING_IN - 6) * s, 3, dash=True)
    outline_circle(cx, cy, (CENTER_R + 4) * s, 2, dash=True)

    # Right column.
    rx = bx + plate_box + 120
    # 2. The centre piece.
    cbox = 2 * (CENTER_R + 8) * s                      # 512
    frame("center", rx, by, cbox, cbox, "2  CENTRE PIECE (r=56)",
          ["A frame round a PLAIN middle (r<40, dashed):",
           "the profile's icon and the hovered item's",
           "name show there. Decorate the rim only."])
    ccx, ccy = rx + cbox / 2, by + cbox / 2
    outline_circle(ccx, ccy, CENTER_R * s, 5)
    outline_circle(ccx, ccy, 40 * s, 2, dash=True)

    # 3. The small stone for the menu you came from.
    kx = rx + cbox + 80
    kbox = 2 * (BACK_R + 6) * s                        # 224
    frame("back", kx, by, kbox, kbox, "3  BACK ITEM (r=22)", ["The way back, shown", "beside a submenu.", "Icon goes on top."])
    outline_circle(kx + kbox / 2, by + kbox / 2, BACK_R * s, 4)

    # 4 + 5. The slice, idle and hovered: one item's piece for a ring of 8, pointing up.
    half = SPAN / 2
    sw = 2 * RING_OUT * math.sin(math.radians(half)) * s + 48
    sh = (RING_OUT - RING_IN * math.cos(math.radians(half))) * s + 48
    sy = by + cbox + 220
    for name, caption, x, notes in (
        ("slice", "4  ITEM SLICE (idle)", rx, ["One item's piece, for 8 items.", "The icon sits on the dot:", "keep it plain there."]),
        ("slice_hover", "5  ITEM SLICE (hovered)", rx + sw + 120, ["The same piece, lit up /", "glowing: it fades in", "under the pointer."]),
    ):
        frame(name, x, sy, sw, sh, caption, notes)
        ocx, ocy = x + sw / 2, sy + 24 + RING_OUT * s          # the ring's centre, below the frame
        d.polygon(wedge_points(ocx, ocy, RING_IN * s, RING_OUT * s, half, scale=s), outline=INK, width=5)
        icx, icy = ocx, ocy - 96 * s
        d.ellipse([icx - 16 * s, icy - 16 * s, icx + 16 * s, icy + 16 * s], outline=INK, width=2)
        regions[name].update({"ring_cx": ocx, "ring_cy": ocy})

    meta = {"scale": SCALE, "width": W, "height": H, "plate_r": PLATE_R, "ring_in": RING_IN, "ring_out": RING_OUT,
            "center_r": CENTER_R, "back_r": BACK_R, "slice_span": SPAN, "regions": regions}
    OUT.mkdir(exist_ok=True)
    img.save(OUT / "blueprint.png")
    (OUT / "blueprint.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"blueprint.png {W}x{H}")


if __name__ == "__main__":
    main()
