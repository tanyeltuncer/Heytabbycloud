"""Access to the 84 original Taby animations from the upstream asset pack.

The originals are not committed to this repository (licence: private use,
guardrail L2). They are fetched on demand from the upstream firmware repo
into a local cache, and every file is checked against the sha256 in the
upstream catalog before use.

    TABBY_ORIGINALS=/path/to/assets/amoled-1.64   # optional: use an existing checkout
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import gif

UPSTREAM = "https://github.com/TRIIIS-LABS/firmware-taby.git"
PACK_SUBDIR = "assets/amoled-1.64"


@dataclass
class Original:
    id: str
    frames: list[Image.Image]  # landscape, resampled to the 24 fps timeline
    loop: bool
    entry: dict  # the upstream catalog entry


def pack_dir() -> Path:
    env = os.environ.get("TABBY_ORIGINALS")
    if env:
        return Path(env)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache / "tabby_anim" / "firmware-taby" / PACK_SUBDIR


def ensure_pack() -> Path:
    """Return the asset pack directory, cloning the upstream repo (sparse, shallow) if needed."""
    d = pack_dir()
    if (d / "catalog.json").exists():
        return d
    if os.environ.get("TABBY_ORIGINALS"):
        raise FileNotFoundError(f"TABBY_ORIGINALS={d} has no catalog.json")
    root = d.parents[len(Path(PACK_SUBDIR).parts) - 1]
    root.parent.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", UPSTREAM, str(root)],
                       check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "sparse-checkout", "set", PACK_SUBDIR], check=True, capture_output=True)
    if not (d / "catalog.json").exists():
        raise FileNotFoundError(f"upstream checkout has no {PACK_SUBDIR}/catalog.json")
    return d


def catalog() -> dict[str, dict]:
    d = ensure_pack()
    data = json.loads((d / "catalog.json").read_text(encoding="utf-8"))
    return {e["id"]: e for e in data["animations"]}


def to_timeline(stored: Image.Image, fps: int = gif.FPS) -> list[Image.Image]:
    """Decode a stored GIF and resample it to one frame per 1/fps s.
    GIF encoders merge identical frames and add up their delays; this undoes that."""
    frames, ends, t = [], [], 0
    for i in range(getattr(stored, "n_frames", 1)):
        stored.seek(i)
        frames.append(stored.convert("RGB").transpose(Image.Transpose.ROTATE_90))
        t += stored.info.get("duration", 40) or 40
        ends.append(t)
    count = max(1, round(t * fps / 1000))
    out, j = [], 0
    for k in range(count):
        mid = (k + 0.5) * 1000 / fps
        while j < len(ends) - 1 and ends[j] <= mid:
            j += 1
        out.append(frames[j])
    return out


def load(anim_id: str) -> Original:
    cat = catalog()
    if anim_id not in cat:
        raise KeyError(f"unknown original '{anim_id}' (python -m tabby_anim originals list)")
    entry = cat[anim_id]
    data = (pack_dir() / entry["relative_path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"{anim_id}: file does not match the sha256 in the upstream catalog")
    frames = to_timeline(Image.open(io.BytesIO(data)))
    return Original(anim_id, frames, entry.get("loop_policy") == "loop", entry)
