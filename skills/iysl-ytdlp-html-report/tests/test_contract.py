import json
import re
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Personal-machine residue that must never ship in a portable, installable skill.
NON_PORTABLE = ("/Users/", "study_flow", "mlxwhisper", "miniconda", "Caskroom")

SECTIONS = ["內容重述", "洞見", "food for thoughts", "可行啟發", "驗證與限制"]


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
            if "tests" in path.relative_to(ROOT).parts:
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
        self.assertIn("/path/to/skill/scripts/transcribe_groq.mjs", self.skill)
        self.assertIn("/path/to/skill/scripts/render_html.mjs", self.skill)

    def test_two_core_principles_present(self):
        self.assertIn("逐字稿是唯一內容來源", self.skill)
        self.assertIn("讀者與 operator 資訊分離", self.skill)

    def test_five_sections_named_in_order(self):
        positions = [self.skill.find(name) for name in SECTIONS]
        self.assertTrue(all(pos >= 0 for pos in positions), positions)
        self.assertEqual(positions, sorted(positions))

    def test_audio_fallback_is_backend_agnostic_with_clean_degradation(self):
        self.assertIn("backend-agnostic", self.skill)
        self.assertIn("無字幕且無可用轉錄 backend", self.skill)
        # yt-dlp is the portable audio-download layer; keep it explicit.
        self.assertIn("yt-dlp", self.skill)

    def test_groq_fallback_is_explicit_and_secret_safe(self):
        helper = (ROOT / "scripts" / "transcribe_groq.mjs").read_text(encoding="utf-8")
        self.assertIn("GROQ_API_KEY", self.skill)
        self.assertIn("transcribe_groq.mjs", self.skill)
        self.assertIn("parseGroqApiKey", helper)
        self.assertIn("process.env.GROQ_API_KEY", helper)
        self.assertIn("api.groq.com/openai/v1/audio/transcriptions", helper)
        self.assertNotIn("console.log(apiKey", helper)

    def test_extractor_persists_metadata_when_captions_are_unavailable(self):
        extractor = (ROOT / "scripts" / "extract_transcript.mjs").read_text(encoding="utf-8")
        self.assertIn('subtitle_status: "unavailable"', extractor)
        self.assertIn('capture_status: "captions-unavailable"', extractor)

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

1. 限制一。
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            report_path = temp / "report.md"
            metadata_path = temp / "metadata.json"
            output_path = temp / "report.html"
            report_path.write_text(report, encoding="utf-8")
            metadata_path.write_text(json.dumps({"title": "Test", "webpage_url": "https://example.com"}), encoding="utf-8")
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
            for section_id in ("insights", "food", "actions", "verification"):
                section = re.search(rf'<section id="{section_id}".*?</section>', html, re.DOTALL)
                self.assertIsNotNone(section, section_id)
                self.assertIn("<ul>", section.group(0))
                self.assertNotIn("<ol>", section.group(0))
            insights = re.search(r'<section id="insights".*?</section>', html, re.DOTALL).group(0)
            self.assertEqual(insights.count("<ul>"), 1)

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
        for definition in ("keyPointsBlock", "foodForThoughtBlock"):
            self.assertIn(f"#/$defs/{definition}", block_refs)

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
            self.assertIn("@media (max-width:375px)", html)
            self.assertIn('content:"→"', html)
            self.assertIn('content:"↓"', html)
            self.assertIn('class="key-points"', html)
            self.assertIn('class="thoughts"', html)
            self.assertIn("原生字幕 整理；未下載或檢視影片畫面。", markdown)
            self.assertIn("原生字幕 整理；未下載或檢視影片畫面。", html)
            for reader_output in (markdown, html):
                self.assertNotRegex(reader_output, r"\[E\d+\]")
                self.assertNotIn("講者主張", reader_output)
                self.assertNotIn("報告綜整", reader_output)
                self.assertNotIn("開放問題", reader_output)
                self.assertNotIn("逐字稿證據", reader_output)
                self.assertNotIn("先確認問題，再建立基準，最後才選擇工具。", reader_output)
            self.assertNotIn("file://", html)
            self.assertNotRegex(html, r"/Users/|/home/")
            self.assertNotIn("<script", html.lower())

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
