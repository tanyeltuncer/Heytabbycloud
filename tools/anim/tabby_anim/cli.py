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

from PIL import Image

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
        keyframes, duration, loop = rig.load(json.loads(kf_path.read_text(encoding="utf-8")))
        return rig.render(keyframes, duration, loop=loop), loop
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
    args = parser.parse_args(argv)
    return args.func(args)
