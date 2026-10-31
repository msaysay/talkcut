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
from engine.motion import captions_from_edit, classify_caption, load_preset, render_motion, segments_from_plan, split_caption_phrases, _music_track
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
            for earlier, later in zip(captions, captions[1:]):
                self.assertLessEqual(earlier["end"], later["start"])

    def test_phrases_split_on_punctuation_pause_and_length(self):
        phrases = split_caption_phrases(
            [
                {
                    "text": "先把判断说清，再给一个例子。",
                    "start": 0,
                    "end": 3,
                    "emphasis": "body",
                    "keywords": [],
                }
            ]
        )
        self.assertEqual([item["text"] for item in phrases], ["先把判断说清", "再给一个例子"])
        paused = split_caption_phrases(
            [{"text": "先说判断……再补一句", "start": 0, "end": 2, "emphasis": "body", "keywords": []}]
        )
        self.assertEqual([item["text"] for item in paused], ["先说判断", "再补一句"])
        long_text = "我认为一条片子只讲一个判断其余都先放下"
        wrapped = split_caption_phrases(
            [{"text": long_text, "start": 1, "end": 4, "emphasis": "body", "keywords": ["一个"]}]
        )
        self.assertTrue(wrapped)
        self.assertTrue(all(len(item["text"]) <= 18 for item in wrapped))
        self.assertEqual("".join(item["text"] for item in wrapped), long_text)
        self.assertIn("一个", wrapped[0]["keywords"])
        self.assertEqual(wrapped[-1]["keywords"], [])
        overlapping = split_caption_phrases(
            [
                {"text": "第一句", "start": 0, "end": 1.2, "emphasis": "body", "keywords": []},
                {"text": "第二句", "start": 1.0, "end": 2.0, "emphasis": "body", "keywords": []},
            ]
        )
        self.assertLessEqual(overlapping[0]["end"], overlapping[1]["start"])
        for earlier, later in zip(phrases, phrases[1:]):
            self.assertLessEqual(earlier["end"], later["start"])
            self.assertGreaterEqual(later["end"] - later["start"], 0.04)

    def test_graphic_card_does_not_repeat_the_sentence(self):
        segments, captions = segments_from_plan(
            {
                "items": [
                    {
                        "layout": "v2",
                        "start": 0,
                        "end": 2,
                        "text": "先说判断，再给例子。",
                        "roleLabel": "观点",
                        "emphasis": "body",
                        "keywords": [],
                        "font": "body",
                        "effects": [],
                    }
                ]
            }
        )
        self.assertEqual(segments[0]["body"], "")
        self.assertEqual(segments[0]["title"], "观点")
        self.assertGreater(len(captions), 1)
        self.assertTrue(all(len(item["text"]) <= 18 for item in captions))

    def test_music_track_skips_drum_bed_without_a_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            track, beats, rate = _music_track(folder, 2.0, None, None, "ffmpeg")
            self.assertIsNone(track)
            self.assertEqual(beats, [])
            self.assertIsNone(rate)
            self.assertFalse((folder / "motion" / "public" / "music.wav").exists())
            track, beats, rate = _music_track(folder, 2.0, None, 120, "ffmpeg")
            self.assertIsNone(track)
            self.assertEqual(beats[:3], [0.0, 0.5, 1.0])
            self.assertFalse((folder / "motion" / "public" / "music.wav").exists())


class RenderPresetTest(unittest.TestCase):
    def test_both_presets_render_vertical_mp4(self):
        if not (ROOT / "motion-pack" / "node_modules" / "remotion").is_dir():
            self.skipTest("remotion is not installed")
        ffmpeg, ffprobe = require_ffmpeg()
        with tempfile.TemporaryDirectory() as temporary:
            project = _prepare(Path(temporary), ffmpeg)
            movies = []
            for name in ("clean-knowledge", "gold-line"):
                for orientation, width, height in (("vertical", 1080, 1920), ("landscape", 1920, 1080)):
                    rendered = render_motion(project, name, bpm=120, orientation=orientation)
                    movie = Path(rendered["movie"])
                    info = probe(ffprobe, movie)
                    self.assertTrue(info["hasVideo"] and info["hasAudio"])
                    self.assertEqual(info["width"], width, f"{name} {orientation}")
                    self.assertEqual(info["height"], height, f"{name} {orientation}")
                    self.assertGreater(info["duration"], 0.8)
                    if orientation == "vertical":
                        self.assertTrue(Path(rendered["cover"]).is_file())
                        movies.append((name, movie, Path(rendered["cover"])))
            self.assertEqual(len(movies), 2)
            artifact_dir = Path("/opt/cursor/artifacts")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            for name, movie, cover in movies:
                target = artifact_dir / f"preset-{name}-vertical.mp4"
                target.write_bytes(movie.read_bytes())
                frame = artifact_dir / f"preset-{name}-vertical.png"
                subprocess.run(
                    [ffmpeg, "-y", "-v", "error", "-ss", "0.2", "-i", str(movie), "-frames:v", "1", str(frame)],
                    check=True,
                )
                if name == "gold-line":
                    subprocess.run(
                        [ffmpeg, "-y", "-v", "error", "-ss", "1.05", "-i", str(movie), "-frames:v", "1", str(artifact_dir / "preset-gold-line-late.png")],
                        check=True,
                    )
                shutil_cover = artifact_dir / f"preset-cover-{name}.png"
                shutil_cover.write_bytes(cover.read_bytes())


    def test_stock_layout_reels(self):
        if not (ROOT / "motion-pack" / "node_modules" / "remotion").is_dir():
            self.skipTest("remotion is not installed")
        from engine.reel import render_layout_reel
        import urllib.request

        ffmpeg, ffprobe = require_ffmpeg()
        video = Path("/tmp/talkcut-assets/pexels-8048443.mp4")
        if not video.is_file():
            video.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(
                "https://videos.pexels.com/video-files/8048443/8048443-hd_1080_1920_25fps.mp4",
                video,
            )
        vertical = render_layout_reel(Path("/tmp/talkcut-reel-v"), video, "vertical", "clean-knowledge")
        landscape = render_layout_reel(Path("/tmp/talkcut-reel-h"), video, "landscape", "gold-line")
        artifact_dir = Path("/opt/cursor/artifacts")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        for label, rendered, stamps in (
            ("vertical", vertical, [("v1", 0.4), ("v2", 2.4), ("v3", 3.8), ("v4", 4.6), ("v5", 6.0), ("v6", 7.3)]),
            ("landscape", landscape, [("h1", 0.4), ("h2", 1.8), ("h3", 3.2), ("h4", 4.6), ("h5", 6.2)]),
        ):
            movie = Path(rendered["movie"])
            info = probe(ffprobe, movie)
            self.assertEqual((info["width"], info["height"]), (1080, 1920) if label == "vertical" else (1920, 1080))
            (artifact_dir / f"reel-{label}.mp4").write_bytes(movie.read_bytes())
            for name, second in stamps:
                subprocess.run(
                    [ffmpeg, "-y", "-v", "error", "-ss", str(second), "-i", str(movie), "-frames:v", "1", str(artifact_dir / f"layout-{name}.png")],
                    check=True,
                )


if __name__ == "__main__":
    unittest.main()
