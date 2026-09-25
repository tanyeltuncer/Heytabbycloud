"""Classic rubber-hose cartoon gloves: three chubby fingers and a thumb.

Shapes are organic outlines, not geometric primitives: every finger is a
bulb (narrow at the base, swelling towards a round tip, gently bent), the
palm is a soft blob that narrows towards the wrist, and the cuff is a puffy
rolled ring wider than the wrist, with curved creases.

Local coordinates of a *right* hand, palm facing the viewer (thumb on the
screen-left side), palm centre at (0, 0), fingers pointing up (-y). The left
hand is mirrored. About 90 px tall at scale 1 (fingertip to cuff).

Style (track `variant`):
  "filled"  (default) white glove, black contour and thin black crease lines.
  "outline" white contour on black, like the gloves in the upstream Taby clips.

Drawing order: a contour around the whole silhouette first, then the parts
in order; parts marked `sep` get their own thin contour on top of what is
already drawn (finger against palm, thumb in front of fingers).
"""

from __future__ import annotations

import math

from .shapes import BLACK, WHITE, Canvas, Xf, _prim, lerp_color

Pt = tuple[float, float]


def bulb(base: Pt, angle: float, length: float, wb: float, wt: float, bend: float = 0.0, n: int = 14) -> list[Pt]:
    """Finger outline. angle in degrees from straight up (clockwise positive),
    wb/wt = width at base/tip (wt > wb gives the chubby cartoon look),
    bend = sideways bow as a fraction of the length (+ bows to the right)."""
    a = math.radians(angle)
    d = (math.sin(a), -math.cos(a))   # along the finger
    nrm = (math.cos(a), math.sin(a))  # to the right of the finger

    def centre(s: float) -> Pt:
        bow = bend * length * 4 * s * (1 - s)
        return (base[0] + d[0] * length * s + nrm[0] * bow, base[1] + d[1] * length * s + nrm[1] * bow)

    def normal(s: float) -> Pt:
        p0, p1 = centre(max(0.0, s - 0.02)), centre(min(1.0, s + 0.02))
        tx, ty = p1[0] - p0[0], p1[1] - p0[1]
        m = math.hypot(tx, ty) or 1.0
        return (-ty / m, tx / m)

    def width(s: float) -> float:
        k = s * s * (3 - 2 * s)
        return wb + (wt - wb) * k

    right, left = [], []
    for i in range(n + 1):
        s = i / n * 0.999
        c, nn, w = centre(s), normal(s), width(s) / 2
        right.append((c[0] - nn[0] * w, c[1] - nn[1] * w))
        left.append((c[0] + nn[0] * w, c[1] + nn[1] * w))
    tip, nn, r = centre(1.0), normal(1.0), wt / 2
    p0 = centre(0.98)
    fwd = (tip[0] - p0[0], tip[1] - p0[1])
    ang0 = math.atan2(-nn[1], -nn[0])  # the right-edge side
    # sweep the round cap through the forward direction, from the right edge to the left edge
    sgn = 1 if math.cos(ang0 + math.pi / 2) * fwd[0] + math.sin(ang0 + math.pi / 2) * fwd[1] > 0 else -1
    cap = [(tip[0] + r * math.cos(ang0 + sgn * math.pi * j / 12), tip[1] + r * math.sin(ang0 + sgn * math.pi * j / 12))
           for j in range(13)]
    return right + cap + left[::-1]


def blob(cx: float, cy: float, rx: float, ry: float, taper: float = 0.0, power: float = 2.4, n: int = 48) -> list[Pt]:
    """Soft superellipse; taper > 0 narrows the lower half (towards the wrist)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** (2 / power), c)
        y = ry * math.copysign(abs(s) ** (2 / power), s)
        if y > 0:
            x *= 1 - taper * (y / ry)
        pts.append((cx + x, cy + y))
    return pts


def arc(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 10) -> list[Pt]:
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


PALM = blob(1, 2, 22, 21, taper=0.22)
CUFF = blob(1, 25, 16.5, 8, power=2.2)
CUFF_LINES = [arc(1, 18.5, 12.5, 40, 140, 10),             # rolled rim
              [(-5, 20), (-6, 25), (-5, 31)], [(7, 20), (8, 25), (7, 31)]]


def sausage(p0: Pt, p1: Pt, w0: float, w1: float | None = None, n: int = 14) -> list[Pt]:
    """Rounded at both ends, slightly fuller in the middle: a curled finger or a thumb seen whole."""
    w1 = w0 if w1 is None else w1
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    pts = []
    for j in range(n + 1):  # end cap at p1
        a = ang - math.pi / 2 + math.pi * j / n
        pts.append((p1[0] + w1 / 2 * math.cos(a), p1[1] + w1 / 2 * math.sin(a)))
    for j in range(n + 1):  # end cap at p0
        a = ang + math.pi / 2 + math.pi * j / n
        pts.append((p0[0] + w0 / 2 * math.cos(a), p0[1] + w0 / 2 * math.sin(a)))
    return pts


def roll(x: float, top: float = -20.0) -> list[Pt]:
    """A curled finger seen from the front: short and fat, round at both ends."""
    return sausage((x, 0), (x, top + 7), 14, 14.5)


def side_roll(y: float, length: float = 18.0) -> list[Pt]:
    """A curled finger seen from the side (thumbs up, grip): lying horizontally, pointing right."""
    return sausage((-2, y), (-2 + length, y), 13.5, 14.5)


def _knuckles(xs: list[float], y: float) -> list[list[Pt]]:
    return [arc(x, y, 5, 200, 340, 6) for x in xs]


# shape -> (parts [(outline, sep)], crease lines)
GLOVES: dict[str, tuple[list[tuple[list[Pt], bool]], list[list[Pt]]]] = {
    "open": (
        [(bulb((12, -9), 22, 30, 12, 16.5, 0.06), True),
         (bulb((1, -13), 2, 36, 12.5, 17.5, 0.02), True),
         (bulb((-10, -10), -20, 32, 12.5, 17, -0.06), True),
         (PALM, False),
         (bulb((-14, 6), -52, 22, 13.5, 16.5, 0.08), True),
         (CUFF, True)],
        [[(-5, -10), (-4.5, -4)], [(6.5, -11), (6.5, -5)], arc(-7, 7, 9, -30, 60, 8)],
    ),
    "fist": (
        [(PALM, False),
         (roll(12), True), (roll(1, -22), True), (roll(-10), True),
         (sausage((-18, 12), (2, -1), 13, 14.5), True),
         (CUFF, True)],
        _knuckles([12, 1, -10], -6),
    ),
    "point": (
        [(bulb((-6, -10), -2, 36, 13, 17, -0.02), True),
         (PALM, False),
         (roll(14, -18), True), (roll(4, -19), True),
         (sausage((-17, 11), (0, -1), 13, 14), True),
         (CUFF, True)],
        _knuckles([14, 4], -4),
    ),
    "peace": (
        [(bulb((5, -11), 13, 36, 12.5, 16.5, 0.03), True),
         (bulb((-8, -9), -17, 34, 12.5, 16.5, -0.03), True),
         (PALM, False),
         (roll(14, -17), True),
         (sausage((-17, 11), (5, -2), 13, 14.5), True),
         (CUFF, True)],
        _knuckles([14], -3),
    ),
    "thumbs_up": (  # fist turned sideways: curled fingers stacked to the right, thumb straight up
        [(bulb((-10, -4), -6, 30, 14.5, 19, 0.06), True),
         (blob(3, 5, 20, 22, taper=0.15), False),
         (side_roll(-10), True), (side_roll(4, 20), True), (side_roll(18, 17), True),
         (CUFF, True)],
        [arc(10, -10, 5, 290, 430, 6), arc(12, 4, 5, 290, 430, 6)],
    ),
    "hold": (  # gripping: fingers wrap across a held item (draw the item before the hand)
        [(PALM, False),
         (sausage((-8, -20), (17, -20), 13, 14), True),
         (sausage((-8, -6), (19, -6), 13.5, 14.5), True),
         (sausage((-8, 8), (17, 8), 13.5, 14.5), True),
         (bulb((-17, 10), -16, 30, 14, 16.5, 0.06), True),
         (CUFF, True)],
        [],
    ),
}

HAND_SHAPES = sorted(GLOVES)
HAND_STYLES = ("filled", "outline")
ARM_COLOR = (120, 120, 120)


def draw_hand(cv: Canvas, xf: Xf, shape: str, variant: str = "", arm: float = 0.0) -> None:
    if shape not in GLOVES:
        raise ValueError(f"unknown hand shape '{shape}', use one of {HAND_SHAPES}")
    style = variant or "filled"
    if style not in HAND_STYLES:
        raise ValueError(f"unknown hand style '{style}', use one of {HAND_STYLES}")
    fill, line = (WHITE, BLACK) if style == "filled" else (BLACK, WHITE)
    outer = 2.4 * xf.scale  # contour around the whole hand
    inner = 1.3 * xf.scale  # thin inner lines, like ink lines in the reference style
    parts, creases = GLOVES[shape]

    if arm > 1:  # optional rubber-hose arm below the cuff
        pts = [xf((1 + 5 * math.sin(i / 8 * math.pi / 2), 36 + arm * i / 8)) for i in range(9)]
        cv.polyline(pts, 8 * xf.scale, ARM_COLOR if style == "filled" else lerp_color(WHITE, BLACK, 0.3))

    for outline, _ in parts:
        _prim(cv, xf, ("poly", outline), outer, line)
    for outline, sep in parts:
        if sep:
            _prim(cv, xf, ("poly", outline), inner, line)
        _prim(cv, xf, ("poly", outline), 0.0, fill)
    for pts in CUFF_LINES + creases:
        cv.polyline([xf(p) for p in pts], 1.7 * xf.scale, line)
