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

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_minimum_gate_and_native_owner_boundary(self):
        normalized = re.sub(r"\s+", " ", self.skill).replace(TICK, "")
        for phrase in (
            "valid security identity",
            "current price with as-of timestamp",
            "explicit decision horizon",
            "minimally usable Public Equity Investing",
            "Never fan out across every constituent skill",
            "Do not invoke equity-data directly",
            "formal provider coverage",
            "do not create a competing coverage artifact",
            "requires Public Equity Investing verification",
            "the only targeted Public Equity Investing refill",
            "Do not start a second refill",
            "intake failure, not Avoid",
        ):
            self.assertIn(phrase, normalized)

    def test_targeted_refill_ranks_overflow_and_has_one_terminal_disposition(self):
        skill = re.sub(r"\s+", " ", self.skill)
        judgment = re.sub(r"\s+", " ", self.judgment)
        for phrase in (
            "Rank all newly discovered model- or sign-changing company facts",
            "Select at most two",
            "the only targeted Public Equity Investing refill",
            "All remaining facts stay unverified research leads",
            "may not enter established inputs",
            "Do not start a second refill",
        ):
            self.assertIn(phrase, skill)
        for phrase in (
            "selects it among the at-most-two facts",
            "single targeted PEI refill",
            "Every unselected or unaccepted fact remains an unverified research lead",
            "may not change a model input or start another refill",
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

    def test_three_agents_are_isolated_but_can_browse(self):
        normalized = re.sub(r"\s+", " ", self.council)
        for phrase in (
            "Spawn exactly three parallel leaf agents",
            "the same security identity, current price/as-of, decision horizon",
            "one exact committee-member name and its distinct method card",
            "named method-specific work product and freshness receipt",
            "browse accessible external sources",
            "no Chair conclusion, other member memo, upstream disposition",
            "prohibition on further delegation",
            "First-round memos remain sealed",
            "independent work paths, not independent proof",
        ):
            self.assertIn(phrase, normalized)
        self.assertNotIn("authority to reason from the pack but not to search", normalized)

    def test_market_refresh_and_options_evidence_are_not_sealed_from_soros(self):
        council = re.sub(r"\s+", " ", self.council)
        skill = re.sub(r"\s+", " ", self.skill)
        judgment = re.sub(r"\s+", " ", self.judgment)
        for phrase in (
            "Use a current market refresh for the requested horizon",
            "options, short-interest, positioning, or liquidity",
            "provider freshness receipt",
            "live_refreshed",
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

    def test_exploration_is_broad_and_adoption_is_strict(self):
        normalized = re.sub(r"\s+", " ", self.council)
        self.assertIn("Exploration is broad; adoption is strict", normalized)
        self.assertIn("Do not prescribe a fixed domain list", normalized)
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
        self.assertIn("Headlines and search snippets are discovery aids", self.judgment)
        self.assertIn("Count the underlying event, document, dataset", self.judgment)

    def test_ambient_context_and_provider_fallback_are_explicit(self):
        council_phrases = (
            "ambient_market_context",
            "workflow and run identifier",
            "coverage universe and matched security/topic",
            "current matched security",
            "new or unmatched security",
            "Stale receipts are historical context",
            "Receipt absence never prevents fresh research",
            "SA route unavailable; public-web-only",
        )
        for phrase in council_phrases:
            self.assertIn(phrase, self.council)
        self.assertIn("public-web-only route is valid if disclosed", self.judgment)

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
                "mixed-baseline-and-external",
                "fresh-discovery",
                "correlated-provider-signals",
                "accepted-ambient-context",
                "public-web-only",
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
            "public-web-only research",
            "exclude the unsupported popular narrative",
            "set implementation readiness to Blocked",
            "at most one targeted Public Equity Investing refill",
            "preserve Long Short and Avoid differentiation",
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
            "Stanley Druckenmiller PM Chair names expectations revision as the dominant variable",
            "Stanley Druckenmiller PM Chair issues Avoid from the balanced state matrix rather than member disagreement",
            "Stanley Druckenmiller PM Chair does not infer sizing concentration orders execution or a simulated personal position",
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
        self.assertFalse((ROOT / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
