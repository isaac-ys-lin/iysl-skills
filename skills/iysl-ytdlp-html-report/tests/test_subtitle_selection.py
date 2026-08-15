import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts" / "extract_transcript.mjs"
PREPARE = ROOT / "scripts" / "prepare_source.mjs"
FORMATS = [{"ext": "vtt"}]


def metadata(language=None, subtitles=None, automatic_captions=None):
    return {
        "id": "demo123",
        "title": "字幕選擇測試",
        "language": language,
        "subtitles": subtitles or {},
        "automatic_captions": automatic_captions or {},
    }


class SubtitleSelectionTest(unittest.TestCase):
    def test_metadata_selector_covers_language_priority_and_override(self):
        cases = [
            (
                "zh-manual",
                metadata("zh-TW", {"zh-TW": FORMATS, "en": FORMATS}),
                None,
                {"language": "zh-TW", "kind": "manual", "fallback": False},
            ),
            (
                "en-manual-over-auto",
                metadata("en", {"en": FORMATS}, {"en": FORMATS}),
                None,
                {"language": "en", "kind": "manual", "fallback": False},
            ),
            (
                "original-auto-over-translation",
                metadata("ja", {"zh-TW": FORMATS}, {"ja": FORMATS}),
                None,
                {"language": "ja", "kind": "automatic", "fallback": False},
            ),
            (
                "traditional-fallback",
                metadata("ja", {"zh-TW": FORMATS}),
                None,
                {"language": "zh-TW", "kind": "manual", "fallback": True},
            ),
            (
                "simplified-fallback",
                metadata("ja", {"zh-Hans": FORMATS}),
                None,
                {"language": "zh-Hans", "kind": "manual", "fallback": True},
            ),
            (
                "english-fallback",
                metadata("ja", {"en": FORMATS}),
                None,
                {"language": "en", "kind": "manual", "fallback": True},
            ),
            (
                "no-subtitle-asr-boundary",
                metadata("ja"),
                None,
                None,
            ),
            (
                "explicit-override",
                metadata("en", {"en": FORMATS, "zh-TW": FORMATS}),
                "zh-TW",
                {"language": "zh-TW", "kind": "manual", "fallback": True},
            ),
        ]
        module_uri = EXTRACTOR.as_uri()
        payload = json.dumps(
            [{"id": case_id, "metadata": item, "langsOverride": override} for case_id, item, override, _ in cases],
            ensure_ascii=False,
        )
        script = textwrap.dedent(
            f"""
            import {{ selectSubtitleCandidate }} from {json.dumps(module_uri)};
            const cases = {payload};
            console.log(JSON.stringify(cases.map((item) => ({{
              id: item.id,
              selected: selectSubtitleCandidate(item.metadata, {{ langsOverride: item.langsOverride }})
            }}))));
            """
        )
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        selected = {item["id"]: item["selected"] for item in json.loads(result.stdout)}
        for case_id, _, _, expected in cases:
            with self.subTest(case=case_id):
                actual = selected[case_id]
                if expected is None:
                    self.assertIsNone(actual)
                else:
                    self.assertEqual(actual["language"], expected["language"])
                    self.assertEqual(actual["kind"], expected["kind"])
                    self.assertEqual(actual["isFallbackLanguage"], expected["fallback"])

    @unittest.skipIf(os.name == "nt", "POSIX fake yt-dlp fixture requires chmod and shebang execution")
    def test_extractor_records_selected_language_kind_and_fallback_from_metadata(self):
        scenarios = [
            ("zh-TW", {"zh-TW": FORMATS}, {}, "zh-TW", "manual", False),
            ("en", {"en": FORMATS}, {"en": FORMATS}, "en", "manual", False),
            ("ja", {"zh-TW": FORMATS}, {"ja": FORMATS}, "ja", "automatic", False),
            ("ja", {"zh-TW": FORMATS}, {}, "zh-TW", "manual", True),
            ("ja", {"zh-Hans": FORMATS}, {}, "zh-Hans", "manual", True),
            ("ja", {"en": FORMATS}, {}, "en", "manual", True),
        ]
        for language, subtitles, automatic, selected_language, selected_kind, is_fallback in scenarios:
            with self.subTest(language=language, selected_language=selected_language):
                result, run_dir, log_path = self._run_extractor(
                    metadata(language, subtitles, automatic)
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                metadata_payload = json.loads((run_dir / "demo123.metadata.json").read_text(encoding="utf-8"))
                manifest = json.loads((run_dir / "demo123.manifest.json").read_text(encoding="utf-8"))
                for payload in (metadata_payload, manifest):
                    self.assertEqual(payload["source_language"], language)
                    self.assertEqual(payload["subtitle_language"], selected_language)
                    self.assertEqual(payload["subtitle_kind"], selected_kind)
                    self.assertEqual(payload["subtitle_is_fallback"], is_fallback)
                    self.assertEqual(payload["subtitle_selection"]["selected_language"], selected_language)
                    self.assertEqual(payload["subtitle_selection"]["selected_kind"], selected_kind)
                download_args = json.loads(log_path.read_text(encoding="utf-8").splitlines()[1])
                self.assertEqual(download_args[download_args.index("--sub-langs") + 1], selected_language)
                expected_flag = "--write-subs" if selected_kind == "manual" else "--write-auto-subs"
                self.assertIn(expected_flag, download_args)
                other_flag = "--write-auto-subs" if selected_kind == "manual" else "--write-subs"
                self.assertNotIn(other_flag, download_args)

    @unittest.skipIf(os.name == "nt", "POSIX fake yt-dlp fixture requires chmod and shebang execution")
    def test_no_subtitles_persists_manifest_and_prepare_source_enters_asr_boundary(self):
        no_subtitles = metadata("ja")
        result, run_dir, log_path = self._run_extractor(no_subtitles)
        self.assertNotEqual(result.returncode, 0)
        manifest = json.loads((run_dir / "demo123.manifest.json").read_text(encoding="utf-8"))
        metadata_payload = json.loads((run_dir / "demo123.metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["capture_status"], "captions-unavailable")
        for payload in (metadata_payload, manifest):
            self.assertEqual(payload["subtitle_status"], "unavailable")
            self.assertIsNone(payload["subtitle_language"])
            self.assertIsNone(payload["subtitle_kind"])
            self.assertFalse(payload["subtitle_is_fallback"])
        self.assertEqual(len(log_path.read_text(encoding="utf-8").splitlines()), 1)

        prepare_result, prepare_dir, _ = self._run_extractor(no_subtitles, use_prepare=True, asr="none")
        self.assertNotEqual(prepare_result.returncode, 0)
        self.assertIn("未配置 ASR backend", prepare_result.stderr)
        self.assertTrue((prepare_dir / "demo123.manifest.json").is_file())

    @unittest.skipIf(os.name == "nt", "POSIX fake yt-dlp fixture requires chmod and shebang execution")
    def test_prepare_source_forwards_explicit_lang_override(self):
        result, run_dir, _ = self._run_extractor(
            metadata("en", {"en": FORMATS, "zh-TW": FORMATS}),
            use_prepare=True,
            langs="zh-TW",
            asr="none",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((run_dir / "demo123.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["subtitle_language"], "zh-TW")
        self.assertEqual(manifest["subtitle_selection"]["requested_languages"], "zh-TW")
        self.assertEqual(manifest["subtitle_selection"]["selection_reason"], "user-override")

    def _run_extractor(self, metadata_payload, use_prepare=False, langs=None, asr=None):
        temp_dir = tempfile.TemporaryDirectory()
        temp = Path(temp_dir.name)
        fake_bin = temp / "yt-dlp"
        metadata_path = temp / "metadata.json"
        log_path = temp / "calls.log"
        metadata_path.write_text(json.dumps(metadata_payload), encoding="utf-8")
        fake_bin.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                from pathlib import Path

                args = sys.argv[1:]
                metadata = json.loads(Path(os.environ["FAKE_YTDLP_METADATA"]).read_text())
                with Path(os.environ["FAKE_YTDLP_LOG"]).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(args) + "\\n")
                if "--dump-json" in args:
                    print(json.dumps(metadata))
                    raise SystemExit(0)
                output = args[args.index("--output") + 1]
                language = args[args.index("--sub-langs") + 1]
                target = output.replace("%(id)s", metadata["id"]).replace("%(ext)s", f"{language}.json3")
                target_path = Path(target)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(json.dumps({"events": [{"tStartMs": 0, "segs": [{"utf8": f"字幕 {language}"}]}]}), encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IXUSR)
        env = {
            **os.environ,
            "PATH": f"{temp}:{os.environ.get('PATH', '')}",
            "FAKE_YTDLP_METADATA": str(metadata_path),
            "FAKE_YTDLP_LOG": str(log_path),
        }
        command = ["node", str(PREPARE if use_prepare else EXTRACTOR), "https://youtu.be/demo123", "--out-dir", str(temp / "run")]
        if use_prepare and asr:
            command.extend(["--asr", asr])
        if langs:
            command.extend(["--langs", langs])
        result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
        run_dir = temp / "run"
        # Keep the temporary directory alive until the caller has read files.
        self.addCleanup(temp_dir.cleanup)
        return result, run_dir, log_path


if __name__ == "__main__":
    unittest.main()
