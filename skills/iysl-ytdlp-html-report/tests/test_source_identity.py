import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts" / "prepare_source.mjs"
CURRENT_ID = "aaa111"
CURRENT_URL = f"https://youtu.be/{CURRENT_ID}"
STALE_ID = "zzz999"
STALE_URL = f"https://youtu.be/{STALE_ID}"


class SourceIdentityTest(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX fake CLI fixture requires chmod and shebang execution")
    def test_caption_run_ignores_lexically_later_stale_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            out_dir = temp / "run"
            stale_manifest, stale_before = self._write_stale_source(out_dir)
            env = self._write_fake_tools(temp, self._metadata(with_captions=True))

            result = self._run_prepare(out_dir, env, "--asr", "none")

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            current_manifest = json.loads((out_dir / f"{CURRENT_ID}.manifest.json").read_text(encoding="utf-8"))
            current_metadata = json.loads((out_dir / f"{CURRENT_ID}.metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["id"], CURRENT_ID)
            self.assertEqual(summary["source_manifest"], str(out_dir / f"{CURRENT_ID}.manifest.json"))
            self.assertEqual(current_manifest["id"], CURRENT_ID)
            self.assertEqual(current_manifest["prepared_by"], "prepare_source.mjs")
            self.assertEqual(current_metadata["requested_url"], CURRENT_URL)
            self.assertEqual(stale_manifest.read_text(encoding="utf-8"), stale_before)

    @unittest.skipIf(os.name == "nt", "POSIX fake CLI fixture requires chmod and shebang execution")
    def test_asr_run_ignores_lexically_later_stale_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            out_dir = temp / "run"
            stale_manifest, stale_before = self._write_stale_source(out_dir)
            env = self._write_fake_tools(temp, self._metadata(with_captions=False), with_asr=True)

            result = self._run_prepare(out_dir, env, "--asr", "local-qwen", "--no-opencc")

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            current_manifest = json.loads((out_dir / f"{CURRENT_ID}.manifest.json").read_text(encoding="utf-8"))
            current_metadata = json.loads((out_dir / f"{CURRENT_ID}.metadata.json").read_text(encoding="utf-8"))
            transcript = out_dir / "transcripts" / f"{CURRENT_ID}.clean-transcript.md"
            self.assertEqual(summary["id"], CURRENT_ID)
            self.assertEqual(current_manifest["capture_status"], "audio-asr-ready")
            self.assertEqual(current_manifest["asr_backend"], "mlx-qwen3-asr")
            self.assertEqual(current_metadata["requested_url"], CURRENT_URL)
            self.assertEqual(transcript.read_text(encoding="utf-8"), "本次影片的逐字稿\n")
            self.assertEqual(stale_manifest.read_text(encoding="utf-8"), stale_before)

    @unittest.skipIf(os.name == "nt", "POSIX fake CLI fixture requires chmod and shebang execution")
    def test_same_video_can_rerun_in_the_same_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            out_dir = temp / "run"
            env = self._write_fake_tools(temp, self._metadata(with_captions=True))

            first = self._run_prepare(out_dir, env, "--asr", "none")
            second = self._run_prepare(out_dir, env, "--asr", "none")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)["id"], CURRENT_ID)

    def test_receipt_validation_accepts_only_matching_in_directory_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            out_dir = temp / "run"
            out_dir.mkdir()
            metadata_path = out_dir / f"{CURRENT_ID}.metadata.json"
            manifest_path = out_dir / f"{CURRENT_ID}.manifest.json"
            metadata_path.write_text(
                json.dumps({
                    "id": CURRENT_ID,
                    "requested_url": CURRENT_URL,
                    "original_url": CURRENT_URL,
                }),
                encoding="utf-8",
            )
            manifest_path.write_text(
                json.dumps({
                    "id": CURRENT_ID,
                    "url": CURRENT_URL,
                    "metadata": str(metadata_path),
                    "transcript": None,
                    "subtitle": None,
                    "capture_status": "captions-unavailable",
                }),
                encoding="utf-8",
            )
            outside_manifest = temp / "escape.manifest.json"
            outside_manifest.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
            valid = {
                "id": CURRENT_ID,
                "url": CURRENT_URL,
                "metadata": str(metadata_path),
                "manifest": str(manifest_path),
                "transcript": None,
                "subtitle": None,
                "capture_status": "captions-unavailable",
            }
            cases = [
                valid,
                None,
                {**valid, "id": "wrong-id"},
                {**valid, "id": "escape", "manifest": str(outside_manifest)},
                {**valid, "url": "https://youtu.be/wrong"},
            ]
            script = textwrap.dedent(
                f"""
                import {{ writeFileSync }} from "node:fs";
                import {{ validateSourceReceipt }} from {json.dumps(PREPARE.as_uri())};
                const cases = {json.dumps(cases)};
                const outDir = {json.dumps(str(out_dir))};
                const url = {json.dumps(CURRENT_URL)};
                const metadataPath = {json.dumps(str(metadata_path))};
                const results = cases.map((receipt) => {{
                  try {{
                    validateSourceReceipt(receipt, {{ outDir, url }});
                    return true;
                  }} catch {{
                    return false;
                  }}
                }});
                writeFileSync(metadataPath, JSON.stringify({{
                  id: {json.dumps(CURRENT_ID)},
                  requested_url: "https://youtu.be/wrong",
                  original_url: url,
                }}));
                try {{
                  validateSourceReceipt(cases[0], {{ outDir, url }});
                  results.push(true);
                }} catch {{
                  results.push(false);
                }}
                console.log(JSON.stringify(results));
                """
            )

            result = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [True, False, False, False, False, False])

    def _metadata(self, with_captions):
        return {
            "id": CURRENT_ID,
            "title": "本次影片",
            "language": "zh-TW",
            "webpage_url": f"https://www.youtube.com/watch?v={CURRENT_ID}",
            "original_url": CURRENT_URL,
            "subtitles": {"zh-TW": [{"ext": "json3"}]} if with_captions else {},
            "automatic_captions": {},
        }

    def _write_stale_source(self, out_dir):
        out_dir.mkdir(parents=True)
        stale_metadata = out_dir / f"{STALE_ID}.metadata.json"
        stale_manifest = out_dir / f"{STALE_ID}.manifest.json"
        stale_metadata.write_text(
            json.dumps({"id": STALE_ID, "original_url": STALE_URL}),
            encoding="utf-8",
        )
        stale_manifest.write_text(
            json.dumps({
                "id": STALE_ID,
                "url": STALE_URL,
                "metadata": str(stale_metadata),
                "transcript": None,
                "subtitle": None,
                "capture_status": "captions-ready",
            }),
            encoding="utf-8",
        )
        return stale_manifest, stale_manifest.read_text(encoding="utf-8")

    def _write_fake_tools(self, temp, metadata, with_asr=False):
        metadata_path = temp / "metadata.json"
        log_path = temp / "calls.log"
        fake_ytdlp = temp / "yt-dlp"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        fake_ytdlp.write_text(
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
                if "--format" in args:
                    target = output.replace("%(ext)s", "m4a")
                    target_path = Path(target)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_bytes(b"fake audio")
                    raise SystemExit(0)
                language = args[args.index("--sub-langs") + 1]
                target = output.replace("%(id)s", metadata["id"]).replace("%(ext)s", f"{language}.json3")
                target_path = Path(target)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(json.dumps({"events": [{"tStartMs": 0, "segs": [{"utf8": "字幕內容"}]}]}), encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        fake_ytdlp.chmod(fake_ytdlp.stat().st_mode | stat.S_IXUSR)
        env = {
            **os.environ,
            "PATH": f"{temp}:{os.environ.get('PATH', '')}",
            "FAKE_YTDLP_METADATA": str(metadata_path),
            "FAKE_YTDLP_LOG": str(log_path),
        }
        if with_asr:
            fake_asr = temp / "mlx-qwen3-asr"
            fake_asr.write_text("#!/usr/bin/env python3\nprint('本次影片的逐字稿')\n", encoding="utf-8")
            fake_asr.chmod(fake_asr.stat().st_mode | stat.S_IXUSR)
            env["QWEN3_ASR_BIN"] = str(fake_asr)
        return env

    def _run_prepare(self, out_dir, env, *extra_args):
        return subprocess.run(
            ["node", str(PREPARE), CURRENT_URL, "--out-dir", str(out_dir), *extra_args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )


if __name__ == "__main__":
    unittest.main()
