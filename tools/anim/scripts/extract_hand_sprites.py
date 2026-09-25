"""Cut glove hands out of a drawing into transparent PNG sprites for the rig.

Usage: python scripts/extract_hand_sprites.py <drawing.png|jpg> <out_dir>

- The background colour is taken from the top-left pixel and made transparent
  (also enclosed gaps between fingers).
- Rubber-hose arms are removed by their warm brown tint; the neutral black ink
  lines of the glove stay.
- Boxes are for the 740 x 493 sheet the user supplied; adjust for other sheets.
Only use drawings you own or are licensed to use.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageFilter

UP = 4  # upscale factor before segmentation
BOXES = {  # shape name -> box in the 740 x 493 sheet
    "open": (62, 78, 182, 202), "peace": (185, 135, 274, 248), "rock": (285, 88, 374, 216),
    "thumbs_up": (376, 58, 487, 180), "fist": (498, 100, 584, 206), "point": (593, 88, 677, 216),
}

src = Image.open(sys.argv[1]).convert("RGB")
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
sx, sy = src.width / 740, src.height / 493
bg = src.getpixel((5, 5))
meta = {}
def near(c, ref, tol):
    return sum((a - b) ** 2 for a, b in zip(c, ref)) <= tol * tol


for name, (x0, y0, x1, y1) in BOXES.items():
    crop = src.crop((int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)))
    # small JPEG source: upscale 4x and blur lightly before segmenting, which smooths
    # compression noise into clean, even lines (a poor man's vectorisation)
    crop = crop.resize((crop.width * UP, crop.height * UP), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(UP * 0.45))
    w, h = crop.size
    px = crop.load()
    # 1) background: flood fill from the border, plus enclosed pockets of pure background colour
    bgmask = Image.new("L", (w, h), 0)
    bm = bgmask.load()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if bm[x, y] or not near(px[x, y], bg, 22):  # white is only ~40 away from the beige: stay strict
            continue
        bm[x, y] = 255
        stack += [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < w and 0 <= y + dy < h]
    # enclosed pockets of background (gaps between fingers). Only real areas count: the blurred
    # transition from black ink to white glove passes through beige-like greys, and those thin
    # seams must not be mistaken for background, so small structures are removed by an opening.
    pocket = Image.new("L", (w, h), 0)
    pk = pocket.load()
    for y in range(h):
        for x in range(w):
            if near(px[x, y], bg, 10):
                pk[x, y] = 255
    pocket = pocket.filter(ImageFilter.MinFilter(2 * UP + 1)).filter(ImageFilter.MaxFilter(2 * UP + 1))
    pk = pocket.load()
    for y in range(h):
        for x in range(w):
            if pk[x, y]:
                bm[x, y] = 255
    # 2) keep only ink that hugs the white glove (drops the brown arms and their outlines)
    white = Image.new("L", (w, h), 0)
    wm = white.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            wm[x, y] = 255 if min(r, g, b) > 232 else 0
    near_glove = white.filter(ImageFilter.MaxFilter(6 * UP + 1))
    ng = near_glove.load()
    # the glove's own ink line hugs the white; after blurring it can look slightly warm,
    # so the brown "arm" test only applies further away from the glove
    ink_zone_img = white.filter(ImageFilter.MaxFilter(4 * UP + 1))  # keep a reference: .load() alone
    ink_zone = ink_zone_img.load()                                    # would point at a freed image
    keepmask = Image.new("L", (w, h), 0)
    km = keepmask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            arm = (r - b) >= 13 and (r + g + b) < 330 and not ink_zone[x, y]
            km[x, y] = 255 if (not bm[x, y] and ng[x, y] and not arm) else 0
    # opening removes JPEG specks around the ink line, one more erosion trims the ragged rim
    # light anti-aliasing pixels between the black contour and the background form a pale
    # halo on a black display: drop everything light that lies right next to the background
    rim_img = bgmask.filter(ImageFilter.MaxFilter(2 * UP + 1))
    rim = rim_img.load()
    for y in range(h):
        for x in range(w):
            if km[x, y] and rim[x, y]:
                r, g, b = px[x, y]
                if 0.299 * r + 0.587 * g + 0.114 * b > 95:
                    km[x, y] = 0
    k = 2 * UP - 1
    keepmask = keepmask.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(UP + 1 | 1))
    km = keepmask.load()
    rgba = Image.new("RGBA", (w, h))
    dst = rgba.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if km[x, y]:
                # gloves are only white and black ink: snap to a clean ramp, which removes JPEG noise
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                v = max(0, min(255, round((lum - 130) * 255 / (215 - 130))))
                dst[x, y] = (v, v, v, 255)
            else:
                dst[x, y] = (0, 0, 0, 0)
    # JPEG block edges leave thin straight nicks across the ink lines: a median filter removes
    # such thin strokes without changing line weight
    r_, _, _, a_ = rgba.split()
    ink = r_.filter(ImageFilter.MedianFilter(2 * UP + 1))
    rgba = Image.merge("RGBA", (ink, ink, ink, a_))
    rgba = rgba.crop(rgba.getbbox())
    rgba.save(out / f"{name}.png")
    meta[name] = {"size": rgba.size}
(out / "sprites.json").write_text(json.dumps({"height_px_at_scale_1": 90, "sprites": meta}, indent=2) + "\n")
print(f"wrote {len(meta)} sprites to {out}")
