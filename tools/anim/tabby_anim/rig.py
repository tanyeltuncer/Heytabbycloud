"""Procedural Tabby face rig.

An animation is a list of keyframes over a few named parameters. That makes
it easy to write by hand *and* easy for an LLM to generate: describe a mood,
get keyframes back, render them here in the exact upstream look (pure black
background, white eyes, thin mouth stroke, glove hands, flat props, 24 fps).

Geometry is measured from the upstream `idle_01_loop` clip (landscape view):
eyes ~73 x 124 px rounded rectangles centred at x=112/348, y=133; mouth a
~94 px wide brush stroke around y=195. A blink squashes the eyes towards
their bottom.

Besides the face (`keyframes`), an animation can have `props`: tracks for
glove hands and items, each with its own keyframes (position, rotation,
scale, show, progress, shape/variant). A track can be attached to another
named track, e.g. a glass held by a hand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields

from PIL import Image, ImageDraw

from .gif import FPS, LANDSCAPE
from .hands import GLOVES, HAND_SHAPES, draw_hand
from .props import PROPS
from .shapes import (BLACK, BLUE, BLUE_LIGHT, GOLD, MOUTH_RED, PINK, RED, SS, WHITE, Canvas, Xf, drop_points,
                     heart_points, lerp_color, star_points)

BLUSH_PINK = PINK

EYE_SHAPES = ("pill", "happy", "closed", "angry", "sad", "squint", "heart", "star", "dizzy")


@dataclass
class Pose:
    look_x: float = 0.0       # px, whole face offset (eyes move 1.0, mouth 0.6)
    look_y: float = 0.0
    bounce: float = 0.0       # px, extra vertical offset of the whole face (negative = up)
    eye_open: float = 1.0     # 0 = closed line, 1 = fully open (squashes towards bottom)
    eye_scale: float = 1.0    # uniform eye size
    squash: float = 1.0       # >1 wider+flatter, <1 narrower+taller (volume kept)
    happy: float = 0.0        # legacy switch: >= 0.5 behaves like eye_shape "happy"
    mouth_curve: float = 12.0  # px, >0 smile, <0 frown, 0 straight line
    mouth_width: float = 94.0
    mouth_open: float = 0.0   # 0 = stroke only, >0 = open mouth height in px
    blush: float = 0.0        # 0..1 cheek intensity
    tears: float = 0.0        # 0..1 tears running from both eyes
    sweat: float = 0.0        # 0..1 sweat drop at the side of the head
    face_x: float = 0.0       # px, move the whole face (eyes, mouth, cheeks) anywhere on screen
    face_y: float = 0.0
    face_scale: float = 1.0   # whole face size, 0.5..1.2
    turn: float = 0.0         # -1..1 head turned to screen left (-) / right (+): eyes and mouth shift,
                              # spacing compresses, the far eye narrows (three-quarter side view)
    eye_shape: str = "pill"   # see EYE_SHAPES; switches at its keyframe (no blending)


POSE_FIELDS = {f.name for f in fields(Pose)}
TRACK_NUMBERS = {"x": 228.0, "y": 140.0, "rot": 0.0, "scale": 1.0, "show": 1.0, "progress": 0.0}
TRACK_STRINGS = {"shape", "variant"}


@dataclass
class Keyframe:
    t: float                  # seconds
    pose: dict = field(default_factory=dict)
    ease: str = "inOut"       # easing *into* this keyframe


@dataclass
class Track:
    type: str                 # "hand" or a prop name from props.PROPS
    keyframes: list[Keyframe]
    name: str = ""
    side: str = "right"       # hands only
    layer: str = "front"      # "front" (over the face) or "back"
    attach_to: str = ""       # name of another track; x/y/rot become relative to it


@dataclass
class Animation:
    keyframes: list[Keyframe]
    duration_s: float
    loop: bool = True
    tracks: list[Track] = field(default_factory=list)


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


def _interp(keyframes: list[Keyframe], t: float, defaults: dict, allowed: set[str]) -> dict:
    """Interpolate numbers; strings switch at their keyframe. Unset values carry over."""
    resolved: list[tuple[float, dict, str]] = []
    current = dict(defaults)
    for kf in sorted(keyframes, key=lambda k: k.t):
        unknown = set(kf.pose) - allowed
        if unknown:
            raise ValueError(f"unknown parameter(s): {sorted(unknown)}")
        current = {**current, **kf.pose}
        resolved.append((kf.t, current, kf.ease))
    if t <= resolved[0][0]:
        return dict(resolved[0][1])
    for (t0, p0, _), (t1, p1, ease) in zip(resolved, resolved[1:]):
        if t0 <= t <= t1:
            k = _ease(ease, (t - t0) / (t1 - t0) if t1 > t0 else 1.0)
            out = {}
            for n, v0 in p0.items():
                v1 = p1[n]
                if isinstance(v0, str) or isinstance(v1, str):
                    out[n] = v1 if t >= t1 else v0
                else:
                    out[n] = v0 + (v1 - v0) * k
            return out
    return dict(resolved[-1][1])


def pose_at(keyframes: list[Keyframe], t: float) -> Pose:
    values = _interp(keyframes, t, vars(Pose()), POSE_FIELDS)
    if values["eye_shape"] not in EYE_SHAPES:
        raise ValueError(f"unknown eye_shape '{values['eye_shape']}', use one of {EYE_SHAPES}")
    return Pose(**values)


def track_state(track: Track, t: float) -> dict:
    defaults = {**TRACK_NUMBERS, "shape": "open", "variant": ""}
    return _interp(track.keyframes, t, defaults, set(TRACK_NUMBERS) | TRACK_STRINGS)


# --- face ---------------------------------------------------------------------

def _eye_box(cx: float, bottom: float, p: Pose, sw: float = 1.0, sh: float = 1.0) -> tuple[float, float, float, float]:
    w = 73 * p.eye_scale * p.squash * sw
    h = 124 * p.eye_scale / p.squash * sh
    # clamp: "back" easing may overshoot past fully open, eyes must not stretch
    eh = max(10.0, h * min(1.05, max(0.0, p.eye_open)))
    return cx - w / 2, bottom - eh, cx + w / 2, bottom


def _eye(cv: Canvas, draw: ImageDraw.ImageDraw, cx: float, bottom: float, p: Pose, inner_right: bool,
         sw: float = 1.0, sh: float = 1.0) -> None:
    shape = "happy" if (p.eye_shape == "pill" and p.happy >= 0.5) else p.eye_shape
    w = 73 * p.eye_scale * p.squash * sw
    h = 124 * p.eye_scale / p.squash * sh
    cy = bottom - h / 2
    if shape == "happy":
        th = 16 * p.eye_scale * sh
        box = [cx - w / 2, bottom - h * 0.55, cx + w / 2, bottom + h * 0.25]
        draw.arc([v * SS for v in box], start=200, end=340, fill=WHITE, width=int(th * SS))
        return
    if shape == "closed" or (shape == "pill" and p.eye_open <= 0.02):
        cv.capsule((cx - w / 2 + 6 * sh, bottom - 6 * sh), (cx + w / 2 - 6 * sh, bottom - 6 * sh), 6 * sh, WHITE)
        return
    if shape == "squint":  # ">" on the left eye, "<" on the right eye
        d = 1 if inner_right else -1
        hw, hh = w / 2 - 4, h * 0.28
        pts = [(cx - d * hw, cy - hh), (cx + d * hw, cy), (cx - d * hw, cy + hh)]
        cv.polyline(pts, 15 * p.eye_scale * sh, WHITE)
        return
    if shape == "heart":
        cv.poly(heart_points(cx, cy + 6, w * 1.35), RED)
        cv.capsule((cx - w * 0.28, cy - w * 0.12), (cx - w * 0.18, cy - w * 0.22), 4, lerp_color(RED, WHITE, 0.6))
        return
    if shape == "star":
        cv.poly(star_points(cx, cy, w * 0.72, w * 0.32), GOLD)
        return
    if shape == "dizzy":
        pts = []
        for i in range(60):
            a = i * 0.36 + (0 if inner_right else math.pi)
            r = (3 + i * 0.55 * p.eye_scale) * sh
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        cv.polyline(pts, 7 * sh, WHITE)
        return
    x0, y0, x1, y1 = _eye_box(cx, bottom, p, sw, sh)
    r = min(x1 - x0, y1 - y0) * 0.42  # rounded rectangle, not a full pill (upstream look)
    draw.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=WHITE)
    if shape in ("angry", "sad"):
        inner, outer = (x1, x0) if inner_right else (x0, x1)
        low_x = inner if shape == "angry" else outer
        high_x = outer if shape == "angry" else inner
        # widen the cut past both edges so no anti-aliased sliver of the corner survives
        away = 8 if low_x > high_x else -8
        cut = [(high_x - away, y0 - 12), (low_x + away, y0 - 12), (low_x + away, y0 + (y1 - y0) * 0.42 + 3),
               (low_x, y0 + (y1 - y0) * 0.42)]
        cv.poly(cut, BLACK)


def _mouth(cv: Canvas, draw: ImageDraw.ImageDraw, cx: float, cy: float, p: Pose) -> None:
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
        top.append((x * SS, (y - half) * SS))
        bottom.append((x * SS, (y + half) * SS))
    draw.polygon(top + bottom[::-1], fill=WHITE)
    for u in (-1, 1):
        cv.circle((cx + u * w / 2, cy - c / 2), th * 0.35 / 2, WHITE)


def _cycle(t: float, period: float, duration: float, loop: bool) -> float:
    """Phase 0..1 of a repeating effect; for loops the period is snapped so it repeats seamlessly."""
    if loop and duration > 0:
        period = duration / max(1, round(duration / period))
    return (t / period) % 1.0


def face_layout(p: Pose) -> dict:
    """Screen positions of eyes and mouth after face_x/face_y/face_scale/turn."""
    k = p.face_scale
    turn = max(-1.0, min(1.0, p.turn))
    cx = 230 + p.face_x + p.look_x  # upstream eyes sit at x=112/348, i.e. centred on 230
    oy = p.face_y + p.look_y + p.bounce
    shift = 70 * turn * k
    half = 118 * k * (1 - 0.3 * abs(turn))
    eyes = []
    for side in (-1, 1):  # -1 = screen-left eye
        # three-quarter view: the eye in the turn direction is farther away, so it is foreshortened
        narrow = (turn > 0 and side > 0) or (turn < 0 and side < 0)
        sw = k * (1 - 0.45 * abs(turn)) if narrow else k * (1 + 0.06 * abs(turn))
        eyes.append({"x": cx + shift + side * half, "sw": sw, "sh": k * (1 - 0.06 * abs(turn) if narrow else 1),
                     "inner_right": side < 0})
    bottom = 140 + (195 - 140) * k + oy
    mouth = {"x": cx - 2 * k + shift * 1.35 - p.look_x * 0.4, "y": 140 + (195 - 140) * k + (p.face_y + p.bounce + p.look_y * 0.6),
             "w": k * (1 - 0.35 * abs(turn))}
    return {"eyes": eyes, "bottom": bottom, "mouth": mouth, "k": k}


def _face(cv: Canvas, draw: ImageDraw.ImageDraw, p: Pose, t: float, duration: float, loop: bool) -> None:
    lay = face_layout(p)
    k, eye_bottom = lay["k"], lay["bottom"]
    for e in lay["eyes"]:
        _eye(cv, draw, e["x"], eye_bottom, p, inner_right=e["inner_right"], sw=e["sw"], sh=e["sh"])
    if p.blush > 0.05:
        blush = lerp_color(BLACK, BLUSH_PINK, min(1.0, p.blush))
        for e in lay["eyes"]:
            out = -1 if e["inner_right"] else 1
            bx, by = e["x"] + out * 8 * k, eye_bottom + 14 * k
            n = 5 if e["sw"] >= k else 3
            for i in range(n):
                x0 = bx + (-34 + i * 14) * k * e["sw"] / k
                cv.capsule((x0, by + 8 * k), (x0 + 12 * k, by - 5 * k), 2 * k, blush)
    if p.tears > 0.05:
        ph = _cycle(t, 0.7, duration, loop)
        for e in lay["eyes"]:
            x = e["x"] + (22 if e["inner_right"] else -22) * e["sw"]
            for off in (0.0, 0.5):
                q = (ph + off) % 1.0
                y = eye_bottom + 4 + q * 70 * k
                size = 7 * k * min(1.0, p.tears) * (1 - 0.3 * q)
                cv.poly(drop_points(x, y, size), lerp_color(BLUE, BLACK, max(0.0, q - 0.7) / 0.3))
    if p.sweat > 0.05:
        q = _cycle(t, 1.6, duration, loop)
        right = lay["eyes"][1]
        x, y = right["x"] + 72 * k, eye_bottom - 125 * k + 30 * k * q
        size = 9 * k * min(1.0, p.sweat)
        cv.poly(drop_points(x, y, size), BLUE_LIGHT)
        cv.circle((x - 3 * k, y - 1 * k), size * 0.3, WHITE)
    m = lay["mouth"]
    mp = Pose(**{**vars(p), "mouth_width": p.mouth_width * m["w"], "mouth_curve": p.mouth_curve * k,
                 "mouth_open": p.mouth_open * k})
    _mouth(cv, draw, m["x"], m["y"] + (8 * k if p.mouth_open > 1 else 0), mp)


# --- tracks (hands and props) ---------------------------------------------------

def _track_xf(track: Track, states: dict[str, dict], tracks_by_name: dict[str, Track], t: float, depth: int = 0) -> tuple[Xf, dict]:
    st = states.setdefault(id(track), track_state(track, t))
    show = max(0.0, st["show"])
    xf = Xf(st["x"], st["y"], st["rot"], st["scale"] * show, mirror=(track.type == "hand" and track.side == "left"))
    if track.attach_to:
        if depth > 4 or track.attach_to not in tracks_by_name:
            raise ValueError(f"attach_to '{track.attach_to}' does not name another track")
        parent_xf, _ = _track_xf(tracks_by_name[track.attach_to], states, tracks_by_name, t, depth + 1)
        px, py = parent_xf((st["x"], st["y"]))
        xf = Xf(px, py, parent_xf.rot + st["rot"], st["scale"] * show * (parent_xf.scale or 1), xf.mirror)
    return xf, st


def _draw_track(cv: Canvas, track: Track, xf: Xf, st: dict, t: float) -> None:
    if xf.scale <= 0.02:
        return
    if track.type == "hand":
        draw_hand(cv, xf, st["shape"])
    else:
        PROPS[track.type](cv, xf, st["progress"], t, st["variant"])


def render_frame(anim: Animation, t: float) -> Image.Image:
    W, H = LANDSCAPE
    img = Image.new("RGB", (W * SS, H * SS), BLACK)
    draw = ImageDraw.Draw(img)
    cv = Canvas(draw)
    by_name = {tr.name: tr for tr in anim.tracks if tr.name}
    states: dict[int, dict] = {}
    placed = [(tr, *_track_xf(tr, states, by_name, t)) for tr in anim.tracks]
    for tr, xf, st in placed:
        if tr.layer == "back":
            _draw_track(cv, tr, xf, st, t)
    _face(cv, draw, pose_at(anim.keyframes, t), t, anim.duration_s, anim.loop)
    for tr, xf, st in placed:
        if tr.layer != "back":
            _draw_track(cv, tr, xf, st, t)
    return img.resize((W, H), Image.Resampling.LANCZOS)


def render_pose(p: Pose, t: float = 0.0) -> Image.Image:
    """Render a single face pose (no props)."""
    return render_frame(Animation([Keyframe(0.0, {k: getattr(p, k) for k in POSE_FIELDS})], 1.0, False), t)


def render_animation(anim: Animation, fps: int = FPS) -> list[Image.Image]:
    """Render all frames. For loops the last frame is omitted so frame 0 follows seamlessly."""
    n = round(anim.duration_s * fps)
    count = n if anim.loop else n + 1
    return [render_frame(anim, i / fps) for i in range(count)]


def render(keyframes: list[Keyframe], duration_s: float, fps: int = FPS, loop: bool = True) -> list[Image.Image]:
    return render_animation(Animation(keyframes, duration_s, loop), fps)


# --- loading ------------------------------------------------------------------

def _keyframes(raw: list[dict], where: str, flat: bool) -> list[Keyframe]:
    out = []
    for k in raw:
        if "t" not in k:
            raise ValueError(f"{where}: every keyframe needs 't'")
        pose = {n: v for n, v in k.items() if n not in ("t", "ease")} if flat else k.get("pose", {})
        out.append(Keyframe(t=float(k["t"]), pose=pose, ease=k.get("ease", "inOut")))
    if not out:
        raise ValueError(f"{where}: keyframes must not be empty")
    if not math.isclose(out[0].t, 0):
        out.insert(0, Keyframe(t=0.0))
    return out


def load_animation(spec: dict) -> Animation:
    """Parse a keyframes.json document."""
    duration = float(spec["duration_s"])
    if not 0.2 <= duration <= 12:
        raise ValueError("duration_s must be between 0.2 and 12 seconds")
    tracks = []
    for i, raw in enumerate(spec.get("props", [])):
        kind = raw.get("type", "")
        if kind != "hand" and kind not in PROPS:
            raise ValueError(f"props[{i}]: unknown type '{kind}', use 'hand' or one of {sorted(PROPS)}")
        tr = Track(type=kind, keyframes=_keyframes(raw.get("keyframes", []), f"props[{i}]", flat=True),
                   name=raw.get("name", ""), side=raw.get("side", "right"), layer=raw.get("layer", "front"),
                   attach_to=raw.get("attach_to", ""))
        if tr.side not in ("left", "right") or tr.layer not in ("front", "back"):
            raise ValueError(f"props[{i}]: side must be left/right, layer front/back")
        for kf in tr.keyframes:
            shape = kf.pose.get("shape")
            if kind == "hand" and shape is not None and shape not in GLOVES:
                raise ValueError(f"props[{i}]: unknown hand shape '{shape}', use one of {HAND_SHAPES}")
        tracks.append(tr)
    anim = Animation(_keyframes(spec["keyframes"], "keyframes", flat=False), duration, bool(spec.get("loop", True)), tracks)
    render_frame(anim, 0.0)  # validates every parameter name up front
    return anim


def load(spec: dict) -> tuple[list[Keyframe], float, bool]:
    """Backwards-compatible: face keyframes only."""
    anim = load_animation(spec)
    return anim.keyframes, anim.duration_s, anim.loop
