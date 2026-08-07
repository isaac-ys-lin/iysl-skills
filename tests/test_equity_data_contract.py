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
        cls.intake = (
            SKILL_DIR / "references" / "seeking-alpha-intake.md"
        ).read_text(encoding="utf-8")
        cls.plugin_handoff = (
            SKILL_DIR / "references" / "plugin-handoff.md"
        ).read_text(encoding="utf-8")
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

    def test_embedded_handoff_pointer_reaches_canonical_fields(self):
        self.assertIn("references/plugin-handoff.md", self.skill)
        for field in (
            "owning_workflow",
            "decision_impact",
            "readiness_effect",
            "artifact_role=embedded_support_artifact",
            "hidden_unless_requested=true",
        ):
            self.assertIn(field, self.plugin_handoff)

    def test_seeking_alpha_account_route_is_preserved(self):
        self.assertIn("Seeking Alpha Chat", self.skill)
        self.assertIn("references/seeking-alpha-intake.md", self.skill)
        self.assertIn("access_mode=account_route", self.source_map)
        self.assertIn("Record the returned answer as an evidence artifact", self.intake)
        self.assertNotIn("user-supervised", self.intake)

    def test_direct_http_403_is_not_mistaken_for_chat_unavailability(self):
        for text in (
            "in-app browser",
            "HTTP fetch, API call, or search-crawl `403`",
            "direct_http_403",
            "it does not establish that the account route",
            "or Ask Chat is unavailable",
        ):
            self.assertIn(text, self.intake)
        self.assertIn("attempt it before", self.source_map)
        self.assertIn("failed retrieval leg", self.source_map)

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
