import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_council_run.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_module("validate_council_run", VALIDATOR_PATH)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_chain(tmp_path):
    plugin_root = tmp_path / "plugin"
    artifact_dir = tmp_path / "artifact"
    plugin_root.mkdir(exist_ok=True)
    (artifact_dir / "support").mkdir(parents=True, exist_ok=True)
    pei_path = artifact_dir / "support" / "pei_input_receipt.json"
    ambient_claim_id = "STUDY_FLOW:claim:ambient"
    pei_receipt = {
        "schema_version": 2,
        "ticker": "EXAMPLE",
        "security_identity": {
            "symbol": "EXAMPLE",
            "issuer": "Example Corporation",
            "listing": "NASDAQ",
            "security_id": "SEC-CIK-0000001",
        },
        "evidence_cutoff": "2026-08-22T10:00:00+08:00",
        "output_posture": "PASS",
        "owner_declaration": {"declared_receipt_kinds": []},
        "subordinate_receipts": [],
        "evidence_registry": [
            {
                "id": "SA:market:2026-08-22",
                "requirement_class": "provider",
                "source_kind": "seeking_alpha",
            },
            {
                "id": "IR:earnings-release:2026Q2",
                "requirement_class": "primary",
                "source_kind": "primary",
            },
            {
                "id": ambient_claim_id,
                "requirement_class": "ambient_context",
                "source_kind": "study_flow",
            },
        ],
        "requirements": [
            {
                "id": "market_and_estimates",
                "requirement_class": "provider",
                "criticality": "hard",
                "status": "satisfied",
                "evidence_ids": ["SA:market:2026-08-22"],
                "gap_reason": None,
            },
            {
                "id": "reported_financials",
                "requirement_class": "primary",
                "criticality": "hard",
                "status": "satisfied",
                "evidence_ids": ["IR:earnings-release:2026Q2"],
                "gap_reason": None,
            },
            {
                "id": "ambient_market_context",
                "requirement_class": "ambient_context",
                "criticality": "soft",
                "status": "satisfied",
                "evidence_ids": [ambient_claim_id],
                "gap_reason": None,
            },
        ],
    }
    _write_json(pei_path, pei_receipt)
    pei_errors, pei_posture = VALIDATOR._validate_pei_admission_receipt(pei_receipt)
    assert pei_errors == []
    assert pei_posture == "PASS"
    return plugin_root, artifact_dir, pei_path, pei_receipt


def test_pei_admission_accepts_current_schema_v3(tmp_path):
    _, _, _, pei_receipt = _build_chain(tmp_path)
    pei_receipt["schema_version"] = 3
    errors, posture = VALIDATOR._validate_pei_admission_receipt(pei_receipt)
    assert errors == []
    assert posture == "PASS"


def test_pei_admission_accepts_split_cutoff_schema_v4(tmp_path):
    _, _, _, pei_receipt = _build_chain(tmp_path)
    pei_receipt["schema_version"] = 4
    pei_receipt["owner_model_evidence_cutoff"] = "2026-08-22T11:00:00+00:00"
    pei_receipt["final_research_evidence_cutoff"] = pei_receipt["evidence_cutoff"]
    errors, posture = VALIDATOR._validate_pei_admission_receipt(pei_receipt)
    assert errors == []
    assert posture == "PASS"


def _damodaran_artifact(evidence_id):
    return {
        "artifact_type": "damodaran_reverse_valuation_v1",
        "requested_horizon": "12 months",
        "proposition_id": "damodaran:price_implied_growth_gap",
        "company_archetype": "high_growth",
        "archetype_rationale": "Growth duration and reinvestment efficiency dominate value.",
        "valuation_frame": "reverse_dcf",
        "anchor_price": 100.0,
        "currency": "USD",
        "price_implied_drivers": [
            {"id": "revenue_cagr", "value": 28.0, "unit": "percent", "evidence_ids": [evidence_id]},
            {"id": "target_operating_margin", "value": 24.0, "unit": "percent", "evidence_ids": [evidence_id]},
            {"id": "sales_to_capital", "value": 1.8, "unit": "ratio", "evidence_ids": [evidence_id]},
        ],
        "owner_case_drivers": [
            {"id": "revenue_cagr", "value": 20.0, "unit": "percent", "evidence_ids": [evidence_id]},
            {"id": "target_operating_margin", "value": 20.0, "unit": "percent", "evidence_ids": [evidence_id]},
            {"id": "sales_to_capital", "value": 1.4, "unit": "ratio", "evidence_ids": [evidence_id]},
        ],
        "story_to_numbers_bridge": [
            {
                "driver_id": "revenue_cagr",
                "story": "Category adoption must remain unusually fast.",
                "implied_value": 28.0,
                "owner_value": 20.0,
                "unit": "percent",
                "directional_effect": "downside",
                "evidence_ids": [evidence_id],
                "falsifier": "Two years of growth above 28 percent with stable retention.",
            },
            {
                "driver_id": "target_operating_margin",
                "story": "Scale must produce mature software-like margins.",
                "implied_value": 24.0,
                "owner_value": 20.0,
                "unit": "percent",
                "directional_effect": "downside",
                "evidence_ids": [evidence_id],
                "falsifier": "Incremental margin exceeds 35 percent for four quarters.",
            },
            {
                "driver_id": "sales_to_capital",
                "story": "Growth must require less capital than recent history.",
                "implied_value": 1.8,
                "owner_value": 1.4,
                "unit": "ratio",
                "directional_effect": "downside",
                "evidence_ids": [evidence_id],
                "falsifier": "Sales-to-capital stays above 1.8 through the next investment cycle.",
            },
        ],
        "fundamental_value_range": {"low": 75.0, "base": 115.0, "high": 155.0, "currency": "USD", "evidence_ids": [evidence_id]},
        "least_plausible_implied_driver": "revenue_cagr",
        "requested_horizon_transmission": "Estimate revisions transmit the growth gap into the 12-month multiple.",
        "method_gap": None,
    }


def _soros_artifact(evidence_id):
    return {
        "artifact_type": "soros_reflexivity_chain_v1",
        "requested_horizon": "12 months",
        "proposition_id": "soros:revision_feedback_loop",
        "classification": "reflexive",
        "current_trend": {"direction": "up", "observation": "Price and volume rise after estimate revisions.", "evidence_ids": [evidence_id]},
        "prevailing_bias": {"belief": "Growth acceleration improves access to financing.", "reality_gap": "Cash conversion still lags the narrative.", "evidence_ids": [evidence_id]},
        "marginal_actors": [
            {"actor": "momentum buyers", "incentive": "follow positive revisions", "expected_action": "add on price confirmation", "evidence_ids": [evidence_id]}
        ],
        "feedback_chain": [
            {"step": "trend_to_bias", "claim": "Price strength reinforces the acceleration belief.", "evidence_ids": [evidence_id]},
            {"step": "bias_to_actor_action", "claim": "The belief attracts marginal momentum demand.", "evidence_ids": [evidence_id]},
            {"step": "actor_action_to_price", "claim": "Incremental demand lifts price and volume.", "evidence_ids": [evidence_id]},
            {"step": "price_to_fundamentals", "claim": "A higher price lowers equity-financing friction.", "evidence_ids": [evidence_id]},
            {"step": "fundamentals_to_bias", "claim": "Financing access extends the growth narrative.", "evidence_ids": [evidence_id]},
        ],
        "phase": "accelerating",
        "phase_rationale": "Positive revisions and price response still reinforce each other.",
        "reversal_trigger": {"metric": "revision breadth", "operator": "<", "threshold": 0.0, "unit": "percent", "observation_window": "two consecutive months", "evidence_ids": [evidence_id]},
        "horizon_price_paths": [
            {"state_id": "reinforcing", "scenario_role": "upside", "condition": "Revisions stay positive", "probability_pct": 40.0, "gross_return_pct": 30.0, "mechanism": "Marginal demand and financing reinforce growth.", "evidence_ids": [evidence_id]},
            {"state_id": "stall", "scenario_role": "base", "condition": "Revisions flatten", "probability_pct": 35.0, "gross_return_pct": 0.0, "mechanism": "The loop loses fuel without reversing.", "evidence_ids": [evidence_id]},
            {"state_id": "reversal", "scenario_role": "downside", "condition": "Revisions turn negative", "probability_pct": 25.0, "gross_return_pct": -25.0, "mechanism": "Marginal buyers leave and financing feedback reverses.", "evidence_ids": [evidence_id]},
        ],
        "expected_path_return_pct": 5.75,
        "non_reflexive_tests": [],
        "method_gap": None,
    }


def _mauboussin_artifact(evidence_id):
    return {
        "artifact_type": "mauboussin_expectations_distribution_v1",
        "requested_horizon": "12 months",
        "proposition_id": "mauboussin:positive_expectations_distribution",
        "anchor_price": 100.0,
        "currency": "USD",
        "price_implied_expectations": [
            {"metric": "revenue_cagr", "implied_value": 28.0, "unit": "percent", "evidence_ids": [evidence_id], "disconfirming_observation": "Consensus growth falls below 20 percent."}
        ],
        "reference_class": {
            "status": "available",
            "definition": "Listed high-growth firms entering margin scale-up.",
            "inclusion_criteria": ["revenue growth above 20 percent", "positive gross margin", "public history above eight quarters"],
            "exclusion_criteria": ["distressed financing within twelve months"],
            "sample_size": 32,
            "base_rate_label": "sustained scale-up success",
            "base_rate_pct": 68.0,
            "evidence_ids": [evidence_id],
            "gap_reason": None,
        },
        "inside_view_updates": [
            {"signal": "Revision breadth is positive.", "direction": "increase", "probability_delta_pct": 7.0, "affected_state_ids": ["base", "upside"], "rationale": "Current evidence is better than the reference-class median.", "evidence_ids": [evidence_id]}
        ],
        "probability_payoff_states": [
            {"state_id": "downside", "scenario_role": "downside", "definition": "Growth fades", "probability_pct": 25.0, "target_price": 70.0, "gross_return_pct": -30.0, "evidence_ids": [evidence_id]},
            {"state_id": "base", "scenario_role": "base", "definition": "Orderly scale-up", "probability_pct": 50.0, "target_price": 115.0, "gross_return_pct": 15.0, "evidence_ids": [evidence_id]},
            {"state_id": "upside", "scenario_role": "upside", "definition": "Growth and margins exceed implied path", "probability_pct": 25.0, "target_price": 160.0, "gross_return_pct": 60.0, "evidence_ids": [evidence_id]},
        ],
        "posterior_mode": "base_rate_update",
        "posterior_success_probability_pct": 75.0,
        "success_state_ids": ["base", "upside"],
        "expected_return_pct": 15.0,
        "sign_sensitivity": [
            {"variable": "revenue_cagr", "low_input": 15.0, "base_input": 20.0, "high_input": 28.0, "unit": "percent", "low_expected_return_pct": -8.0, "high_expected_return_pct": 24.0, "sign_flips": True}
        ],
        "method_gap": None,
    }


def _method_artifact(seat, evidence_id):
    return {
        "damodaran": _damodaran_artifact,
        "soros": _soros_artifact,
        "mauboussin": _mauboussin_artifact,
    }[seat](evidence_id)


def _seat_memo(
    seat,
    *,
    mechanism,
    mechanism_tag,
    mechanism_tags,
    condition,
    metric,
    source_posture,
    evidence_id,
):
    return {
        "seat": seat,
        "method_completion": "Complete",
        "work_product": f"Completed {seat} method-specific work product",
        "method_artifact": _method_artifact(seat, evidence_id),
        "sealed_at": "2026-08-22T10:20:00+08:00",
        "browsed": False,
        "added_evidence_ids": [],
        "accepted_evidence_ids": [evidence_id],
        "research_lead_ids": [],
        "contribution": {
            "causal_mechanism": mechanism,
            "primary_mechanism_tag": mechanism_tag,
            "mechanism_tags": mechanism_tags,
            "disconfirming_condition": condition,
            "key_metric": metric,
            "source_posture": source_posture,
        },
        "provisional_direction": "Long",
    }


def _chair_matrix(sa_market_source_id):
    return {
        "artifact_type": "dominant_variable_state_matrix_v1",
        "requested_horizon": "12 months",
        "dominant_variable": "Revenue estimate revision breadth",
        "dominant_variable_unit": "percent",
        "dominance_rationale": "It changes both expected cash flows and the marginal buyer within the horizon.",
        "transition": {"from": "positive revisions", "to": "sustained breadth or reversal", "mechanism": "Revision breadth changes expectations and price-sensitive flows.", "timing": "monthly observations over 12 months"},
        "states": [
            {
                "state_id": "revision_down",
                "scenario_role": "downside",
                "definition": "Revision breadth is materially negative.",
                "dominant_variable_interval": {"lower": None, "lower_inclusive": False, "upper": -5.0, "upper_inclusive": False},
                "probability_pct": 25.0,
                "target_price": 70.0,
                "gross_return_pct": -30.0,
                "decisive_mechanism": "Negative revisions remove marginal demand.",
                "seat_inputs": ["mauboussin"],
                "target_components": [{"seat": "mauboussin", "proposition_id": "mauboussin:positive_expectations_distribution", "source_kind": "probability_payoff_target", "source_id": "downside", "weight_pct": 100.0}],
                "probability_components": [{"seat": "mauboussin", "proposition_id": "mauboussin:positive_expectations_distribution", "source_kind": "probability_payoff_probability", "source_id": "downside", "weight_pct": 100.0, "scenario_probability_basis": "Mauboussin payoff-state probability anchored to the accepted reference class and inside-view update."}],
                "evidence_ids": [sa_market_source_id],
            },
            {
                "state_id": "revision_flat",
                "scenario_role": "base",
                "definition": "Revision breadth remains near zero.",
                "dominant_variable_interval": {"lower": -5.0, "lower_inclusive": True, "upper": 5.0, "upper_inclusive": True},
                "probability_pct": 35.0,
                "target_price": 100.0,
                "gross_return_pct": 0.0,
                "decisive_mechanism": "Fundamental value anchors price as expectations stop changing.",
                "seat_inputs": ["soros"],
                "target_components": [{"seat": "soros", "proposition_id": "soros:revision_feedback_loop", "source_kind": "horizon_path_return", "source_id": "stall", "weight_pct": 100.0}],
                "probability_components": [{"seat": "soros", "proposition_id": "soros:revision_feedback_loop", "source_kind": "horizon_path_probability", "source_id": "stall", "weight_pct": 100.0, "scenario_probability_basis": "Soros path probability is conditional on the sealed revision-feedback regime."}],
                "evidence_ids": [sa_market_source_id],
            },
            {
                "state_id": "revision_up",
                "scenario_role": "upside",
                "definition": "Revision breadth stays materially positive.",
                "dominant_variable_interval": {"lower": 5.0, "lower_inclusive": False, "upper": None, "upper_inclusive": False},
                "probability_pct": 40.0,
                "target_price": 155.0,
                "gross_return_pct": 55.0,
                "decisive_mechanism": "Upward revisions and marginal demand reinforce the growth path.",
                "seat_inputs": ["damodaran", "soros"],
                "target_components": [{"seat": "damodaran", "proposition_id": "damodaran:price_implied_growth_gap", "source_kind": "fundamental_value_high", "source_id": None, "weight_pct": 100.0}],
                "probability_components": [{"seat": "soros", "proposition_id": "soros:revision_feedback_loop", "source_kind": "horizon_path_probability", "source_id": "reinforcing", "weight_pct": 100.0, "scenario_probability_basis": "Soros path probability is conditional on the sealed revision-feedback regime."}],
                "evidence_ids": ["IR:earnings-release:2026Q2", sa_market_source_id],
            },
        ],
        "gross_expected_return_pct": 14.5,
        "strongest_disconfirming_state_id": "revision_down",
        "reversal_triggers": [
            {"observable": "Revision breadth is at or below negative five percent for two months.", "metric": "Revenue estimate revision breadth", "operator": "<=", "threshold": -5.0, "unit": "percent", "observation_window": "two consecutive months", "resulting_stance": "Short", "evidence_ids": [sa_market_source_id]}
        ],
    }


def _council_payload(pei_path, pei_receipt):
    ambient_claim_id = next(
        entry["id"]
        for entry in pei_receipt["evidence_registry"]
        if entry["source_kind"] == "study_flow"
    )
    sa_market_source_id = next(
        entry["id"]
        for entry in pei_receipt["evidence_registry"]
        if entry["source_kind"] == "seeking_alpha"
    )
    return {
        "schema_version": 2,
        "council_runtime": "collaboration_available",
        "ticker": "EXAMPLE",
        "security_identity": {
            "symbol": "EXAMPLE",
            "issuer": "Example Corporation",
            "listing": "NASDAQ",
            "security_id": "SEC-CIK-0000001",
            "source_id": "SEC:company_tickers:0000001",
        },
        "current_price": {
            "value": 100.0,
            "currency": "USD",
            "as_of": "2026-08-22T09:00:00+08:00",
            "source_id": sa_market_source_id,
        },
        "decision_horizon": "12 months",
        "evidence_cutoff": pei_receipt["evidence_cutoff"],
        "pei_input_receipt": {
            "artifact": "support/pei_input_receipt.json",
            "sha256": _sha256(pei_path),
            "declared_posture": pei_receipt["output_posture"],
        },
        "research_admission": "ADMITTED",
        "sealed_inputs": {
            "upstream_verdict": True,
            "full_pei_narrative": True,
            "participation": True,
            "implementation_readiness": True,
            "other_seat_outputs": True,
        },
        "common_factual_spine": {
            "fields": [
                {
                    "id": "current_price",
                    "field_class": "market_fact",
                    "value": 100.0,
                    "unit": "USD_per_share",
                    "as_of": "2026-08-22T09:00:00+08:00",
                    "evidence_ids": [sa_market_source_id],
                },
                {
                    "id": "latest_revenue",
                    "field_class": "company_fact",
                    "value": 1000000.0,
                    "unit": "USD",
                    "as_of": "2026-08-21T16:00:00+08:00",
                    "evidence_ids": ["IR:earnings-release:2026Q2"],
                },
            ]
        },
        "private_partitions": {
            "damodaran": {
                "allowed_domains": [
                    "fundamentals",
                    "reverse_valuation",
                    "capital_structure",
                ],
                "evidence_ids": ["IR:earnings-release:2026Q2"],
            },
            "soros": {
                "allowed_domains": [
                    "price_path",
                    "marginal_actors",
                    "positioning_reflexivity",
                ],
                "evidence_ids": [
                    sa_market_source_id,
                    ambient_claim_id,
                ],
            },
            "mauboussin": {
                "allowed_domains": [
                    "expectations_revisions",
                    "reference_class",
                    "probability_payoff",
                ],
                "evidence_ids": [sa_market_source_id],
            },
        },
        "first_round": {
            "unavailable_seats": [],
            "memos": [
                _seat_memo(
                    "damodaran",
                    mechanism="Reinvestment returns determine value convergence.",
                    mechanism_tag="fundamental_reinvestment",
                    mechanism_tags=["fundamental_reinvestment"],
                    condition="Returns on capital fall below the cost of capital.",
                    metric="Incremental return on invested capital",
                    source_posture="Primary filings plus accepted owner model inputs",
                    evidence_id="IR:earnings-release:2026Q2",
                ),
                _seat_memo(
                    "soros",
                    mechanism="Marginal buyers reinforce price through financing feedback.",
                    mechanism_tag="financing_feedback",
                    mechanism_tags=["marginal_actor_flow", "financing_feedback"],
                    condition="Price strength no longer improves financing access.",
                    metric="Price-volume response around catalyst dates",
                    source_posture="Current market tape and resolved ambient research leads",
                    evidence_id=sa_market_source_id,
                ),
                _seat_memo(
                    "mauboussin",
                    mechanism="Estimate revisions shift the probability-payoff distribution.",
                    mechanism_tag="estimate_revisions",
                    mechanism_tags=["estimate_revisions", "probability_asymmetry"],
                    condition="Revision breadth turns negative versus the reference class.",
                    metric="Revenue estimate revision breadth",
                    source_posture="Timestamped consensus plus explicit base-rate limits",
                    evidence_id=sa_market_source_id,
                ),
            ]
        },
        "convergence": {
            "first_pass_status": "distinct",
            "implicated_seats": [],
            "semantic_review": {
                "reviewed": True,
                "first_overlap_detected": False,
                "final_overlap_detected": False,
                "rationale": "Canonical mechanism tags and the four contribution fields are distinct.",
            },
            "corrective_pass_count": 0,
            "corrective_memos": [],
            "final_status": "distinct",
        },
        "chair": {
            "name": "Stanley Druckenmiller — PM Chair",
            "public_method_persona": True,
            "started_at": "2026-08-22T10:30:00+08:00",
            "finalized_at": "2026-08-22T10:40:00+08:00",
            "evidence_closed": True,
            "browsed": False,
            "added_evidence_ids": [],
            "used_evidence_ids": [
                sa_market_source_id,
                "IR:earnings-release:2026Q2",
            ],
            "seat_decisions": [
                {"seat": "damodaran", "decision": "Accept", "proposition_id": "damodaran:price_implied_growth_gap", "proposition": "The owner case is below the price-implied growth path.", "reason": "The numerical bridge is supported by accepted model inputs.", "retained_limitation": "Fundamental convergence can be mistimed within the requested horizon.", "impact": {"stance": "Supports the Long stance only if revisions keep the convergence path open.", "participation_effect": "Does not establish execution suitability.", "refresh_route": "Refresh PEI if the price-implied driver gap closes."}},
                {"seat": "soros", "decision": "Conditional", "proposition_id": "soros:revision_feedback_loop", "proposition": "Positive revisions sustain a financing feedback loop.", "reason": "The loop reverses if revision breadth turns negative.", "retained_limitation": "Marginal-actor evidence can reverse before fundamentals change.", "impact": {"stance": "Limits the Long stance when the feedback loop breaks.", "participation_effect": "Requires current implementation checks outside Council.", "refresh_route": "Request a PEI refresh when the reversal trigger is observed."}},
                {"seat": "mauboussin", "decision": "Accept", "proposition_id": "mauboussin:positive_expectations_distribution", "proposition": "The probability-payoff distribution remains positive.", "reason": "The reference class and inside-view update support positive expected return.", "retained_limitation": "The reference class may not capture the next regime change.", "impact": {"stance": "Supports the Long stance while expectation revisions remain positive.", "participation_effect": "Does not override liquidity or execution constraints.", "refresh_route": "Refresh PEI if the reference-class fit or revision inputs change."}},
            ],
            "dominant_variable": "Revenue estimate revision breadth",
            "strongest_disconfirming_path": "Returns fade while revisions reverse.",
            "reversal_trigger": "Revision breadth is at or below negative five percent for two months.",
            "decision_matrix": _chair_matrix(sa_market_source_id),
            "gross_expected_return_pct": 14.5,
            "research_stance": "Long",
            "confidence": "Medium",
            "robustness": "Conditional",
            "participation": "Conditional",
            "implementation_readiness": "Conditional",
            "implementation_blockers": ["Executable liquidity not yet refreshed"],
            "independent_confirmation": False,
        },
    }


def _fixture(tmp_path):
    plugin_root, artifact_dir, pei_path, pei_receipt = _build_chain(tmp_path)
    council = _council_payload(pei_path, pei_receipt)
    council_path = artifact_dir / "support" / "council_run.json"
    _write_json(council_path, council)
    return plugin_root, artifact_dir, council_path, council, pei_path, pei_receipt


def _descriptor(path, artifact_dir):
    return {
        "path": path.relative_to(artifact_dir).as_posix(),
        "sha256": _sha256(path),
    }


def _bind_current_authority(council, artifact_dir):
    support = artifact_dir / "support" / "current-council"
    identity = {
        "ticker": council["ticker"],
        "security_id": council["security_identity"]["security_id"],
        "evidence_cutoff": council["evidence_cutoff"],
    }
    underwrite = {
        "schema_version": "pei-preliminary-underwrite-v1",
        **identity,
        "candidate_assumptions": [
            {"id": "revenue_growth", "base": 20.0, "reasonable_range": [10.0, 30.0]}
        ],
    }
    underwrite_path = support / "preliminary_underwrite.json"
    _write_json(underwrite_path, underwrite)

    packet_refs = {}
    memo_refs = {}
    for seat in sorted(VALIDATOR.SEATS):
        packet = {
            "schema_version": "council-premodel-seat-packet-v1",
            **identity,
            "seat": seat,
            "candidate_assumptions": underwrite["candidate_assumptions"],
            "private_partition": council["private_partitions"][seat],
        }
        packet_path = support / "packets" / f"{seat}.json"
        _write_json(packet_path, packet)
        packet_refs[seat] = _descriptor(packet_path, artifact_dir)

        memo = {
            "schema_version": "council-sealed-memo-v1",
            "seat": seat,
            "packet_sha256": packet_refs[seat]["sha256"],
            "memo": next(
                item for item in council["first_round"]["memos"] if item["seat"] == seat
            ),
        }
        memo_path = support / "memos" / f"{seat}.json"
        _write_json(memo_path, memo)
        memo_refs[seat] = _descriptor(memo_path, artifact_dir)

    final_spec = {
        "schema_version": "owner-model-spec-v1",
        "identity": identity,
        "evidence_cutoff": council["evidence_cutoff"],
        "owner": "PEI owner",
        "formula_version": "test-formula-v1",
    }
    final_spec_path = support / "final_model_spec.json"
    _write_json(final_spec_path, final_spec)
    final_spec_ref = _descriptor(final_spec_path, artifact_dir)

    adjudication = {
        "schema_version": "pei-council-adjudication-v1",
        **identity,
        "adjudicated_at": "2026-08-22T10:23:00+08:00",
        "packet_hashes": {seat: packet_refs[seat]["sha256"] for seat in sorted(VALIDATOR.SEATS)},
        "memo_hashes": {seat: memo_refs[seat]["sha256"] for seat in sorted(VALIDATOR.SEATS)},
        "final_model_spec_sha256": final_spec_ref["sha256"],
    }
    adjudication_path = support / "owner_adjudication.json"
    _write_json(adjudication_path, adjudication)

    freeze = {
        "schema_version": "owner-fv-freeze-v1",
        **identity,
        "frozen_at": "2026-08-22T10:28:00+08:00",
        "model_spec_sha256": final_spec_ref["sha256"],
        "model_output_sha256": "1" * 64,
        "independent_audit_sha256": "2" * 64,
    }
    freeze_path = support / "fv_freeze_receipt.json"
    _write_json(freeze_path, freeze)
    freeze_ref = _descriptor(freeze_path, artifact_dir)

    chair = {
        "schema_version": "council-pm-chair-receipt-v1",
        **identity,
        "model_spec_sha256": final_spec_ref["sha256"],
        "fv_freeze_receipt_sha256": freeze_ref["sha256"],
        "chair": council["chair"],
    }
    chair_path = support / "pm_chair.json"
    _write_json(chair_path, chair)

    council["artifact_bindings"] = {
        "authority_version": 1,
        "validator_sha256": _sha256(VALIDATOR_PATH),
        "preliminary_underwrite": _descriptor(underwrite_path, artifact_dir),
        "seat_packets": packet_refs,
        "sealed_memos": memo_refs,
        "owner_adjudication": _descriptor(adjudication_path, artifact_dir),
        "final_model_spec": final_spec_ref,
        "model_committed_at": "2026-08-22T10:25:00+08:00",
        "fv_freeze_receipt": freeze_ref,
        "pm_chair": _descriptor(chair_path, artifact_dir),
    }
    return council["artifact_bindings"]


def _validate(council, plugin_root, artifact_dir):
    return VALIDATOR.validate(
        council, plugin_root=plugin_root, artifact_dir=artifact_dir
    )


def test_full_receipt_chain_admits_council_and_validates_final_judgment(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []


def test_current_authority_reopens_one_hash_bound_council_root(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    _bind_current_authority(council, artifact_dir)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_current_authority_allows_an_earlier_owner_model_cutoff(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    bindings = _bind_current_authority(council, artifact_dir)
    spec_path = artifact_dir / bindings["final_model_spec"]["path"]
    spec = json.loads(spec_path.read_text())
    spec["identity"]["evidence_cutoff"] = "2026-08-22T09:00:00+08:00"
    spec["evidence_cutoff"] = spec["identity"]["evidence_cutoff"]
    _write_json(spec_path, spec)
    bindings["final_model_spec"]["sha256"] = _sha256(spec_path)
    adjudication_path = artifact_dir / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication["final_model_spec_sha256"] = bindings["final_model_spec"]["sha256"]
    _write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"]["sha256"] = _sha256(adjudication_path)
    freeze_path = artifact_dir / bindings["fv_freeze_receipt"]["path"]
    freeze = json.loads(freeze_path.read_text())
    freeze["model_spec_sha256"] = bindings["final_model_spec"]["sha256"]
    _write_json(freeze_path, freeze)
    bindings["fv_freeze_receipt"]["sha256"] = _sha256(freeze_path)
    chair_path = artifact_dir / bindings["pm_chair"]["path"]
    chair = json.loads(chair_path.read_text())
    chair["model_spec_sha256"] = bindings["final_model_spec"]["sha256"]
    chair["fv_freeze_receipt_sha256"] = bindings["fv_freeze_receipt"]["sha256"]
    _write_json(chair_path, chair)
    bindings["pm_chair"]["sha256"] = _sha256(chair_path)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_current_authority_rejects_packet_hash_drift(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    bindings = _bind_current_authority(council, artifact_dir)
    packet_path = artifact_dir / bindings["seat_packets"]["damodaran"]["path"]
    packet = json.loads(packet_path.read_text())
    packet["candidate_assumptions"][0]["base"] = 99.0
    _write_json(packet_path, packet)

    errors = _validate(council, plugin_root, artifact_dir)

    assert "artifact_bindings.seat_packets.damodaran.sha256 does not match artifact" in errors


def test_current_authority_rejects_final_value_leaked_into_premodel_packet(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    bindings = _bind_current_authority(council, artifact_dir)
    packet_path = artifact_dir / bindings["seat_packets"]["damodaran"]["path"]
    packet = json.loads(packet_path.read_text())
    packet["owner_fair_value"] = 160.0
    _write_json(packet_path, packet)
    bindings["seat_packets"]["damodaran"]["sha256"] = _sha256(packet_path)

    errors = _validate(council, plugin_root, artifact_dir)

    assert "damodaran packet has unexpected fields: owner_fair_value" in errors


def test_current_authority_rejects_memo_content_drift_even_when_rehashed(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    bindings = _bind_current_authority(council, artifact_dir)
    memo_path = artifact_dir / bindings["sealed_memos"]["soros"]["path"]
    memo = json.loads(memo_path.read_text())
    memo["memo"]["work_product"] = "Changed after sealing"
    _write_json(memo_path, memo)
    bindings["sealed_memos"]["soros"]["sha256"] = _sha256(memo_path)
    adjudication_path = artifact_dir / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication["memo_hashes"]["soros"] = bindings["sealed_memos"]["soros"]["sha256"]
    _write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"]["sha256"] = _sha256(adjudication_path)

    errors = _validate(council, plugin_root, artifact_dir)

    assert "soros sealed memo content must equal Council root memo" in errors


def test_current_authority_rejects_out_of_order_chair(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    _bind_current_authority(council, artifact_dir)
    council["chair"]["started_at"] = "2026-08-22T10:24:00+08:00"

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("current Council timeline must be" in error for error in errors)


def test_current_authority_binds_exact_public_validator(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    bindings = _bind_current_authority(council, artifact_dir)
    bindings["validator_sha256"] = "0" * 64

    errors = _validate(council, plugin_root, artifact_dir)

    assert "artifact_bindings.validator_sha256 does not match this validator" in errors


def test_plausible_prose_without_named_method_artifacts_is_rejected(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    for memo in council["first_round"]["memos"]:
        memo["work_product"] = "A fluent and plausible investment analysis."
        memo["method_artifact"] = None

    errors = _validate(council, plugin_root, artifact_dir)

    for seat in ("damodaran", "soros", "mauboussin"):
        assert any(f"{seat} Complete requires its named structured method artifact" in error for error in errors)


def test_partial_or_unavailable_method_requires_structured_gap_artifact(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    for memo in council["first_round"]["memos"]:
        memo["method_completion"] = "Partial"
        memo["method_artifact"] = None

    errors = _validate(council, plugin_root, artifact_dir)

    for seat in ("damodaran", "soros", "mauboussin"):
        assert any(
            f"{seat} Partial requires a structured gap artifact" in error
            for error in errors
        )


def test_partial_numeric_artifact_is_rejected_before_chair_use(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memo = council["first_round"]["memos"][0]
    memo["method_completion"] = "Partial"
    artifact = memo["method_artifact"]
    artifact["method_gap"] = "The owner case lacks one accepted capital input."
    artifact["fundamental_value_range"].update(
        {"low": "bad", "base": [], "high": 9999.0}
    )
    upside = council["chair"]["decision_matrix"]["states"][2]
    upside["target_price"] = 9999.0
    upside["gross_return_pct"] = 9899.0
    council["chair"]["decision_matrix"]["gross_expected_return_pct"] = 3952.1
    council["chair"]["gross_expected_return_pct"] = 3952.1

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Damodaran Partial must use only a qualitative gap artifact" in error
        for error in errors
    )


def test_partial_seat_cannot_inject_numeric_probability_artifact(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memo = next(memo for memo in council["first_round"]["memos"] if memo["seat"] == "soros")
    memo["method_completion"] = "Partial"

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Soros Partial must use only a qualitative gap artifact" in error
        for error in errors
    )


def test_partial_seat_with_qualitative_gap_artifact_can_pass(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memo = next(memo for memo in council["first_round"]["memos"] if memo["seat"] == "soros")
    memo["method_completion"] = "Partial"
    memo["method_artifact"] = {
        "artifact_type": "soros_reflexivity_chain_v1",
        "requested_horizon": "12 months",
        "proposition_id": "soros:revision_feedback_loop",
        "method_gap": "No accepted actor-flow observation supports a numeric path distribution.",
    }

    states = council["chair"]["decision_matrix"]["states"]
    for state, source_id, probability, target, gross_return in (
        (states[1], "base", 50.0, 115.0, 15.0),
        (states[2], "upside", 25.0, 155.0, 55.0),
    ):
        state["probability_pct"] = probability
        state["target_price"] = target
        state["gross_return_pct"] = gross_return
        state["seat_inputs"] = ["mauboussin"]
        state["target_components"] = [{
            "seat": "mauboussin",
            "proposition_id": "mauboussin:positive_expectations_distribution",
            "source_kind": "probability_payoff_target",
            "source_id": source_id,
            "weight_pct": 100.0,
        }]
        state["probability_components"] = [{
            "seat": "mauboussin",
            "proposition_id": "mauboussin:positive_expectations_distribution",
            "source_kind": "probability_payoff_probability",
            "source_id": source_id,
            "weight_pct": 100.0,
            "scenario_probability_basis": "Mauboussin payoff-state probability anchored to the accepted reference class and inside-view update.",
        }]
    states[2]["seat_inputs"] = ["damodaran", "mauboussin"]
    states[2]["target_components"] = [{
        "seat": "damodaran",
        "proposition_id": "damodaran:price_implied_growth_gap",
        "source_kind": "fundamental_value_high",
        "source_id": None,
        "weight_pct": 100.0,
    }]
    council["chair"]["decision_matrix"]["gross_expected_return_pct"] = 13.75
    council["chair"]["gross_expected_return_pct"] = 13.75

    errors = _validate(council, plugin_root, artifact_dir)

    assert errors == []


def test_all_partial_seats_preserve_qualitative_challenge_without_numeric_matrix(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    for memo in council["first_round"]["memos"]:
        artifact = memo["method_artifact"]
        memo["method_completion"] = "Partial"
        memo["method_artifact"] = {
            "artifact_type": artifact["artifact_type"],
            "requested_horizon": artifact["requested_horizon"],
            "proposition_id": artifact["proposition_id"],
            "method_gap": "The accepted packet supports a qualitative countercase but not an eligible numeric distribution.",
        }
    council["chair"]["decision_matrix"] = None
    council["chair"]["gross_expected_return_pct"] = None
    council["chair"]["robustness"] = "Fragile"

    errors = _validate(council, plugin_root, artifact_dir)

    assert errors == []


def test_probability_component_requires_scenario_probability_basis(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    component = council["chair"]["decision_matrix"]["states"][0]["probability_components"][0]
    component["scenario_probability_basis"] = ""

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "scenario_probability_basis must be a non-empty string" in error
        for error in errors
    )


def test_chair_seat_decision_requires_retained_limitation_and_impacts(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    decision = council["chair"]["seat_decisions"][0]
    decision.pop("retained_limitation", None)
    decision.pop("impact", None)

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("chair.seat_decisions[0] is missing fields" in error for error in errors)


def test_all_named_method_artifacts_bind_to_requested_horizon(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    for memo in council["first_round"]["memos"]:
        memo["method_artifact"]["requested_horizon"] = "5 years"

    errors = _validate(council, plugin_root, artifact_dir)

    for seat in ("Damodaran", "Soros", "Mauboussin"):
        assert any(
            f"{seat} requested_horizon must equal decision_horizon" in error
            for error in errors
        )


def test_damodaran_complete_requires_archetype_drivers_and_numeric_bridge(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    artifact = council["first_round"]["memos"][0]["method_artifact"]
    artifact["price_implied_drivers"].pop()
    artifact["story_to_numbers_bridge"][0]["owner_value"] = 999.0

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Damodaran price-implied drivers must match the high_growth archetype" in error for error in errors)
    assert any("Damodaran story bridge values must equal its driver tables" in error for error in errors)


def test_soros_complete_requires_full_evidenced_feedback_chain(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    artifact = council["first_round"]["memos"][1]["method_artifact"]
    artifact["feedback_chain"].pop()
    artifact["reversal_trigger"]["evidence_ids"] = ["NEW:unsupported"]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Soros reflexive chain must contain all five ordered links" in error for error in errors)
    assert any("Soros method artifact uses evidence outside its sealed packet" in error for error in errors)


def test_mauboussin_complete_requires_reference_class_and_recomputed_distribution(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memo = council["first_round"]["memos"][2]
    artifact = memo["method_artifact"]
    artifact["reference_class"]["status"] = "gap"
    artifact["reference_class"]["gap_reason"] = "No comparable sample was accepted."
    artifact["probability_payoff_states"][0]["probability_pct"] = 35.0
    artifact["sign_sensitivity"][0]["sign_flips"] = False

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Mauboussin reference-class gap requires Partial completion" in error for error in errors)
    assert any("Mauboussin state probabilities must sum to 100" in error for error in errors)
    assert any("Mauboussin sign_flips must equal the recomputed sign range" in error for error in errors)


def test_mauboussin_prior_updates_must_reconcile_to_posterior_states(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    artifact = council["first_round"]["memos"][2]["method_artifact"]
    artifact["reference_class"]["base_rate_pct"] = 1.0
    artifact["inside_view_updates"][0]["probability_delta_pct"] = 1.0

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Mauboussin posterior must equal base rate plus inside-view updates" in error
        for error in errors
    )

    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    artifact = council["first_round"]["memos"][2]["method_artifact"]
    artifact["reference_class"]["base_rate_pct"] = 1.0
    artifact["inside_view_updates"][0]["probability_delta_pct"] = 1.0
    artifact["posterior_success_probability_pct"] = 2.0
    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Mauboussin success-state probability must equal posterior" in error
        for error in errors
    )


def test_chair_requires_mece_recomputed_state_matrix_and_opposing_path(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    matrix = council["chair"]["decision_matrix"]
    matrix["states"][2]["dominant_variable_interval"]["lower"] = 4.0
    matrix["states"][0]["gross_return_pct"] = -1.0
    matrix["gross_expected_return_pct"] = 99.0
    matrix["strongest_disconfirming_state_id"] = "revision_up"

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Chair state intervals must be contiguous and non-overlapping" in error for error in errors)
    assert any("Chair state gross return must equal target-price return" in error for error in errors)
    assert any("Chair matrix gross expected return must equal recomputed state EV" in error for error in errors)
    assert any("Chair strongest disconfirming state must oppose the final stance" in error for error in errors)


def test_chair_targets_and_decisions_bind_to_named_method_artifacts(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    matrix = council["chair"]["decision_matrix"]
    matrix["states"][0]["target_price"] = 50.0
    matrix["states"][0]["gross_return_pct"] = -50.0
    matrix["states"][1]["target_price"] = 100.0
    matrix["states"][1]["gross_return_pct"] = 0.0
    matrix["states"][2]["target_price"] = 200.0
    matrix["states"][2]["gross_return_pct"] = 100.0
    matrix["states"][0]["probability_pct"] = 30.0
    matrix["states"][1]["probability_pct"] = 20.0
    matrix["states"][2]["probability_pct"] = 50.0
    matrix["gross_expected_return_pct"] = 35.0
    council["chair"]["gross_expected_return_pct"] = 35.0
    council["chair"]["seat_decisions"][0]["proposition_id"] = "damodaran:invented"

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Chair state target_price must equal weighted method-artifact inputs" in error
        for error in errors
    )
    assert any(
        "Chair state probability_pct must equal weighted method-artifact inputs" in error
        for error in errors
    )
    assert any(
        "chair seat decision proposition_id must match its method artifact" in error
        for error in errors
    )


def test_chair_components_must_match_the_same_economic_scenario(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    states = council["chair"]["decision_matrix"]["states"]

    states[0]["target_components"] = [{
        "seat": "damodaran",
        "proposition_id": "damodaran:price_implied_growth_gap",
        "source_kind": "fundamental_value_high",
        "source_id": None,
        "weight_pct": 100.0,
    }]
    states[0]["probability_components"] = [{
        "seat": "soros",
        "proposition_id": "soros:revision_feedback_loop",
        "source_kind": "horizon_path_probability",
        "source_id": "reinforcing",
        "weight_pct": 100.0,
    }]
    states[0]["seat_inputs"] = ["damodaran", "soros"]
    states[0].update({"probability_pct": 40.0, "target_price": 155.0, "gross_return_pct": 55.0})

    states[1]["target_components"] = [{
        "seat": "mauboussin",
        "proposition_id": "mauboussin:positive_expectations_distribution",
        "source_kind": "probability_payoff_target",
        "source_id": "upside",
        "weight_pct": 100.0,
    }]
    states[1]["seat_inputs"] = ["mauboussin", "soros"]
    states[1].update({"probability_pct": 35.0, "target_price": 160.0, "gross_return_pct": 60.0})

    states[2]["target_components"] = [{
        "seat": "mauboussin",
        "proposition_id": "mauboussin:positive_expectations_distribution",
        "source_kind": "probability_payoff_target",
        "source_id": "downside",
        "weight_pct": 100.0,
    }]
    states[2]["probability_components"] = [{
        "seat": "mauboussin",
        "proposition_id": "mauboussin:positive_expectations_distribution",
        "source_kind": "probability_payoff_probability",
        "source_id": "downside",
        "weight_pct": 100.0,
    }]
    states[2]["seat_inputs"] = ["mauboussin"]
    states[2].update({"probability_pct": 25.0, "target_price": 70.0, "gross_return_pct": -30.0})

    council["chair"]["decision_matrix"]["gross_expected_return_pct"] = 35.5
    council["chair"]["decision_matrix"]["strongest_disconfirming_state_id"] = "revision_up"
    council["chair"]["gross_expected_return_pct"] = 35.5

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("target component scenario_role" in error for error in errors)
    assert any("probability component scenario_role" in error for error in errors)
    assert any(
        "Chair decision_matrix.states scenario roles must be ordered" in error
        for error in errors
    )


def test_method_probability_state_cannot_be_counted_twice_across_matrix(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    soros = council["first_round"]["memos"][1]["method_artifact"]
    soros_paths = {row["state_id"]: row for row in soros["horizon_price_paths"]}
    soros_paths["reinforcing"]["probability_pct"] = 40.0
    soros_paths["stall"]["probability_pct"] = 10.0
    soros_paths["reversal"]["probability_pct"] = 50.0
    soros["expected_path_return_pct"] = -0.5

    mauboussin = council["first_round"]["memos"][2]["method_artifact"]
    maub_states = {
        row["state_id"]: row for row in mauboussin["probability_payoff_states"]
    }
    maub_states["downside"]["probability_pct"] = 10.0
    maub_states["base"]["probability_pct"] = 50.0
    maub_states["upside"]["probability_pct"] = 40.0
    mauboussin["reference_class"]["base_rate_pct"] = 83.0
    mauboussin["posterior_success_probability_pct"] = 90.0
    mauboussin["expected_return_pct"] = 28.5

    states = council["chair"]["decision_matrix"]["states"]
    states[0]["probability_pct"] = 10.0
    states[1]["probability_pct"] = 10.0
    states[2]["probability_components"] = [{
        "seat": "mauboussin",
        "proposition_id": "mauboussin:positive_expectations_distribution",
        "source_kind": "probability_payoff_probability",
        "source_id": "upside",
        "weight_pct": 100.0,
    }]
    states[2]["seat_inputs"] = ["damodaran", "mauboussin"]
    states[2]["dominant_variable_interval"].update(
        {"upper": 10.0, "upper_inclusive": True}
    )

    second_upside = copy.deepcopy(states[2])
    second_upside.update(
        {
            "state_id": "revision_up_extreme",
            "definition": "Revision breadth accelerates beyond ten percent.",
            "target_price": 160.0,
            "gross_return_pct": 60.0,
            "seat_inputs": ["mauboussin"],
            "target_components": [{
                "seat": "mauboussin",
                "proposition_id": "mauboussin:positive_expectations_distribution",
                "source_kind": "probability_payoff_target",
                "source_id": "upside",
                "weight_pct": 100.0,
            }],
        }
    )
    second_upside["dominant_variable_interval"] = {
        "lower": 10.0,
        "lower_inclusive": False,
        "upper": None,
        "upper_inclusive": False,
    }
    states.append(second_upside)
    council["chair"]["decision_matrix"]["gross_expected_return_pct"] = 43.0
    council["chair"]["gross_expected_return_pct"] = 43.0

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "Chair probability source state may be used by only one matrix state"
        in error
        for error in errors
    )


def test_zero_price_and_zero_probability_states_fail_closed_without_crashing(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["current_price"]["value"] = 0.0
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("current_price.value must be positive finite numeric" in error for error in errors)

    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["fields"][0]["value"] = float("nan")
    errors = _validate(council, plugin_root, artifact_dir)
    assert any(
        "value must be finite numeric for current_price" in error
        for error in errors
    )

    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["fields"][0]["value"] = 99.0
    errors = _validate(council, plugin_root, artifact_dir)
    assert any(
        "common factual current_price must equal current_price.value" in error
        for error in errors
    )

    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    soros = council["first_round"]["memos"][1]["method_artifact"]
    soros["horizon_price_paths"][0]["probability_pct"] = 0.0
    soros["horizon_price_paths"][1]["probability_pct"] = 75.0
    soros["expected_path_return_pct"] = -6.25
    mauboussin = council["first_round"]["memos"][2]["method_artifact"]
    mauboussin["probability_payoff_states"][0]["probability_pct"] = 0.0
    mauboussin["probability_payoff_states"][1]["probability_pct"] = 75.0
    mauboussin["expected_return_pct"] = 26.25
    matrix = council["chair"]["decision_matrix"]
    matrix["states"][0]["probability_pct"] = 0.0
    matrix["states"][1]["probability_pct"] = 65.0
    matrix["gross_expected_return_pct"] = 19.25
    council["chair"]["gross_expected_return_pct"] = 19.25

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Soros path probability must be greater than 0" in error for error in errors)
    assert any("Mauboussin state probability must be greater than 0" in error for error in errors)
    assert any("Chair state probability must be greater than 0" in error for error in errors)


def test_chair_strongest_disconfirming_state_must_be_most_adverse(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    matrix = council["chair"]["decision_matrix"]
    matrix["states"][0]["target_price"] = 90.0
    matrix["states"][0]["gross_return_pct"] = -10.0
    matrix["states"][1]["target_price"] = 70.0
    matrix["states"][1]["gross_return_pct"] = -30.0
    matrix["gross_expected_return_pct"] = 9.0
    council["chair"]["gross_expected_return_pct"] = 9.0

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("Chair strongest disconfirming state must be the most adverse state" in error for error in errors)


def test_limited_pei_baseline_remains_admissible_with_explicit_soft_gap(tmp_path):
    plugin_root, artifact_dir, _, council, pei_path, pei_receipt = _fixture(tmp_path)
    pei_receipt["requirements"].append(
        {
            "id": "optional_peer_context",
            "description": "Optional peer context",
            "source_category": "Market Data & Estimates",
            "requirement_class": "provider",
            "criticality": "soft",
            "status": "gap",
            "evidence_ids": [],
            "as_of": None,
            "cutoff": pei_receipt["evidence_cutoff"],
            "gap_reason": "Comparable peer coverage was thin.",
            "decision_impact": "Reduces robustness without blocking research.",
            "contract_refs": [],
        }
    )
    pei_receipt["output_posture"] = "LIMITED"
    _write_json(pei_path, pei_receipt)
    council["pei_input_receipt"].update(
        {"sha256": _sha256(pei_path), "declared_posture": "LIMITED"}
    )

    errors = _validate(council, plugin_root, artifact_dir)

    assert errors == []
    assert council["research_admission"] == "ADMITTED"


def test_study_flow_lead_cannot_enter_the_common_factual_spine(tmp_path):
    plugin_root, artifact_dir, _, council, _, pei_receipt = _fixture(tmp_path)
    ambient_claim_id = next(
        entry["id"]
        for entry in pei_receipt["evidence_registry"]
        if entry["source_kind"] == "study_flow"
    )
    council["common_factual_spine"]["fields"][1]["evidence_ids"] = [
        ambient_claim_id
    ]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("uses non-established evidence" in error for error in errors)


def test_first_round_seats_are_browse_closed_and_cannot_add_evidence(tmp_path):
    plugin_root, artifact_dir, _, council, _, pei_receipt = _fixture(tmp_path)
    ambient_claim_id = next(
        entry["id"]
        for entry in pei_receipt["evidence_registry"]
        if entry["source_kind"] == "study_flow"
    )
    memo = council["first_round"]["memos"][0]
    memo["browsed"] = True
    memo["added_evidence_ids"] = [ambient_claim_id]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("first_round.memos[0].browsed must be false" in error for error in errors)
    assert any(
        "first_round.memos[0].added_evidence_ids must be empty" in error
        for error in errors
    )


def test_member_and_chair_cannot_smuggle_unvalidated_fields(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["upstream_verdict"] = "Long"
    council["first_round"]["memos"][0]["upstream_verdict"] = "Long"
    council["first_round"]["upstream_verdict"] = "Long"
    council["convergence"]["new_company_fact"] = "Unsupported claim"
    council["chair"]["new_company_fact"] = "Unsupported claim"

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("root has unexpected fields: upstream_verdict" in error for error in errors)
    assert any("sealed input leaked outside its declaration" in error for error in errors)
    assert any("first_round.memos[0] has unexpected fields: upstream_verdict" in error for error in errors)
    assert any("first_round has unexpected fields: upstream_verdict" in error for error in errors)
    assert any("convergence has unexpected fields: new_company_fact" in error for error in errors)
    assert any("chair has unexpected fields: new_company_fact" in error for error in errors)


def test_first_round_memo_cannot_escape_its_sealed_partition(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["first_round"]["memos"][2]["accepted_evidence_ids"] = [
        "IR:10-Q:2026Q2"
    ]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("outside its sealed packet" in error for error in errors)


def test_first_round_research_lead_must_be_pei_accepted_and_seat_partitioned(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memo = council["first_round"]["memos"][0]
    memo["research_lead_ids"] = ["STUDY_FLOW:unaccepted-lead"]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("research leads not accepted by PEI" in error for error in errors)
    assert any("research leads outside its sealed packet" in error for error in errors)


def test_unavailable_runtime_does_not_impersonate_seats(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    numeric_matrix = copy.deepcopy(council["chair"]["decision_matrix"])
    numeric_return = council["chair"]["gross_expected_return_pct"]
    council["council_runtime"] = "unavailable"
    council["first_round"] = {
        "unavailable_seats": ["damodaran", "soros", "mauboussin"],
        "memos": [],
    }
    council["convergence"] = {
        "first_pass_status": "unavailable",
        "implicated_seats": [],
        "semantic_review": {
            "reviewed": False,
            "first_overlap_detected": False,
            "final_overlap_detected": False,
            "rationale": "No member memos exist because collaboration is unavailable.",
        },
        "corrective_pass_count": 0,
        "corrective_memos": [],
        "final_status": "unavailable",
    }
    council["chair"]["seat_decisions"] = []
    council["chair"]["robustness"] = "Fragile"
    council["chair"]["decision_matrix"] = None
    council["chair"]["gross_expected_return_pct"] = None
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []

    council["chair"]["decision_matrix"] = numeric_matrix
    council["chair"]["gross_expected_return_pct"] = numeric_return
    errors = _validate(council, plugin_root, artifact_dir)
    assert any(
        "unavailable Council runtime must not produce a numeric decision matrix"
        in error
        for error in errors
    )
    assert any(
        "unavailable Council runtime must not produce numeric expected return" in error
        for error in errors
    )


def test_unavailable_runtime_rejects_fabricated_member_memos(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["council_runtime"] = "unavailable"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("unavailable runtime cannot contain member memos" in e for e in errors)


def test_hard_research_gap_blocks_council_admission(tmp_path):
    plugin_root, artifact_dir, _, council, pei_path, pei_receipt = _fixture(tmp_path)
    pei_receipt["requirements"][1].update(
        {
            "status": "gap",
            "evidence_ids": [],
            "as_of": None,
            "gap_reason": "Primary filing was unavailable.",
        }
    )
    pei_receipt["output_posture"] = "BLOCKED"
    _write_json(pei_path, pei_receipt)
    council["pei_input_receipt"]["sha256"] = _sha256(pei_path)
    council["pei_input_receipt"]["declared_posture"] = "BLOCKED"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("research admission blocked by hard primary gap" in error for error in errors)


def test_implementation_only_blocker_does_not_erase_research_direction(tmp_path):
    plugin_root, artifact_dir, _, council, pei_path, pei_receipt = _fixture(tmp_path)
    implementation_path = artifact_dir / "support" / "implementation_receipt.json"
    _write_json(
        implementation_path,
        {
            "schema_version": 1,
            "kind": "implementation",
            "ticker": "EXAMPLE",
            "security_id": "SEC-CIK-0000001",
            "evidence_cutoff": pei_receipt["evidence_cutoff"],
            "generated_at": "2026-08-22T10:01:00+08:00",
            "validation_status": "BLOCKED",
            "evidence_ids": [],
            "reason": "borrow unavailable",
        },
    )
    pei_receipt["owner_declaration"]["declared_receipt_kinds"] = ["implementation"]
    pei_receipt["subordinate_receipts"].append(
        {
            "kind": "implementation",
            "artifact": "support/implementation_receipt.json",
            "sha256": _sha256(implementation_path),
            "validation_status": "BLOCKED",
        }
    )
    pei_receipt["requirements"].append(
        {
            "id": "borrow_route",
            "description": "Borrow availability",
            "source_category": "Market Data & Estimates",
            "requirement_class": "implementation",
            "criticality": "hard",
            "status": "gap",
            "evidence_ids": [],
            "as_of": None,
            "cutoff": pei_receipt["evidence_cutoff"],
            "gap_reason": "Borrow route is unavailable.",
            "decision_impact": "Blocks implementation, not research direction.",
            "contract_refs": [],
        }
    )
    pei_receipt["output_posture"] = "BLOCKED"
    _write_json(pei_path, pei_receipt)
    council["pei_input_receipt"]["sha256"] = _sha256(pei_path)
    council["pei_input_receipt"]["declared_posture"] = "BLOCKED"
    council["chair"]["participation"] = "Stand aside"
    council["chair"]["implementation_readiness"] = "Blocked"
    council["chair"]["implementation_blockers"] = ["Borrow route unavailable"]
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []
    assert council["chair"]["research_stance"] == "Long"


def test_common_spine_rejects_upstream_narrative_or_verdict(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["upstream_verdict"] = "Long"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("common_factual_spine contains sealed field: upstream_verdict" in e for e in errors)


def test_private_partitions_have_exact_non_overlapping_method_domains(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["private_partitions"]["soros"]["allowed_domains"].append("fundamentals")
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("soros.allowed_domains must equal its method partition" in e for e in errors)


def test_non_common_private_evidence_cannot_be_shared_across_seats(tmp_path):
    plugin_root, artifact_dir, _, council, _, pei_receipt = _fixture(tmp_path)
    ambient_claim_id = next(
        entry["id"]
        for entry in pei_receipt["evidence_registry"]
        if entry["source_kind"] == "study_flow"
    )
    council["private_partitions"]["damodaran"]["evidence_ids"].append(
        ambient_claim_id
    )

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        f"private evidence appears in multiple method partitions: {ambient_claim_id}"
        in error
        for error in errors
    )


def test_detected_persona_convergence_requires_exactly_one_corrective_pass(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memos = council["first_round"]["memos"]
    memos[1]["contribution"]["causal_mechanism"] = memos[0]["contribution"]["causal_mechanism"]
    memos[1]["contribution"]["primary_mechanism_tag"] = "fundamental_reinvestment"
    memos[1]["contribution"]["mechanism_tags"] = ["fundamental_reinvestment"]
    council["convergence"]["first_pass_status"] = "persona_convergence"
    council["convergence"]["implicated_seats"] = ["damodaran", "soros"]
    council["convergence"]["semantic_review"].update(
        {"first_overlap_detected": True, "final_overlap_detected": True}
    )
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("persona_convergence requires exactly one corrective pass" in e for e in errors)


def test_one_corrective_pass_can_restore_distinct_contributions(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memos = council["first_round"]["memos"]
    memos[1]["contribution"]["causal_mechanism"] = memos[0]["contribution"]["causal_mechanism"]
    memos[1]["contribution"]["primary_mechanism_tag"] = "fundamental_reinvestment"
    memos[1]["contribution"]["mechanism_tags"] = ["fundamental_reinvestment"]
    council["convergence"] = {
        "first_pass_status": "persona_convergence",
        "implicated_seats": ["damodaran", "soros"],
        "semantic_review": {
            "reviewed": True,
            "first_overlap_detected": True,
            "final_overlap_detected": False,
            "rationale": "The corrective pass replaced the repeated causal line.",
        },
        "corrective_pass_count": 1,
        "corrective_memos": [
            {
                "seat": "soros",
                "browsed": False,
                "added_evidence_ids": [],
                "contribution": {
                    "causal_mechanism": "Forced covering changes price and financing access.",
                    "primary_mechanism_tag": "positioning_squeeze",
                    "mechanism_tags": ["positioning_squeeze", "financing_feedback"],
                    "disconfirming_condition": "Short interest falls without price response.",
                    "key_metric": "Short-interest and price-response divergence",
                    "source_posture": "Current positioning and market-response evidence",
                },
            }
        ],
        "final_status": "distinct",
    }
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []


def test_corrective_pass_cannot_repeat_or_add_evidence(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["convergence"]["corrective_pass_count"] = 2
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("corrective_pass_count must be 0 or 1" in e for e in errors)


def test_unresolved_convergence_forces_fragile_robustness(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memos = council["first_round"]["memos"]
    memos[1]["contribution"]["causal_mechanism"] = memos[0]["contribution"]["causal_mechanism"]
    memos[1]["contribution"]["primary_mechanism_tag"] = "fundamental_reinvestment"
    memos[1]["contribution"]["mechanism_tags"] = ["fundamental_reinvestment"]
    council["convergence"] = {
        "first_pass_status": "persona_convergence",
        "implicated_seats": ["damodaran", "soros"],
        "semantic_review": {
            "reviewed": True,
            "first_overlap_detected": True,
            "final_overlap_detected": True,
            "rationale": "Two seats repeated the same causal mechanism.",
        },
        "corrective_pass_count": 1,
        "corrective_memos": [
            {
                "seat": "soros",
                "browsed": False,
                "added_evidence_ids": [],
                "contribution": copy.deepcopy(memos[1]["contribution"]),
            }
        ],
        "final_status": "unresolved_convergence",
    }
    council["chair"]["robustness"] = "Fragile"
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []


def test_chair_is_evidence_closed_and_cannot_add_or_browse(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["chair"]["browsed"] = True
    council["chair"]["added_evidence_ids"] = ["NEW:web-source"]
    council["chair"]["used_evidence_ids"].append("NEW:web-source")
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("chair.browsed must be false" in e for e in errors)
    assert any("chair.added_evidence_ids must be empty" in e for e in errors)
    assert any("chair used evidence outside accepted PEI inputs" in e for e in errors)


def test_chair_seat_decisions_must_be_exactly_one_per_member(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["chair"]["seat_decisions"].append(
        copy.deepcopy(council["chair"]["seat_decisions"][0])
    )

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("duplicate chair seat decision: damodaran" in error for error in errors)


def test_council_must_match_pei_security_and_cutoff(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["ticker"] = "WRONG"
    council["security_identity"]["symbol"] = "WRONG"
    council["evidence_cutoff"] = "2026-08-22T09:59:00+08:00"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("Council ticker must equal PEI ticker" in e for e in errors)
    assert any("Council evidence_cutoff must equal PEI evidence_cutoff" in e for e in errors)


def test_common_spine_rejects_nested_narrative_and_partition_payloads(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["fields"][0]["value"] = {
        "narrative": "Complete PEI Long thesis"
    }
    council["private_partitions"]["soros"]["full_pei_narrative"] = "Long thesis"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("common factual spine values must be scalar" in e for e in errors)
    assert any("private_partitions.soros has unexpected fields" in e for e in errors)

    _, _, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["fields"].append(
        {
            "id": "factor_grade",
            "field_class": "provider_snapshot",
            "value": "Long: revenue revisions imply fair value 160",
            "unit": "grade",
            "as_of": "2026-08-22T09:00:00+08:00",
            "evidence_ids": ["SA:market_snapshot:2026-08-22"],
        }
    )
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("value is not an allowed provider enum" in e for e in errors)

    _, _, _, council, _, _ = _fixture(tmp_path)
    council["common_factual_spine"]["fields"].append(
        {
            "id": "currency",
            "field_class": "identity_fact",
            "value": "BUY",
            "unit": "currency_code",
            "as_of": "2026-08-22T09:00:00+08:00",
            "evidence_ids": ["SA:market_snapshot:2026-08-22"],
        }
    )
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("value must equal current_price.currency" in e for e in errors)


def test_canonical_mechanism_tags_detect_paraphrased_convergence(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memos = council["first_round"]["memos"]
    memos[1]["contribution"]["causal_mechanism"] = (
        "Capital returns weakening causes the market to mark value down."
    )
    memos[1]["contribution"]["primary_mechanism_tag"] = memos[0]["contribution"][
        "primary_mechanism_tag"
    ]
    memos[1]["contribution"]["mechanism_tags"] = ["fundamental_reinvestment"]
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("convergence.first_pass_status must be persona_convergence" in e for e in errors)


def test_mechanism_tag_cannot_be_mislabeled_to_hide_semantic_overlap(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    soros = council["first_round"]["memos"][1]["contribution"]
    soros["causal_mechanism"] = (
        "Capital returns weakening causes the market to mark value down."
    )
    soros["primary_mechanism_tag"] = "cash_flow_conversion"
    soros["mechanism_tags"] = ["cash_flow_conversion"]
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("mechanism_tags must equal validator-derived semantic tags" in e for e in errors)


def test_cash_conversion_paraphrase_with_sentiment_filler_still_converges(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    memos = council["first_round"]["memos"]
    memos[0]["contribution"]["causal_mechanism"] = (
        "Cash flow conversion weakens as revenue growth consumes working capital."
    )
    memos[0]["contribution"]["primary_mechanism_tag"] = "cash_flow_conversion"
    memos[0]["contribution"]["mechanism_tags"] = [
        "cash_flow_conversion",
        "fundamental_growth",
    ]
    memos[1]["contribution"]["causal_mechanism"] = (
        "More sales fail to turn into cash, reducing sentiment."
    )
    memos[1]["contribution"]["primary_mechanism_tag"] = "cash_flow_conversion"
    memos[1]["contribution"]["mechanism_tags"] = [
        "cash_flow_conversion",
        "narrative_attention",
    ]

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "convergence.first_pass_status must be persona_convergence" in error
        for error in errors
    )


def test_research_stance_sign_and_decision_dimensions_are_separate(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["chair"]["research_stance"] = "Avoid"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("research_stance must be Long for positive gross expected return" in e for e in errors)
    council["chair"]["research_stance"] = "Long"
    council["chair"]["participation"] = "Blocked"
    errors = _validate(council, plugin_root, artifact_dir)
    assert any("chair.participation must be Eligible, Conditional, or Stand aside" in e for e in errors)


def test_malformed_enum_and_component_selector_types_fail_closed(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    council["first_round"]["memos"][0]["method_artifact"][
        "company_archetype"
    ] = []
    council["first_round"]["memos"][1]["method_artifact"]["classification"] = {}
    council["chair"]["decision_matrix"]["states"][0]["target_components"][0][
        "source_id"
    ] = []
    council["chair"]["research_stance"] = []

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("company_archetype" in error for error in errors)
    assert any("classification" in error for error in errors)
    assert any("cannot resolve Mauboussin target input" in error for error in errors)
    assert any(
        "chair.research_stance must be Long, Short, or Avoid" in error
        for error in errors
    )


def test_cli_validates_the_public_artifact_seam(tmp_path):
    plugin_root, _, council_path, _, _, _ = _fixture(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--plugin-root",
            str(plugin_root),
            str(council_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Council run is valid" in completed.stdout
