"""GIF encoding/decoding in the format the Taby firmware plays (LVGL lv_gif).

Frames are handled in *landscape* orientation (456 x 280), the way the
animation is seen on the device. On disk the upstream packs store them
rotated by 90 degrees clockwise (280 x 456).
"""

from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
from dataclasses import dataclass

from PIL import Image

LANDSCAPE = (456, 280)
STORED = (280, 456)
FPS = 24
# GIF delays are centiseconds; 24 fps = 41.67 ms is stored as 4,4,4,4,4,5
# (six frames = 250 ms), exactly like the upstream packs.
DELAY_PATTERN_MS = (40, 40, 40, 40, 40, 50)
BLACK_THRESHOLD = 8


@dataclass
class EncodedGif:
    data: bytes
    frame_count: int
    duration_ms: int
    colors: int

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def delays_for(frame_count: int) -> list[int]:
    return [DELAY_PATTERN_MS[i % len(DELAY_PATTERN_MS)] for i in range(frame_count)]


def clamp_black(frame: Image.Image, threshold: int = BLACK_THRESHOLD) -> Image.Image:
    """Force near-black pixels to pure #000000 (AMOLED pixels fully off)."""
    rgb = frame.convert("RGB")
    lum = rgb.convert("L").point(lambda v: 255 if v >= threshold else 0)
    black = Image.new("RGB", rgb.size, (0, 0, 0))
    return Image.composite(rgb, black, lum)


def _global_palette(frames: list[Image.Image], max_colors: int) -> Image.Image:
    """Build one palette from *all* frames (short flashes of colour must survive);
    black and white are always kept."""
    w, h = frames[0].size
    strip = Image.new("RGB", (w, h * len(frames) + 2), (0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (0, i * h))
    strip.putpixel((0, h * len(frames)), (255, 255, 255))
    return strip.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def encode(frames: list[Image.Image], *, loop: bool, max_colors: int = 16) -> EncodedGif:
    """Encode landscape RGB frames into a firmware-ready GIF."""
    if not frames:
        raise ValueError("no frames")
    for f in frames:
        if f.size != LANDSCAPE:
            raise ValueError(f"frame size {f.size}, expected {LANDSCAPE} (landscape)")

    prepared = [clamp_black(f).transpose(Image.Transpose.ROTATE_270) for f in frames]
    palette = _global_palette(prepared, max_colors)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in prepared]

    delays = delays_for(len(indexed))
    params = dict(save_all=True, append_images=indexed[1:], duration=delays, disposal=1, optimize=False)
    if loop:
        params["loop"] = 0  # NETSCAPE2.0 extension only on looping clips, as upstream
    buf = io.BytesIO()
    indexed[0].save(buf, format="GIF", **params)
    data = optimize(buf.getvalue())

    used = set()
    for f in indexed:
        used.update(c for _, c in f.getcolors(256))
    # Pillow merges identical consecutive frames and sums their delays (upstream
    # packs do the same), so count what actually landed in the file.
    stored = Image.open(io.BytesIO(data))
    stored_delays = []
    for i in range(stored.n_frames):
        stored.seek(i)
        stored_delays.append(stored.info.get("duration", 0))
    return EncodedGif(data, stored.n_frames, sum(stored_delays), len(used))


def optimize(data: bytes) -> bytes:
    """Delta-optimise with gifsicle when available (cropped frames + transparency,
    the same structure as the upstream packs). Never lossy: that smears the edges."""
    exe = shutil.which("gifsicle")
    if not exe:
        return data
    result = subprocess.run([exe, "-O3", "--no-comments", "--no-names"], input=data, capture_output=True, check=True)
    return result.stdout if len(result.stdout) < len(data) else data


def decode(data: bytes | str) -> list[Image.Image]:
    """Decode a stored GIF back into landscape RGB frames."""
    im = Image.open(io.BytesIO(data) if isinstance(data, bytes) else data)
    frames = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        frames.append(im.convert("RGB").transpose(Image.Transpose.ROTATE_90))
    return frames
