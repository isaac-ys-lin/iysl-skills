import json
import re
import unittest
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
