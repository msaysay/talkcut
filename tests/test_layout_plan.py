"""Offline sentence roles and the rhythm limits around them."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.layout_plan import build_plan, load_rules, load_script, write_agent_request


def _line(text, start, end, role=None, sid="x"):
    return {"id": sid, "text": text, "start": start, "end": end, "role": role}


class LayoutPlanTest(unittest.TestCase):
    def test_demo_script_covers_every_role(self):
        sentences = load_script(ROOT / "examples" / "demo-script.json")
        plan = build_plan(sentences, "vertical")
        roles = [item["role"] for item in plan["items"]]
        for role in ("hook", "pain", "opinion", "case", "number", "list", "gold", "cta", "bridge"):
            self.assertIn(role, roles)
        by_role = {item["role"]: item for item in plan["items"]}
        self.assertEqual(by_role["hook"]["layout"], "v1")
        self.assertEqual(by_role["case"]["layout"], "v3")
        self.assertEqual(by_role["list"]["layout"], "v4")
        self.assertEqual(by_role["gold"]["layout"], "v5")
        self.assertIn("number-roll", by_role["number"]["effects"])
        self.assertIn("lower-third", by_role["cta"]["effects"])
        landscape = build_plan(sentences, "landscape")
        land = {item["role"]: item["layout"] for item in landscape["items"]}
        self.assertEqual(land["hook"], "h4")
        self.assertEqual(land["case"], "h1")
        self.assertEqual(land["list"], "h2")
        self.assertEqual(land["gold"], "h5")

    def test_first_three_seconds_stay_a_hook_even_with_a_digit(self):
        plan = build_plan([_line("三秒就划走", 0.2, 1.8, sid="a")], "vertical")
        self.assertEqual(plan["items"][0]["role"], "hook")

    def test_extra_gold_lines_are_demoted(self):
        rules = load_rules()
        rules["rhythm"]["alternateFaceAndGraphic"] = False
        sentences = [
            _line("真正重要的是第一句金句", 4, 6, sid="g1"),
            _line("真正留下的是第二句金句", 6, 8, sid="g2"),
        ]
        plan = build_plan(sentences, "vertical", rules)
        roles = [item["role"] for item in plan["items"]]
        self.assertEqual(roles.count("gold"), 1)
        self.assertIn("opinion", roles)

    def test_same_layout_breaks_after_the_limit(self):
        rules = load_rules()
        rules["rhythm"]["alternateFaceAndGraphic"] = False
        rules["rhythm"]["maxSameLayoutSentences"] = 2
        sentences = [_line("我认为这是判断", i * 2, i * 2 + 2, role="opinion", sid=f"o{i}") for i in range(3)]
        plan = build_plan(sentences, "vertical", rules)
        layouts = [item["layout"] for item in plan["items"]]
        self.assertEqual(layouts[0], "v1")
        self.assertEqual(layouts[1], "v1")
        self.assertNotEqual(layouts[2], "v1")

    def test_short_line_is_merged(self):
        sentences = [
            _line("我认为先讲判断", 0, 2.0, sid="a"),
            _line("所以", 2.0, 2.4, sid="b"),
        ]
        plan = build_plan(sentences, "vertical")
        self.assertEqual(len(plan["items"]), 1)
        self.assertIn("所以", plan["items"][0]["text"])

    def test_long_face_run_becomes_a_morph(self):
        rules = load_rules()
        rules["rhythm"]["alternateFaceAndGraphic"] = False
        rules["rhythm"]["maxSameLayoutSeconds"] = 100
        rules["rhythm"]["maxSameLayoutSentences"] = 20
        rules["rhythm"]["maxFaceSeconds"] = 11
        sentences = [_line("我认为这是判断", i * 3, i * 3 + 3, role="opinion", sid=f"o{i}") for i in range(5)]
        plan = build_plan(sentences, "vertical", rules, beats=[])
        layouts = [item["layout"] for item in plan["items"]]
        self.assertEqual(layouts[0], "v1")
        self.assertIn("v3", layouts)
        self.assertTrue(any("全屏人脸" in item["reason"] for item in plan["items"]))

    def test_display_text_stays_separate_from_the_spoken_line(self):
        plan = build_plan([
            {"id": "s1", "text": "你知道为什么三秒就划走吗", "displayText": "三秒就划走", "start": 0.2, "end": 1.8},
        ], "vertical", beats=[])
        self.assertEqual(plan["items"][0]["text"], "你知道为什么三秒就划走吗")
        self.assertEqual(plan["items"][0]["displayText"], "三秒就划走")

    def test_cut_snaps_toward_a_beat(self):
        rules = load_rules()
        rules["rhythm"]["alternateFaceAndGraphic"] = False
        sentences = [
            _line("我认为甲", 0, 2.0, role="opinion", sid="a"),
            _line("我认为乙", 2.0, 4.0, role="opinion", sid="b"),
        ]
        plan = build_plan(sentences, "vertical", rules, beats=[0, 1.85, 4.0])
        self.assertAlmostEqual(plan["items"][0]["end"], 1.85)
        self.assertEqual(plan["items"][1]["transitionBeat"], 1.85)

    def test_agent_mode_writes_a_prompt_and_does_not_classify(self):
        import tempfile

        sentences = load_script(ROOT / "examples" / "demo-script.json")
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            result = write_agent_request(folder, sentences)
            prompt = Path(result["prompt"]).read_text(encoding="utf-8")
            self.assertIn("不要调用", prompt)
            schema = json.loads(Path(result["schema"]).read_text(encoding="utf-8"))
            self.assertIn("hook", schema["properties"]["sentences"]["items"]["properties"]["role"]["enum"])
            self.assertFalse((folder / "layout-plan.json").exists())


if __name__ == "__main__":
    unittest.main()
