"""Regression for the ported cut kernel and a synthetic talking-head export."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.errors import TalkCutError
from engine.media import probe
from engine.pipeline import apply_edit, export_movie, import_media, propose, read_project
from engine.runtime import require_ffmpeg
from engine.shared.audio_cuts import apply_audio_cuts
from engine.shared.speech_alignment import aligned_chars, interior_filler_context
from engine.native_audio import seconds
from engine.synthetic import make_breath_demo, make_filler_demo


def _overlap(left: tuple[float, float], right: tuple[float, float]) -> float:
    return min(left[1], right[1]) - max(left[0], right[0])


class PortedHelpersTest(unittest.TestCase):
    def test_audio_cuts_split_a_word(self):
        source = [
            {
                "id": "s1",
                "words": [
                    {"word": "今", "start": 0.0, "end": 0.4},
                    {"word": "嗯", "start": 0.4, "end": 0.7},
                    {"word": "天", "start": 0.7, "end": 1.1},
                ],
            }
        ]
        clip = {
            "id": "s1",
            "start": 0.0,
            "end": 1.1,
            "firstIndex": 0,
            "lastIndex": 2,
            "text": "今嗯天",
        }
        pieces = apply_audio_cuts(
            [clip],
            source,
            {"s1:0:2": [{"id": "a" * 32, "start": 0.4, "end": 0.7, "wordCut": True}]},
        )
        self.assertEqual(len(pieces), 2)
        self.assertLess(pieces[0]["end"], 0.41)
        self.assertGreater(pieces[1]["start"], 0.69)

    def test_alignment_chars_and_filler_context(self):
        row = {
            "text": "好",
            "start": 0.0,
            "end": 0.4,
            "words": [{"word": "好"}],
        }
        groups = [{"word": "好", "start": 0.0, "end": 0.4, "probability": 0.9}]
        chars = aligned_chars(row, groups, groups)
        self.assertEqual([item["word"] for item in chars], ["好"])
        source = {
            "words": [{"word": "你"}, {"word": "说"}, {"word": "嗯"}, {"word": "得"}, {"word": "对"}],
        }
        edit = {
            "words": source["words"],
            "removed": [2],
            "deleted": False,
        }
        self.assertTrue(interior_filler_context(source, edit))

    def test_native_clock(self):
        self.assertAlmostEqual(seconds("1:02.5"), 62.5)

    def test_whisper_path_is_explicit_when_missing(self):
        from engine.asr import transcribe

        if __import__("engine.asr", fromlist=["available"]).available():
            self.skipTest("faster-whisper is installed")
        with self.assertRaises(TalkCutError):
            transcribe(Path("/tmp/does-not-matter.wav"))


class SyntheticEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ffmpeg, ffprobe = require_ffmpeg()
        cls.ffmpeg = ffmpeg
        cls.ffprobe = ffprobe

    def test_breath_and_silence_are_removed_from_the_mp4(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            demo = make_breath_demo(folder, self.ffmpeg)
            project = folder / "project"
            imported = import_media(demo["video"], project, asr="energy")
            self.assertEqual(imported["asr"], "energy")
            proposal = propose(project)
            self.assertFalse((project / "export" / "final.mp4").exists())
            self.assertEqual(proposal["directions"][0]["video_type"], "pillar_daily")
            self.assertTrue(proposal["directions"][0]["cut_candidates"])
            changes = {
                "summary": "去掉气口和长静音",
                "revision": imported["revision"],
                "confirmed": True,
                "cleanup": {"breath": True, "filler": True, "silence": True},
            }
            applied = apply_edit(project, changes)
            self.assertGreater(applied["durationKept"], 1.2)
            self.assertLess(applied["durationKept"], 1.8)
            for region in demo["regions"]:
                window = (region["start"], region["end"])
                covered = sum(max(0.0, _overlap(window, (span["start"], span["end"]))) for span in applied["spans"])
                if region["kind"] == "speech":
                    self.assertGreater(covered, (region["end"] - region["start"]) * 0.8, region)
                else:
                    self.assertLess(covered, 0.06, region)
            exported = export_movie(project)
            info = probe(self.ffprobe, Path(exported["movie"]))
            self.assertTrue(info["hasVideo"])
            self.assertTrue(info["hasAudio"])
            self.assertLess(info["duration"], demo["duration"] - 1.6)
            self.assertTrue(Path(exported["bundle"]).is_file())

    def test_keep_human_moment_preserves_breath(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            demo = make_breath_demo(folder, self.ffmpeg)
            project = folder / "project"
            imported = import_media(demo["video"], project)
            read = read_project(project)
            breath_segments = [
                segment["id"]
                for segment in read["segments"]
                if any(word.get("kind") == "breath" for word in segment["words"])
            ]
            self.assertTrue(breath_segments)
            changes = {
                "summary": "这段气口留下",
                "revision": imported["revision"],
                "confirmed": True,
                "cleanup": {"breath": True, "silence": True, "filler": True},
                "keepHumanMoments": [{"id": breath_segments[0], "reason": "breath"}],
            }
            applied = apply_edit(project, changes)
            breath = next(region for region in demo["regions"] if region["kind"] == "breath")
            covered = sum(
                max(0.0, _overlap((breath["start"], breath["end"]), (span["start"], span["end"])))
                for span in applied["spans"]
            )
            self.assertGreater(covered, 0.2)

    def test_explicit_filler_word_is_cut_even_when_loud(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            demo = make_filler_demo(folder, self.ffmpeg)
            project = folder / "project"
            imported = import_media(demo["video"], project, transcript=demo["transcript"])
            segment = imported["segments"][0]
            index = next(i for i, word in enumerate(segment["words"]) if word["word"] == "嗯")
            changes = {
                "summary": "去掉填充词嗯",
                "revision": imported["revision"],
                "confirmed": True,
                "removeWords": [{"id": segment["id"], "indices": [index], "quote": "嗯", "reason": "filler"}],
            }
            applied = apply_edit(project, changes)
            filler = demo["words"][1]
            covered = sum(
                max(0.0, _overlap((filler["start"], filler["end"]), (span["start"], span["end"])))
                for span in applied["spans"]
            )
            self.assertLess(covered, 0.05)
            kept_text = "".join(span["text"] for span in applied["spans"])
            self.assertNotIn("嗯", kept_text)
            self.assertIn("今天", kept_text)
            exported = export_movie(project)
            info = probe(self.ffprobe, Path(exported["movie"]))
            self.assertLess(info["duration"], demo["duration"] - 0.15)

    def test_stale_revision_and_unconfirmed_apply_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            demo = make_breath_demo(folder, self.ffmpeg)
            project = folder / "project"
            imported = import_media(demo["video"], project)
            with self.assertRaises(TalkCutError):
                apply_edit(project, {"summary": "未确认", "revision": imported["revision"], "confirmed": False})
            with self.assertRaises(TalkCutError):
                apply_edit(
                    project,
                    {
                        "summary": "过期",
                        "revision": "0" * 64,
                        "confirmed": True,
                        "cleanup": {"silence": True},
                    },
                )

    def test_cli_doctor_and_export(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "pipeline/cli/talkcut.py"), "doctor"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("ffmpeg", completed.stdout)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            demo = make_breath_demo(folder, self.ffmpeg)
            project = folder / "project"
            imported = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "pipeline/cli/talkcut.py"),
                    "import",
                    "--video",
                    str(demo["video"]),
                    "--project",
                    str(project),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            payload = json.loads(imported.stdout)
            changes = folder / "changes.json"
            changes.write_text(
                json.dumps(
                    {
                        "summary": "命令行粗剪",
                        "revision": payload["revision"],
                        "confirmed": True,
                        "cleanup": {"breath": True, "silence": True, "filler": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            applied = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "pipeline/cli/talkcut.py"),
                    "apply",
                    "--project",
                    str(project),
                    "--changes",
                    str(changes),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            exported = subprocess.run(
                [sys.executable, str(ROOT / "pipeline/cli/talkcut.py"), "export", "--project", str(project)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            movie = json.loads(exported.stdout)["movie"]
            self.assertTrue(Path(movie).is_file())


if __name__ == "__main__":
    unittest.main()
