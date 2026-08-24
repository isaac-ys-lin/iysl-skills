import json
import math
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TICK = chr(96)


class EquityCouncilContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.judgment = (ROOT / "references" / "judgment-contract.md").read_text(
            encoding="utf-8"
        )
        cls.council = (ROOT / "references" / "council-protocol.md").read_text(
            encoding="utf-8"
        )
        cls.triggers = json.loads(
            (ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8")
        )
        cls.behavior = json.loads(
            (ROOT / "evals" / "behavior_cases.json").read_text(encoding="utf-8")
        )
        cls.openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        cls.interface = (ROOT / "agents" / "interface.yaml").read_text(
            encoding="utf-8"
        )
        cls.run_template = json.loads(
            (ROOT / "templates" / "council-run.json").read_text(encoding="utf-8")
        )

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_public_council_package_does_not_load_private_skill_code(self):
        inspected = [
            ROOT / "scripts" / "validate_council_run.py",
            ROOT / "tests" / "test_council_run_validator.py",
        ]
        for path in inspected:
            body = path.read_text(encoding="utf-8")
            self.assertNotIn('/ "iysl-equity-data"', body, path)
            self.assertNotIn("test_pei_input_receipt_validator.py", body, path)
            self.assertNotIn("test_study_flow_adapter.py", body, path)

    def test_minimum_gate_and_native_owner_boundary(self):
        normalized = re.sub(r"\s+", " ", self.skill).replace(TICK, "")
        for phrase in (
            "valid security identity",
            "current price with as-of timestamp",
            "explicit decision horizon",
            "minimally usable Public Equity Investing",
            "Never fan out across every constituent skill",
            "Do not invoke iysl-equity-data directly",
            "formal provider coverage",
            "may not browse, create a competing coverage artifact, or repair the gap",
            "Return a targeted refill request to Public Equity Investing",
            "start a new Council run only after the updated PEI receipt",
            "do not start a second refill loop",
            "intake failure, not Avoid",
        ):
            self.assertIn(phrase, normalized)

    def test_targeted_refill_ranks_overflow_and_has_one_terminal_disposition(self):
        skill = re.sub(r"\s+", " ", self.skill)
        judgment = re.sub(r"\s+", " ", self.judgment)
        for phrase in (
            "identifies a model- or sign-changing gap",
            "at most two exact inputs",
            "one targeted Public Equity Investing refill request",
            "Do not browse or patch the live Council record",
            "creates a new accepted PEI baseline and a new Council run",
            "do not start a second refill loop",
        ):
            self.assertIn(phrase, skill)
        for phrase in (
            "current Council run stops",
            "at most two inputs in one targeted PEI refill request",
            "Only a new independently accepted PEI receipt",
            "An unaccepted lead may not change a model input or start another refill",
        ):
            self.assertIn(phrase, judgment)

    def test_named_personas_are_public_method_priors(self):
        normalized = re.sub(r"\s+", " ", self.council)
        for phrase in (
            "Aswath Damodaran — Fundamental Committee Member",
            "George Soros — Reflexivity Committee Member",
            "Michael Mauboussin — Expectations Committee Member",
            "Public-method simulation of Aswath Damodaran",
            "Public-method simulation of George Soros",
            "Public-method simulation of Michael Mauboussin",
            "Stanley Druckenmiller — PM Chair",
            "Public-method simulation of Stanley Druckenmiller",
            "Reputation never increases source quality",
            "They do not claim access to private process",
        ):
            self.assertIn(phrase, normalized)
        for url in (
            "pages.stern.nyu.edu/~adamodar/New_Home_Page/NNPreface.html",
            "pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/growthdeterminants.htm",
            "aswathdamodaran.blogspot.com/2015/08/dcf-myth-2-dcf-is-exercise-in-modeling.html",
            "georgesoros.com/2014/01/13/fallibility-reflexivity-and-the-human-uncertainty-principle-2",
            "georgesoros.com/2012/06/02/remarks_at_the_festival_of_economics_trento_italy",
            "article_marketexpectedreturnoninvestment_en.pdf",
            "article_bayesandbaserates_ltr.pdf",
            "article_probabilitiesandpayoffs.pdf",
            "morganstanley.com/insights/videos/hard-lessons/duquesne-stan-druckenmiller-iliana-bouzali",
            "goldmansachs.com/insights/talks-at-gs/stanley-druckenmiller.html",
            "nbim.no/en/news-and-insights/podcast/2024/stan-druckenmiller-inside-the-mind-of-a-legendary-investor",
        ):
            self.assertIn(url, self.council)
        self.assertIn(
            "Their names and public methods affect question generation, required work products, and interpretation, never source quality",
            re.sub(r"\s+", " ", self.skill),
        )

    def test_named_methods_require_distinct_non_generic_work_products(self):
        normalized = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        for phrase in (
            "Reverse valuation and story-to-numbers bridge",
            "PEI baseline, price-implied, and plausible range",
            "least plausible embedded assumption",
            "Reflexive loop and phase map",
            "belief or bias -> participant action -> price, volume, options, liquidity, or financing response",
            "inception, acceleration, negative-feedback test, twilight, or reversal",
            "Expectations infrastructure and calibrated distribution",
            "reference class by causal driver, company life-cycle state",
            "base-rate prior with source, sample/vintage, outcome definition",
            "Reference-class gap",
            "Never invent precise probabilities",
        ):
            self.assertIn(phrase, normalized)

    def test_named_pm_chair_is_decision_persona_not_fourth_research_seat(self):
        council = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        skill = re.sub(r"\s+", " ", self.skill).replace(TICK, "")
        judgment = re.sub(r"\s+", " ", self.judgment).replace(TICK, "")
        for phrase in (
            "Stanley Druckenmiller — PM Chair",
            "not a fourth research seat",
            "may not browse, add a source, create a fourth memo",
            "Dominant-variable decision matrix",
            "Horizon transition",
            "Dominant variable",
            "State matrix",
            "Seat decisions",
            "Strongest disconfirming path",
            "Reversal trigger",
            "Accept, Conditional, or Reject",
            "no sizing, order, execution, or simulated personal position",
        ):
            self.assertIn(phrase, council)
        for phrase in (
            "The Chair is not a fourth agent",
            "does not browse or create a fourth research memo",
            "may not invent missing member work",
            "never authorizes the Chair to infer sizing, concentration, orders, execution",
        ):
            self.assertIn(phrase, skill)
        for phrase in (
            "separate Stanley Druckenmiller — PM Chair completion gate",
            "public-method decision persona",
            "may use only accepted PEI inputs and sealed member memos",
            "may not browse, add evidence, simulate a personal position, infer sizing",
        ):
            self.assertIn(phrase, judgment)

    def test_three_agents_are_isolated_and_evidence_closed(self):
        normalized = re.sub(r"\s+", " ", self.council)
        for phrase in (
            "Spawn exactly three parallel leaf agents",
            "the same common factual spine",
            "one exact committee-member name and its distinct method card",
            "one method-specific private evidence partition",
            "named method-specific work product and freshness receipt",
            "evidence-closed authority to inspect only that packet",
            "browsed=false",
            "no added evidence IDs",
            "no full PEI narrative, Chair conclusion, other member memo, upstream disposition",
            "prohibition on further delegation",
            "First-round memos remain sealed",
            "independent work paths, not independent proof",
        ):
            self.assertIn(phrase, normalized)
        self.assertNotIn("browse accessible external sources", normalized)

    def test_common_factual_spine_and_private_partitions_prevent_narrative_anchoring(self):
        council = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        skill = re.sub(r"\s+", " ", self.skill).replace(TICK, "")
        for phrase in (
            "common factual spine",
            "private_partitions.damodaran",
            "fundamentals, reverse_valuation, and capital_structure",
            "private_partitions.soros",
            "price_path, marginal_actors, and positioning_reflexivity",
            "private_partitions.mauboussin",
            "expectations_revisions, reference_class, and probability_payoff",
            "owner fair value remains sealed from George Soros",
            "full PEI thesis narrative remains sealed from Michael Mauboussin",
        ):
            self.assertIn(phrase, council)
        for phrase in (
            "support/pei_input_receipt.json",
            "hard research gap",
            "implementation-only blocker does not block research admission",
            "full accepted PEI baseline only after",
        ):
            self.assertIn(phrase, skill)

    def test_unique_contribution_gate_has_one_bounded_correction(self):
        normalized = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        for phrase in (
            "causal_mechanism",
            "primary_mechanism_tag",
            "mechanism_tags",
            "disconfirming_condition",
            "key_metric",
            "source_posture",
            "persona_convergence",
            "exactly one corrective pass",
            "may not browse or add evidence during the corrective pass",
            "unresolved_convergence",
            "Robustness: Fragile",
            "not independent confirmation",
            "semantic convergence review",
            "near-synonym paraphrases",
        ):
            self.assertIn(phrase, normalized)

    def test_council_run_template_exposes_admission_partitions_and_separate_outputs(self):
        template = self.run_template
        self.assertEqual(template["schema_version"], 2)
        self.assertIn("council_runtime", template)
        self.assertIn("pei_input_receipt", template)
        self.assertEqual(set(template["private_partitions"]), {"damodaran", "soros", "mauboussin"})
        for memo in template["first_round"]["memos"]:
            self.assertIs(memo["browsed"], False)
            self.assertEqual(memo["added_evidence_ids"], [])
        self.assertEqual(set(template["sealed_inputs"]), {
            "upstream_verdict",
            "full_pei_narrative",
            "participation",
            "implementation_readiness",
            "other_seat_outputs",
        })
        self.assertIn("corrective_pass_count", template["convergence"])
        self.assertIn("semantic_review", template["convergence"])
        for memo in template["first_round"]["memos"]:
            self.assertIn("primary_mechanism_tag", memo["contribution"])
            self.assertIn("mechanism_tags", memo["contribution"])
            self.assertIn("method_artifact", memo)
            self.assertIn("proposition_id", memo["method_artifact"])
        artifacts = {
            memo["seat"]: memo["method_artifact"]
            for memo in template["first_round"]["memos"]
        }
        self.assertEqual(
            artifacts["damodaran"]["artifact_type"],
            "damodaran_reverse_valuation_v1",
        )
        self.assertIn("price_implied_drivers", artifacts["damodaran"])
        self.assertIn("story_to_numbers_bridge", artifacts["damodaran"])
        self.assertEqual(
            artifacts["soros"]["artifact_type"], "soros_reflexivity_chain_v1"
        )
        self.assertIn("feedback_chain", artifacts["soros"])
        self.assertIn("horizon_price_paths", artifacts["soros"])
        self.assertEqual(
            artifacts["mauboussin"]["artifact_type"],
            "mauboussin_expectations_distribution_v1",
        )
        self.assertIn("reference_class", artifacts["mauboussin"])
        self.assertIn("probability_payoff_states", artifacts["mauboussin"])
        self.assertIn("posterior_success_probability_pct", artifacts["mauboussin"])
        self.assertIn("success_state_ids", artifacts["mauboussin"])
        for decision in template["chair"]["seat_decisions"]:
            self.assertIn("proposition_id", decision)
        for field in (
            "research_stance",
            "confidence",
            "robustness",
            "participation",
            "implementation_readiness",
            "decision_matrix",
        ):
            self.assertIn(field, template["chair"])
        self.assertEqual(
            template["chair"]["decision_matrix"]["artifact_type"],
            "dominant_variable_state_matrix_v1",
        )
        self.assertIn("states", template["chair"]["decision_matrix"])
        self.assertEqual(len(template["chair"]["decision_matrix"]["states"]), 3)
        self.assertEqual(
            [
                state["scenario_role"]
                for state in template["chair"]["decision_matrix"]["states"]
            ],
            ["downside", "base", "upside"],
        )
        for state in template["chair"]["decision_matrix"]["states"]:
            self.assertIn("target_components", state)
            self.assertIn("probability_components", state)
            self.assertIn("evidence_ids", state)
        self.assertIn(
            "reversal_triggers", template["chair"]["decision_matrix"]
        )
        self.assertIn("validate_council_run.py", self.skill)

    def test_docs_make_structured_method_artifacts_and_recomputation_mandatory(self):
        council = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        judgment = re.sub(r"\s+", " ", self.judgment).replace(TICK, "")
        skill = re.sub(r"\s+", " ", self.skill).replace(TICK, "")
        for phrase in (
            "damodaran_reverse_valuation_v1",
            "soros_reflexivity_chain_v1",
            "mauboussin_expectations_distribution_v1",
            "dominant_variable_state_matrix_v1",
            "fluent prose is not a substitute",
            "probabilities must sum to 100",
            "recompute every target-price return and expected value",
            "strongest disconfirming state must oppose the final stance",
            "prior + signed updates = posterior",
            "success-state probabilities = posterior",
            "target_components",
            "probability_components",
            "weights must sum to 100",
            "target price must equal the weighted resolved inputs",
            "state probability must equal the weighted resolved inputs",
            "scenario_role",
            "each component source must have the same role",
            "downside <= base <= upside",
            "gap-only artifact",
            "cannot supply Chair numeric components",
            "each named method source state may be allocated to only one",
            "does not permit split allocation or duplicate probability counting",
        ):
            self.assertIn(phrase, council)
        for phrase in (
            "Council run schema v2",
            "named structured method_artifact",
            "validator-recomputed arithmetic",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("machine-checkable structured artifact", judgment)

    def test_accepted_market_evidence_is_sealed_into_soros_partition(self):
        council = re.sub(r"\s+", " ", self.council)
        skill = re.sub(r"\s+", " ", self.skill)
        judgment = re.sub(r"\s+", " ", self.judgment)
        for phrase in (
            "Use the accepted current market packet for the requested horizon",
            "options, short-interest, positioning, or liquidity",
            "upstream freshness receipt",
            "current_upstream_reused",
            "surfaces_attempted",
            "distinct_evidence_edge",
        ):
            self.assertIn(phrase, council)
        self.assertIn(
            "Public options, volume, price, short-interest, positioning, and liquidity evidence",
            skill,
        )
        self.assertIn(
            "Public options, price, volume, short-interest, positioning, liquidity, and market-reaction evidence",
            judgment,
        )

    def test_analysis_is_broad_but_the_evidence_set_is_closed(self):
        normalized = re.sub(r"\s+", " ", self.council)
        self.assertIn("Analysis may be broad, but the evidence set is closed", normalized)
        self.assertIn("may not browse, follow an unaccepted lead", normalized)
        for field in (
            "claim",
            "origin_key",
            "source_locator",
            "as_of",
            "evidence_nature",
            "truth_relevance",
            "price_relevance",
            "mechanism",
            "horizon",
            "falsifier",
        ):
            self.assertRegex(self.council, rf"\| {TICK}{field}{TICK} \|")
        self.assertIn("Headlines and search snippets remain research leads", self.judgment)
        self.assertIn("Count the underlying event, document, dataset", self.judgment)

    def test_ambient_context_and_provider_fallback_are_explicit(self):
        council_phrases = (
            "ambient_market_context",
            "workflow and run identifier",
            "coverage universe and matched security/topic",
            "current matched security",
            "new, unmatched, stale, or absent receipt",
            "return the gap upstream",
            "Council does not launch collection",
            "accepted public-web route",
        )
        for phrase in council_phrases:
            self.assertIn(phrase, self.council)
        self.assertIn(
            "Council does not open a replacement route itself",
            re.sub(r"\s+", " ", self.judgment).replace(TICK, ""),
        )

    def test_evidence_truth_and_price_relevance_are_separate(self):
        normalized = re.sub(r"\s+", " ", self.judgment)
        for phrase in (
            "Established company fact",
            "Market-belief signal",
            "Supported inference",
            "Testable conjecture",
            "Unsupported narrative",
            "truth_relevance",
            "price_relevance",
            "may have high price relevance while having low truth relevance",
            "may not directly change revenue, cash flow, margins, or intrinsic value",
        ):
            self.assertIn(phrase, normalized)
        for phrase in (
            "causal mechanism",
            "evidence anchor and source receipt",
            "reference class",
            "probability range",
            "within-horizon financial, valuation, or price-path consequence",
            "falsifier or deletion condition",
        ):
            self.assertIn(phrase, normalized)

    def test_memo_and_cross_examination_form_a_real_discussion(self):
        normalized = re.sub(r"\s+", " ", self.council).replace(TICK, "")
        for phrase in (
            "Committee member",
            "Method completion",
            "Method-specific work product",
            "Central price path",
            "No differentiated view",
            "strongest opposing path",
            "up to three load-bearing observations",
            "marginal buyer, seller, or forced actor",
            "Accept",
            "Conditional",
            "Reject",
            "at most two material disputes",
            "Defend",
            "Revise",
            "Concede",
            "Do not vote or average",
            "without restarting open-ended discovery",
            "Close the evidence set",
            "may not browse, open a new source, cite a new origin, or introduce a new fact",
            "from the sealed first-round evidence",
            "recorded for a future research cycle and cannot affect the current distribution",
            "method-completion ledger naming Aswath Damodaran, George Soros, and Michael Mauboussin",
        ):
            self.assertIn(phrase, normalized)

    def test_unavailable_collaboration_does_not_impersonate_members(self):
        normalized = re.sub(r"\s+", " ", self.council.replace(TICK, ""))
        for phrase in (
            "do not run or impersonate the three method cards inside the Chair",
            "Mark Aswath Damodaran, George Soros, and Michael Mauboussin Unavailable",
            "Council runtime: unavailable",
            "no independent Council occurred",
            "only the accepted PEI inputs",
            "Robustness: Fragile",
            "may not browse, fabricate sealed memos, or claim a member contribution",
        ):
            self.assertIn(phrase, normalized)
        self.assertNotIn("Council runtime: single-model persona emulation", normalized)

    def test_canonical_dimensions_and_price_formation_precedence(self):
        normalized = self.judgment.replace(TICK, "")
        for phrase in (
            "Research stance",
            "Confidence",
            "Robustness",
            "Participation",
            "Implementation readiness",
            "Later dimensions never overwrite an earlier research stance",
            "Use 0% gross expected price return",
            "Fundamental convergence",
            "Expectations revision",
            "Reflexive path",
            "genuinely balanced requested-horizon distribution",
        ):
            self.assertIn(phrase, normalized)

    def test_trigger_fixtures_preserve_terminal_and_native_owner_routes(self):
        self.assertGreaterEqual(len(self.triggers["should_trigger"]), 7)
        self.assertGreaterEqual(len(self.triggers["should_not_trigger"]), 7)
        self.assertEqual(
            {case["expected_route"] for case in self.triggers["should_trigger"]},
            {"iysl-equity-council"},
        )
        negative_families = {
            case["family"] for case in self.triggers["should_not_trigger"]
        }
        self.assertTrue(
            {
                "evidence_collection",
                "valuation_build",
                "scenario_only",
                "implementation_only",
                "first_pass_judgment_without_pack",
            }
            <= negative_families
        )

    def test_behavior_matrix_is_nine_anonymous_mece_routes(self):
        cases = self.behavior["cases"]
        self.assertEqual(len(cases), 9)
        self.assertEqual(len({case["id"] for case in cases}), 9)
        self.assertTrue(all("匿名" in case["prompt"] for case in cases))
        self.assertEqual(
            {case["evidence_route"] for case in cases},
            {
                "sealed-pei-baseline",
                "correlated-provider-signals",
                "accepted-ambient-context",
                "accepted-public-web-upstream",
                "unsupported-popular-narrative",
                "sealed-implementation-inputs",
                "targeted-pei-refill",
                "common-batch-header",
            },
        )
        for case in cases:
            expected = case["expected"]
            expected_subagents = 0 if case["id"] == "cyclical-peak-earnings" else 3
            self.assertEqual(expected["max_subagents"], expected_subagents, case["id"])
            self.assertTrue(expected["required_validation"], case["id"])
            if expected_subagents == 3:
                self.assertTrue(
                    any(
                        "three isolated named public-method personas" in item
                        or "exactly-three-named-persona" in item
                        for item in expected["must_do"]
                    ),
                    case["id"],
                )
            else:
                self.assertIn(
                    "mark Aswath Damodaran George Soros and Michael Mauboussin Unavailable and record Council runtime unavailable",
                    expected["must_do"],
                )
            self.assertTrue(
                any(
                    "Stanley Druckenmiller public-method PM Chair" in item
                    for item in expected["must_do"]
                ),
                case["id"],
            )

    def test_numeric_behavior_distributions_match_declared_stances(self):
        for case in self.behavior["cases"][:6]:
            distribution = case["distribution"]
            probability = sum(state["probability"] for state in distribution["states"])
            self.assertTrue(math.isclose(probability, 1.0), case["id"])
            expected_price = sum(
                state["price"] * state["probability"]
                for state in distribution["states"]
            )
            delta = expected_price - distribution["current_price"]
            calculated = "Long" if delta > 1e-9 else "Short" if delta < -1e-9 else "Avoid"
            self.assertEqual(calculated, distribution["expected_stance"], case["id"])
            self.assertTrue(
                any(
                    f"issue {calculated}" in item
                    for item in case["expected"]["must_do"]
                ),
                case["id"],
            )

    def test_behavior_cases_cover_failure_controls(self):
        cases = {case["id"]: case for case in self.behavior["cases"]}
        rendered = json.dumps(self.behavior, ensure_ascii=False)
        for phrase in (
            "deduplicate the correlated provider signals by underlying origin",
            "reuse the current matched ambient receipt",
            "upstream accepted public-web evidence",
            "exclude the unsupported popular narrative",
            "set implementation readiness to Blocked",
            "at most one targeted Public Equity Investing refill",
            "preserve Long Short and Avoid differentiation",
            "give all seats the common factual spine and distinct private evidence partitions",
            "give every seat the full PEI narrative",
            "use one common factual spine plus three method-specific private partitions",
            "claim repeated persona mechanisms are independent confirmation",
            "claim fraud or misconduct",
            "average the council opinions",
        ):
            self.assertIn(phrase, rendered)
        bearish = cases["bearish-missing-borrow"]
        self.assertEqual(bearish["distribution"]["expected_stance"], "Short")
        self.assertIn("來源獨立性低", bearish["prompt"])
        self.assertIn("合理模型範圍跨過 0%", bearish["prompt"])
        self.assertEqual(
            bearish["expected"]["must_do"][:4],
            [
                "issue Short",
                "set confidence to Low and robustness to Fragile",
                "set participation to Stand aside",
                "set implementation readiness to Blocked",
            ],
        )
        rendered_validations = " ".join(
            validation
            for case in cases.values()
            for validation in case["expected"]["required_validation"]
        )
        for phrase in (
            "Aswath Damodaran memo includes an archetype-appropriate reverse valuation",
            "George Soros memo includes current trend bias evidenced marginal actors full feedback chain phase and reversal trigger",
            "Michael Mauboussin memo defines reference-class criteria",
            "public options price volume positioning and liquidity evidence remain available to George Soros",
            "Chair method-completion ledger names Aswath Damodaran George Soros and Michael Mauboussin",
            "detect persona_convergence and allow at most one same-evidence corrective pass before Chair synthesis",
            "each seat states a distinct causal mechanism disconfirming condition key metric and source posture",
            "Stanley Druckenmiller PM Chair names expectations revision as the dominant variable",
            "Stanley Druckenmiller PM Chair issues Avoid from the balanced state matrix rather than member disagreement",
            "Stanley Druckenmiller PM Chair does not infer sizing concentration orders execution or a simulated personal position",
            "every Chair state target resolves through weighted components to named method artifact proposition IDs and accepted evidence",
            "Mauboussin base-rate prior plus signed state-mapped updates reconciles to posterior and success-state probability",
            "Chair seat decisions bind each proposition ID to the matching named method artifact",
        ):
            self.assertIn(phrase, rendered_validations)

    def test_metadata_is_implicit_and_consistent(self):
        for surface in (self.openai, self.interface):
            self.assertIn('display_name: "iysl-equity-council"', surface)
            self.assertIn("$iysl-equity-council", surface)
            for name in (
                "Aswath Damodaran",
                "George Soros",
                "Michael Mauboussin",
                "Stanley Druckenmiller",
            ):
                self.assertIn(name, surface)
            self.assertIn("public-method personas", surface)
        self.assertIn("allow_implicit_invocation: true", self.openai)
        self.assertIn('mode: "implicit"', self.interface)
        self.assertEqual(
            {path.name for path in (ROOT / "scripts").glob("*.py")},
            {"validate_council_run.py"},
        )


if __name__ == "__main__":
    unittest.main()
