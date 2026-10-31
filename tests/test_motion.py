"""Motion props, beat grid, and both Remotion presets."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.beats import beats_from_bpm, detect_beats, write_drum_bed
from engine.media import load_pcm, probe
from engine.motion import captions_from_edit, classify_caption, load_preset, render_motion
from engine.pipeline import apply_edit, import_media
from engine.runtime import require_ffmpeg
from engine.synthetic import make_breath_demo


def _prepare(folder: Path, ffmpeg: str) -> Path:
    demo = make_breath_demo(folder, ffmpeg)
    project = folder / "project"
    imported = import_media(demo["video"], project, transcript=ROOT / "examples" / "demo-caption-words.json")
    apply_edit(
        project,
        {
            "summary": "去掉气口后上字幕",
            "revision": imported["revision"],
            "confirmed": True,
            "cleanup": {"breath": True, "silence": True, "filler": True},
        },
    )
    return project


class MotionPropsTest(unittest.TestCase):
    def test_emphasis_rules(self):
        self.assertEqual(classify_caption(0, 3, "先把三秒说清", "clean-knowledge"), "hook")
        self.assertEqual(classify_caption(1, 3, "第二步要具体", "clean-knowledge"), "list")
        self.assertEqual(classify_caption(1, 3, "花了3年", "clean-knowledge"), "number")
        self.assertEqual(classify_caption(2, 3, "真正留下的是金句", "gold-line"), "gold")
        self.assertEqual(classify_caption(2, 3, "评论区打钩子", "clean-knowledge"), "cta")

    def test_ducking_is_lower_while_speaking(self):
        for name in ("clean-knowledge", "gold-line"):
            music = load_preset(name)["music"]
            self.assertLess(music["speechVolume"], music["gapVolume"])
            self.assertLess(music["ctaVolume"], music["speechVolume"])
            self.assertLessEqual(load_preset(name)["maxColors"], 3)

    def test_beat_grid_and_onset_detection(self):
        self.assertEqual(beats_from_bpm(2.0, 120)[:3], [0.0, 0.5, 1.0])
        ffmpeg, _probe = require_ffmpeg()
        with tempfile.TemporaryDirectory() as temporary:
            bed = Path(temporary) / "bed.wav"
            expected = write_drum_bed(bed, 2.4, bpm=120)
            samples = load_pcm(ffmpeg, bed)
            found, bpm = detect_beats(samples)
            self.assertGreater(bpm, 100)
            self.assertLess(bpm, 140)
            self.assertGreaterEqual(len(found), len(expected) - 1)

    def test_caption_timeline_uses_kept_speech(self):
        ffmpeg, _probe = require_ffmpeg()
        with tempfile.TemporaryDirectory() as temporary:
            project = _prepare(Path(temporary), ffmpeg)
            from engine.store import load

            doc = load(project)
            captions = captions_from_edit(doc, "gold-line")
            texts = [item["text"] for item in captions]
            self.assertEqual(texts, ["先把三秒说清", "钩子要具体", "真正留下的是金句"])
            self.assertEqual(captions[0]["emphasis"], "hook")
            self.assertIn("三", captions[0]["keywords"])
            self.assertEqual(captions[2]["emphasis"], "gold")
            self.assertLess(captions[0]["end"], captions[1]["start"] + 0.05)


class RenderPresetTest(unittest.TestCase):
    def test_both_presets_render_vertical_mp4(self):
        if not (ROOT / "motion-pack" / "node_modules" / "remotion").is_dir():
            self.skipTest("remotion is not installed")
        ffmpeg, ffprobe = require_ffmpeg()
        with tempfile.TemporaryDirectory() as temporary:
            project = _prepare(Path(temporary), ffmpeg)
            movies = []
            for name in ("clean-knowledge", "gold-line"):
                rendered = render_motion(project, name, bpm=120)
                movie = Path(rendered["movie"])
                self.assertTrue(movie.is_file(), name)
                info = probe(ffprobe, movie)
                self.assertTrue(info["hasVideo"])
                self.assertTrue(info["hasAudio"])
                self.assertEqual(info["width"], 1080)
                self.assertEqual(info["height"], 1920)
                self.assertGreater(info["duration"], 0.8)
                self.assertTrue(Path(rendered["cover"]).is_file())
                movies.append((name, movie, Path(rendered["cover"])))
            self.assertEqual(len(movies), 2)
            artifact_dir = Path("/opt/cursor/artifacts")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            for name, movie, cover in movies:
                target = artifact_dir / f"motion-{name}.mp4"
                target.write_bytes(movie.read_bytes())
                frame = artifact_dir / f"motion-{name}.png"
                subprocess.run(
                    [ffmpeg, "-y", "-v", "error", "-ss", "0.2", "-i", str(movie), "-frames:v", "1", str(frame)],
                    check=True,
                )
                if name == "gold-line":
                    subprocess.run(
                        [ffmpeg, "-y", "-v", "error", "-ss", "1.05", "-i", str(movie), "-frames:v", "1", str(artifact_dir / "motion-gold-line-late.png")],
                        check=True,
                    )
                shutil_cover = artifact_dir / f"cover-{name}.png"
                shutil_cover.write_bytes(cover.read_bytes())


if __name__ == "__main__":
    unittest.main()
