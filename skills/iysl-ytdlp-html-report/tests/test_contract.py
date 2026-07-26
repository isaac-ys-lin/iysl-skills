import json
import os
import re
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Personal-machine residue that must never ship in a portable, installable skill.
NON_PORTABLE = ("/Users/", "study_flow", "mlxwhisper", "miniconda", "Caskroom")

SECTIONS = ["內容重述", "洞見", "food for thoughts", "可行啟發"]


class YtdlpReportContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.cases = json.loads(
            (ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8")
        )

    def test_frontmatter_name_matches_directory_and_is_iysl_prefixed(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)
        self.assertTrue(match.group(1).startswith("iysl-"))

    def test_no_personal_machine_paths_anywhere_in_skill_tree(self):
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
                continue
            # Skip the checker itself: it names these needles as literals.
            if set(path.relative_to(ROOT).parts) & {"tests", "evals"}:
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in NON_PORTABLE:
                if needle in body:
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}::{needle}")
        self.assertEqual(offenders, [], offenders)

    def test_script_invocations_use_skill_relative_placeholder(self):
        # Bash invocations must use the portable /path/to/skill/ placeholder,
        # never an author-specific absolute install path.
        self.assertIn("/path/to/skill/scripts/extract_transcript.mjs", self.skill)
        self.assertIn("/path/to/skill/scripts/transcribe_local_qwen.mjs", self.skill)
        self.assertIn("/path/to/skill/scripts/render_html.mjs", self.skill)

    def test_two_core_principles_present(self):
        self.assertIn("逐字稿是唯一內容來源", self.skill)
        self.assertIn("讀者與 operator 資訊分離", self.skill)

    def test_kami_composition_owns_formal_presentation_without_vendoring(self):
        self.assertIn("內容與 presentation 分工", self.skill)
        self.assertIn("唯一語意 handoff", self.skill)
        self.assertIn("presentation_backend", self.skill)
        self.assertIn("presentation_fallback_reason", self.skill)
        self.assertIn("不要硬編碼安裝路徑", self.skill)
        self.assertIn("不要把 Kami 的 template、diagram、CSS、字型、reference 或 script 複製進本 skill", self.skill)
        self.assertIn("只保留一份 final report HTML", self.skill)
        self.assertNotIn("/path/to/kami", self.skill.lower())

        vendored = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and "kami" in path.name.lower()
        ]
        self.assertEqual(vendored, [], vendored)

    def test_four_reader_sections_named_in_order(self):
        positions = [self.skill.find(name) for name in SECTIONS]
        self.assertTrue(all(pos >= 0 for pos in positions), positions)
        self.assertEqual(positions, sorted(positions))

    def test_audio_fallback_is_local_qwen_first_with_clean_degradation(self):
        self.assertIn("Qwen/Qwen3-ASR-1.7B", self.skill)
        self.assertIn("無字幕且本機 Qwen3-ASR 不可用", self.skill)
        self.assertIn("不要呼叫雲端 API", self.skill)
        # yt-dlp is the portable audio-download layer; keep it explicit.
        self.assertIn("yt-dlp", self.skill)

    def test_skill_has_no_groq_or_cloud_asr_dependency(self):
        offenders = []
        needles = ("GROQ_API_KEY", "api.groq.com", "transcribe_groq")
        for path in ROOT.rglob("*"):
            if not path.is_file() or "tests" in path.relative_to(ROOT).parts:
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in needles:
                if needle in body:
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}::{needle}")
        self.assertEqual(offenders, [], offenders)

    def test_local_qwen_wrapper_passes_model_language_context_and_writes_transcript(self):
        helper = ROOT / "scripts" / "transcribe_local_qwen.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fake_cli = temp / "mlx-qwen3-asr"
            fake_opencc = temp / "opencc"
            captured_args = temp / "args.txt"
            captured_opencc_args = temp / "opencc-args.txt"
            captured_offline_env = temp / "offline-env.txt"
            audio_path = temp / "meeting.m4a"
            output_path = temp / "nested" / "meeting.clean-transcript.md"
            fake_cli.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$@\" > \"$QWEN3_ASR_TEST_ARGS\"\n"
                "printf '%s|%s\\n' \"$HF_HUB_OFFLINE\" \"$TRANSFORMERS_OFFLINE\" > \"$QWEN3_ASR_TEST_ENV\"\n"
                "printf '這是一份本機逐字稿。\\n'\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            fake_opencc.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$@\" > \"$OPENCC_TEST_ARGS\"\n"
                "cat\n",
                encoding="utf-8",
            )
            fake_opencc.chmod(0o755)
            audio_path.write_bytes(b"fake-audio")
            result = subprocess.run(
                [
                    "node", str(helper),
                    "--audio", str(audio_path),
                    "--out", str(output_path),
                    "--binary", str(fake_cli),
                    "--opencc-binary", str(fake_opencc),
                    "--model", "Qwen/Qwen3-ASR-1.7B",
                    "--language", "Chinese",
                    "--context", "IFRS 17 CSM",
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "QWEN3_ASR_TEST_ARGS": str(captured_args),
                    "QWEN3_ASR_TEST_ENV": str(captured_offline_env),
                    "OPENCC_TEST_ARGS": str(captured_opencc_args),
                },
            )
            summary = json.loads(result.stdout)
            self.assertEqual(summary["backend"], "mlx-qwen3-asr")
            self.assertEqual(summary["model"], "Qwen/Qwen3-ASR-1.7B")
            self.assertEqual(summary["language"], "Chinese")
            self.assertTrue(summary["context_provided"])
            self.assertEqual(summary["normalization"], "opencc:s2twp.json")
            self.assertEqual(summary["model_network_policy"], "offline-cache-only")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "這是一份本機逐字稿。\n")
            args = captured_args.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                args,
                [
                    str(audio_path.absolute()),
                    "--model", "Qwen/Qwen3-ASR-1.7B",
                    "--stdout-only",
                    "--no-progress",
                    "--language", "Chinese",
                    "--context", "IFRS 17 CSM",
                ],
            )
            self.assertEqual(
                captured_opencc_args.read_text(encoding="utf-8").splitlines(),
                ["-c", "s2twp.json"],
            )
            self.assertEqual(captured_offline_env.read_text(encoding="utf-8"), "1|1\n")

    def test_local_qwen_wrapper_fails_cleanly_when_cli_is_missing(self):
        helper = ROOT / "scripts" / "transcribe_local_qwen.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            audio_path = temp / "meeting.wav"
            audio_path.write_bytes(b"fake-audio")
            result = subprocess.run(
                [
                    "node", str(helper),
                    "--audio", str(audio_path),
                    "--out", str(temp / "transcript.md"),
                    "--binary", str(temp / "missing-cli"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("找不到 mlx-qwen3-asr CLI", result.stderr)
            self.assertFalse((temp / "transcript.md").exists())

    def test_local_qwen_wrapper_fails_cleanly_when_opencc_is_missing(self):
        helper = ROOT / "scripts" / "transcribe_local_qwen.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fake_cli = temp / "mlx-qwen3-asr"
            audio_path = temp / "meeting.wav"
            output_path = temp / "transcript.md"
            fake_cli.write_text(
                "#!/bin/sh\nprintf '模型輸出。\\n'\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            audio_path.write_bytes(b"fake-audio")
            result = subprocess.run(
                [
                    "node", str(helper),
                    "--audio", str(audio_path),
                    "--out", str(output_path),
                    "--binary", str(fake_cli),
                    "--opencc-binary", str(temp / "missing-opencc"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("找不到 OpenCC CLI", result.stderr)
            self.assertFalse(output_path.exists())

    def test_extractor_persists_metadata_when_captions_are_unavailable(self):
        extractor = (ROOT / "scripts" / "extract_transcript.mjs").read_text(encoding="utf-8")
        self.assertIn('subtitle_status: "unavailable"', extractor)
        self.assertIn('capture_status: "captions-unavailable"', extractor)

    def test_prepare_source_exports_url_and_manifest_contract(self):
        helper = (ROOT / "scripts" / "prepare_source.mjs").as_uri()
        script = f"""
            import {{ isSupportedPublicVideoUrl, buildSourceManifest }} from {json.dumps(helper)};
            const manifest = buildSourceManifest({{
              id: "demo123",
              url: "https://www.youtube.com/watch?v=demo123",
              metadataPath: "/run/metadata.json",
              captureStatus: "captions-ready",
              subtitlePath: "/run/subtitles.vtt"
            }});
            console.log(JSON.stringify({{
              accepted: isSupportedPublicVideoUrl("https://www.youtube.com/watch?v=demo123"),
              youtu: isSupportedPublicVideoUrl("https://youtu.be/demo123"),
              tco: isSupportedPublicVideoUrl("https://t.co/AbCdEf123"),
              playlist: isSupportedPublicVideoUrl("https://www.youtube.com/watch?v=demo123&list=PL123"),
              credentials: isSupportedPublicVideoUrl("https://user:pass@youtu.be/demo123"),
              manifest
            }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["accepted"])
        self.assertTrue(payload["youtu"])
        self.assertTrue(payload["tco"])
        self.assertFalse(payload["playlist"])
        self.assertFalse(payload["credentials"])
        self.assertEqual(payload["manifest"]["capture_status"], "captions-ready")
        self.assertEqual(payload["manifest"]["subtitle_status"], "available")
        self.assertEqual(payload["manifest"]["id"], "demo123")

    def test_prepare_source_rejects_out_of_scope_url_and_cookie_flags(self):
        helper = ROOT / "scripts" / "prepare_source.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            unsupported = subprocess.run(
                ["node", str(helper), "https://example.com/video", "--out-dir", str(temp / "unsupported")],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(unsupported.returncode, 0)
            self.assertIn("只接受單一公開", unsupported.stderr)

            cookies = subprocess.run(
                [
                    "node", str(helper), "https://youtu.be/demo123",
                    "--out-dir", str(temp / "cookies"),
                    "--cookies-from-browser", "chrome",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cookies.returncode, 0)
            self.assertIn("browser cookies", cookies.stderr)

    def test_finalize_report_writes_valid_bundle_and_stops_on_invalid_evidence(self):
        helper = ROOT / "scripts" / "finalize_report.mjs"
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "spec.json"
            manifest_path = temp / "manifest.json"
            out_dir = temp / "out"
            spec_path.write_text(json.dumps(fixture), encoding="utf-8")
            manifest_path.write_text(
                json.dumps({
                    "id": "demo123",
                    "url": "https://www.youtube.com/watch?v=demo123",
                    "resolved_url": "https://www.youtube.com/watch?v=demo123",
                    "metadata": None,
                    "transcript": None,
                    "subtitle": None,
                    "subtitle_status": "available",
                    "prepared_by": "test fixture",
                }),
                encoding="utf-8",
            )
            passed = subprocess.run(
                ["node", str(helper), "--spec", str(spec_path), "--manifest", str(manifest_path), "--out-dir", str(out_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(passed.stdout)
            for key in ("report_markdown", "report_html", "verification_sidecar"):
                self.assertTrue(Path(result[key]).is_file(), key)
            sidecar = Path(result["verification_sidecar"]).read_text(encoding="utf-8")
            self.assertIn("presentation_backend: built-in-v2", sidecar)
            self.assertIn("deterministic_verification: v2 validator and artifact validator passed", sidecar)

            invalid = json.loads(json.dumps(fixture))
            invalid["blocks"][0]["evidence_refs"] = ["E404"]
            invalid_spec = temp / "invalid.json"
            invalid_spec.write_text(json.dumps(invalid), encoding="utf-8")
            invalid_out = temp / "invalid-out"
            rejected = subprocess.run(
                ["node", str(helper), "--spec", str(invalid_spec), "--manifest", str(manifest_path), "--out-dir", str(invalid_out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("不存在的 evidence", rejected.stderr)
            self.assertFalse((invalid_out / "demo123.report.html").exists())

    def test_renderer_keeps_enumerated_sections_as_single_bullet_lists(self):
        report = """# 內容重述

摘要。

# 洞見

1. 第一點。

1. 第二點。

# food for thoughts

1. 思考提示。

# 可行啟發

1. 行動一。

1. 行動二。

# 驗證與限制

1. /Users/example/private.txt 只能留在 sidecar。
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            report_path = temp / "report.md"
            metadata_path = temp / "metadata.json"
            output_path = temp / "report.html"
            report_path.write_text(report, encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "title": "Test",
                        "webpage_url": "https://example.com",
                        "extracted_at": "2026-07-26T08:00:00+08:00",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_html.mjs"),
                    "--report", str(report_path),
                    "--metadata", str(metadata_path),
                    "--out", str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            html = output_path.read_text(encoding="utf-8")
            for section_id in ("summary", "insights", "food", "actions"):
                section = re.search(rf'<section id="{section_id}".*?</section>', html, re.DOTALL)
                self.assertIsNotNone(section, section_id)
                if section_id != "summary":
                    self.assertIn("<ul>", section.group(0))
                    self.assertNotIn("<ol>", section.group(0))
            insights = re.search(r'<section id="insights".*?</section>', html, re.DOTALL).group(0)
            self.assertEqual(insights.count("<ul>"), 1)
            self.assertNotIn("驗證與限制", html)
            self.assertNotIn("/Users/example/private.txt", html)
            self.assertNotIn("2026-07-26T08:00:00+08:00", html)

    def test_v2_schema_fixture_validator_and_dual_renderer(self):
        schema = json.loads(
            (ROOT / "references" / "report-v2.schema.json").read_text(encoding="utf-8")
        )
        fixture = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        self.assertEqual(schema["properties"]["version"]["const"], "2.0")
        self.assertEqual(
            set(schema["$defs"]["claimType"]["enum"]),
            {"speaker_claim", "report_synthesis", "open_question"},
        )
        block_refs = {
            entry["$ref"] for entry in schema["properties"]["blocks"]["items"]["oneOf"]
        }
        for definition in ("narrativeBlock", "keyPointsBlock", "foodForThoughtBlock"):
            self.assertIn(f"#/$defs/{definition}", block_refs)
        self.assertEqual(len(schema["properties"]["blocks"]["allOf"]), 4)

        validated = subprocess.run(
            ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(fixture)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertTrue(json.loads(validated.stdout)["valid"])

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec",
                    str(fixture),
                    "--markdown-out",
                    str(markdown_path),
                    "--html-out",
                    str(html_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            markdown = markdown_path.read_text(encoding="utf-8")
            html = html_path.read_text(encoding="utf-8")
            HTMLParser().feed(html)
            section_markers = [f"## {name}" for name in SECTIONS]
            markdown_positions = [markdown.index(marker) for marker in section_markers]
            html_positions = [html.index(f"<h2>{name}</h2>") for name in SECTIONS]
            self.assertEqual(markdown_positions, sorted(markdown_positions))
            self.assertEqual(html_positions, sorted(html_positions))
            for heading in (
                "講者提出的工作流程",
                "方案取捨",
                "控制與缺口",
                "下一步",
                "先抓住這三件事",
                "Food for thoughts",
            ):
                self.assertIn(heading, markdown)
                self.assertIn(heading, html)
            self.assertIn('content:"→"', html)
            self.assertIn('content:"↓"', html)
            self.assertIn('class="key-points"', html)
            self.assertIn('class="thoughts"', html)
            for reader_output in (markdown, html):
                self.assertNotIn("驗證與限制", reader_output)
                self.assertNotIn("原生字幕 整理", reader_output)
                self.assertNotIn("未下載或檢視影片畫面", reader_output)
                self.assertNotRegex(reader_output, r"\[E\d+\]")
                self.assertNotIn("講者主張", reader_output)
                self.assertNotIn("報告綜整", reader_output)
                self.assertNotIn("開放問題", reader_output)
                self.assertNotIn("逐字稿證據", reader_output)
                self.assertNotIn("先確認問題，再建立基準，最後才選擇工具。", reader_output)
            self.assertNotIn("file://", html)
            self.assertNotRegex(html, r"/Users/|/home/")
            self.assertNotIn("<script", html.lower())

    def test_v2_renderer_supports_markdown_only_kami_handoff(self):
        fixture = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            rendered = subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec",
                    str(fixture),
                    "--markdown-out",
                    str(markdown_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(rendered.stdout)
            self.assertTrue(result["valid"])
            self.assertEqual(result["markdown"], str(markdown_path))
            self.assertNotIn("html", result)
            self.assertTrue(markdown_path.is_file())
            self.assertFalse(html_path.exists())
            markdown = markdown_path.read_text(encoding="utf-8")
            for section in SECTIONS:
                self.assertIn(f"## {section}", markdown)
            self.assertNotIn("驗證與限制", markdown)
            self.assertNotIn("evidence_refs", markdown)

    def test_v2_validator_requires_all_four_reader_sections(self):
        original = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        cases = [
            ("內容重述", {"narrative", "process", "comparison", "control-gap"}),
            ("洞見", {"key-points"}),
            ("food for thoughts", {"food-for-thought"}),
            ("可行啟發", {"actions"}),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for section, removed_types in cases:
                with self.subTest(section=section):
                    fixture = json.loads(json.dumps(original))
                    fixture["blocks"] = [
                        block for block in fixture["blocks"] if block["type"] not in removed_types
                    ]
                    invalid_path = temp / f"missing-{next(iter(removed_types))}.json"
                    invalid_path.write_text(json.dumps(fixture), encoding="utf-8")
                    result = subprocess.run(
                        ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(invalid_path)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"缺少 reader-facing 章節：{section}", result.stderr)

    def test_v2_narrative_supports_text_only_content_restated_section(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        fixture["blocks"] = [
            {
                "id": "story",
                "type": "narrative",
                "title": "訪談主線",
                "claim_type": "speaker_claim",
                "evidence_refs": ["E1", "E2"],
                "paragraphs": [
                    {"text": "訪談先界定問題，再談速度與錯誤成本的取捨。", "evidence_refs": ["E1", "E2"]}
                ],
            },
            *[block for block in fixture["blocks"] if block["type"] in {"actions", "key-points", "food-for-thought"}],
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "narrative.json"
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            spec_path.write_text(json.dumps(fixture), encoding="utf-8")
            subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(spec_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec", str(spec_path),
                    "--markdown-out", str(markdown_path),
                    "--html-out", str(html_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            for output in (markdown_path.read_text(encoding="utf-8"), html_path.read_text(encoding="utf-8")):
                self.assertIn("訪談主線", output)
                self.assertIn("訪談先界定問題，再談速度與錯誤成本的取捨。", output)
                self.assertNotIn("講者提出的工作流程", output)

    def test_v2_validator_rejects_source_url_markdown_injection(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        fixture["source"]["url"] = "https://example.com/video\n\n## 驗證與限制"
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "url-injection.json"
            spec_path.write_text(json.dumps(fixture), encoding="utf-8")
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(spec_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("無空白、換行或憑證", result.stderr)

    def test_final_artifact_validator_covers_kami_handoff_contract(self):
        fixture = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            sidecar_path = temp / "demo123.verification.md"
            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec", str(fixture),
                    "--markdown-out", str(markdown_path),
                    "--html-out", str(html_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            fields = [
                "source_url", "resolved_url", "video_id", "metadata_path",
                "transcript_path", "report_markdown_path", "report_html_path",
                "presentation_backend", "presentation_fallback_reason",
                "subtitle_source", "extraction_tool", "transcription_method",
                "asr_backend", "asr_model", "asr_network_policy",
                "transcript_normalization",
                "audio_preprocess", "audio_cache_path", "extracted_at",
            ]
            command_fields = [
                "transcript_extract", "html_render", "html_parse",
                "section_scan", "deterministic_verification",
            ]
            sidecar_path.write_text(
                "# Verification\n\n"
                + "\n".join(f"- {field}: test" for field in fields)
                + "\n\n## Command Evidence\n\n"
                + "\n".join(f"- {field}: passed" for field in command_fields)
                + "\n\n## Limits\n\n- source: recorded in sidecar only\n",
                encoding="utf-8",
            )
            command = [
                "node", str(ROOT / "scripts" / "validate_report_artifacts.mjs"),
                "--spec", str(fixture),
                "--markdown", str(markdown_path),
                "--html", str(html_path),
                "--sidecar", str(sidecar_path),
            ]
            passed = subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertTrue(json.loads(passed.stdout)["valid"])

            original_html = html_path.read_text(encoding="utf-8")
            html_path.write_text(
                original_html.replace("先界定真正要解的問題。", "遺漏內容"),
                encoding="utf-8",
            )
            missing = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("HTML 遺漏 spec 內容", missing.stderr)

            html_path.write_text(
                original_html.replace("</main>", "<h2>驗證與限制</h2></main>"),
                encoding="utf-8",
            )
            leaked = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertNotEqual(leaked.returncode, 0)
            self.assertIn("HTML 四章不完整或順序錯誤", leaked.stderr)
            self.assertIn("reader-facing 禁止文字", leaked.stderr)

            for name, injected, expected in (
                (
                    "source-limit",
                    "<p>本報告使用自動字幕，未檢視影片畫面。</p>",
                    "reader-facing 來源或轉錄限制",
                ),
                (
                    "operator-path",
                    "<p>/Library/Application Support/operator.log</p>",
                    "絕對本機路徑",
                ),
                (
                    "source-limit-paraphrase",
                    "<p>內容根據 YouTube 自動生成的字幕整理，畫面未經人工核對。</p>",
                    "reader-facing 來源或轉錄限制",
                ),
            ):
                with self.subTest(name=name):
                    html_path.write_text(
                        original_html.replace("</main>", f"{injected}</main>"),
                        encoding="utf-8",
                    )
                    result = subprocess.run(command, check=False, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)

            html_path.write_text(original_html, encoding="utf-8")
            original_markdown = markdown_path.read_text(encoding="utf-8")
            for name, path_leak in (
                ("backtick-path", "`/Library/Application Support/operator.log`"),
                ("cjk-punctuation-path", "操作者路徑：/Library/Application Support/operator.log"),
            ):
                with self.subTest(name=name):
                    markdown_path.write_text(
                        original_markdown + f"\n{path_leak}\n",
                        encoding="utf-8",
                    )
                    markdown_path_leak = subprocess.run(command, check=False, capture_output=True, text=True)
                    self.assertNotEqual(markdown_path_leak.returncode, 0)
                    self.assertIn("Markdown 含絕對本機路徑", markdown_path_leak.stderr)
            markdown_path.write_text(original_markdown, encoding="utf-8")

            sidecar_path.write_text(
                "# Verification\n\n"
                + "\n".join(f"- {field}:" for field in fields)
                + "\n\n## Command Evidence\n\n"
                + "\n".join(f"- {field}:" for field in command_fields)
                + "\n\n## Limits\n",
                encoding="utf-8",
            )
            empty_sidecar = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertNotEqual(empty_sidecar.returncode, 0)
            self.assertIn("sidecar 缺少非空欄位", empty_sidecar.stderr)
            self.assertIn("sidecar Command Evidence 缺少非空欄位", empty_sidecar.stderr)
            self.assertIn("sidecar 缺少非空 Command Evidence", empty_sidecar.stderr)
            self.assertIn("sidecar 缺少非空 Limits", empty_sidecar.stderr)

    def test_v2_visuals_are_transcript_derived_without_media_path_contract(self):
        schema = (ROOT / "references" / "report-v2.schema.json").read_text(encoding="utf-8")
        renderer = (ROOT / "scripts" / "render_report_v2.mjs").read_text(encoding="utf-8")
        structure = (ROOT / "references" / "report-structure.md").read_text(encoding="utf-8")
        self.assertNotIn('"image_path"', schema)
        self.assertNotIn('loading="lazy"', renderer)
        self.assertIn("不要下載影片、不要擷取畫面", self.skill)
        self.assertIn("視覺化只編碼逐字稿中的關係與數值", structure)
        self.assertIn("縮圖只作來源錨點", structure)

    def test_v2_validator_rejects_missing_visual_evidence(self):
        original = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            cases = [
                ("process", 0, "nodes"),
                ("key-points", 4, "items"),
                ("food-for-thought", 5, "items"),
            ]
            for name, block_index, item_key in cases:
                with self.subTest(name=name):
                    fixture = json.loads(json.dumps(original))
                    del fixture["blocks"][block_index][item_key][0]["evidence_refs"]
                    invalid_path = temp / f"missing-evidence-{name}.json"
                    invalid_path.write_text(json.dumps(fixture), encoding="utf-8")
                    result = subprocess.run(
                        ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(invalid_path)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("evidence_refs", result.stderr)

    def test_v2_validator_rejects_unknown_evidence_and_chart(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        cases = []
        unknown_evidence = json.loads(json.dumps(fixture))
        unknown_evidence["blocks"][0]["nodes"][0]["evidence_refs"] = ["E404"]
        cases.append(("unknown-evidence", unknown_evidence, "不存在的 evidence"))
        chart = json.loads(json.dumps(fixture))
        chart["blocks"][0]["type"] = "chart"
        cases.append(("unsupported-chart", chart, "禁止 chart"))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for name, payload, expected in cases:
                with self.subTest(name=name):
                    invalid_path = temp / f"{name}.json"
                    invalid_path.write_text(json.dumps(payload), encoding="utf-8")
                    result = subprocess.run(
                        ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(invalid_path)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)

    def test_v2_validator_rejects_reader_facing_local_paths(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        fixture["blocks"][-1]["items"][0]["when"] = "讀取 /Users/example/private.txt 後執行。"
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "local-path.json"
            invalid_path.write_text(json.dumps(fixture), encoding="utf-8")
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(invalid_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("絕對本機路徑", result.stderr)

    def test_v2_thumbnail_accepts_safe_relative_path_and_rejects_traversal(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            relative_path = temp / "relative-thumbnail.json"
            fixture["source"]["thumbnail_url"] = "media/demo123.jpg"
            relative_path.write_text(json.dumps(fixture), encoding="utf-8")
            accepted = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(relative_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            fixture["source"]["thumbnail_url"] = "/Users/example/private/demo123.jpg"
            absolute_path = temp / "absolute-thumbnail.json"
            absolute_path.write_text(json.dumps(fixture), encoding="utf-8")
            rejected_absolute = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(absolute_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            fixture["source"]["thumbnail_url"] = "../private/demo123.jpg"
            traversal_path = temp / "traversal-thumbnail.json"
            traversal_path.write_text(json.dumps(fixture), encoding="utf-8")
            rejected = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(traversal_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertNotEqual(rejected_absolute.returncode, 0)
        self.assertIn("安全相對路徑", rejected_absolute.stderr)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("安全相對路徑", rejected.stderr)

    def test_v2_renderer_escapes_all_spec_strings(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        fixture["title"] = '<img src=x onerror="alert(1)">'
        fixture["blocks"][0]["nodes"][0]["detail"] = "<script>alert(1)</script>"
        fixture["blocks"][4]["items"][0]["text"] = '<b onclick="alert(2)">重點</b>'
        fixture["blocks"][5]["items"][0]["context"] = "<em>反思</em>"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "escaped.json"
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            spec_path.write_text(json.dumps(fixture), encoding="utf-8")
            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec",
                    str(spec_path),
                    "--markdown-out",
                    str(markdown_path),
                    "--html-out",
                    str(html_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            html = html_path.read_text(encoding="utf-8")
            markdown = markdown_path.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn('<img src=x onerror="alert(1)">', html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", markdown)
        self.assertIn(r"\<script\>alert(1)\</script\>", markdown)
        self.assertNotIn('<b onclick="alert(2)">', html)
        self.assertNotIn("<em>反思</em>", html)

    def test_declared_relative_resources_exist(self):
        pattern = re.compile(r"(?<![A-Za-z0-9_.-])((?:references|scripts|assets)/[A-Za-z0-9_./-]+)")
        for rel in pattern.findall(self.skill):
            rel = rel.rstrip(".,):;`")
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_eval_cases_present_unique_and_nonempty(self):
        buckets = ("should_trigger", "should_not_trigger", "near_neighbor")
        self.assertTrue(self.cases["should_trigger"])
        self.assertTrue(self.cases["should_not_trigger"])
        texts = [c["text"].strip() for key in buckets for c in self.cases.get(key, [])]
        self.assertTrue(all(texts))
        self.assertEqual(len(texts), len(set(texts)))


if __name__ == "__main__":
    unittest.main()
