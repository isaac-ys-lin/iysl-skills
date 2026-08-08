import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


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
        cls.checklist = (
            SKILL_DIR / "templates" / "data-request-checklist.md"
        ).read_text(encoding="utf-8")

    def test_router_owns_embedded_provider_selection(self):
        self.assertIn("plugin router own", self.skill)
        self.assertIn("category-to-provider mapping", self.skill)
        self.assertIn("Keep the evidence pack subordinate", self.skill)

    def test_embedded_handoff_fields_are_canonical_and_inline(self):
        for field in (
            "owning_workflow",
            "decision_impact",
            "readiness_effect",
            "artifact_role=embedded_support_artifact",
            "hidden_unless_requested=true",
        ):
            self.assertIn(field, self.skill)

    def test_seeking_alpha_is_a_two_stage_default_scan(self):
        for phrase in (
            "Default Seeking Alpha scan",
            "two-stage Seeking Alpha scan",
            "Use two stages",
            "Ask SA",
            "Seeking Alpha structured fields",
            "provider_synthesis",
            "Keep the raw Ask SA response",
        ):
            self.assertIn(phrase, self.skill)
        self.assertIn("access_mode=account_route", self.source_map)
        self.assertNotIn("forward non-GAAP P/E and PEG", self.skill)

    def test_two_stage_order_is_repeated_across_eval_surfaces(self):
        self.assertLess(
            self.skill.index("Use Ask SA to identify"),
            self.skill.index("Retrieve only the relevant Seeking Alpha structured fields"),
        )
        self.assertIn("Ask SA recall followed by targeted structured data", self.checklist)
        self.assertIn("Ask SA recall first", (SKILL_DIR / "evals" / "behavior_cases.json").read_text(encoding="utf-8"))
        self.assertIn("Seeking Alpha scan", (SKILL_DIR / "evals" / "trigger_cases.json").read_text(encoding="utf-8"))

    def test_owner_required_fields_survive_the_scan(self):
        self.assertIn(
            "or independently required by the owning workflow",
            self.skill,
        )

    def test_multi_security_scan_does_not_expand_context_unnecessarily(self):
        self.assertIn(
            "record the selection rule and any material",
            self.skill,
        )
        self.assertIn("not every unscanned name", self.skill)

    def test_data_skill_does_not_own_decision_blockers(self):
        self.assertIn(
            "the owning workflow\ndetermines their effect",
            self.source_map,
        )
        self.assertNotIn(
            "Keep those as decision blockers",
            self.source_map,
        )

    def test_direct_http_403_is_not_mistaken_for_chat_unavailability(self):
        for phrase in (
            "in-app browser",
            "direct HTTP",
            "direct_http_403",
            "marks only that retrieval leg",
        ):
            self.assertIn(phrase, self.skill)
        self.assertIn("attempt it before", self.source_map)
        self.assertIn("failed retrieval leg", self.source_map)

    def test_ask_sa_failure_does_not_disable_structured_data(self):
        self.assertIn(
            "Ask SA failure does not make accessible Seeking Alpha symbol-page",
            self.skill,
        )
        self.assertIn("structured data unavailable", self.skill)

    def test_stock_move_analysis_returns_to_the_owning_workflow(self):
        self.assertIn("owner defines the decision", self.skill)
        self.assertIn("decision-relevant findings", self.skill)
        self.assertIn("investor-facing conclusion", self.skill)

    def test_transcript_indexes_are_not_full_transcripts(self):
        self.assertIn("transcript indexes or summaries", self.skill)
        self.assertIn("Once a full transcript is opened", self.skill)
        self.assertIn("formal issuer disclosures", self.skill)
        self.assertIn("opened full transcript", self.source_map)

    def test_source_map_does_not_duplicate_plugin_contract(self):
        self.assertNotIn("## Plugin Source Categories", self.source_map)
        self.assertNotIn("## Minimum Handoff By Workflow", self.source_map)
        self.assertNotIn("Quodd", self.source_map)
        self.assertNotIn("S&P Global Market Intelligence", self.source_map)

    def test_owner_defined_metadata_and_template_confidence_labels(self):
        self.assertIn("Owner-defined readiness or artifact metadata", self.checklist)
        self.assertNotIn("Evidence cut-off and readiness posture", self.checklist)
        self.assertIn("Ask SA recall followed by targeted structured data", self.checklist)
        self.assertNotIn("Seeking Alpha or Ask SA scan", self.checklist)
        self.assertIn("Evidence Confidence", self.matrix)
        self.assertIn("Source Reliability", self.ledger)

    def test_public_search_snippets_remain_discovery_only(self):
        self.assertIn("search snippets", self.skill)
        self.assertIn(
            "Search results, snippets, cached previews, and AI summaries are discovery aids",
            self.source_map,
        )
        self.assertIn("Open and cite the actual page or document", self.source_map)

    def test_provider_vintages_cannot_be_blended(self):
        self.assertIn("synthetic consensus", self.skill)
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
        self.assertIn("Verification Status", self.matrix)
        self.assertIn("estimate_consensus", self.matrix)
        self.assertIn("provider_proprietary_score", self.matrix)
        self.assertIn("direct_http_403", self.ledger)


if __name__ == "__main__":
    unittest.main()
