import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import hashlib
import os
from unittest import mock

from tabby_anim import cli, edit, gif, originals, rig

REPO = Path(__file__).resolve().parents[3]
SOURCES = REPO / "animations" / "src"


def solid(color, size=gif.LANDSCAPE):
    return Image.new("RGB", size, color)


class GifFormatTests(unittest.TestCase):
    def test_delay_pattern_is_24_fps(self):
        delays = gif.delays_for(24)
        self.assertEqual(sum(delays), 1000)
        self.assertEqual(delays[:6], [40, 40, 40, 40, 40, 50])

    def test_stored_orientation_and_size(self):
        frame = solid((0, 0, 0))
        frame.paste((255, 255, 255), (0, 0, 40, 40))  # marker top-left in landscape
        enc = gif.encode([frame, solid((0, 0, 0))], loop=False)
        stored = Image.open(io.BytesIO(enc.data))
        self.assertEqual(stored.size, gif.STORED)
        # rotated 90 deg clockwise: landscape top-left lands at stored top-right
        self.assertEqual(stored.convert("RGB").getpixel((gif.STORED[0] - 5, 5)), (255, 255, 255))
        back = gif.decode(enc.data)[0]
        self.assertEqual(back.size, gif.LANDSCAPE)
        self.assertEqual(back.getpixel((5, 5)), (255, 255, 255))

    def test_near_black_is_clamped_to_pure_black(self):
        enc = gif.encode([solid((5, 5, 5))], loop=False)
        self.assertEqual(gif.decode(enc.data)[0].getpixel((100, 100)), (0, 0, 0))

    def test_loop_extension_only_for_loops(self):
        self.assertIn(b"NETSCAPE2.0", gif.encode([solid((0, 0, 0))], loop=True).data)
        self.assertNotIn(b"NETSCAPE2.0", gif.encode([solid((0, 0, 0))], loop=False).data)

    def test_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            gif.encode([solid((0, 0, 0), gif.STORED)], loop=False)

    def test_palette_limit(self):
        frames = [solid((i * 9 % 256, i * 37 % 256, i * 71 % 256)) for i in range(40)]
        self.assertLessEqual(gif.encode(frames, loop=False, max_colors=8).colors, 8)


class RigTests(unittest.TestCase):
    def test_interpolation_and_carry_over(self):
        kfs = [rig.Keyframe(0, {"look_x": 0}), rig.Keyframe(1, {"look_x": 10}, "linear"), rig.Keyframe(2, {"eye_open": 0})]
        self.assertAlmostEqual(rig.pose_at(kfs, 0.5).look_x, 5)
        self.assertAlmostEqual(rig.pose_at(kfs, 2).look_x, 10)  # carried over
        self.assertAlmostEqual(rig.pose_at(kfs, 5).eye_open, 0)

    def test_unknown_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            rig.pose_at([rig.Keyframe(0, {"laser_eyes": 1})], 0)

    def test_render_is_black_background_with_white_face(self):
        img = rig.render_pose(rig.Pose())
        self.assertEqual(img.size, gif.LANDSCAPE)
        self.assertEqual(img.getpixel((5, 5)), (0, 0, 0))
        self.assertEqual(img.getpixel((112, 140)), (255, 255, 255))  # inside left eye

    def test_loop_omits_duplicate_last_frame(self):
        kfs = [rig.Keyframe(0)]
        self.assertEqual(len(rig.render(kfs, 1.0, loop=True)), 24)
        self.assertEqual(len(rig.render(kfs, 1.0, loop=False)), 25)


class ExampleSourcesTests(unittest.TestCase):
    def test_all_examples_build_within_budget(self):
        with tempfile.TemporaryDirectory() as out:
            for src in sorted(p for p in SOURCES.iterdir() if (p / "meta.json").exists()):
                with self.subTest(src=src.name):
                    result = cli.build_one(src, Path(out))
                    entry = result["catalog_entry"]
                    self.assertEqual(entry["id"], src.name)
                    self.assertEqual(len(entry["sha256"]), 64)
                    self.assertLessEqual(result["kb"], json.loads((src / "meta.json").read_text())["max_kb"])
                    self.assertIn(entry["id"], result["firmware_row"])


class PartsTests(unittest.TestCase):
    """Hands, eye shapes and props from the parts catalogue."""

    FACE_OFF = rig.Keyframe(0, {"eye_open": 0.0, "mouth_curve": 0, "mouth_width": 40})

    def lit_pixels(self, img):
        return img.convert("L").point(lambda v: 255 if v > 40 else 0).histogram()[255]

    def test_every_eye_shape_renders_distinctly(self):
        pill = rig.render_pose(rig.Pose()).tobytes()
        for shape in rig.EYE_SHAPES:
            with self.subTest(shape=shape):
                img = rig.render_pose(rig.Pose(eye_shape=shape))
                self.assertEqual(img.getpixel((2, 2)), (0, 0, 0))
                if shape != "pill":
                    self.assertNotEqual(img.tobytes(), pill)

    def test_unknown_eye_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            rig.pose_at([rig.Keyframe(0, {"eye_shape": "laser"})], 0)

    def test_every_hand_shape_renders_and_left_mirrors_right(self):
        from PIL import ImageChops, ImageOps, ImageStat
        from tabby_anim.hands import HAND_SHAPES
        for shape in HAND_SHAPES:
            with self.subTest(shape=shape):
                frames = {}
                for side in ("left", "right"):
                    tr = rig.Track("hand", [rig.Keyframe(0, {"x": 228, "y": 140, "shape": shape})], side=side)
                    frames[side] = rig.render_frame(rig.Animation([self.FACE_OFF], 1, False, [tr]), 0)
                self.assertGreater(self.lit_pixels(frames["right"]), self.lit_pixels(rig.render_frame(
                    rig.Animation([self.FACE_OFF], 1, False), 0)) + 300)
                diff = ImageStat.Stat(ImageChops.difference(ImageOps.mirror(frames["left"]), frames["right"]).convert("L")).mean[0]
                self.assertLess(diff, 1.0)

    def test_every_prop_draws_something(self):
        from tabby_anim.props import PROPS
        empty = self.lit_pixels(rig.render_frame(rig.Animation([self.FACE_OFF], 1, False), 0))
        for name in PROPS:
            with self.subTest(prop=name):
                tr = rig.Track(name, [rig.Keyframe(0, {"x": 228, "y": 140, "progress": 0.6, "variant": ""})])
                img = rig.render_frame(rig.Animation([self.FACE_OFF], 1, False, [tr]), 0.3)
                self.assertGreater(self.lit_pixels(img), empty + 150)

    def test_invalid_tracks_are_rejected(self):
        base = {"duration_s": 1, "keyframes": [{"t": 0}]}
        for props in ([{"type": "rocket_ship", "keyframes": [{"t": 0}]}],
                      [{"type": "hand", "keyframes": [{"t": 0, "shape": "claw"}]}],
                      [{"type": "heart", "keyframes": [{"t": 0, "wobble": 1}]}],
                      [{"type": "heart", "attach_to": "nobody", "keyframes": [{"t": 0}]}]):
            with self.subTest(props=props):
                with self.assertRaises(ValueError):
                    rig.load_animation({**base, "props": props})

    def test_attached_prop_follows_its_parent(self):
        spec = {"duration_s": 1, "loop": False, "keyframes": [{"t": 0}], "props": [
            {"type": "hand", "name": "h", "keyframes": [{"t": 0, "x": 100, "y": 200}, {"t": 1, "x": 300, "y": 200}]},
            {"type": "heart", "attach_to": "h", "keyframes": [{"t": 0, "x": 0, "y": -50}]}]}
        anim = rig.load_animation(spec)
        by_name = {t.name: t for t in anim.tracks if t.name}
        xf0, _ = rig._track_xf(anim.tracks[1], {}, by_name, 0.0)
        xf1, _ = rig._track_xf(anim.tracks[1], {}, by_name, 1.0)
        self.assertAlmostEqual(xf0.x, 100)
        self.assertAlmostEqual(xf1.x, 300)
        self.assertAlmostEqual(xf1.y, 150)

    def test_strings_switch_at_their_keyframe(self):
        kfs = [rig.Keyframe(0, {"eye_shape": "pill"}), rig.Keyframe(1, {"eye_shape": "heart"})]
        self.assertEqual(rig.pose_at(kfs, 0.99).eye_shape, "pill")
        self.assertEqual(rig.pose_at(kfs, 1.0).eye_shape, "heart")

    def test_loop_examples_are_seamless(self):
        from PIL import ImageChops, ImageStat
        for src in sorted(p for p in SOURCES.iterdir() if (p / "keyframes.json").exists()):
            anim = rig.load_animation(json.loads((src / "keyframes.json").read_text()))
            if not anim.loop:
                continue
            with self.subTest(src=src.name):
                a, b = rig.render_frame(anim, 0.0), rig.render_frame(anim, anim.duration_s)
                self.assertLess(ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0], 1.0)



class FaceLayoutAndLiquidTests(unittest.TestCase):
    def test_default_layout_matches_measured_upstream_face(self):
        lay = rig.face_layout(rig.Pose())
        self.assertEqual([round(e["x"]) for e in lay["eyes"]], [112, 348])
        self.assertAlmostEqual(lay["bottom"], 195)
        self.assertAlmostEqual(lay["mouth"]["x"], 228)

    def test_face_moves_and_scales(self):
        lay = rig.face_layout(rig.Pose(face_x=100, face_scale=0.5))
        xs = [e["x"] for e in lay["eyes"]]
        self.assertAlmostEqual(sum(xs) / 2, 330)
        self.assertAlmostEqual(xs[1] - xs[0], 118)  # spacing halves with the face

    def test_turn_foreshortens_the_eye_in_turn_direction(self):
        left_turn = rig.face_layout(rig.Pose(turn=-0.8))["eyes"]
        self.assertLess(left_turn[0]["sw"], left_turn[1]["sw"])
        right_turn = rig.face_layout(rig.Pose(turn=0.8))["eyes"]
        self.assertLess(right_turn[1]["sw"], right_turn[0]["sw"])
        self.assertLess(rig.face_layout(rig.Pose(turn=-0.8))["mouth"]["x"], 228)

    def test_liquid_fills_requested_share_of_a_tilted_container(self):
        from tabby_anim.shapes import Xf, clip_below, poly_area
        xf = Xf(200, 140, rot=-50, scale=1.5)
        interior = [xf(p) for p in [(-23, -34), (23, -34), (17, 31), (-17, 31)]]
        total = poly_area(interior)
        for level in (0.2, 0.5, 0.9):
            lo, hi = min(p[1] for p in interior), max(p[1] for p in interior)
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if poly_area(clip_below(interior, mid)) / total > level else (lo, mid)
            self.assertAlmostEqual(poly_area(clip_below(interior, lo)) / total, level, places=2)

    def test_water_stream_stays_vertical_when_its_parent_rotates(self):
        spec = {"duration_s": 1, "loop": False, "keyframes": [{"t": 0, "eye_open": 0}], "props": [
            {"type": "bottle", "name": "b", "keyframes": [{"t": 0, "x": 200, "y": 60, "rot": -115, "show": 0.001}]},
            {"type": "water_stream", "attach_to": "b", "keyframes": [{"t": 0, "x": 0, "y": -66, "progress": 1}]}]}
        spec["keyframes"] = [{"t": 0, "pose": {"eye_open": 0, "mouth_width": 1}}]
        anim = rig.load_animation(spec)
        anim.tracks[0].keyframes[0].pose["show"] = 1.0
        img = rig.render_frame(anim, 0.0).convert("L")
        by_name = {t.name: t for t in anim.tracks if t.name}
        xf, _ = rig._track_xf(anim.tracks[1], {}, by_name, 0.0)
        # the column straight below the stream origin is lit over most of the stream length
        lit = sum(1 for y in range(int(xf.y) + 10, int(xf.y) + 90) if img.getpixel((round(xf.x), y)) > 60)
        self.assertGreater(lit, 60)


class GripTests(unittest.TestCase):
    def spec(self, shape):
        return {"duration_s": 1, "loop": False, "keyframes": [{"t": 0}], "props": [
            {"type": "hand", "name": "h", "keyframes": [{"t": 0, "x": 228, "y": 200, "shape": shape}]},
            {"type": "water_glass", "attach_to": "h", "keyframes": [{"t": 0, "x": 0, "y": -34, "progress": 0.8}]}]}

    def order(self, shape):
        anim = rig.load_animation(self.spec(shape))
        by = {t.name: t for t in anim.tracks if t.name}
        placed = [(tr, *rig._track_xf(tr, {}, by, 0.0)) for tr in anim.tracks]
        return [(tr.type, which) for tr, _, _, which in rig._draw_order(placed)]

    def test_grip_puts_the_item_between_palm_and_fingers(self):
        self.assertEqual(self.order("grip"), [("hand", "back"), ("water_glass", "all"), ("hand", "front")])
        self.assertEqual(self.order("grip_behind"), [("hand", "back"), ("water_glass", "all"), ("hand", "front")])

    def test_ordinary_hand_keeps_list_order(self):
        self.assertEqual(self.order("open"), [("hand", "all"), ("water_glass", "all")])

    def test_grip_fingers_cover_the_glass_front(self):
        from PIL import ImageChops, ImageStat
        a = rig.render_frame(rig.load_animation(self.spec("grip")), 0)
        b = rig.render_frame(rig.load_animation(self.spec("grip_behind")), 0)
        # fingers across the front make the two grips look clearly different over the glass
        self.assertGreater(ImageStat.Stat(ImageChops.difference(a, b).crop((190, 140, 270, 200)).convert("L")).mean[0], 20)


class SpriteHandTests(unittest.TestCase):
    def test_sprite_style_uses_drawings_and_falls_back_without_them(self):
        import os
        import tempfile as tf
        from PIL import Image as Img
        from tabby_anim import hands
        face = rig.Keyframe(0, {"eye_open": 0.0, "mouth_width": 1})

        def render():
            hands._sprite_cache.clear()
            tr = rig.Track("hand", [rig.Keyframe(0, {"x": 228, "y": 140, "shape": "open", "variant": "sprite"})])
            return rig.render_frame(rig.Animation([face], 1, False, [tr]), 0)

        with tf.TemporaryDirectory() as d:
            os.environ["TABBY_HAND_SPRITES"] = d
            try:
                fallback = render()  # no drawing -> procedural glove
                self.assertEqual(fallback.getpixel((228, 140)), (255, 255, 255))
                Img.new("RGBA", (40, 80), (255, 0, 0, 255)).save(Path(d) / "open.png")
                drawn = render()
                r, g, b = drawn.getpixel((228, 140))
                self.assertGreater(r, 200)
                self.assertLess(g, 60)  # the red test sprite is used
            finally:
                del os.environ["TABBY_HAND_SPRITES"]
                hands._sprite_cache.clear()


def fake_pack(root: Path, clips: dict) -> Path:
    """Minimal upstream-style asset pack: catalog.json + a/<sha8>.gif."""
    (root / "a").mkdir(parents=True, exist_ok=True)
    entries = []
    for anim_id, (frames, loop) in clips.items():
        enc = gif.encode(frames, loop=loop)
        rel = f"a/{enc.sha256[:8]}.gif"
        (root / rel).write_bytes(enc.data)
        entries.append({"id": anim_id, "duration_ms": enc.duration_ms, "loop_policy": "loop" if loop else "play_once",
                        "relative_path": rel, "byte_length": len(enc.data), "sha256": enc.sha256})
    (root / "catalog.json").write_text(json.dumps({"animations": entries}))
    return root


def ramp(n):
    """n frames with a white bar moving right, and one blue square (for recolor)."""
    out = []
    for i in range(n):
        f = solid((0, 0, 0))
        f.paste((255, 255, 255), (10 + i * 4, 100, 30 + i * 4, 180))
        f.paste((0, 151, 203), (300, 40, 360, 100))
        out.append(f)
    return out


class OriginalsAndEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.frames = ramp(24)
        self.frozen = [self.frames[0]] * 6 + self.frames[1:]  # identical frames get merged in the file
        fake_pack(Path(self.tmp.name), {"base": (self.frames, True), "other": (self.frozen, False)})
        self.env = mock.patch.dict(os.environ, {"TABBY_ORIGINALS": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_ops(self, ops, **extra):
        return edit.apply({"base": "base", "ops": ops, **extra}, originals.load)

    def test_load_is_pixel_identical_and_keeps_timeline(self):
        orig = originals.load("base")
        self.assertTrue(orig.loop)
        self.assertEqual(len(orig.frames), 24)
        for a, b in zip(orig.frames, self.frames):
            self.assertEqual(a.tobytes(), b.tobytes())
        # merged duplicate frames are expanded back to 24 fps
        self.assertEqual(len(originals.load("other").frames), len(self.frozen))

    def test_checksum_mismatch_is_rejected(self):
        cat = originals.catalog()
        path = Path(self.tmp.name) / cat["base"]["relative_path"]
        path.write_bytes(path.read_bytes() + b"x")
        with self.assertRaises(ValueError):
            originals.load("base")

    def test_timing_ops(self):
        f, loop = self.run_ops([{"op": "trim", "start_s": 0.25, "end_s": 0.75}])
        self.assertEqual(len(f), 12)
        self.assertEqual(f[0].tobytes(), self.frames[6].tobytes())
        self.assertTrue(loop)
        self.assertEqual(len(self.run_ops([{"op": "speed", "factor": 2}])[0]), 12)
        self.assertEqual(len(self.run_ops([{"op": "speed", "factor": 0.5}])[0]), 48)
        rev, _ = self.run_ops([{"op": "reverse"}])
        self.assertEqual(rev[0].tobytes(), self.frames[-1].tobytes())
        self.assertEqual(len(self.run_ops([{"op": "pingpong"}])[0]), 24 + 22)
        self.assertEqual(len(self.run_ops([{"op": "hold", "at_s": 0.5, "duration_s": 0.5}])[0]), 36)
        self.assertEqual(len(self.run_ops([{"op": "repeat", "times": 3}])[0]), 72)
        cat, loop = self.run_ops([{"op": "concat", "base": "other", "end_s": 0.5}], loop=False)
        self.assertEqual(len(cat), 36)
        self.assertFalse(loop)

    def test_image_ops(self):
        f, _ = self.run_ops([{"op": "recolor", "from": "#0097cb", "to": "#e0780a"}])
        self.assertEqual(f[3].getpixel((330, 70)), (224, 120, 10))
        self.assertEqual(f[3].getpixel((30, 140)), (255, 255, 255))  # other colours untouched
        f, _ = self.run_ops([{"op": "erase", "rect": [290, 30, 370, 110], "from_s": 0.5}])
        self.assertEqual(f[5].getpixel((330, 70)), (0, 151, 203))
        self.assertEqual(f[12].getpixel((330, 70)), (0, 0, 0))
        f, _ = self.run_ops([{"op": "move", "x": 40}])
        self.assertEqual(f[0].getpixel((330 + 40, 70)), (0, 151, 203))

    def test_overlay_draws_props_without_a_second_face(self):
        heart = [{"type": "heart", "keyframes": [{"t": 0, "x": 228, "y": 60, "variant": "pink"}]}]
        f, _ = self.run_ops([{"op": "overlay", "from_s": 0.5, "props": heart}])
        self.assertEqual(f[0].getpixel((228, 60)), (0, 0, 0))
        self.assertNotEqual(f[20].getpixel((228, 60)), (0, 0, 0))
        # everything outside the heart is still the original
        self.assertEqual(f[20].getpixel((330, 70)), (0, 151, 203))
        self.assertEqual(f[20].getpixel((228, 240)), (0, 0, 0))

    def test_errors(self):
        for ops in ([{"op": "explode"}], [{"op": "trim", "start_s": 5}], [{"op": "speed", "factor": 9}],
                    [{"op": "overlay", "props": [{"type": "heart", "x": 1, "keyframes": [{"t": 0}]}]}]):
            with self.subTest(ops=ops), self.assertRaises(ValueError):
                self.run_ops(ops)
        with self.assertRaises(KeyError):
            edit.apply({"base": "nope"}, originals.load)

    def test_edit_source_builds(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "remix"
            src.mkdir()
            (src / "meta.json").write_text(json.dumps({"id": "remix", "max_kb": 50}))
            (src / "edit.json").write_text(json.dumps({"base": "base", "ops": [{"op": "reverse"}]}))
            result = cli.build_one(src, Path(d) / "out")
            self.assertEqual(result["catalog_entry"]["loop_policy"], "loop")
            self.assertEqual(result["frames"], 24)


if __name__ == "__main__":
    unittest.main()
