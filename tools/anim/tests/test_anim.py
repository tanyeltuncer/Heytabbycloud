import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tabby_anim import cli, gif, rig

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


if __name__ == "__main__":
    unittest.main()
