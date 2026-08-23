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
        "schema_version": 1,
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
        "schema_version": 1,
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
                {"seat": "damodaran", "decision": "Accept"},
                {"seat": "soros", "decision": "Conditional"},
                {"seat": "mauboussin", "decision": "Accept"},
            ],
            "dominant_variable": "Revenue estimate revision breadth",
            "strongest_disconfirming_path": "Returns fade while revisions reverse.",
            "reversal_trigger": "Two consecutive monthly revision-breadth declines.",
            "gross_expected_return_pct": 12.5,
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


def _validate(council, plugin_root, artifact_dir):
    return VALIDATOR.validate(
        council, plugin_root=plugin_root, artifact_dir=artifact_dir
    )


def test_full_receipt_chain_admits_council_and_validates_final_judgment(tmp_path):
    plugin_root, artifact_dir, _, council, _, _ = _fixture(tmp_path)
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []


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
    errors = _validate(council, plugin_root, artifact_dir)
    assert errors == []


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
