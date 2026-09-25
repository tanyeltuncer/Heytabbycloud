"""Procedural Tabby face rig.

An animation is a list of keyframes over a few named parameters. That makes
it easy to write by hand *and* easy for an LLM to generate: describe a mood,
get keyframes back, render them here in the exact upstream look (pure black
background, white pill eyes, thin mouth stroke, few colours, 24 fps).

Geometry is measured from the upstream `idle_01_loop` clip (landscape view):
eyes ~73 x 124 px pills centred at x=112/348, y=133; mouth a ~94 px wide,
6 px thick arc around y=195. A blink squashes the eyes towards their bottom.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields

from PIL import Image, ImageDraw

from .gif import FPS, LANDSCAPE

SS = 4  # supersampling factor for smooth, anti-aliased edges

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MOUTH_RED = (214, 84, 77)
BLUSH_PINK = (240, 120, 140)


@dataclass
class Pose:
    look_x: float = 0.0       # px, whole face offset (eyes move 1.0, mouth 0.6)
    look_y: float = 0.0
    bounce: float = 0.0       # px, extra vertical offset of the whole face (negative = up)
    eye_open: float = 1.0     # 0 = closed line, 1 = fully open (squashes towards bottom)
    eye_scale: float = 1.0    # uniform eye size
    squash: float = 1.0       # >1 wider+flatter, <1 narrower+taller (volume kept)
    happy: float = 0.0        # 0 = pill eyes, 1 = "^ ^" arc eyes (crossfade by threshold)
    mouth_curve: float = 12.0  # px, >0 smile, <0 frown, 0 straight line
    mouth_width: float = 94.0
    mouth_open: float = 0.0   # 0 = stroke only, >0 = open mouth height in px
    blush: float = 0.0        # 0..1 cheek intensity


POSE_FIELDS = {f.name for f in fields(Pose)}


@dataclass
class Keyframe:
    t: float                  # seconds
    pose: dict = field(default_factory=dict)
    ease: str = "inOut"       # easing *into* this keyframe


def _ease(name: str, x: float) -> float:
    x = min(1.0, max(0.0, x))
    if name == "linear":
        return x
    if name == "in":
        return x ** 3
    if name == "out":
        return 1 - (1 - x) ** 3
    if name == "back":  # overshoot, then settle
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
    if name == "hold":
        return 0.0 if x < 1 else 1.0
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2  # inOut


def pose_at(keyframes: list[Keyframe], t: float) -> Pose:
    """Interpolate the pose at time t. Parameters not set in a keyframe carry over."""
    resolved: list[tuple[float, dict, str]] = []
    current = vars(Pose()).copy()
    for kf in sorted(keyframes, key=lambda k: k.t):
        unknown = set(kf.pose) - POSE_FIELDS
        if unknown:
            raise ValueError(f"unknown pose parameter(s): {sorted(unknown)}")
        current = {**current, **kf.pose}
        resolved.append((kf.t, current, kf.ease))
    if t <= resolved[0][0]:
        return Pose(**resolved[0][1])
    for (t0, p0, _), (t1, p1, ease) in zip(resolved, resolved[1:]):
        if t0 <= t <= t1:
            k = _ease(ease, (t - t0) / (t1 - t0) if t1 > t0 else 1.0)
            return Pose(**{n: p0[n] + (p1[n] - p0[n]) * k for n in POSE_FIELDS})
    return Pose(**resolved[-1][1])


def _eye(draw: ImageDraw.ImageDraw, cx: float, cy_bottom: float, p: Pose) -> None:
    w = 73 * p.eye_scale * p.squash
    h = 124 * p.eye_scale / p.squash
    if p.happy >= 0.5:
        # "^" arc eye: thick upward arc
        th = 16 * p.eye_scale
        box = [cx - w / 2, cy_bottom - h * 0.55, cx + w / 2, cy_bottom + h * 0.25]
        draw.arc([v * SS for v in box], start=200, end=340, fill=WHITE, width=int(th * SS))
        return
    # clamp: "back" easing may overshoot past fully open, eyes must not stretch
    eh = max(10.0, h * min(1.05, max(0.0, p.eye_open)))
    r = min(w, eh) * 0.42  # rounded rectangle, not a full pill (upstream look)
    box = [cx - w / 2, cy_bottom - eh, cx + w / 2, cy_bottom]
    draw.rounded_rectangle([v * SS for v in box], radius=r * SS, fill=WHITE)


def _mouth(draw: ImageDraw.ImageDraw, cx: float, cy: float, p: Pose) -> None:
    w = p.mouth_width
    th = 9
    if p.mouth_open > 1:
        h = p.mouth_open
        box = [cx - w / 2, cy - h, cx + w / 2, cy + h]
        draw.chord([v * SS for v in box], start=0, end=180, fill=MOUTH_RED, outline=WHITE, width=5 * SS)
        draw.line([(box[0] + 2) * SS, cy * SS, (box[2] - 2) * SS, cy * SS], fill=WHITE, width=5 * SS)
        return
    # Brush-like stroke: thickest in the middle, tapering to round ends.
    c = p.mouth_curve
    steps = 24
    top, bottom = [], []
    for i in range(steps + 1):
        u = -1 + 2 * i / steps
        x = cx + u * w / 2
        y = cy + c * (1 - u * u) - c / 2
        half = (th / 2) * (0.35 + 0.65 * math.sqrt(max(0.0, 1 - u * u)))
        top.append(((x) * SS, (y - half) * SS))
        bottom.append(((x) * SS, (y + half) * SS))
    draw.polygon(top + bottom[::-1], fill=WHITE)
    for u in (-1, 1):
        x, y = cx + u * w / 2, cy - c / 2
        r = th * 0.35 / 2
        draw.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=WHITE)


def render_pose(p: Pose) -> Image.Image:
    W, H = LANDSCAPE
    img = Image.new("RGB", (W * SS, H * SS), BLACK)
    draw = ImageDraw.Draw(img)
    ox, oy = p.look_x, p.look_y + p.bounce
    eye_bottom = 195 + oy
    for ex in (112, 348):
        _eye(draw, ex + ox, eye_bottom, p)
    if p.blush > 0.05:
        a = int(255 * min(1.0, p.blush))
        blush = tuple(int(c * a / 255) for c in BLUSH_PINK)
        for ex in (112, 348):
            bx, by = ex + ox + (-8 if ex < 228 else 8), eye_bottom + 14
            for i in range(5):  # short slanted strokes, like the upstream blush
                x0 = bx - 34 + i * 14
                draw.line([x0 * SS, (by + 8) * SS, (x0 + 12) * SS, (by - 5) * SS], fill=blush, width=4 * SS)
    _mouth(draw, 228 + ox * 0.6, 195 + oy * 0.6 + (8 if p.mouth_open > 1 else 0), p)
    return img.resize((W, H), Image.Resampling.LANCZOS)


def render(keyframes: list[Keyframe], duration_s: float, fps: int = FPS, loop: bool = True) -> list[Image.Image]:
    """Render all frames. For loops the last frame is omitted so frame 0 follows seamlessly."""
    n = round(duration_s * fps)
    count = n if loop else n + 1
    return [render_pose(pose_at(keyframes, i / fps)) for i in range(count)]


def load(spec: dict) -> tuple[list[Keyframe], float, bool]:
    """Parse a keyframes.json document."""
    kfs = [Keyframe(t=float(k["t"]), pose=k.get("pose", {}), ease=k.get("ease", "inOut")) for k in spec["keyframes"]]
    if not kfs:
        raise ValueError("keyframes must not be empty")
    duration = float(spec["duration_s"])
    if not 0.2 <= duration <= 12:
        raise ValueError("duration_s must be between 0.2 and 12 seconds")
    if math.isclose(kfs[0].t, 0) is False:
        kfs.insert(0, Keyframe(t=0.0))
    return kfs, duration, bool(spec.get("loop", True))
