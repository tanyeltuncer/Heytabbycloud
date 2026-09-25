"""Classic cartoon glove hands: three chubby fingers and a thumb, flared cuff.

Local coordinates of a *right* hand, palm facing the viewer (thumb on the
screen-left side), palm centre at (0, 0), fingers pointing up (-y). The left
hand is mirrored. About 95 px tall at scale 1 (fingertip to cuff).

Style (track `variant`):
  "filled"  (default) white glove, black outline and black crease lines, like
            classic rubber-hose cartoons.
  "outline" white outline on black, like the gloves in the upstream Taby clips.

A glove is drawn in layers. First the silhouette of *all* parts is stroked,
so the whole hand has one clean contour. Then the layers are filled in order;
layers marked `sep` get their own contour on top of what is already drawn,
which yields the separation lines between fingers, thumb and palm.
"""

from __future__ import annotations

import math

from .shapes import BLACK, WHITE, Canvas, Xf, _prim, lerp_color

Layer = tuple[list[tuple], bool]  # (primitives, separate contour?)


def finger(x0: float, y0: float, x1: float, y1: float, r0: float = 9.5, r1: float = 8.8) -> tuple:
    """Slightly tapered, rounded finger from base (x0, y0) to tip (x1, y1)."""
    return ("hull", [((x0, y0), r0), ((x1, y1), r1)])


def curled(x: float) -> tuple:
    """A finger curled down, seen from the front: a short fat roll."""
    return finger(x, -14, x, 0, 9.2, 9.2)


PALM = ("ellipse", (1, 3), 24, 23)
CUFF = ("hull", [((-11, 23), 6), ((13, 23), 6), ((-16, 32), 9), ((18, 32), 9)])  # small flared bell
CUFF_CREASES = [[(-5, 27), (-6, 39)], [(7, 27), (8, 39)]]
THUMB_ACROSS = finger(-24, 8, -3, 6, 9.4, 8.8)  # thumb folded over curled fingers

# shape -> (layers, crease lines). Proportions follow classic rubber-hose gloves:
# big round palm, short chubby fingers, stubby thumb, small flared cuff.
GLOVES: dict[str, tuple[list[Layer], list[list[tuple[float, float]]]]] = {
    "open": (
        [([finger(13, -11, 21, -34, 10, 9.5)], True),
         ([finger(1, -15, 3, -43, 10.5, 10)], True),
         ([finger(-11, -12, -17, -38, 10.5, 10)], True),
         ([PALM], False),
         ([finger(-17, 8, -34, -4, 10, 9.5)], True),
         ([CUFF], True)],
        [[(-4, 9), (2, 14), (9, 13)]],
    ),
    "fist": (
        [([PALM], False),
         ([curled(12)], True), ([curled(1)], True), ([curled(-10)], True),
         ([THUMB_ACROSS], True),
         ([CUFF], True)],
        [],
    ),
    "point": (
        [([finger(-7, -12, -6, -46, 10, 9.5)], True),
         ([PALM], False),
         ([curled(15)], True), ([curled(5)], True),
         ([finger(-24, 8, -4, 6, 9.4, 8.8)], True),
         ([CUFF], True)],
        [],
    ),
    "peace": (
        [([finger(5, -13, 11, -43, 10, 9.5)], True),
         ([finger(-9, -11, -16, -41, 10, 9.5)], True),
         ([PALM], False),
         ([curled(15)], True),
         ([finger(-24, 8, -2, 6, 9.4, 8.8)], True),
         ([CUFF], True)],
        [],
    ),
    "thumbs_up": (  # fist turned sideways: curled fingers stacked to the right, thumb straight up
        [([finger(-12, -4, -11, -42, 11, 10)], True),
         ([("ellipse", (3, 6), 21, 22)], False),
         ([finger(-4, -10, 16, -10, 9, 9)], True),
         ([finger(-4, 5, 18, 5, 9, 9)], True),
         ([finger(-4, 20, 15, 20, 9, 9)], True),
         ([CUFF], True)],
        [],
    ),
    "hold": (  # gripping: fingers wrap across a held item (draw the item before the hand)
        [([PALM], False),
         ([finger(-12, -22, 17, -22, 8.8, 8.8)], True),
         ([finger(-12, -7, 19, -7, 9, 9)], True),
         ([finger(-12, 8, 17, 8, 9, 9)], True),
         ([finger(-19, 9, -24, -21, 10, 9.4)], True),
         ([CUFF], True)],
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
    stroke = 3.8 * xf.scale  # outer contour
    inner = 1.6 * xf.scale   # thin inner separation lines, like the reference drawings
    layers, creases = GLOVES[shape]

    if arm > 1:  # optional rubber-hose arm hanging below the cuff
        pts = [xf((2 + 6 * math.sin(i / 8 * math.pi / 2), 40 + arm * i / 8)) for i in range(9)]
        cv.polyline(pts, 8 * xf.scale, ARM_COLOR if style == "filled" else lerp_color(WHITE, BLACK, 0.3))

    # 1) one contour around the whole silhouette (in the filled style a dark halo
    #    that keeps the white glove apart from white eyes behind it)
    for prims, _ in layers:
        for p in prims:
            _prim(cv, xf, p, stroke, line)
    # 2) fill the layers in order; `sep` layers get their own contour first
    for prims, sep in layers:
        if sep:
            for p in prims:
                _prim(cv, xf, p, inner, line)
        for p in prims:
            _prim(cv, xf, p, 0.0, fill)
    for pts in CUFF_CREASES + creases:
        cv.polyline([xf(p) for p in pts], 2.2 * xf.scale, line)
