"""Edit an original Taby animation: `animations/src/<id>/edit.json`.

    { "base": "drink_water", "loop": false,
      "ops": [ { "op": "trim", "start_s": 0.5, "end_s": 3.0 },
               { "op": "speed", "factor": 1.25 },
               { "op": "overlay", "from_s": 1.0, "props": [ ... rig props ... ] } ] }

Operations run in order on 24 fps frames; times always refer to the clip as
it is *after* the previous operations.
"""

from __future__ import annotations

from typing import Callable

from PIL import Image

from . import gif, rig

FPS = gif.FPS
MAX_FRAMES = 12 * FPS


def _idx(s: float, n: int) -> int:
    return max(0, min(n, round(float(s) * FPS)))


def _span(op: dict, n: int) -> range:
    return range(_idx(op.get("from_s", 0), n), _idx(op.get("to_s", n / FPS), n))


def _rgb(value) -> tuple[int, int, int]:
    if isinstance(value, str):
        v = value.lstrip("#")
        if len(v) != 6:
            raise ValueError(f"colour '{value}' must be #rrggbb")
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    r, g, b = value
    return int(r), int(g), int(b)


def _recolor(frame: Image.Image, src: tuple, dst: tuple, tol: float) -> Image.Image:
    """Swap one colour for another, including its anti-aliased edges against black:
    a pixel that is `src` darkened by factor a becomes `dst` darkened by a."""
    ss = sum(c * c for c in src) or 1
    cache: dict[tuple, tuple] = {}

    def remap(p):
        out = cache.get(p)
        if out is None:
            a = sum(x * y for x, y in zip(p, src)) / ss
            dist = sum((x - a * y) ** 2 for x, y in zip(p, src)) ** 0.5
            out = p
            if a > 0.08 and dist <= tol:
                a = min(1.0, a)
                out = tuple(round(c * a) for c in dst)
            cache[p] = out
        return out

    img = Image.new("RGB", frame.size)
    img.putdata([remap(p) for p in frame.getdata()])
    return img


def _transform(frame: Image.Image, dx: float, dy: float, scale: float) -> Image.Image:
    W, H = frame.size
    if scale != 1:
        sw, sh = round(W * scale), round(H * scale)
        scaled = frame.resize((sw, sh), Image.Resampling.LANCZOS)
    else:
        scaled, sw, sh = frame, W, H
    out = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(scaled, (round((W - sw) / 2 + dx), round((H - sh) / 2 + dy)))
    return out


def _overlay(frames: list[Image.Image], op: dict, loop: bool) -> list[Image.Image]:
    span = _span(op, len(frames))
    if not span:
        return frames
    whole = span.start == 0 and span.stop == len(frames)
    spec = {"duration_s": max(0.2, len(span) / FPS), "loop": loop and whole,
            "keyframes": [{"t": 0, "pose": {}}], "props": op.get("props", [])}
    if not spec["props"]:
        raise ValueError("overlay needs 'props'")
    anim = rig.load_animation(spec)
    anim.face = False
    out = list(frames)
    for k, i in enumerate(span):
        layer = rig.render_frame(anim, k / FPS)
        # black = transparent; anti-aliased edges blend over the original
        mask = layer.convert("L").point(lambda v: min(255, v * 4))
        out[i] = Image.composite(layer, frames[i], mask)
    return out


def apply(spec: dict, load_original: Callable) -> tuple[list[Image.Image], bool]:
    """Run edit.json. `load_original(id)` returns an originals.Original."""
    if "base" not in spec:
        raise ValueError("edit.json needs 'base' (id of an original)")
    base = load_original(spec["base"])
    frames, loop = list(base.frames), base.loop
    for n, op in enumerate(spec.get("ops", [])):
        kind = op.get("op")
        where = f"ops[{n}] ({kind})"
        count = len(frames)
        if kind == "trim":
            a, b = _idx(op.get("start_s", 0), count), _idx(op.get("end_s", count / FPS), count)
            frames = frames[a:b]
        elif kind == "speed":
            f = float(op["factor"])
            if not 0.25 <= f <= 4:
                raise ValueError(f"{where}: factor must be between 0.25 and 4")
            new = max(1, round(count / f))
            frames = [frames[min(count - 1, int(k * f))] for k in range(new)]
        elif kind == "reverse":
            frames = frames[::-1]
        elif kind == "pingpong":
            frames = frames + frames[-2:0:-1]
        elif kind == "hold":
            i = min(count - 1, _idx(op["at_s"], count))
            frames = frames[:i] + [frames[i]] * round(float(op["duration_s"]) * FPS) + frames[i:]
        elif kind == "concat":
            other = load_original(op["base"]).frames
            other = other[_idx(op.get("start_s", 0), len(other)):_idx(op.get("end_s", len(other) / FPS), len(other))]
            frames = frames + other
        elif kind == "repeat":
            frames = frames * int(op.get("times", 2))
        elif kind == "recolor":
            src, dst, tol = _rgb(op["from"]), _rgb(op["to"]), float(op.get("tolerance", 40))
            for i in _span(op, count):
                frames[i] = _recolor(frames[i], src, dst, tol)
        elif kind == "move":
            for i in _span(op, count):
                frames[i] = _transform(frames[i], op.get("x", 0), op.get("y", 0), float(op.get("scale", 1)))
        elif kind == "erase":
            x0, y0, x1, y1 = op["rect"]
            for i in _span(op, count):
                f = frames[i].copy()
                f.paste((0, 0, 0), (int(x0), int(y0), int(x1), int(y1)))
                frames[i] = f
        elif kind == "overlay":
            frames = _overlay(frames, op, loop)
        else:
            raise ValueError(f"{where}: unknown op, use trim, speed, reverse, pingpong, hold, concat, repeat, "
                             "recolor, move, erase or overlay")
        if not frames:
            raise ValueError(f"{where}: no frames left")
        if len(frames) > MAX_FRAMES:
            raise ValueError(f"{where}: clip longer than {MAX_FRAMES / FPS:.0f} s")
    loop = bool(spec.get("loop", loop))
    return frames, loop


def colors_of(frame: Image.Image, limit: int = 8) -> list[tuple[str, int]]:
    """Most frequent non-black colours of a frame as #rrggbb (helps choosing recolor sources)."""
    counts = frame.getcolors(1 << 18) or []
    out = [(n, c) for n, c in counts if max(c) > 40]
    out.sort(reverse=True)
    return [("#%02x%02x%02x" % c, n) for n, c in out[:limit]]
