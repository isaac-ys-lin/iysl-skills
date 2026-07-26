import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "equity-data"


class EquityDataContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        cls.source_map = (SKILL_DIR / "references" / "source-map.md").read_text(
            encoding="utf-8"
        )
        cls.ledger = (SKILL_DIR / "templates" / "source-ledger.md").read_text(
            encoding="utf-8"
        )
        cls.matrix = (
            SKILL_DIR / "templates" / "collected-data-matrix.md"
        ).read_text(encoding="utf-8")

    def test_router_owns_embedded_provider_selection(self):
        self.assertIn("plugin router own", self.skill)
        self.assertIn("category-to-provider mapping", self.skill)
        self.assertIn("Keep the evidence pack subordinate", self.skill)

    def test_seeking_alpha_is_not_an_automated_retrieval_route(self):
        self.assertIn("Do not automate retrieval", self.skill)
        self.assertIn("user-provided excerpt", self.skill)
        self.assertIn("screenshot, or export", self.skill)
        self.assertIn("route_status=terms_blocked", self.skill)
        self.assertIn(
            "Do not automate or systematically extract Seeking Alpha pages",
            self.source_map,
        )
        self.assertNotIn("access_mode=authorized_browser", self.source_map)

    def test_public_search_snippets_remain_discovery_only(self):
        self.assertIn(
            "Treat search results and snippets as discovery only", self.skill
        )
        self.assertIn(
            "Search results, snippets, cached previews, and AI summaries are discovery aids",
            self.source_map,
        )
        self.assertIn("Open and cite the actual page or document", self.source_map)

    def test_provider_vintages_cannot_be_blended(self):
        self.assertIn("averaging unlike vintages", self.skill)
        self.assertIn("Never blend revenue from one provider", self.source_map)
        self.assertIn("provider_vintage_mismatch", self.matrix)
        self.assertIn("synthetic consensus", self.matrix)

    def test_provenance_templates_capture_route_and_consensus_definition(self):
        for field in (
            "Source Kind",
            "Access Mode",
            "Permission",
            "Route Status",
            "Provider As-Of",
            "Retrieved / TZ",
            "URL / File Ref / Section",
        ):
            self.assertIn(field, self.ledger)
        self.assertIn("Definition / Provider Universe", self.matrix)
        self.assertIn("estimate_consensus", self.matrix)
        self.assertIn("provider_proprietary_score", self.matrix)


if __name__ == "__main__":
    unittest.main()
