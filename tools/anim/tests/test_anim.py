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


if __name__ == "__main__":
    unittest.main()
