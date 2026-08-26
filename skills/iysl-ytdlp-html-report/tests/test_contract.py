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

    @staticmethod
    def _write_fixture_transcript(temp: Path, fixture: dict) -> Path:
        quotes = {item["id"]: item["transcript_quote"] for item in fixture["evidence"]}
        transcript = (quotes["E1"] + "開" * 1000 + quotes["E2"] + "中" * 1000
                      + quotes["E3"] + "後" * 1000 + quotes["E4"])
        path = temp / "clean-transcript.md"
        path.write_text(transcript, encoding="utf-8")
        return path

    @staticmethod
    def _v24_fixture() -> dict:
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        fixture["version"] = "2.4"
        block_by_id = {block["id"]: block for block in fixture["blocks"]}
        job_by_type = {
            "narrative": "explain",
            "process": "sequence",
            "comparison": "compare",
            "control-gap": "control",
            "spotlight": "emphasize",
            "key-points": "derive_insight",
            "food-for-thought": "raise_question",
            "actions": "prompt_action",
        }
        units = []
        unit_by_topic = {}
        for index, topic in enumerate(fixture["topic_coverage"]["topics"], start=1):
            unit_id = f"U{index}"
            unit_by_topic[topic["id"]] = unit_id
            primary = topic["block_ids"][0]
            signals = set(topic["salience_signals"])
            kind = next(
                (candidate for signal, candidate in (
                    ("concrete_metric", "metric"), ("decision", "decision"),
                    ("anecdote", "anecdote"), ("tradeoff", "tradeoff"),
                    ("caveat", "caveat"), ("open_question", "question"),
                ) if signal in signals),
                "claim",
            )
            units.append({
                "id": unit_id,
                "kind": kind,
                "statement": topic["title"],
                "evidence_refs": topic["evidence_refs"],
                "disposition": "included",
                "duplicate_of": None,
                "cognitive_job": job_by_type[block_by_id[primary]["type"]],
                "primary_block_id": primary,
                "secondary_block_ids": topic["block_ids"][1:],
                "routing_rationale": "使用能直接承載讀者認知任務的最小既有區塊。",
            })
        fixture["semantic_inventory"] = units
        fixture["interpretations"] = [
            {
                "id": f"I{index}",
                "kind": "question" if block["claim_type"] == "open_question" else (
                    "action" if block["type"] == "actions" else "insight"
                ),
                "text": block["title"],
                "basis_unit_ids": [
                    unit["id"] for unit in units
                    if block["id"] in [unit["primary_block_id"], *unit["secondary_block_ids"]]
                    or set(unit["evidence_refs"]) & set(block["evidence_refs"])
                ],
                "block_ids": [block["id"]],
            }
            for index, block in enumerate(fixture["blocks"], start=1)
            if block["claim_type"] != "speaker_claim"
        ]
        fixture["completeness_review"] = {
            "status": "passed",
            "sweep": {
                region: [unit_by_topic[topic_id] for topic_id in topic_ids]
                for region, topic_ids in fixture["topic_coverage"]["sweep"].items()
            },
        }
        fixture["source_limitation"] = {
            "scope": "transcript_only",
            "notice": "本報告以逐字稿為唯一內容來源，可能未涵蓋純畫面、語氣與示範細節；需要核對時請回到原影片。",
        }
        return fixture

    @staticmethod
    def _write_v24_spec(path: Path, spec: dict) -> None:
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        minutes = subprocess.run(
            ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path), "--print-reading-minutes"],
            check=True, capture_output=True, text=True,
        )
        spec["reading_minutes"] = int(minutes.stdout.strip())
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

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

    def test_two_core_principles_present(self):
        self.assertIn("逐字稿是唯一內容來源", self.skill)
        self.assertIn("讀者與 operator 資訊分離", self.skill)

    def test_pdf_export_is_explicit_and_routes_to_a_dedicated_contract(self):
        normalized = " ".join(self.skill.split())
        self.assertIn("PDF and page images remain opt-in", normalized)
        self.assertIn("references/pdf-export.md", self.skill)
        self.assertIn("scripts/export_report_pdf.mjs", self.skill)
        self.assertIn("scripts/validate_report_pdf.mjs", self.skill)
        self.assertTrue((ROOT / "references" / "pdf-export.md").is_file())

    def test_pdf_print_css_uses_report_anchors_without_forcing_every_chapter_to_a_new_page(self):
        css = (ROOT / "assets" / "report-print.css").read_text(encoding="utf-8")
        self.assertIn('[data-report-chrome="cover"]', css)
        self.assertIn("[data-report-brief]", css)
        self.assertIn("[data-report-section]", css)
        self.assertIn("[data-report-block]", css)
        self.assertIn("break-inside: avoid", css)
        self.assertNotRegex(css, r"\[data-report-section\][^{]*\{[^}]*break-before\s*:\s*page")

    def test_pdf_export_injects_print_contract_and_preserves_existing_output_on_failure(self):
        helper = ROOT / "scripts" / "export_report_pdf.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            html_path = temp / "report.html"
            html_path.write_text(
                '<!doctype html><html><head><title>測試</title></head><body><main>'
                '<header data-report-chrome="cover">封面</header>'
                '<section data-report-brief>摘要</section>'
                '<section data-report-section="recap"><article data-report-block="b1">內容</article></section>'
                '</main></body></html>',
                encoding="utf-8",
            )
            capture = temp / "captured.html"
            captured_args = temp / "captured.args"
            fake_browser = temp / "fake-chrome"
            fake_browser.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$@\" > \"$PDF_EXPORT_CAPTURE_ARGS\"\n"
                "out=''\ninput=''\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in --print-to-pdf=*) out=${arg#--print-to-pdf=} ;; file://*) input=$arg ;; esac\n"
                "done\n"
                "cp \"${input#file://}\" \"$PDF_EXPORT_CAPTURE_HTML\"\n"
                "printf '%%PDF-1.4\\nfake\\n%%%%EOF\\n' > \"$out\"\n"
                "sleep 5\n",
                encoding="utf-8",
            )
            fake_browser.chmod(0o755)
            pdf_path = temp / "report.pdf"
            env = os.environ.copy()
            env["PDF_EXPORT_CAPTURE_HTML"] = str(capture)
            env["PDF_EXPORT_CAPTURE_ARGS"] = str(captured_args)
            exported = subprocess.run(
                [
                    "node", str(helper), "--html", str(html_path), "--pdf", str(pdf_path),
                    "--browser-executable", str(fake_browser), "--browser-timeout-ms", "1000",
                ],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertEqual(json.loads(exported.stdout)["browser_completion"], "timed_out_after_pdf")
            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF-"))
            injected = capture.read_text(encoding="utf-8")
            self.assertIn('data-iysl-report-print="v1"', injected)
            self.assertIn('[data-report-chrome="cover"]', injected)
            self.assertIn("--no-pdf-header-footer", captured_args.read_text(encoding="utf-8"))

            pdf_path.write_bytes(b"existing-pdf")
            failing_browser = temp / "failing-chrome"
            failing_browser.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
            failing_browser.chmod(0o755)
            rejected = subprocess.run(
                [
                    "node", str(helper), "--html", str(html_path), "--pdf", str(pdf_path),
                    "--browser-executable", str(failing_browser),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(pdf_path.read_bytes(), b"existing-pdf")

    def test_pdf_validator_requires_a4_text_sections_and_complete_page_images(self):
        helper = ROOT / "scripts" / "validate_report_pdf.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            pdf_path = temp / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            pdfinfo = fake_bin / "pdfinfo"
            pdfinfo.write_text(
                "#!/bin/sh\n"
                "printf 'Pages: 2\\nEncrypted: no\\nJavaScript: no\\nPage size: 595 x 842 pts (A4)\\n'\n",
                encoding="utf-8",
            )
            pdftotext = fake_bin / "pdftotext"
            pdftotext.write_text("#!/bin/sh\nprintf '%s\\n' \"$PDF_TEST_TEXT\"\n", encoding="utf-8")
            pdftoppm = fake_bin / "pdftoppm"
            pdftoppm.write_text(
                "#!/bin/sh\n"
                "for last do :; done\n"
                "printf png > \"${last}-01.png\"\n"
                "printf png > \"${last}-02.png\"\n",
                encoding="utf-8",
            )
            for executable in (pdfinfo, pdftotext, pdftoppm):
                executable.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["PDF_TEST_TEXT"] = ("內容重述 洞見 Food for thoughts 可行啟發 " * 20).strip()
            qa_dir = temp / "qa"
            accepted = subprocess.run(
                ["node", str(helper), "--pdf", str(pdf_path), "--qa-dir", str(qa_dir)],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            result = json.loads(accepted.stdout)
            self.assertEqual(result["pages"], 2)
            self.assertTrue(result["visual_review_required"])
            self.assertEqual(len(result["page_images"]), 2)

            env["PDF_TEST_TEXT"] = ("內容重述 洞見 可行啟發 " * 30).strip()
            rejected = subprocess.run(
                ["node", str(helper), "--pdf", str(pdf_path)],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("foodforthoughts", rejected.stderr.lower())

            env["PDF_TEST_TEXT"] = (("內容重述 洞見 Food for thoughts 可行啟發 " * 20)
                                    + "file:///private/tmp/report.print.html")
            leaked = subprocess.run(
                ["node", str(helper), "--pdf", str(pdf_path)],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertNotEqual(leaked.returncode, 0)
            self.assertIn("file url", leaked.stderr.lower())

    def test_generic_video_summary_keeps_the_full_report_bundle(self):
        normalized_skill = " ".join(self.skill.split())
        self.assertIn("generic request", normalized_skill)
        self.assertIn(
            "transcript → validated v2 spec → Markdown → HTML → verification sidecar → artifact validation",
            normalized_skill,
        )
        self.assertIn("Do not create a summary-only shortcut", normalized_skill)
        self.assertIn("or an inline/deep mode", normalized_skill)

    def test_kami_composition_owns_formal_presentation_without_vendoring(self):
        normalized_skill = " ".join(self.skill.split())
        self.assertIn("內容與 presentation 分工", self.skill)
        self.assertIn("唯一語意 handoff", self.skill)
        self.assertIn("presentation_backend", self.skill)
        self.assertIn("presentation_fallback_reason", self.skill)
        self.assertIn("不要硬編碼安裝路徑", self.skill)
        self.assertIn(
            "不要把 Kami 的 template、diagram、CSS、字型、reference 或 script 複製進本 skill",
            normalized_skill,
        )
        self.assertIn("只保留一份 final report HTML", self.skill)
        self.assertNotIn("/path/to/kami", self.skill.lower())

        # 交接契約是「不必抄」的介面定義，不是被抄進來的資產，所以它是唯一例外。
        handoff = ROOT / "references" / "kami-handoff.md"
        self.assertTrue(handoff.is_file())
        vendored = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and "kami" in path.name.lower() and path != handoff
        ]
        self.assertEqual(vendored, [], vendored)

        # 契約只描述介面，不得夾帶 Kami 的樣式或模板。標籤名稱會以「規則」的身分
        # 出現在散文裡（例如「必須包在 <main> 裡」），那不是夾帶，所以只看真正
        # 屬於資產的痕跡：DOCTYPE、樣式表、字型宣告。
        contract = handoff.read_text(encoding="utf-8")
        for smell in ("<style", "font-family", "@page", "@font-face", "<!doctype"):
            self.assertNotIn(smell, contract.lower(), smell)
        for required in (
            "data-report-section",
            "data-report-brief",
            "data-report-chrome",
            "結構檢查，不是語意檢查",
            "硬失敗",
        ):
            self.assertIn(required, contract, required)

    def test_four_reader_sections_named_in_order(self):
        positions = [self.skill.find(name) for name in SECTIONS]
        self.assertTrue(all(pos >= 0 for pos in positions), positions)
        self.assertEqual(positions, sorted(positions))

    def test_insufficient_transcript_stops_before_reader_artifacts(self):
        normalized_skill = " ".join(self.skill.split())
        for phrase in (
            "confirm the transcript can support the `brief` and every required v2 section",
            "If the brief or any required section lacks support",
            "retain the manifest and clean transcript",
            "create no v2 spec, reader report, or verification sidecar",
        ):
            self.assertIn(phrase, normalized_skill)

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

    @unittest.skipIf(os.name == "nt", "POSIX fake CLI fixture requires chmod and shebang execution")
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

    @unittest.skipIf(os.name == "nt", "POSIX fake CLI fixture requires chmod and shebang execution")
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
        fixture = self._v24_fixture()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "spec.json"
            manifest_path = temp / "manifest.json"
            out_dir = temp / "out"
            self._write_v24_spec(spec_path, fixture)
            transcript_path = self._write_fixture_transcript(temp, fixture)
            manifest_path.write_text(
                json.dumps({
                    "id": "demo123",
                    "url": "https://www.youtube.com/watch?v=demo123",
                    "resolved_url": "https://www.youtube.com/watch?v=demo123",
                    "metadata": None,
                    "transcript": str(transcript_path),
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
            self.assertIn(
                "topical_coverage_gate: passed; transcript_regions=verified; topics=4",
                sidecar,
            )
            self.assertIn("deterministic_verification: v2 validator and artifact validator passed", sidecar)

            missing_transcript_manifest = temp / "missing-transcript-manifest.json"
            missing_transcript_manifest.write_text(
                json.dumps({
                    "id": "demo123",
                    "url": "https://www.youtube.com/watch?v=demo123",
                    "resolved_url": "https://www.youtube.com/watch?v=demo123",
                    "metadata": None,
                    "transcript": None,
                }),
                encoding="utf-8",
            )
            missing_transcript = subprocess.run(
                [
                    "node", str(helper), "--spec", str(spec_path),
                    "--manifest", str(missing_transcript_manifest),
                    "--out-dir", str(temp / "missing-transcript-out"),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(missing_transcript.returncode, 0)
            self.assertIn("semantic completeness gate 不可略過", missing_transcript.stderr)

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

    def test_finalizer_rejects_new_v23_bundle_but_legacy_validator_remains(self):
        helper = ROOT / "scripts" / "finalize_report.mjs"
        legacy_validator = ROOT / "scripts" / "validate_report_v2.mjs"
        fixture_path = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            validated = subprocess.run(
                ["node", str(legacy_validator), str(fixture_path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            transcript_path = self._write_fixture_transcript(temp, fixture)
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps({
                "id": "demo123", "url": fixture["source"]["url"],
                "transcript": str(transcript_path), "subtitle_status": "available",
            }), encoding="utf-8")
            out_dir = temp / "out"
            rejected = subprocess.run(
                [
                    "node", str(helper), "--spec", str(fixture_path),
                    "--manifest", str(manifest_path), "--out-dir", str(out_dir),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("只建立 v2.4", rejected.stderr)
            self.assertFalse(out_dir.exists())

    def test_v2_schema_fixture_validator_and_dual_renderer(self):
        schema = json.loads(
            (ROOT / "references" / "report-v2.schema.json").read_text(encoding="utf-8")
        )
        fixture = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        self.assertEqual(schema["properties"]["version"]["const"], "2.3")
        self.assertIn("reading_minutes", schema["required"])
        self.assertIn("brief", schema["required"])
        self.assertEqual(
            set(schema["$defs"]["briefClaim"]["properties"]["claim_type"]["enum"]),
            {"speaker_claim", "report_synthesis"},
        )
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
                "順序、成本、紀錄，三件事決定比較有沒有意義",
                "還沒被回答的兩個問題",
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

    def test_v24_validator_requires_semantic_inventory(self):
        helper = ROOT / "scripts" / "validate_report_v2_4.mjs"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec = self._v24_fixture()
            spec_path = temp / "report-v2.4.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            minutes = subprocess.run(
                ["node", str(helper), str(spec_path), "--print-reading-minutes"],
                check=True, capture_output=True, text=True,
            )
            spec["reading_minutes"] = int(minutes.stdout.strip())
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            accepted = subprocess.run(
                ["node", str(helper), str(spec_path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            del spec["semantic_inventory"]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            rejected = subprocess.run(
                ["node", str(helper), str(spec_path)],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("semantic_inventory", rejected.stderr)

    def test_v24_schema_documents_inventory_routing_and_source_boundary(self):
        schema = json.loads(
            (ROOT / "references" / "report-v2.4.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["version"]["const"], "2.4")
        for field in (
            "semantic_inventory", "interpretations", "completeness_review", "source_limitation"
        ):
            self.assertIn(field, schema["required"])
        self.assertNotIn("minItems", schema["properties"]["interpretations"])
        self.assertEqual(
            schema["$defs"]["sourceLimitation"]["properties"]["notice"]["const"],
            "本報告以逐字稿為唯一內容來源，可能未涵蓋純畫面、語氣與示範細節；需要核對時請回到原影片。",
        )
        unit = schema["$defs"]["semanticUnit"]
        self.assertEqual(
            set(unit["required"]),
            {
                "id", "kind", "statement", "evidence_refs", "disposition", "duplicate_of",
                "cognitive_job", "primary_block_id", "secondary_block_ids", "routing_rationale",
            },
        )
        self.assertEqual(
            set(schema["$defs"]["disposition"]["enum"]),
            {"included", "compressed_duplicate", "excluded_nonsemantic"},
        )

    def test_v24_renderer_shows_source_limitation_without_operator_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec = self._v24_fixture()
            spec_path = temp / "report-v2.4.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            minutes = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(spec_path), "--print-reading-minutes"],
                check=True, capture_output=True, text=True,
            )
            spec["reading_minutes"] = int(minutes.stdout.strip())
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            rendered = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec", str(spec_path), "--markdown-out", str(markdown_path),
                    "--html-out", str(html_path),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            notice = spec["source_limitation"]["notice"]
            for output in (
                markdown_path.read_text(encoding="utf-8"),
                html_path.read_text(encoding="utf-8"),
            ):
                self.assertIn(notice, output)
                self.assertIn(spec["source"]["url"], output)
                self.assertNotIn("semantic_inventory", output)
                self.assertNotIn("routing_rationale", output)
                self.assertNotIn("basis_unit_ids", output)

    def test_v24_rejects_weakened_source_limitation_notice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = self._v24_fixture()
            spec["source_limitation"]["notice"] = "本報告只參考逐字稿。"
            path = Path(temp_dir) / "report-v2.4.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path)],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("固定警語", result.stderr)

    def test_v24_allows_no_interpretations_when_report_adds_no_derivation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = self._v24_fixture()
            spec["interpretations"] = []
            for block in spec["blocks"]:
                if block["claim_type"] == "report_synthesis":
                    block["claim_type"] = "speaker_claim"
            self.assertTrue(any(block["claim_type"] == "open_question" for block in spec["blocks"]))
            path = Path(temp_dir) / "report-v2.4.json"
            self._write_v24_spec(path, spec)
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_v24_completeness_sweep_does_not_force_nonsemantic_filler(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = self._v24_fixture()
            spec["semantic_inventory"].append({
                "id": "U-nonsemantic",
                "kind": "nonsemantic",
                "statement": "開場寒暄，不改變理解。",
                "evidence_refs": ["E2"],
                "disposition": "excluded_nonsemantic",
                "duplicate_of": None,
                "cognitive_job": None,
                "primary_block_id": None,
                "secondary_block_ids": [],
                "routing_rationale": "純寒暄，不承載主張、背景、例子、數字、限制或問題。",
            })
            path = Path(temp_dir) / "report-v2.4.json"
            self._write_v24_spec(path, spec)
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_v24_finalization_proves_semantic_completeness_and_reader_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec = self._v24_fixture()
            spec_path = temp / "report-v2.4.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            minutes = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(spec_path), "--print-reading-minutes"],
                check=True, capture_output=True, text=True,
            )
            spec["reading_minutes"] = int(minutes.stdout.strip())
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            transcript_path = self._write_fixture_transcript(temp, spec)
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps({
                "id": spec["source"]["video_id"],
                "url": spec["source"]["url"],
                "transcript": str(transcript_path),
                "subtitle_status": "available",
            }), encoding="utf-8")
            out_dir = temp / "out"
            finalized = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                    "--spec", str(spec_path), "--manifest", str(manifest_path),
                    "--out-dir", str(out_dir), "--fallback-reason", "kami-not-selected",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(finalized.returncode, 0, finalized.stderr)
            bundle = json.loads(finalized.stdout)
            sidecar = Path(bundle["verification_sidecar"]).read_text(encoding="utf-8")
            self.assertIn("semantic_completeness_gate: passed", sidecar)
            self.assertIn("source_scope: transcript_only", sidecar)
            self.assertIn("semantic_warnings:", sidecar)

            html_path = Path(bundle["report_html"])
            html = html_path.read_text(encoding="utf-8")
            html_path.write_text(html.replace(spec["source_limitation"]["notice"], ""), encoding="utf-8")
            rejected = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "validate_report_artifacts.mjs"),
                    "--spec", str(spec_path), "--markdown", bundle["report_markdown"],
                    "--html", str(html_path), "--sidecar", bundle["verification_sidecar"],
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("source limitation", rejected.stderr)

    def test_v24_artifacts_require_source_limitation_inside_brief(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec = self._v24_fixture()
            spec_path = temp / "report-v2.4.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            minutes = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(spec_path), "--print-reading-minutes"],
                check=True, capture_output=True, text=True,
            )
            spec["reading_minutes"] = int(minutes.stdout.strip())
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            transcript_path = self._write_fixture_transcript(temp, spec)
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps({
                "id": spec["source"]["video_id"],
                "url": spec["source"]["url"],
                "transcript": str(transcript_path),
                "subtitle_status": "available",
            }), encoding="utf-8")
            out_dir = temp / "out"
            finalized = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                    "--spec", str(spec_path), "--manifest", str(manifest_path),
                    "--out-dir", str(out_dir), "--fallback-reason", "kami-not-selected",
                ],
                check=True, capture_output=True, text=True,
            )
            bundle = json.loads(finalized.stdout)
            html_path = Path(bundle["report_html"])
            html = html_path.read_text(encoding="utf-8")
            paragraph = re.search(r'<p class="source-limitation">.*?</p>', html).group(0)
            html = html.replace(paragraph, "").replace("</main>", f"{paragraph}</main>")
            html_path.write_text(html, encoding="utf-8")
            rejected = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "validate_report_artifacts.mjs"),
                    "--spec", str(spec_path), "--markdown", bundle["report_markdown"],
                    "--html", str(html_path), "--sidecar", bundle["verification_sidecar"],
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("brief", rejected.stderr)

    def test_v24_hard_fails_orphans_false_exclusions_duplicates_and_unbased_interpretations(self):
        helper = ROOT / "scripts" / "validate_report_v2_4.mjs"

        def validate(mutator):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                spec = self._v24_fixture()
                path = temp / "report-v2.4.json"
                path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
                minutes = subprocess.run(
                    ["node", str(helper), str(path), "--print-reading-minutes"],
                    check=True, capture_output=True, text=True,
                )
                spec["reading_minutes"] = int(minutes.stdout.strip())
                mutator(spec)
                path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
                return subprocess.run(
                    ["node", str(helper), str(path)],
                    check=False, capture_output=True, text=True,
                )

        cases = []

        def orphan(spec):
            spec["semantic_inventory"][0]["primary_block_id"] = "missing-block"
        cases.append((orphan, "primary_block_id"))

        def false_exclusion(spec):
            unit = spec["semantic_inventory"][0]
            unit.update({
                "disposition": "excluded_nonsemantic", "duplicate_of": None,
                "cognitive_job": None, "primary_block_id": None, "secondary_block_ids": [],
            })
        cases.append((false_exclusion, "有效語意不可標成 excluded_nonsemantic"))

        def duplicate_cycle(spec):
            first = spec["semantic_inventory"][0]
            second = spec["semantic_inventory"][1]
            for unit, target in ((first, second["id"]), (second, first["id"])):
                unit.update({
                    "disposition": "compressed_duplicate", "duplicate_of": target,
                    "cognitive_job": None, "primary_block_id": None, "secondary_block_ids": [],
                })
        cases.append((duplicate_cycle, "duplicate chain 形成循環"))

        def missing_basis(spec):
            spec["interpretations"][0]["basis_unit_ids"] = ["missing-unit"]
        cases.append((missing_basis, "basis_unit_ids 必須指向 included unit"))

        def incomplete_sweep(spec):
            missing = spec["semantic_inventory"][0]["id"]
            for ids in spec["completeness_review"]["sweep"].values():
                while missing in ids:
                    ids.remove(missing)
        cases.append((incomplete_sweep, "沒有出現在 completeness review sweep"))

        def brief_only(spec):
            spec["brief"]["claim"]["evidence_refs"] = ["E404"]
        cases.append((brief_only, "沒有來自 included semantic unit"))

        for mutator, expected in cases:
            with self.subTest(expected=expected):
                result = validate(mutator)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_v24_routing_exception_warns_without_deleting_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec = self._v24_fixture()
            spec["semantic_inventory"][0]["cognitive_job"] = "compare"
            path = temp / "report-v2.4.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            minutes = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path), "--print-reading-minutes"],
                check=True, capture_output=True, text=True,
            )
            spec["reading_minutes"] = int(minutes.stdout.strip())
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / "validate_report_v2_4.mjs"), str(path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            warnings = json.loads(result.stdout)["warnings"]
            self.assertTrue(any("routing exception" in warning for warning in warnings), warnings)

    def test_v23_topic_coverage_maps_salient_topics_to_reader_blocks(self):
        schema = json.loads(
            (ROOT / "references" / "report-v2.schema.json").read_text(encoding="utf-8")
        )
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["version"]["const"], "2.3")
        self.assertIn("topic_coverage", schema["required"])
        block_refs = {
            entry["$ref"] for entry in schema["properties"]["blocks"]["items"]["oneOf"]
        }
        self.assertIn("#/$defs/spotlightBlock", block_refs)
        self.assertIn("topic_coverage", fixture)
        self.assertTrue(any(block["type"] == "spotlight" for block in fixture["blocks"]))
        handoff = (ROOT / "references" / "kami-handoff.md").read_text(encoding="utf-8")
        self.assertIn("topic_coverage", handoff)
        self.assertIn("不是讀者內容", handoff)

        def validate(spec, transcript=None):
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "spec.json"
                path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
                command = ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(path)]
                if transcript is not None:
                    transcript_path = Path(temp_dir) / "transcript.md"
                    transcript_path.write_text(transcript, encoding="utf-8")
                    command.extend(["--transcript", str(transcript_path)])
                return subprocess.run(
                    command,
                    check=False, capture_output=True, text=True,
                )

        self.assertEqual(validate(fixture).returncode, 0)

        missing = json.loads(json.dumps(fixture))
        del missing["topic_coverage"]
        rejected = validate(missing)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("topic_coverage", rejected.stderr)

        empty_middle = json.loads(json.dumps(fixture))
        empty_middle["topic_coverage"]["sweep"]["middle"] = []
        rejected = validate(empty_middle)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("middle", rejected.stderr)

        missing_block = json.loads(json.dumps(fixture))
        missing_block["topic_coverage"]["topics"][0]["block_ids"] = ["not-a-block"]
        rejected = validate(missing_block)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("not-a-block", rejected.stderr)

        quotes = {item["id"]: item["transcript_quote"] for item in fixture["evidence"]}
        transcript = (quotes["E1"] + "開" * 1000 + quotes["E2"] + "中" * 1000
                      + quotes["E3"] + "後" * 1000 + quotes["E4"])
        self.assertEqual(validate(fixture, transcript).returncode, 0)
        self_declared = json.loads(json.dumps(fixture))
        topic_ids = [topic["id"] for topic in self_declared["topic_coverage"]["topics"]]
        self_declared["topic_coverage"]["sweep"] = {
            "opening": topic_ids,
            "middle": [topic_ids[0]],
            "ending": [topic_ids[0]],
        }
        rejected = validate(self_declared, transcript)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("transcript", rejected.stderr)

    def test_spotlight_is_reader_visible_inside_content_restatement(self):
        fixture = ROOT / "tests" / "fixtures" / "report-v2.valid.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            rendered = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "render_report_v2.mjs"),
                    "--spec", str(fixture),
                    "--markdown-out", str(markdown_path),
                    "--html-out", str(html_path),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            markdown = markdown_path.read_text(encoding="utf-8")
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("一個不能被摘要掉的具體片段", markdown)
            self.assertIn("一個不能被摘要掉的具體片段", html)
            self.assertIn('class="spotlight"', html)
            self.assertIn('data-report-block="pilot-spotlight"', html)
            self.assertIn('data-report-block-type="spotlight"', html)
            self.assertLess(
                html.index('class="spotlight"'),
                html.index('data-report-section="key-points"'),
            )

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
            ("內容重述", {"narrative", "process", "comparison", "control-gap", "spotlight"}),
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
        coverage_blocks = {
            "topic-order": ["story"],
            "topic-cost": ["story", "key-points"],
            "topic-control": ["key-points"],
            "topic-pilot": ["next-actions"],
        }
        for topic in fixture["topic_coverage"]["topics"]:
            topic["block_ids"] = coverage_blocks[topic["id"]]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "narrative.json"
            markdown_path = temp / "report.md"
            html_path = temp / "report.html"
            spec_path.write_text(json.dumps(fixture), encoding="utf-8")
            # 改動 block 會改變讀者文字長度，reading_minutes 必須跟著重算。
            fixture["reading_minutes"] = int(subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "validate_report_v2.mjs"),
                    str(spec_path), "--print-reading-minutes",
                ],
                check=True, capture_output=True, text=True,
            ).stdout.strip())
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
                "topical_coverage_gate",
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
            # 章節識別改用結構化錨點之後，多插一個 h2 不再是章節錯誤；它被擋下來
            # 的理由是 reader-facing 禁止文字，這才是這個案例真正的缺陷。
            self.assertIn("HTML 含 reader-facing 禁止文字：驗證與限制", leaked.stderr)
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
        fixture["blocks"][5]["items"][0]["text"] = '<b onclick="alert(2)">重點</b>'
        fixture["blocks"][6]["items"][0]["context"] = "<em>反思</em>"
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


    # --- Section anchor contract -------------------------------------------------
    # 章節識別的權威是 data-report-section，不是標題文字或標題層級。所有案例
    # 都走協調器 CLI，因為要證明的是「使用者真的跑起來時會不會被擋下」。

    def _finalize_bundle(self, temp: Path):
        fixture = self._v24_fixture()
        spec_path = temp / "spec.json"
        manifest_path = temp / "manifest.json"
        out_dir = temp / "out"
        self._write_v24_spec(spec_path, fixture)
        transcript_path = self._write_fixture_transcript(temp, fixture)
        manifest_path.write_text(
            json.dumps({
                "id": "demo123",
                "url": "https://www.youtube.com/watch?v=demo123",
                "resolved_url": "https://www.youtube.com/watch?v=demo123",
                "metadata": None,
                "transcript": str(transcript_path),
                "subtitle": None,
                "subtitle_status": "available",
                "prepared_by": "test fixture",
            }),
            encoding="utf-8",
        )
        finalized = subprocess.run(
            [
                "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                "--spec", str(spec_path),
                "--manifest", str(manifest_path),
                "--out-dir", str(out_dir),
            ],
            check=True, capture_output=True, text=True,
        )
        return spec_path, json.loads(finalized.stdout)

    def _revalidate(self, spec_path: Path, bundle: dict, html_path: Path):
        """把一份外部最終 HTML 送進協調器 CLI，走使用者真正會走的那條路。"""
        out_dir = html_path.parent / f"out-{html_path.stem}"
        return subprocess.run(
            [
                "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                "--spec", str(spec_path),
                "--manifest", str(spec_path.parent / "manifest.json"),
                "--out-dir", str(out_dir),
                "--html-in", str(html_path),
                "--presentation-backend", "kami-long-doc",
            ],
            check=False, capture_output=True, text=True,
        )

    def test_external_spotlight_requires_a_typed_block_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")
            mistyped = html.replace(
                'data-report-block-type="spotlight"',
                'data-report-block-type="narrative"',
                1,
            )
            html_path = temp / "mistyped-spotlight.html"
            html_path.write_text(mistyped, encoding="utf-8")
            rejected = self._revalidate(spec_path, bundle, html_path)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("type 應為 spotlight", rejected.stderr)

    def test_section_anchors_are_the_channel_the_validator_reads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")

            anchors = re.findall(r'data-report-section="([a-z-]+)"', html)
            self.assertEqual(anchors, ["recap", "key-points", "food-for-thought", "actions"])

            # 標題層級任意但錨點正確：通過。h2 全部降成 h3 並插入額外小節。
            free_form = html.replace("<h2>", "<h3>").replace("</h2>", "</h3>")
            free_form = free_form.replace(
                '<section id="key-points"',
                '<h2>編輯自訂的小節</h2><section id="key-points"',
            )
            free_form_path = temp / "free-form.html"
            free_form_path.write_text(free_form, encoding="utf-8")
            self.assertEqual(self._revalidate(spec_path, bundle, free_form_path).returncode, 0)

            # 標題文字完全正確但缺一個錨點：被拒，且訊息指出缺的是哪一個。
            stripped = html.replace(' data-report-section="food-for-thought"', "")
            stripped_path = temp / "stripped.html"
            stripped_path.write_text(stripped, encoding="utf-8")
            missing = self._revalidate(spec_path, bundle, stripped_path)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("缺少章節錨點：food-for-thought", missing.stderr)

            # 錨點順序錯誤：被拒。
            reordered = html.replace(
                'data-report-section="recap"', "data-report-section=\"__tmp__\""
            ).replace(
                'data-report-section="actions"', 'data-report-section="recap"'
            ).replace(
                'data-report-section="__tmp__"', 'data-report-section="actions"'
            )
            reordered_path = temp / "reordered.html"
            reordered_path.write_text(reordered, encoding="utf-8")
            out_of_order = self._revalidate(spec_path, bundle, reordered_path)
            self.assertNotEqual(out_of_order.returncode, 0)
            self.assertIn("章節錨點順序錯誤", out_of_order.stderr)

            # 未定義的錨點值：被拒。
            unknown = html.replace('data-report-section="actions"', 'data-report-section="appendix"')
            unknown_path = temp / "unknown.html"
            unknown_path.write_text(unknown, encoding="utf-8")
            rejected = self._revalidate(spec_path, bundle, unknown_path)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("未定義的章節錨點：appendix", rejected.stderr)

            # Markdown 端的四章掃描不受影響。
            markdown = Path(bundle["report_markdown"]).read_text(encoding="utf-8")
            self.assertEqual(
                re.findall(r"^## (.+)$", markdown, re.MULTILINE),
                ["內容重述", "洞見", "food for thoughts", "可行啟發"],
            )


    def test_brief_is_required_and_evidence_governed(self):
        # 掃讀層受和其他讀者主張同一套證據治理。負向案例全部打在協調器 CLI 上，
        # 因為要證明的是「使用者真的跑起來時會不會被擋下」。
        base = self._v24_fixture()
        manifest = {
            "id": "demo123",
            "url": "https://www.youtube.com/watch?v=demo123",
            "resolved_url": "https://www.youtube.com/watch?v=demo123",
            "metadata": None,
            "transcript": None,
            "subtitle": None,
            "subtitle_status": "available",
            "prepared_by": "test fixture",
        }

        def finalize(mutate):
            spec = json.loads(json.dumps(base))
            mutate(spec)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                spec_path = temp / "spec.json"
                manifest_path = temp / "manifest.json"
                out_dir = temp / "out"
                self._write_v24_spec(spec_path, spec)
                run_manifest = dict(manifest)
                run_manifest["transcript"] = str(self._write_fixture_transcript(temp, base))
                manifest_path.write_text(json.dumps(run_manifest), encoding="utf-8")
                result = subprocess.run(
                    [
                        "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                        "--spec", str(spec_path),
                        "--manifest", str(manifest_path),
                        "--out-dir", str(out_dir),
                    ],
                    check=False, capture_output=True, text=True,
                )
                produced = sorted(path.name for path in out_dir.iterdir()) if out_dir.exists() else []
                return result, produced

        ok, produced = finalize(lambda spec: None)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(produced)

        def drop_brief(spec):
            del spec["brief"]

        missing, produced = finalize(drop_brief)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("brief", missing.stderr)
        self.assertEqual(produced, [], "被 gate 擋下時不得留下任何交付物")

        def too_few(spec):
            spec["brief"]["takeaways"] = spec["brief"]["takeaways"][:2]

        def too_many(spec):
            extra = json.loads(json.dumps(spec["brief"]["takeaways"][0]))
            spec["brief"]["takeaways"] = spec["brief"]["takeaways"] + [extra, extra]

        for mutate in (too_few, too_many):
            rejected, _ = finalize(mutate)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("$.brief.takeaways 必須有三到四項", rejected.stderr)

        def claim_without_evidence(spec):
            spec["brief"]["claim"]["evidence_refs"] = []

        def takeaway_without_evidence(spec):
            spec["brief"]["takeaways"][1]["evidence_refs"] = []

        for mutate in (claim_without_evidence, takeaway_without_evidence):
            rejected, _ = finalize(mutate)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("evidence ref", rejected.stderr)

        def dangling_evidence(spec):
            spec["brief"]["claim"]["evidence_refs"] = ["E-does-not-exist"]

        dangling, _ = finalize(dangling_evidence)
        self.assertNotEqual(dangling.returncode, 0)
        self.assertIn("指向不存在的 evidence", dangling.stderr)

        def open_question_claim(spec):
            spec["brief"]["claim"]["claim_type"] = "open_question"

        rejected, _ = finalize(open_question_claim)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("$.brief.claim.claim_type", rejected.stderr)

        def synthesis_claim(spec):
            spec["brief"]["claim"]["claim_type"] = "report_synthesis"

        accepted, _ = finalize(synthesis_claim)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        def legacy_version(spec):
            spec["version"] = "2.0"

        legacy, _ = finalize(legacy_version)
        self.assertNotEqual(legacy.returncode, 0)
        self.assertIn("只建立 v2.4", legacy.stderr)


    def test_undeclared_reader_regions_are_violations_and_chrome_must_be_enumerated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")

            # 保底路徑自己的輸出通過：它的 cover 已宣告，四章都有錨點。
            baseline_path = temp / "baseline.html"
            baseline_path.write_text(html, encoding="utf-8")
            self.assertEqual(self._revalidate(spec_path, bundle, baseline_path).returncode, 0)

            # 憑空多出來的一整段讀者內容：沒有錨點也沒有宣告，被擋下。
            injected = html.replace(
                "</main>",
                "<section><h2>編輯補充</h2><p>逐字稿裡沒有的一段話。</p></section></main>",
            )
            injected_path = temp / "injected.html"
            injected_path.write_text(injected, encoding="utf-8")
            rejected = self._revalidate(spec_path, bundle, injected_path)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("沒有 spec 錨點也沒有 chrome 宣告", rejected.stderr)

            # 同一段宣告成列舉內的 chrome：通過。
            for kind in ("cover", "toc", "running-head"):
                declared = html.replace(
                    "</main>",
                    f'<nav data-report-chrome="{kind}"><p>目錄</p></nav></main>',
                )
                declared_path = temp / f"declared-{kind}.html"
                declared_path.write_text(declared, encoding="utf-8")
                self.assertEqual(
                    self._revalidate(spec_path, bundle, declared_path).returncode, 0, kind
                )

            # 列舉之外的宣告值：同樣被擋下，宣告本身不是通行證。
            bogus = html.replace(
                "</main>",
                '<aside data-report-chrome="sidebar"><p>補充</p></aside></main>',
            )
            bogus_path = temp / "bogus.html"
            bogus_path.write_text(bogus, encoding="utf-8")
            bogus_result = self._revalidate(spec_path, bundle, bogus_path)
            self.assertNotEqual(bogus_result.returncode, 0)
            self.assertIn("chrome 宣告未定義：sidebar", bogus_result.stderr)

            # 兩種宣告不能並存：一個區塊要嘛回指 spec，要嘛承認自己沒有證據。
            both = html.replace(
                'data-report-section="recap"',
                'data-report-section="recap" data-report-chrome="cover"',
                1,
            )
            self.assertNotEqual(both, html, "測試字串沒有命中，等於什麼都沒驗到")
            both_path = temp / "both.html"
            both_path.write_text(both, encoding="utf-8")
            both_result = self._revalidate(spec_path, bundle, both_path)
            self.assertNotEqual(both_result.returncode, 0)
            self.assertIn("同時宣告", both_result.stderr)


    def test_brief_appears_in_both_reader_outputs_and_is_not_a_fifth_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")
            markdown = Path(bundle["report_markdown"]).read_text(encoding="utf-8")

            claim = spec["brief"]["claim"]["text"]
            takeaways = [item["text"] for item in spec["brief"]["takeaways"]]

            for text in [claim, *takeaways]:
                self.assertIn(text, markdown)
                self.assertIn(text, html)

            # Markdown 的 brief 不使用二級標題，四章掃描仍恰好四章。
            self.assertEqual(
                re.findall(r"^## (.+)$", markdown, re.MULTILINE),
                ["內容重述", "洞見", "food for thoughts", "可行啟發"],
            )
            self.assertLess(markdown.index(claim), markdown.index("## 內容重述"))

            # HTML 的 brief 沒有標題，帶自己的錨點，且位於四章之前。
            brief_region = re.search(r'<section[^>]*data-report-brief[^>]*>(.*?)</section>', html, re.DOTALL)
            self.assertIsNotNone(brief_region)
            self.assertNotRegex(brief_region.group(1), r"<h[1-6]\b")
            self.assertEqual(len(re.findall(r"data-report-brief\b", html)), 1)
            self.assertLess(
                html.index("data-report-brief"),
                html.index('data-report-section="recap"'),
            )

            # brief 缺席、重複、或落在四章之後，三種情況各自被拒。
            cases = {
                "缺少 brief 掃讀層": re.sub(
                    r'<section[^>]*data-report-brief[^>]*>.*?</section>', "", html, flags=re.DOTALL
                ),
                "必須恰好一個": html.replace(
                    "<section class=\"report-brief\" data-report-brief>",
                    "<section class=\"report-brief\" data-report-brief></section>"
                    "<section class=\"report-brief\" data-report-brief>",
                    1,
                ),
            }
            moved = re.search(r'<section[^>]*data-report-brief[^>]*>.*?</section>', html, re.DOTALL).group(0)
            cases["必須位於四章之前"] = html.replace(moved, "").replace("</main>", moved + "</main>")

            for expected, mutated in cases.items():
                path = temp / f"case-{abs(hash(expected))}.html"
                path.write_text(mutated, encoding="utf-8")
                result = self._revalidate(spec_path, bundle, path)
                self.assertNotEqual(result.returncode, 0, expected)
                self.assertIn(expected, result.stderr)


    def test_external_final_html_is_the_validated_deliverable_and_failure_is_hard(self):
        # 交給讀者的那一份就是被驗的那一份；驗不過就硬失敗，不偷偷退回內建。
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, baseline = self._finalize_bundle(temp)
            manifest_path = temp / "manifest.json"
            good_html = temp / "external-ok.html"
            good_html.write_text(
                Path(baseline["report_html"]).read_text(encoding="utf-8"), encoding="utf-8"
            )

            def finalize(out_name, *extra):
                out_dir = temp / out_name
                result = subprocess.run(
                    [
                        "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                        "--spec", str(spec_path),
                        "--manifest", str(manifest_path),
                        "--out-dir", str(out_dir),
                        *extra,
                    ],
                    check=False, capture_output=True, text=True,
                )
                produced = sorted(path.name for path in out_dir.iterdir()) if out_dir.exists() else []
                return result, out_dir, produced

            accepted, out_dir, produced = finalize(
                "external", "--html-in", str(good_html), "--presentation-backend", "kami-long-doc"
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertIn("demo123.report.html", produced)
            # 交付的 HTML 逐字等於外部那一份，沒有被重新渲染過。
            self.assertEqual(
                (out_dir / "demo123.report.html").read_text(encoding="utf-8"),
                good_html.read_text(encoding="utf-8"),
            )
            sidecar = (out_dir / "demo123.verification.md").read_text(encoding="utf-8")
            self.assertIn("presentation_backend: kami-long-doc", sidecar)
            self.assertIn("presentation_fallback_reason: not-applicable", sidecar)

            bad_html = temp / "external-bad.html"
            bad_html.write_text(
                good_html.read_text(encoding="utf-8").replace(' data-report-section="actions"', ""),
                encoding="utf-8",
            )
            rejected, _, produced = finalize(
                "rejected", "--html-in", str(bad_html), "--presentation-backend", "kami-long-doc"
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("缺少章節錨點：actions", rejected.stderr)
            self.assertNotIn(
                "demo123.report.html", produced,
                "外部出稿驗證失敗時不得留下任何 HTML，尤其不得偷偷退回內建",
            )

            missing_backend, _, _ = finalize("no-backend", "--html-in", str(good_html))
            self.assertNotEqual(missing_backend.returncode, 0)
            self.assertIn("必須以 --presentation-backend 指明", missing_backend.stderr)

            mislabelled, _, _ = finalize(
                "mislabelled", "--presentation-backend", "kami-long-doc"
            )
            self.assertNotEqual(mislabelled.returncode, 0)
            self.assertIn("必須是 built-in-v2", mislabelled.stderr)

            # 保底路徑要說清楚是哪一種：Kami 不可用，還是這次沒選 Kami。
            for reason in ("kami-unavailable", "kami-not-selected"):
                ok, out_dir, produced = finalize(f"fallback-{reason}", "--fallback-reason", reason)
                self.assertEqual(ok.returncode, 0, ok.stderr)
                self.assertIn("demo123.report.html", produced)
                sidecar = (out_dir / "demo123.verification.md").read_text(encoding="utf-8")
                self.assertIn("presentation_backend: built-in-v2", sidecar)
                self.assertIn(f"presentation_fallback_reason: {reason}", sidecar)

            bogus_reason, _, _ = finalize("bogus-reason", "--fallback-reason", "whatever")
            self.assertNotEqual(bogus_reason.returncode, 0)
            self.assertIn("kami-unavailable 或 kami-not-selected", bogus_reason.stderr)


    def test_declaration_cannot_be_forged_and_bare_prose_cannot_slip_in(self):
        # 這些是「排版器偷偷多寫內容」的實際手法。每一種都必須被擋下，否則
        # 「沒有錨點就是違規」只是一句話。
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")

            evasions = {
                "comment-anchor": html.replace(
                    'data-report-section="actions"', 'data-report-chrome="running-head"'
                ).replace("</main>", '<!-- data-report-section="actions" --></main>'),
                "forged-declaration": html.replace(
                    "</main>",
                    "<section title='data-report-chrome=\"cover\"'><p>捏造。</p></section></main>",
                ),
                "bare-paragraph": html.replace("</main>", "<p>逐字稿沒有的一段。</p></main>"),
                "bare-div": html.replace("</main>", "<div><p>捏造。</p></div></main>"),
                "table-of-invented-facts": html.replace(
                    "</main>", "<table><tr><td>捏造數字</td></tr></table></main>"
                ),
                "prose-after-main": html.replace("</body>", "<p>捏造尾聲。</p></body>"),
            }
            for name, mutated in evasions.items():
                path = temp / f"evade-{name}.html"
                path.write_text(mutated, encoding="utf-8")
                result = self._revalidate(spec_path, bundle, path)
                self.assertNotEqual(result.returncode, 0, f"{name} 沒有被擋下")

            # 單引號的合法宣告不該被誤殺——它是排版器最容易踩到的陷阱。
            single_quoted = temp / "single-quoted.html"
            single_quoted.write_text(
                html.replace('data-report-chrome="cover"', "data-report-chrome='cover'"),
                encoding="utf-8",
            )
            self.assertEqual(self._revalidate(spec_path, bundle, single_quoted).returncode, 0)

    def test_a_failed_run_leaves_no_deliverable_behind(self):
        # sidecar 的 Command Evidence 宣稱每一關都過了。驗證沒過卻把它留在
        # out-dir，等於留下一份替失敗背書的紀錄。
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")
            out_dir = Path(bundle["report_html"]).parent
            self.assertTrue(sorted(path.name for path in out_dir.iterdir()))

            broken = temp / "broken.html"
            broken.write_text(html.replace(' data-report-section="actions"', ""), encoding="utf-8")
            result = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                    "--spec", str(spec_path),
                    "--manifest", str(temp / "manifest.json"),
                    "--out-dir", str(out_dir),
                    "--html-in", str(broken),
                    "--presentation-backend", "kami-long-doc",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("缺少章節錨點：actions", result.stderr)
            self.assertEqual(
                sorted(path.name for path in out_dir.iterdir()), [],
                "失敗的執行不得留下任何交付物，包括上一次執行的殘骸",
            )

    def test_sidecar_cannot_claim_a_backend_or_a_fallback_that_did_not_happen(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            external = temp / "external.html"
            external.write_text(
                Path(bundle["report_html"]).read_text(encoding="utf-8"), encoding="utf-8"
            )

            def finalize(*extra):
                return subprocess.run(
                    [
                        "node", str(ROOT / "scripts" / "finalize_report.mjs"),
                        "--spec", str(spec_path),
                        "--manifest", str(temp / "manifest.json"),
                        "--out-dir", str(temp / "guard"),
                        "--html-in", str(external),
                        *extra,
                    ],
                    check=False, capture_output=True, text=True,
                )

            mislabelled = finalize("--presentation-backend", "built-in-v2")
            self.assertNotEqual(mislabelled.returncode, 0)
            self.assertIn("不能標成 built-in-v2", mislabelled.stderr)

            fake_fallback = finalize(
                "--presentation-backend", "kami-long-doc",
                "--fallback-reason", "kami-unavailable",
            )
            self.assertNotEqual(fake_fallback.returncode, 0)
            self.assertIn("不能宣稱 fallback 發生過", fake_fallback.stderr)

    def test_rendered_html_has_no_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")
            ids = re.findall(r'\sid\s*=\s*"([^"]*)"', html)
            self.assertEqual(sorted(ids), sorted(set(ids)), "重複的 id 讓片段連結指向不明")

            collided = temp / "collided.html"
            collided.write_text(html.replace('id="section-recap"', 'id="workflow"', 1), encoding="utf-8")
            result = self._revalidate(spec_path, bundle, collided)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("重複的 id", result.stderr)

    def test_brief_takeaways_are_not_verbatim_copies_of_block_text(self):
        # 逐字重複會讓「brief 內容有沒有出現在輸出裡」失效：文字在別處也找得到，
        # 所以整個掃讀層被丟掉也驗得過。
        spec = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )
        block_text = json.dumps(spec["blocks"], ensure_ascii=False)
        for takeaway in spec["brief"]["takeaways"]:
            self.assertNotIn(takeaway["text"], block_text, takeaway["text"])
        self.assertNotIn(spec["brief"]["claim"]["text"], block_text)


    def test_block_content_must_sit_in_its_own_section(self):
        # 錯置不會被「文字有沒有出現在文件裡」抓到，但 Markdown 版是照真正的
        # 對應渲染的，錯置會讓兩份交付物講不同的故事。
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")

            actions = re.search(
                r'(<section[^>]*data-report-section="actions"[^>]*>)(.*?)(</section>)', html, re.S
            )
            self.assertIsNotNone(actions)
            moved = html.replace(
                actions.group(0),
                actions.group(1) + "<article><header><h3>佔位</h3></header></article>" + actions.group(3),
            ).replace("</section>", actions.group(2) + "</section>", 1)
            self.assertNotEqual(moved, html)

            path = temp / "misfiled.html"
            path.write_text(moved, encoding="utf-8")
            result = self._revalidate(spec_path, bundle, path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("放錯章節，它屬於 actions", result.stderr)

    def test_structural_gate_names_what_is_missing(self):
        # SKILL.md 承諾失敗時說得出缺什麼。最常見的失敗如果只回一句
        # "check failed"，那個承諾就是空的。
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path, bundle = self._finalize_bundle(temp)
            html = Path(bundle["report_html"]).read_text(encoding="utf-8")

            cases = {
                "缺少 <main> 區塊": html.replace("<main", "<div").replace("</main>", "</div>"),
                "含有 <script>": html.replace("</main>", "</main><script>void 0;</script>"),
            }
            for expected, mutated in cases.items():
                path = temp / f"structural-{abs(hash(expected))}.html"
                path.write_text(mutated, encoding="utf-8")
                result = self._revalidate(spec_path, bundle, path)
                self.assertNotEqual(result.returncode, 0, expected)
                self.assertIn(expected, result.stderr)

    def test_handoff_contract_states_every_rule_the_code_enforces(self):
        # 契約與程式碼各說各話，比契約不完整更糟：排版器照做卻失敗。
        contract = (ROOT / "references" / "kami-handoff.md").read_text(encoding="utf-8")
        for rule in (
            "<main>",
            "<script>",
            "雙引號或單引號都可以",
            "不能重複",
            "章節歸屬",
            "narrative",
            "絕對本機路徑",
        ):
            self.assertIn(rule, contract, rule)


    def test_presentation_runs_in_an_isolated_context(self):
        # 「排版器不能加事實」原本只是一條規則。把逐字稿排除在它的 context 之外，
        # 那件事才變成它做不到，而不是它被要求別做。
        normalized_skill = " ".join(self.skill.split())
        for phrase in (
            "排版在隔離的 context 裡進行",
            "dispatch the presentation to a subagent",
            "never receives the clean transcript, the metadata, or the source manifest",
            "Do not pass it the transcript, the metadata, or the manifest",
            "the **only** subagent the standard path uses",
        ):
            self.assertIn(phrase, normalized_skill, phrase)

        contract = (ROOT / "references" / "kami-handoff.md").read_text(encoding="utf-8")
        self.assertIn("排版在隔離的 context 裡進行", contract)
        self.assertIn("拿不到 clean transcript、metadata 或 source manifest", contract)
        # 契約要誠實說出這條保證是 context 隔離守的，不是驗證器守的。
        self.assertIn("這一段是 context 隔離守住的，不是驗證器守住的", contract)

        cases = json.loads(
            (ROOT / "evals" / "behavior_cases.json").read_text(encoding="utf-8")
        )["cases"]
        by_id = {case["id"]: case for case in cases}
        self.assertIn("presentation-subagent-gets-no-transcript", by_id)
        # 標準路徑現在必須用到那一個排版 subagent，舊的 0 上限會把正確行為判成錯。
        for case in cases:
            cap = case["expected"].get("max_subagents")
            if cap is not None:
                self.assertGreaterEqual(cap, 1, case["id"])


    def test_style_and_layout_contract_is_stated_and_enforced_where_it_can_be(self):
        # 風格有兩種：能被機器擋的（標題撞名、閱讀時間造假）與只能寫成契約的
        # （版面節奏）。兩種都要有，而且要分清楚哪一種是哪一種。
        contract = (ROOT / "references" / "kami-handoff.md").read_text(encoding="utf-8")
        for rule in ("## 版面契約", "封面", "表格保持表格", "不要加互動", "reading_minutes"):
            self.assertIn(rule, contract, rule)

        structure = (ROOT / "references" / "report-structure.md").read_text(encoding="utf-8")
        for rule in ("三層閱讀深度", "heading 必須自帶判斷，不能是分類詞", "不可與它所屬章節同名"):
            self.assertIn(rule, structure, rule)

    def test_block_title_may_not_echo_its_section_and_reading_time_may_not_be_invented(self):
        base = json.loads(
            (ROOT / "tests" / "fixtures" / "report-v2.valid.json").read_text(encoding="utf-8")
        )

        def validate(mutate):
            spec = json.loads(json.dumps(base))
            mutate(spec)
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "spec.json"
                path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
                return subprocess.run(
                    ["node", str(ROOT / "scripts" / "validate_report_v2.mjs"), str(path)],
                    check=False, capture_output=True, text=True,
                )

        self.assertEqual(validate(lambda spec: None).returncode, 0)

        for block_type, section in (
            ("key-points", "洞見"),
            ("food-for-thought", "food for thoughts"),
            ("actions", "可行啟發"),
        ):
            def echo(spec, block_type=block_type, section=section):
                for block in spec["blocks"]:
                    if block["type"] == block_type:
                        block["title"] = section
            result = validate(echo)
            self.assertNotEqual(result.returncode, 0, block_type)
            self.assertIn(f"不可與所屬章節同名：{section}", result.stderr)

        def inflate(spec):
            spec["reading_minutes"] = 99

        faked = validate(inflate)
        self.assertNotEqual(faked.returncode, 0)
        self.assertIn("不可自行填寫", faked.stderr)

        # 拉長內容就必須跟著改；否則舊值會靜悄悄地錯下去。
        def lengthen(spec):
            spec["blocks"][0]["summary"] = "補充說明。" * 400

        stale = validate(lengthen)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("$.reading_minutes 必須是", stale.stderr)

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
