"""Props (items) in the upstream look: flat colours, one highlight, white outline.

Every prop is drawn in local coordinates around its centre (0, 0) at about
60-90 px size, and receives:
  progress  animated number with a prop-specific meaning (see PROPS docs)
  t         clip time in seconds, for built-in cyclic motion (steam, zzz)
  variant   a colour or mode name
"""

from __future__ import annotations

import math

from .shapes import (BLACK, BLUE, BLUE_LIGHT, BROWN, BROWN_DARK, CREAM, GOLD, GOLD_DARK, GREEN, GREY, NAMED_COLORS,
                     PINK, RED, WHITE, Canvas, Xf, draw_figure, draw_liquid, drop_points, heart_points, lerp_color, rounded_rect,
                     star_points)


def _ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def water_glass(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """progress = water level 0 (empty) .. 1 (full). The surface stays level when tilted.
    Clear glass by default (face shows through); variant "opaque" for a black interior."""
    top, bottom, wt, wb = -36, 34, 26, 20
    body = [xf(p) for p in [(-wt, top), (wt, top), (wb, bottom), (-wb, bottom)]]
    if variant == "opaque":  # the old look: black inside
        cv.poly(body, BLACK)
    else:  # clear glass (default): what is behind shows through, faintly tinted
        cv.tint(body, BLUE_LIGHT, 0.34)
        # a bright glint along one wall so the glass reads as glass even when empty
        cv.capsule(xf((wt - 9, top + 8)), xf((wb - 6, bottom - 10)), xf.r(2.6), lerp_color(WHITE, BLUE_LIGHT, 0.3))
    interior = [xf(p) for p in [(-wt + 3, top + 2), (wt - 3, top + 2), (wb - 3, bottom - 3), (-wb + 3, bottom - 3)]]
    draw_liquid(cv, interior, progress, BLUE, BLUE_LIGHT)
    if progress > 0.15:  # glint on the glass wall
        cv.capsule(xf((-wb + 5, bottom - 12)), xf((-wt + 9, top + 14)), xf.r(2.2), lerp_color(BLUE_LIGHT, BLACK, 0.2))
    cv.polyline([xf(p) for p in [(-wt, top), (-wb, bottom), (wb, bottom), (wt, top)]], xf.r(5), WHITE)
    cv.polyline([xf((-wt, top)), xf((wt, top))], xf.r(2.5), lerp_color(WHITE, BLACK, 0.3))


BOTTLE_OUTLINE = [(-9, -64), (9, -64), (9, -44), (20, -30), (20, 46), (-20, 46), (-20, -30), (-9, -44)]


def bottle(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Water bottle; progress = fill level 0..1 (surface stays level when tilted).
    Its opening is at local (0, -64): attach a water_stream there for pouring."""
    draw_figure(cv, xf, [("poly", BOTTLE_OUTLINE)], fill=lerp_color(BLUE, BLACK, 0.82), stroke=4)
    inner = [(-6, -61), (6, -61), (6, -42), (17, -28), (17, 43), (-17, 43), (-17, -28), (-6, -42)]
    draw_liquid(cv, [xf(p) for p in inner], progress, BLUE, BLUE_LIGHT)
    label = NAMED_COLORS.get(variant, GREEN)
    cv.poly([xf(p) for p in [(-20, 6), (20, 6), (20, 26), (-20, 26)]], label)
    cv.capsule(xf((-13, -24)), xf((-13, 0)), xf.r(2.5), lerp_color(BLUE_LIGHT, BLACK, 0.3))


def water_stream(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Falling water, always vertical (ignores rotation), ~100 px long at scale 1.
    progress 0..1 the stream grows down from its origin, 1..2 its end falls away."""
    p = max(0.0, progress)
    if p <= 0.01 or p >= 1.99:
        return
    length = 100 * xf.scale
    x0, y0 = xf.x, xf.y
    head, tail = min(p, 1.0) * length, max(0.0, p - 1.0) * length
    width = 3.2 * xf.scale
    wob = 1.2 * math.sin(t * 25)
    cv.capsule((x0, y0 + tail), (x0 + wob, y0 + head), width, BLUE)
    if head - tail > 12:
        cv.capsule((x0 - 1, y0 + tail + 4), (x0 - 1 + wob, y0 + head - 6), width * 0.35, BLUE_LIGHT)
    if p >= 1.0 - 1e-6 or head >= length * 0.98:  # little splash at the bottom
        for i, dx in enumerate((-9, 8)):
            ph = (t * 3 + i * 0.27) % 1.0
            cv.circle((x0 + dx * (0.5 + ph), y0 + length - 4 - 10 * math.sin(math.pi * ph)), 2.4 * xf.scale, BLUE_LIGHT)


def water_drop(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """A single blue drop (splashes, tears). progress unused."""
    color = NAMED_COLORS.get(variant, BLUE)
    cv.poly([xf(p) for p in drop_points(0, 0, 12)], color)
    cv.circle(xf((-4, -2)), xf.r(3), BLUE_LIGHT)


def fireworks(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """progress 0..0.35 rocket rises to the centre, 0.35..1 burst expands and fades.
    variant: gold | pink | blue | green | purple | mix."""
    p = min(1.0, max(0.0, progress))
    palette = [GOLD, PINK, BLUE_LIGHT, GREEN] if variant == "mix" else [NAMED_COLORS.get(variant, GOLD)]
    if p < 0.35:
        k = _ease_out(p / 0.35)
        y = 90 * (1 - k)
        cv.capsule(xf((0, y)), xf((0, y + 22 * (1 - k) + 4)), xf.r(3), lerp_color(GOLD, BLACK, 0.3))
        cv.circle(xf((0, y)), xf.r(4.5), WHITE)
        return
    k = (p - 0.35) / 0.65
    radius = 75 * _ease_out(k)
    fade = k ** 2
    for i in range(14):
        a = math.radians(i * 360 / 14 + 8)
        col = lerp_color(palette[i % len(palette)], BLACK, fade)
        r0, r1 = radius * 0.55, radius
        cv.capsule(xf((r0 * math.cos(a), r0 * math.sin(a))), xf((r1 * math.cos(a), r1 * math.sin(a))),
                   xf.r(3.2 * (1 - 0.6 * k)), col)
        cv.circle(xf(((r1 + 7) * math.cos(a), (r1 + 7) * math.sin(a))), xf.r(3 * (1 - k)), lerp_color(WHITE, BLACK, fade))
    if k < 0.25:
        cv.circle(xf((0, 0)), xf.r(14 * (1 - k * 4)), WHITE)


def book(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """variant 'closed' (cover) or 'open' (spread, default). When open, every whole
    step of progress flips one page from right to left (0..1 = first flip)."""
    if variant == "closed":
        draw_figure(cv, xf, [("poly", rounded_rect(-30, -38, 30, 38, 6))], fill=RED)
        cv.capsule(xf((-22, -32)), xf((-22, 32)), xf.r(3), lerp_color(RED, BLACK, 0.35))
        for y in (-12, 0):
            cv.capsule(xf((-8, y)), xf((18, y)), xf.r(2.5), CREAM)
        return
    page_l = [(-62, -30), (-4, -24), (-4, 36), (-62, 30)]
    page_r = [(4, -24), (62, -30), (62, 30), (4, 36)]
    draw_figure(cv, xf, [("poly", page_l), ("poly", page_r)], fill=CREAM)
    for pts, x0, x1 in ((page_l, -52, -14), (page_r, 14, 52)):
        for i in range(4):
            y = -14 + i * 11
            cv.capsule(xf((x0, y)), xf((x1 - (6 if i == 3 else 0), y)), xf.r(1.6), GREY)
    phase = progress % 1.0
    if 0.02 < phase < 0.98:
        w = 58 * math.cos(math.pi * phase)  # page width shrinks, flips over the spine
        lift = 10 * math.sin(math.pi * phase)
        pts = [(0, -26 - lift), (w, -30 - lift), (w, 30 - lift), (0, 36)]
        draw_figure(cv, xf, [("poly", pts)], fill=lerp_color(CREAM, BLACK, 0.12), stroke=3.5)


def checklist(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Clipboard with three rows; progress 0..3 ticks them off (fractions draw the tick)."""
    draw_figure(cv, xf, [("poly", rounded_rect(-34, -42, 34, 44, 7))], fill=BROWN)
    cv.poly([xf(p) for p in rounded_rect(-27, -32, 27, 38, 4)], CREAM)
    draw_figure(cv, xf, [("poly", rounded_rect(-14, -48, 14, -34, 4))], fill=GREY, stroke=3)
    for i in range(3):
        y = -16 + i * 20
        cv.polyline([xf(p) for p in [(-20, y - 6), (-8, y - 6), (-8, y + 6), (-20, y + 6)]], xf.r(2.5), BROWN_DARK, closed=True)
        cv.capsule(xf((-1, y)), xf((20, y)), xf.r(2), GREY)
        k = min(1.0, max(0.0, progress - i))
        if k > 0:
            a, b, c = (-20, y), (-14, y + 7), (-3, y - 10)
            if k < 0.4:
                e = k / 0.4
                pts = [a, (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e)]
            else:
                e = (k - 0.4) / 0.6
                pts = [a, b, (b[0] + (c[0] - b[0]) * e, b[1] + (c[1] - b[1]) * e)]
            cv.polyline([xf(p) for p in pts], xf.r(5), GREEN)


def coffee(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Mug with rising steam (steam moves by itself over time)."""
    draw_figure(cv, xf, [("poly", rounded_rect(-26, -18, 22, 32, 8)), ("capsule", (22, -4), (22, 16), 10)], fill=BLACK)
    cv.capsule(xf((22, -4)), xf((22, 16)), xf.r(4), BLACK)
    cv.ellipse(xf((-2, -14)), xf.r(20), xf.r(4), BROWN)
    for j, x in enumerate((-12, 2, 14)):
        pts = []
        for i in range(9):
            yy = -26 - i * 5
            ph = t * 4 + j * 1.3 + i * 0.6
            pts.append((x + 4 * math.sin(ph), yy))
        cv.polyline([xf(p) for p in pts], xf.r(3), lerp_color(WHITE, BLACK, 0.35))


def heart(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """A pink heart; progress unused (animate scale for a pulse)."""
    color = NAMED_COLORS.get(variant, PINK)
    pts = [xf(p) for p in heart_points(0, 0, 60)]
    cv.poly(pts, color)
    cv.capsule(xf((-14, -12)), xf((-8, -18)), xf.r(3.5), lerp_color(color, WHITE, 0.6))


def sparkle(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Four-point twinkle; variant colour (default white)."""
    color = NAMED_COLORS.get(variant, WHITE)
    cv.poly([xf(p) for p in star_points(0, 0, 22, 5, n=4, rot=-90)], color)


def star(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Big golden reward star."""
    draw_figure(cv, xf, [("poly", star_points(0, 0, 38, 17))], fill=GOLD, outline=GOLD_DARK, stroke=4)
    cv.poly([xf(p) for p in star_points(-2, -2, 18, 8)], lerp_color(GOLD, WHITE, 0.45))


def trophy(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Golden cup."""
    cup = [(-28, -38), (28, -38), (22, -6), (8, 6), (-8, 6), (-22, -6)]
    for side in (-1, 1):
        cv.polyline([xf((side * x, y)) for x, y in [(24, -30), (38, -30), (36, -14), (20, -6)]], xf.r(6), GOLD_DARK)
    cv.poly([xf(p) for p in cup], GOLD)
    cv.poly([xf(p) for p in [(-4, 6), (4, 6), (6, 22), (-6, 22)]], GOLD_DARK)
    cv.poly([xf(p) for p in rounded_rect(-22, 22, 22, 36, 3)], GOLD_DARK)
    cv.capsule(xf((-16, -30)), xf((-12, -12)), xf.r(3.5), lerp_color(GOLD, WHITE, 0.55))


def clock(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Alarm clock; progress = minute hand turns (1 = full turn)."""
    for side in (-1, 1):
        cv.circle(xf((side * 24, -30)), xf.r(10), RED)
    cv.circle(xf((0, 0)), xf.r(40), WHITE)
    cv.circle(xf((0, 0)), xf.r(34), BLACK)
    for i in range(12):
        a = math.radians(i * 30)
        r0 = 26 if i % 3 else 22
        cv.capsule(xf((r0 * math.sin(a), -r0 * math.cos(a))), xf((30 * math.sin(a), -30 * math.cos(a))), xf.r(1.8), WHITE)
    a = 2 * math.pi * progress
    cv.capsule(xf((0, 0)), xf((22 * math.sin(a), -22 * math.cos(a))), xf.r(3), WHITE)
    b = a / 12 + math.radians(120)
    cv.capsule(xf((0, 0)), xf((14 * math.sin(b), -14 * math.cos(b))), xf.r(3.5), WHITE)
    cv.circle(xf((0, 0)), xf.r(5), RED)


def zzz(cv: Canvas, xf: Xf, progress: float, t: float, variant: str) -> None:
    """Three Z letters drifting up and fading (moves by itself over time)."""
    for i in range(3):
        ph = (t * 0.6 + i / 3) % 1.0
        size = 6 + 9 * ph
        x, y = -18 + 40 * ph, 30 - 80 * ph
        col = lerp_color(WHITE, BLACK, max(0.0, ph - 0.6) / 0.4)
        pts = [(x - size, y - size), (x + size, y - size), (x - size, y + size), (x + size, y + size)]
        cv.polyline([xf(p) for p in pts], xf.r(3 + 1.5 * ph), col)

PROPS = {
    "water_glass": water_glass, "bottle": bottle, "water_stream": water_stream, "water_drop": water_drop, "fireworks": fireworks, "book": book,
    "checklist": checklist, "coffee": coffee, "heart": heart, "sparkle": sparkle, "star": star,
    "trophy": trophy, "clock": clock, "zzz": zzz,
}
