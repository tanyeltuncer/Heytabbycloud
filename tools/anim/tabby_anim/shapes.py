"""Drawing primitives for the rig: supersampled canvas, transforms and
outlined figures in the upstream style (white outline, flat fill)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import ImageDraw

SS = 4  # supersampling factor

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (150, 150, 150)
BLUE = (30, 160, 225)
BLUE_LIGHT = (150, 225, 255)
RED = (225, 65, 55)
MOUTH_RED = (214, 84, 77)
PINK = (240, 120, 140)
GOLD = (245, 190, 40)
GOLD_DARK = (205, 135, 25)
GREEN = (85, 165, 70)
BROWN = (150, 95, 60)
BROWN_DARK = (95, 60, 40)
CREAM = (245, 236, 212)
ORANGE = (250, 135, 45)
PURPLE = (165, 110, 235)

NAMED_COLORS = {
    "white": WHITE, "blue": BLUE, "red": RED, "pink": PINK, "gold": GOLD,
    "green": GREEN, "orange": ORANGE, "purple": PURPLE, "brown": BROWN,
}

Point = tuple[float, float]


@dataclass
class Xf:
    """Local → screen transform: scale, clockwise rotation (deg), optional mirror."""

    x: float = 0.0
    y: float = 0.0
    rot: float = 0.0
    scale: float = 1.0
    mirror: bool = False

    def __call__(self, p: Point) -> Point:
        lx, ly = p
        if self.mirror:
            lx = -lx
        a = math.radians(self.rot)
        c, s = math.cos(a), math.sin(a)
        return (self.x + self.scale * (lx * c - ly * s), self.y + self.scale * (lx * s + ly * c))

    def r(self, radius: float) -> float:
        return radius * self.scale

    def child(self, x: float = 0.0, y: float = 0.0, rot: float = 0.0, scale: float = 1.0) -> "Xf":
        ox, oy = self((x, y))
        return Xf(ox, oy, self.rot + (-rot if self.mirror else rot), self.scale * scale, self.mirror)


class Canvas:
    """ImageDraw wrapper working in logical (non-supersampled) pixels."""

    def __init__(self, draw: ImageDraw.ImageDraw):
        self.d = draw

    @staticmethod
    def _p(p: Point) -> tuple[float, float]:
        return (p[0] * SS, p[1] * SS)

    def circle(self, c: Point, r: float, fill) -> None:
        if r <= 0:
            return
        self.d.ellipse([(c[0] - r) * SS, (c[1] - r) * SS, (c[0] + r) * SS, (c[1] + r) * SS], fill=fill)

    def ellipse(self, c: Point, rx: float, ry: float, fill) -> None:
        if rx <= 0 or ry <= 0:
            return
        self.d.ellipse([(c[0] - rx) * SS, (c[1] - ry) * SS, (c[0] + rx) * SS, (c[1] + ry) * SS], fill=fill)

    def capsule(self, a: Point, b: Point, r: float, fill) -> None:
        if r <= 0:
            return
        self.d.line([self._p(a), self._p(b)], fill=fill, width=max(1, round(2 * r * SS)))
        self.circle(a, r, fill)
        self.circle(b, r, fill)

    def polyline(self, pts: list[Point], width: float, fill, closed: bool = False) -> None:
        if len(pts) < 2 or width <= 0:
            return
        seq = pts + [pts[0]] if closed else pts
        for a, b in zip(seq, seq[1:]):
            self.capsule(a, b, width / 2, fill)

    def poly(self, pts: list[Point], fill) -> None:
        if len(pts) >= 3:
            self.d.polygon([self._p(p) for p in pts], fill=fill)


# --- outlined figures --------------------------------------------------------
# A figure is a list of primitives in local coordinates:
#   ("circle", (x, y), r) | ("capsule", (x1, y1), (x2, y2), r) | ("poly", [(x, y), ...])
# draw_figure() first paints every primitive grown by the stroke width in the
# outline colour, then every primitive in the fill colour. The union of the
# shapes therefore gets one clean outline, like the upstream glove hands.


def rounded_rect(x0: float, y0: float, x1: float, y1: float, r: float, n: int = 6) -> list[Point]:
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts: list[Point] = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _prim(cv: Canvas, xf: Xf, prim: tuple, grow: float, fill) -> None:
    kind = prim[0]
    if kind == "circle":
        cv.circle(xf(prim[1]), xf.r(prim[2]) + grow, fill)
    elif kind == "capsule":
        cv.capsule(xf(prim[1]), xf(prim[2]), xf.r(prim[3]) + grow, fill)
    elif kind == "poly":
        pts = [xf(p) for p in prim[1]]
        cv.poly(pts, fill)
        if grow > 0:
            cv.polyline(pts, 2 * grow, fill, closed=True)
    else:
        raise ValueError(f"unknown primitive {kind}")


def draw_figure(cv: Canvas, xf: Xf, prims: list[tuple], fill, outline=WHITE, stroke: float = 4.5) -> None:
    s = stroke * xf.scale
    if outline is not None:
        for p in prims:
            _prim(cv, xf, p, s, outline)
    for p in prims:
        _prim(cv, xf, p, 0.0, fill)


def lerp_color(a, b, k: float):
    k = min(1.0, max(0.0, k))
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def star_points(cx: float, cy: float, r_out: float, r_in: float, n: int = 5, rot: float = -90) -> list[Point]:
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def heart_points(cx: float, cy: float, size: float, n: int = 40) -> list[Point]:
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * size / 32, cy - y * size / 32))
    return pts


def drop_points(cx: float, cy: float, size: float, n: int = 24) -> list[Point]:
    """Tear/water drop, tip up, (cx, cy) = centre of the round part."""
    pts = [(cx, cy - size * 1.6)]
    for i in range(n + 1):
        a = math.radians(-30 + 240 * i / n)  # round bottom
        pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
    return pts


# --- liquids ------------------------------------------------------------------
# Liquid inside a (possibly rotated) container keeps a horizontal surface: we
# clip the container interior in screen space below a horizontal line whose
# height is solved so that the enclosed area matches the fill level.


def poly_area(pts: list[Point]) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2


def clip_below(pts: list[Point], y: float) -> list[Point]:
    """Part of the polygon with screen y >= y (below the line, since y grows downwards)."""
    out: list[Point] = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        ina, inb = a[1] >= y, b[1] >= y
        if ina:
            out.append(a)
        if ina != inb:
            k = (y - a[1]) / (b[1] - a[1])
            out.append((a[0] + (b[0] - a[0]) * k, y))
    return out


def draw_liquid(cv: Canvas, interior: list[Point], level: float, color, highlight=None) -> None:
    """Fill `level` (0..1) of the interior polygon (screen coords) with a level surface."""
    level = min(1.0, max(0.0, level))
    if level <= 0.005 or len(interior) < 3:
        return
    total = poly_area(interior)
    lo, hi = min(p[1] for p in interior), max(p[1] for p in interior)
    for _ in range(30):  # binary search the surface height
        mid = (lo + hi) / 2
        if poly_area(clip_below(interior, mid)) / total > level:
            lo = mid
        else:
            hi = mid
    body = clip_below(interior, (lo + hi) / 2)
    cv.poly(body, color)
    if highlight is not None and level < 0.995:
        surface = [p for p in body if abs(p[1] - (lo + hi) / 2) < 0.01]
        if len(surface) >= 2:
            xs = sorted(p[0] for p in surface)
            y = (lo + hi) / 2 + 2
            if xs[-1] - xs[0] > 8:
                cv.capsule((xs[0] + 4, y), (xs[-1] - 4, y), 1.8, highlight)
