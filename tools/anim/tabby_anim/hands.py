"""Cartoon glove hands (white outline, black fill), like the upstream clips.

Local coordinates of a *right* hand, palm centre at (0, 0), fingers pointing
up (-y). The left hand is mirrored. Units are px at scale 1; a hand is about
70 px tall, matching the gloves in upstream clips such as `working_laptop_in`.
"""

from __future__ import annotations

from .shapes import BLACK, WHITE, Canvas, Xf, draw_figure

PALM = ("circle", (0, 0), 21)
CUFF = ("capsule", (-15, 27), (15, 27), 8)
FIST_KNUCKLES = ("capsule", (-15, -15), (15, -15), 11)


def _finger(x0: float, y0: float, x1: float, y1: float, r: float = 7.5) -> tuple:
    return ("capsule", (x0, y0), (x1, y1), r)


# shape -> (figure primitives, detail lines [(pts, width)])
GLOVES: dict[str, tuple[list[tuple], list[tuple[list[tuple[float, float]], float]]]] = {
    "open": (
        [PALM, CUFF,
         _finger(-14, -12, -25, -40), _finger(-5, -16, -8, -48), _finger(5, -16, 8, -48), _finger(14, -12, 23, -40),
         _finger(-18, 6, -38, -4, 7)],
        [],
    ),
    "fist": (
        [PALM, CUFF, FIST_KNUCKLES],
        [([(-5, -24), (-5, -10)], 3), ([(5, -24), (5, -10)], 3), ([(-15, -2), (-2, -2)], 3)],
    ),
    "point": (
        [PALM, CUFF, ("capsule", (-4, -15), (15, -15), 11), _finger(-10, -14, -10, -56)],
        [([(5, -24), (5, -10)], 3), ([(-15, -2), (-2, -2)], 3)],
    ),
    "thumbs_up": (  # fist turned sideways: curled fingers stacked to the right, thumb straight up
        [("circle", (-4, 4), 20), ("capsule", (-24, 30), (8, 30), 8),
         ("capsule", (0, -12), (18, -12), 9), ("capsule", (0, 3), (20, 3), 9), ("capsule", (0, 18), (18, 18), 9),
         _finger(-14, -8, -14, -46, 9.5)],
        [([(2, -4), (20, -4)], 3), ([(2, 11), (20, 11)], 3)],
    ),
    "peace": (
        [PALM, CUFF, ("capsule", (2, -15), (15, -15), 11), _finger(-12, -14, -20, -54), _finger(-2, -16, 4, -56)],
        [([(-15, -2), (-2, -2)], 3)],
    ),
    "hold": (  # curled fingers seen from the side, for holding props
        [PALM, CUFF, _finger(-14, -14, -22, -26, 8), _finger(-4, -18, -10, -32, 8), _finger(6, -18, 2, -32, 8),
         _finger(16, -14, 12, -26, 8), _finger(-18, 6, -32, -6, 7)],
        [],
    ),
}

HAND_SHAPES = sorted(GLOVES)


def draw_hand(cv: Canvas, xf: Xf, shape: str) -> None:
    if shape not in GLOVES:
        raise ValueError(f"unknown hand shape '{shape}', use one of {HAND_SHAPES}")
    prims, details = GLOVES[shape]
    draw_figure(cv, xf, prims, fill=BLACK, outline=WHITE, stroke=4.5)
    for pts, width in details:
        cv.polyline([xf(p) for p in pts], width * xf.scale, WHITE)
