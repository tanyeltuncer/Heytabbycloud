"""Side-by-side sheet: reference glove crops (top) vs. our gloves (bottom), same beige background.
Usage: python scripts/compare_hands.py <reference.jpg> <out.png>"""
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, ".")
from tabby_anim.hands import draw_hand  # noqa: E402
from tabby_anim.shapes import SS, Canvas, Xf  # noqa: E402

ref = Image.open(sys.argv[1]).convert("RGB")
sx, sy = ref.width / 740, ref.height / 493
boxes = {"open": (62, 78, 182, 205), "peace": (185, 135, 272, 245), "thumbs_up": (385, 60, 485, 170),
         "fist": (500, 100, 580, 195), "point": (595, 90, 675, 205)}
W, H = 200, 220
bg = ref.getpixel((10, 10))
sheet = Image.new("RGB", (W * len(boxes), H * 2 + 20), bg)
d = ImageDraw.Draw(sheet)
for i, (shape, (x0, y0, x1, y1)) in enumerate(boxes.items()):
    crop = ref.crop((int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)))
    crop.thumbnail((W - 10, H - 10))
    sheet.paste(crop, (i * W + (W - crop.width) // 2, 10 + (H - crop.height) // 2))
    img = Image.new("RGB", (W * SS, H * SS), bg)
    draw_hand(Canvas(ImageDraw.Draw(img)), Xf(W / 2, H / 2 + 5, 0, 1.55), shape)
    sheet.paste(img.resize((W, H), Image.Resampling.LANCZOS), (i * W, H + 20))
    d.text((i * W + 6, H + 4), shape, fill=(60, 60, 60))
sheet.save(sys.argv[2])
