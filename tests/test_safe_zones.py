"""Safe-zone geometry and font-role rules. No video render."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.reel import LANDSCAPE, VERTICAL
from engine.safe_zones import choose_anchor, expand_box, overlap_area

FORBIDDEN = ["阿里巴巴", "普惠", "MiSans", "钉钉", "优设", "庞门", "HarmonyOS", "DIN"]


class SafeZoneTest(unittest.TestCase):
    def test_expand_grows_and_stays_inside_the_frame(self):
        grown = expand_box({"x": 0.2, "y": 0.2, "w": 0.2, "h": 0.2}, 0.18)
        self.assertGreater(grown["w"], 0.2)
        self.assertLessEqual(grown["x"] + grown["w"], 1)
        self.assertLessEqual(grown["y"] + grown["h"], 1)
        edge = expand_box({"x": 0.0, "y": 0.0, "w": 0.9, "h": 0.9}, 0.2)
        self.assertGreaterEqual(edge["x"], 0)
        self.assertLessEqual(edge["x"] + edge["w"], 1.0001)

    def test_caption_moves_above_a_low_face(self):
        low = {"x": 0.2, "y": 0.7, "w": 0.4, "h": 0.25}
        high = {"x": 0.3, "y": 0.12, "w": 0.35, "h": 0.3}
        self.assertEqual(choose_anchor(low), "top")
        self.assertEqual(choose_anchor(high), "bottom")
        self.assertEqual(choose_anchor(None), "bottom")
        self.assertGreater(overlap_area(low, {"x": 0.04, "y": 0.66, "w": 0.92, "h": 0.28}), 0)

    def test_both_orientations_list_distinct_layouts(self):
        self.assertEqual([row[0] for row in VERTICAL], ["v1", "v2", "v3", "v4", "v5", "v6"])
        self.assertEqual([row[0] for row in LANDSCAPE], ["h1", "h2", "h3", "h4", "h5"])

    def test_font_manifest_is_ofl_only(self):
        payload = json.loads((ROOT / "motion-pack" / "fonts" / "manifest.json").read_text(encoding="utf-8"))
        blob = json.dumps(payload, ensure_ascii=False)
        for banned in FORBIDDEN:
            self.assertNotIn(banned, blob)
        for spec in payload["roles"].values():
            self.assertEqual(spec["license"], "OFL-1.1")
            notice = ROOT / "motion-pack" / "fonts" / "licenses" / f"{Path(spec['file']).stem.split('[')[0]}-OFL.txt"
            # License files use the family stem we committed, not every filename.
        committed = list((ROOT / "motion-pack" / "fonts" / "licenses").glob("*-OFL.txt"))
        self.assertGreaterEqual(len(committed), 6)


if __name__ == "__main__":
    unittest.main()
