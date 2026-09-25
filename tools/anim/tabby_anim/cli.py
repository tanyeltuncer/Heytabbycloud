"""Command line: build animation sources into firmware-ready GIFs.

    python -m tabby_anim build animations/src --out dist/animations
    python -m tabby_anim extract some.gif --out frames/

A source directory `animations/src/<id>/` contains `meta.json` and either
`keyframes.json` (procedural face rig) or `frames/*.png` (456 x 280, 24 fps,
black background) exported from any animation tool.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from . import gif, rig

ID_RE = re.compile(r"^[a-z0-9_]{1,80}$")


def load_meta(src: Path) -> dict:
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    if not ID_RE.match(meta.get("id", "")):
        raise ValueError(f"{src}: id must match {ID_RE.pattern}")
    if meta["id"] != src.name:
        raise ValueError(f"{src}: id '{meta['id']}' must equal the folder name")
    meta.setdefault("label", meta["id"].upper()[:12])
    meta.setdefault("max_colors", 16)
    meta.setdefault("max_kb", 150)
    return meta


def load_frames(src: Path, meta: dict) -> tuple[list[Image.Image], bool]:
    kf_path = src / "keyframes.json"
    if kf_path.exists():
        anim = rig.load_animation(json.loads(kf_path.read_text(encoding="utf-8")))
        return rig.render_animation(anim), anim.loop
    pngs = sorted((src / "frames").glob("*.png"))
    if not pngs:
        raise ValueError(f"{src}: needs keyframes.json or frames/*.png")
    return [Image.open(p).convert("RGB") for p in pngs], bool(meta.get("loop", False))


def build_one(src: Path, out: Path) -> dict:
    meta = load_meta(src)
    frames, loop = load_frames(src, meta)
    enc = gif.encode(frames, loop=loop, max_colors=int(meta["max_colors"]))
    kb = len(enc.data) / 1024
    if kb > meta["max_kb"]:
        raise ValueError(f"{meta['id']}: {kb:.0f} KB exceeds budget of {meta['max_kb']} KB")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{meta['id']}.gif").write_bytes(enc.data)
    preview = frames[len(frames) // 2].resize((228, 140))
    preview.save(out / f"{meta['id']}.preview.png")
    entry = {
        "id": meta["id"],
        "version": 1,
        "duration_ms": enc.duration_ms,
        "fallback_label": meta["label"],
        "loop_policy": "loop" if loop else "play_once",
        "relative_path": f"a/{enc.sha256[:8]}.gif",
        "byte_length": len(enc.data),
        "sha256": enc.sha256,
    }
    firmware_row = (
        f'    {{"{meta["id"]}", "/assets/animations/{meta["id"]}.gif", NULL, 0, '
        f'{enc.duration_ms}U, {"true" if loop else "false"}}},'
    )
    return {"catalog_entry": entry, "firmware_row": firmware_row, "frames": enc.frame_count,
            "colors": enc.colors, "kb": round(kb, 1)}


def cmd_build(args: argparse.Namespace) -> int:
    root = Path(args.src)
    sources = [root] if (root / "meta.json").exists() else sorted(p for p in root.iterdir() if (p / "meta.json").exists())
    report = {}
    failed = False
    for src in sources:
        try:
            report[src.name] = build_one(src, Path(args.out))
            r = report[src.name]
            print(f"ok   {src.name}: {r['frames']} frames, {r['colors']} colours, {r['kb']} KB")
        except Exception as exc:  # report every source, fail at the end
            failed = True
            print(f"FAIL {src.name}: {exc}", file=sys.stderr)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


def cmd_extract(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(gif.decode(Path(args.gif).read_bytes())):
        frame.save(out / f"{i:04d}.png")
    print(f"extracted to {out}")
    return 0


def contact_sheet(frames: list[Image.Image], times_ms: list[int], columns: int = 4, count: int = 12) -> Image.Image:
    """Evenly spaced frames with timestamps, for reviewing timing and poses at a glance."""
    count = min(count, len(frames))
    idx = [round(i * (len(frames) - 1) / max(1, count - 1)) for i in range(count)]
    w, h = 228, 140
    rows = (count + columns - 1) // columns
    sheet = Image.new("RGB", (columns * w, rows * (h + 16)), (45, 45, 45))
    draw = ImageDraw.Draw(sheet)
    for k, i in enumerate(idx):
        x, y = (k % columns) * w, (k // columns) * (h + 16)
        draw.text((x + 4, y + 2), f"{times_ms[i] / 1000:.2f} s", fill=(230, 230, 230))
        sheet.paste(frames[i].resize((w - 4, h - 4)), (x + 2, y + 16))
    return sheet


def cmd_preview(args: argparse.Namespace) -> int:
    src = Path(args.src)
    if src.suffix == ".gif":
        stored = Image.open(src)
        frames, times, t = [], [], 0
        for i in range(stored.n_frames):
            stored.seek(i)
            frames.append(stored.convert("RGB").transpose(Image.Transpose.ROTATE_90))
            times.append(t)
            t += stored.info.get("duration", 40)
    else:
        meta = load_meta(src)
        frames, _ = load_frames(src, meta)
        times = [round(i * 1000 / gif.FPS) for i in range(len(frames))]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet(frames, times, count=args.count).save(out)
    print(f"preview written to {out} ({len(frames)} frames)")
    return 0


def catalog_sheet() -> Image.Image:
    """Every eye shape, hand shape and prop on one labelled sheet (for review and docs)."""
    from .hands import HAND_SHAPES
    from .props import PROPS

    tiles: list[tuple[str, Image.Image]] = []
    for shape in rig.EYE_SHAPES:
        tiles.append((f"eye_shape: {shape}", rig.render_pose(rig.Pose(eye_shape=shape))))
    tiles.append(("tears + sweat", rig.render_pose(rig.Pose(tears=1, sweat=1, mouth_curve=-8), t=0.3)))
    tiles.append(("blush + mouth_open", rig.render_pose(rig.Pose(blush=1, mouth_open=16, mouth_width=70, eye_shape="happy"))))
    progress = {"water_glass": 0.7, "fireworks": 0.6, "book": 0.4, "checklist": 2.7, "clock": 0.3}
    variant = {"fireworks": "mix", "book": "open"}
    for shape in HAND_SHAPES:
        face = rig.Keyframe(0, {"eye_open": 0.0, "mouth_curve": 0, "mouth_width": 40})
        tr = rig.Track("hand", [rig.Keyframe(0, {"x": 228, "y": 150, "shape": shape, "scale": 1.6})])
        tiles.append((f"hand: {shape}", rig.render_frame(rig.Animation([face], 1, False, [tr]), 0)))
    for name in PROPS:
        face = rig.Keyframe(0, {"eye_open": 0.0, "mouth_curve": 0, "mouth_width": 40})
        tr = rig.Track(name, [rig.Keyframe(0, {"x": 228, "y": 140, "scale": 1.5,
                                               "progress": progress.get(name, 0.0), "variant": variant.get(name, "")})])
        tiles.append((f"prop: {name}", rig.render_frame(rig.Animation([face], 1, False, [tr]), 0.4)))
    cols, w, h = 5, 228, 140
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 16)), (45, 45, 45))
    draw = ImageDraw.Draw(sheet)
    for k, (label, img) in enumerate(tiles):
        x, y = (k % cols) * w, (k // cols) * (h + 16)
        draw.text((x + 4, y + 2), label, fill=(230, 230, 230))
        sheet.paste(img.resize((w - 4, h - 4)), (x + 2, y + 16))
    return sheet


def cmd_catalog(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    catalog_sheet().save(out)
    print(f"catalog written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tabby_anim")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build sources into GIFs + catalog entries")
    b.add_argument("src")
    b.add_argument("--out", default="dist/animations")
    b.set_defaults(func=cmd_build)
    e = sub.add_parser("extract", help="decode a stored GIF into landscape PNG frames")
    e.add_argument("gif")
    e.add_argument("--out", required=True)
    e.set_defaults(func=cmd_extract)
    pv = sub.add_parser("preview", help="contact sheet with timestamps (source folder or GIF)")
    pv.add_argument("src")
    pv.add_argument("--out", required=True)
    pv.add_argument("--count", type=int, default=12)
    pv.set_defaults(func=cmd_preview)
    cg = sub.add_parser("catalog", help="sheet with every eye shape, hand shape and prop")
    cg.add_argument("--out", required=True)
    cg.set_defaults(func=cmd_catalog)
    args = parser.parse_args(argv)
    return args.func(args)
