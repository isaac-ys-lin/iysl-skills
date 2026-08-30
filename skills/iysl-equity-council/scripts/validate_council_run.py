#!/usr/bin/env python3
"""Validate Equity Council admission, information partitions, and judgment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SEATS = {"damodaran", "soros", "mauboussin"}
ASSUMPTION_FAMILIES = {
    "revenue_orders_capex_recognition",
    "product_mix_and_margins",
    "reinvestment_and_fcff",
    "capital_structure_and_wacc",
    "duration_fade_and_terminal",
    "twelve_month_market_expectations",
}
PARTITION_DOMAINS = {
    "damodaran": {"fundamentals", "reverse_valuation", "capital_structure"},
    "soros": {"price_path", "marginal_actors", "positioning_reflexivity"},
    "mauboussin": {
        "expectations_revisions",
        "reference_class",
        "probability_payoff",
    },
}
SEALED_INPUTS = {
    "upstream_verdict",
    "full_pei_narrative",
    "participation",
    "implementation_readiness",
    "other_seat_outputs",
}
ROOT_FIELDS = {
    "schema_version",
    "council_runtime",
    "ticker",
    "security_identity",
    "current_price",
    "decision_horizon",
    "evidence_cutoff",
    "pei_input_receipt",
    "research_admission",
    "sealed_inputs",
    "common_factual_spine",
    "private_partitions",
    "first_round",
    "convergence",
    "chair",
}
SEALED_OUTPUT_PATHS = {
    "chair.participation",
    "chair.implementation_readiness",
}
SCENARIO_ROLES = {"downside", "base", "upside"}
COMMON_FORBIDDEN_FIELDS = {
    "upstream_verdict",
    "research_stance",
    "full_pei_narrative",
    "participation",
    "implementation",
    "implementation_readiness",
    "owner_fair_value",
    "target_price",
    "other_seat_outputs",
}
COMMON_NUMERIC_FIELDS = {
    "current_price": "market_fact",
    "volume": "market_fact",
    "market_cap": "market_fact",
    "enterprise_value": "market_fact",
    "shares_outstanding": "market_fact",
    "short_interest": "market_fact",
    "options_implied_volatility": "market_fact",
    "latest_revenue": "company_fact",
    "latest_eps": "company_fact",
    "latest_cash": "company_fact",
    "latest_debt": "company_fact",
    "latest_free_cash_flow": "company_fact",
    "latest_margin": "company_fact",
    "latest_capex": "company_fact",
    "management_guidance_low": "company_fact",
    "management_guidance_high": "company_fact",
    "consensus_revenue_estimate": "provider_snapshot",
    "consensus_eps_estimate": "provider_snapshot",
    "estimate_revision": "provider_snapshot",
    "analyst_count": "provider_snapshot",
    "provider_price_target": "provider_snapshot",
}
COMMON_TEXT_FIELDS = {
    "issuer_name": "identity_fact",
    "ticker": "identity_fact",
    "listing": "identity_fact",
    "security_id": "identity_fact",
    "currency": "identity_fact",
    "fiscal_calendar": "identity_fact",
    "reporting_period": "company_fact",
    "event_date": "company_fact",
}
COMMON_ENUM_FIELDS = {
    "consensus_rating": (
        "provider_snapshot",
        {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"},
    ),
    "quant_rating": (
        "provider_snapshot",
        {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"},
    ),
    "factor_grade": (
        "provider_snapshot",
        {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"},
    ),
}
CONTRIBUTION_TEXT_FIELDS = {
    "causal_mechanism",
    "disconfirming_condition",
    "key_metric",
    "source_posture",
}
CONTRIBUTION_FIELDS = CONTRIBUTION_TEXT_FIELDS | {"primary_mechanism_tag"}
MECHANISM_TAGS = {
    "fundamental_growth",
    "fundamental_reinvestment",
    "cash_flow_conversion",
    "capital_intensity",
    "capital_structure",
    "multiple_expectations",
    "estimate_revisions",
    "reference_class_base_rate",
    "probability_asymmetry",
    "marginal_actor_flow",
    "positioning_squeeze",
    "liquidity_feedback",
    "financing_feedback",
    "narrative_attention",
    "catalyst_path",
}
MECHANISM_PATTERNS = {
    "fundamental_growth": (r"\bgrowth\b", r"\brevenue\b", r"需求", r"成長", r"營收"),
    "fundamental_reinvestment": (
        r"reinvest",
        r"return(?:s)? on (?:invested )?capital",
        r"\broic\b",
        r"capital return",
        r"再投資",
        r"資本回報",
    ),
    "cash_flow_conversion": (
        r"cash flow",
        r"cash conversion",
        r"free cash",
        r"(?:revenue|sales|earnings|profits?).{0,40}(?:fail|fails|failed|weak|weakens|weakening|struggl\w*).{0,40}(?:cash|moneti[sz])",
        r"(?:turn|turns|turned|turning).{0,20}(?:revenue|sales|earnings|profits?).{0,20}into cash",
        r"(?:revenue|sales|earnings|profits?).{0,20}(?:turn|turns|turned|turning|convert\w*).{0,20}(?:into )?cash",
        r"現金流",
        r"現金轉換",
        r"(?:營收|銷售|獲利).{0,12}(?:無法|未能|難以|轉不成).{0,12}現金",
    ),
    "capital_intensity": (r"capital intens", r"\bcapex\b", r"資本密集", r"資本支出"),
    "capital_structure": (r"capital structure", r"net debt", r"dilution", r"資本結構", r"淨負債", r"稀釋"),
    "multiple_expectations": (r"multiple", r"valuation", r"priced[- ]in", r"估值", r"定價"),
    "estimate_revisions": (r"estimate revision", r"revision breadth", r"consensus revision", r"預估修正", r"共識修正"),
    "reference_class_base_rate": (r"reference class", r"base rate", r"參考類別", r"基準率"),
    "probability_asymmetry": (r"probability", r"payoff", r"asymmetr", r"機率", r"報酬不對稱"),
    "marginal_actor_flow": (r"marginal buyer", r"marginal seller", r"forced actor", r"邊際買方", r"邊際賣方"),
    "positioning_squeeze": (r"short interest", r"short squeeze", r"forced cover", r"positioning", r"軋空", r"部位"),
    "liquidity_feedback": (r"liquidity", r"market depth", r"流動性"),
    "financing_feedback": (r"financing", r"funding access", r"融資"),
    "narrative_attention": (r"narrative", r"attention", r"sentiment", r"敘事", r"關注", r"情緒"),
    "catalyst_path": (r"catalyst", r"event path", r"催化劑", r"事件路徑"),
}
METHOD_COMPLETION = {"Complete", "Partial", "Unavailable"}
CHAIR_DECISIONS = {"Accept", "Conditional", "Reject"}
STANCES = {"Long", "Short", "Avoid"}
CONFIDENCE = {"High", "Medium", "Low"}
ROBUSTNESS = {"Robust", "Conditional", "Fragile"}
PARTICIPATION = {"Eligible", "Conditional", "Stand aside"}
IMPLEMENTATION_READINESS = {"Ready", "Conditional", "Blocked"}
IMPLEMENTATION_ONLY_CLASSES = {"implementation", "portfolio"}
COUNCIL_RUNTIMES = {"collaboration_available", "unavailable"}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
COUNCIL_SCHEMA_VERSION = 2
CURRENT_AUTHORITY_VERSION = 1
AGENT_COUNCIL_SCHEMA_VERSION = 3
AGENT_COUNCIL_AUTHORITY_VERSION = 2
PEI_RECEIPT_SCHEMA_VERSIONS = {2, 3, 4}
PEI_POSTURES = {"PASS", "LIMITED", "BLOCKED"}
PEI_REQUIREMENT_CLASSES = {
    "provider",
    "primary",
    "public",
    "model",
    "portfolio",
    "event",
    "implementation",
    "ambient_context",
}
PEI_REQUIREMENT_STATUSES = {"satisfied", "gap", "not_required"}
PEI_CRITICALITIES = {"hard", "soft"}
DAMODARAN_ARCHETYPE_DRIVERS = {
    "pre_revenue_optionality": {"addressable_market", "success_probability", "funding_need"},
    "high_growth": {"revenue_cagr", "target_operating_margin", "sales_to_capital"},
    "mature": {"normalized_growth", "normalized_operating_margin", "reinvestment_rate"},
    "cyclical": {"midcycle_revenue", "midcycle_margin", "cycle_multiple"},
    "financial": {"return_on_equity", "cost_of_equity", "payout_ratio"},
    "commodity": {"normalized_commodity_price", "unit_cost", "replacement_capex"},
    "distressed": {"survival_probability", "recovery_value", "funding_need"},
}
DAMODARAN_ARCHETYPE_FRAMES = {
    "pre_revenue_optionality": {"probability_weighted_reverse_dcf"},
    "high_growth": {"reverse_dcf"},
    "mature": {"reverse_dcf", "normalized_dcf"},
    "cyclical": {"normalized_earnings"},
    "financial": {"excess_return"},
    "commodity": {"normalized_earnings", "asset_value"},
    "distressed": {"probability_weighted_recovery"},
}
SOROS_FEEDBACK_STEPS = [
    "trend_to_bias",
    "bias_to_actor_action",
    "actor_action_to_price",
    "price_to_fundamentals",
    "fundamentals_to_bias",
]
SOROS_PHASES = {
    "unrecognized",
    "accelerating",
    "test",
    "twilight",
    "reversal",
    "non_reflexive",
}
COMPARISON_OPERATORS = {"<", "<=", ">", ">=", "=="}
DAMODARAN_ARTIFACT_FIELDS = {
    "artifact_type",
    "requested_horizon",
    "proposition_id",
    "company_archetype",
    "archetype_rationale",
    "valuation_frame",
    "anchor_price",
    "currency",
    "price_implied_drivers",
    "owner_case_drivers",
    "story_to_numbers_bridge",
    "fundamental_value_range",
    "least_plausible_implied_driver",
    "requested_horizon_transmission",
    "method_gap",
}
SOROS_ARTIFACT_FIELDS = {
    "artifact_type",
    "requested_horizon",
    "proposition_id",
    "classification",
    "current_trend",
    "prevailing_bias",
    "marginal_actors",
    "feedback_chain",
    "phase",
    "phase_rationale",
    "reversal_trigger",
    "horizon_price_paths",
    "expected_path_return_pct",
    "non_reflexive_tests",
    "method_gap",
}
MAUBOUSSIN_ARTIFACT_FIELDS = {
    "artifact_type",
    "requested_horizon",
    "proposition_id",
    "anchor_price",
    "currency",
    "price_implied_expectations",
    "reference_class",
    "inside_view_updates",
    "probability_payoff_states",
    "posterior_mode",
    "posterior_success_probability_pct",
    "success_state_ids",
    "expected_return_pct",
    "sign_sensitivity",
    "method_gap",
}
METHOD_GAP_FIELDS = {
    "artifact_type",
    "requested_horizon",
    "proposition_id",
    "method_gap",
}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _allowed_string(value: Any, allowed: set[str]) -> bool:
    return _nonempty_string(value) and value in allowed


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _expect_keys(
    value: dict[str, Any], expected: set[str], label: str, errors: list[str]
) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        errors.append(f"{label} is missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{label} has unexpected fields: {', '.join(extra)}")


def _reject_unexpected_keys(
    value: dict[str, Any], allowed: set[str], label: str, errors: list[str]
) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        errors.append(f"{label} has unexpected fields: {', '.join(extra)}")


def _collect_evidence_ids(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence_ids" and _string_list(child):
                result.update(child)
            else:
                result.update(_collect_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_collect_evidence_ids(child))
    return result


def _validate_artifact_evidence(
    value: Any,
    *,
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_label = f"{label}.{key}"
            if key == "evidence_ids":
                if not _string_list(child) or not child:
                    errors.append(f"{child_label} must be a non-empty string list")
                    continue
                outside = sorted(set(child) - allowed)
                if outside:
                    errors.append(
                        f"{label.split('.', 1)[0].capitalize()} method artifact uses evidence outside its sealed packet: "
                        + ", ".join(outside)
                    )
            else:
                _validate_artifact_evidence(
                    child, allowed=allowed, label=child_label, errors=errors
                )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_artifact_evidence(
                child,
                allowed=allowed,
                label=f"{label}[{index}]",
                errors=errors,
            )


def _require_text_fields(
    value: dict[str, Any], fields: tuple[str, ...], label: str, errors: list[str]
) -> None:
    for field in fields:
        if not _nonempty_string(value.get(field)):
            errors.append(f"{label}.{field} must be a non-empty string")


def _parse_time(value: Any, label: str, errors: list[str]) -> datetime | None:
    if not _nonempty_string(value):
        errors.append(f"{label} must be an ISO-8601 timestamp")
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} must be an ISO-8601 timestamp")
        return None
    if result.tzinfo is None:
        errors.append(f"{label} must include a timezone")
        return None
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_sha(value: Any) -> str | None:
    if not _nonempty_string(value):
        return None
    normalized = value.removeprefix("sha256:")
    return normalized if HEX_SHA256.fullmatch(normalized) else None


def _safe_artifact_path(
    artifact_root: Path, value: Any, label: str, errors: list[str]
) -> Path | None:
    if not _nonempty_string(value):
        errors.append(f"{label} must be a non-empty relative path")
        return None
    relative = Path(value)
    if relative.is_absolute():
        errors.append(f"{label} must be relative")
        return None
    root = artifact_root.resolve()
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        errors.append(f"{label} escapes the artifact root")
        return None
    return path


def _load_json(path: Path | None, label: str, errors: list[str]) -> Any | None:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label} not found: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is invalid JSON: {exc}")
    return None


def _descriptor_payload(
    artifact_root: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an artifact descriptor")
        return None, None
    _expect_keys(value, {"path", "sha256"}, label, errors)
    path = _safe_artifact_path(artifact_root, value.get("path"), f"{label}.path", errors)
    expected = value.get("sha256")
    normalized = _normalized_sha(expected)
    if normalized is None:
        errors.append(f"{label}.sha256 must be a lowercase SHA-256 digest")
    elif path is not None and path.is_file() and _sha256(path) != normalized:
        errors.append(f"{label}.sha256 does not match artifact")
    payload = _load_json(path, label, errors)
    if payload is not None and not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        payload = None
    return payload, normalized


def _identity_values(value: dict[str, Any]) -> tuple[Any, Any, Any]:
    identity = value.get("identity")
    if not isinstance(identity, dict):
        identity = value.get("security_identity")
    if not isinstance(identity, dict):
        identity = {}
    return (
        value.get("ticker", identity.get("ticker", identity.get("symbol"))),
        value.get("security_id", identity.get("security_id")),
        value.get("evidence_cutoff", identity.get("evidence_cutoff")),
    )


def _validate_current_artifact_bindings(
    payload: dict[str, Any], artifact_root: Path, errors: list[str]
) -> None:
    bindings = payload.get("artifact_bindings")
    if bindings is None:
        return
    if not isinstance(bindings, dict):
        errors.append("artifact_bindings must be an object when present")
        return
    _expect_keys(
        bindings,
        {
            "authority_version",
            "validator_sha256",
            "preliminary_underwrite",
            "seat_packets",
            "sealed_memos",
            "owner_adjudication",
            "final_model_spec",
            "model_committed_at",
            "fv_freeze_receipt",
            "pm_chair",
        },
        "artifact_bindings",
        errors,
    )
    if bindings.get("authority_version") != CURRENT_AUTHORITY_VERSION:
        errors.append(
            f"artifact_bindings.authority_version must be {CURRENT_AUTHORITY_VERSION}"
        )
    validator_sha = bindings.get("validator_sha256")
    if not _nonempty_string(validator_sha) or not HEX_SHA256.fullmatch(validator_sha):
        errors.append("artifact_bindings.validator_sha256 must be a lowercase SHA-256 digest")
    elif validator_sha != _sha256(Path(__file__).resolve()):
        errors.append("artifact_bindings.validator_sha256 does not match this validator")

    root_identity = (
        payload.get("ticker"),
        payload.get("security_identity", {}).get("security_id"),
        payload.get("evidence_cutoff"),
    )
    underwrite, _ = _descriptor_payload(
        artifact_root,
        bindings.get("preliminary_underwrite"),
        "artifact_bindings.preliminary_underwrite",
        errors,
    )
    if underwrite is not None and _identity_values(underwrite) != root_identity:
        errors.append("preliminary underwrite identity/cutoff must equal Council root")

    packet_refs = bindings.get("seat_packets")
    memo_refs = bindings.get("sealed_memos")
    if not isinstance(packet_refs, dict) or set(packet_refs) != SEATS:
        errors.append("artifact_bindings.seat_packets must contain exactly the three seats")
        packet_refs = {}
    if not isinstance(memo_refs, dict) or set(memo_refs) != SEATS:
        errors.append("artifact_bindings.sealed_memos must contain exactly the three seats")
        memo_refs = {}
    packet_hashes: dict[str, str] = {}
    memo_hashes: dict[str, str] = {}
    root_memos = {
        memo.get("seat"): memo
        for memo in payload.get("first_round", {}).get("memos", [])
        if isinstance(memo, dict) and memo.get("seat") in SEATS
    }
    for seat in sorted(SEATS):
        packet, packet_sha = _descriptor_payload(
            artifact_root,
            packet_refs.get(seat),
            f"artifact_bindings.seat_packets.{seat}",
            errors,
        )
        if packet_sha is not None:
            packet_hashes[seat] = packet_sha
        if packet is not None:
            _expect_keys(
                packet,
                {
                    "schema_version",
                    "ticker",
                    "security_id",
                    "evidence_cutoff",
                    "seat",
                    "candidate_assumptions",
                    "private_partition",
                },
                f"{seat} packet",
                errors,
            )
            if _identity_values(packet) != root_identity or packet.get("seat") != seat:
                errors.append(f"{seat} packet identity/cutoff must equal Council root")
            if underwrite is not None and packet.get("candidate_assumptions") != underwrite.get("candidate_assumptions"):
                errors.append(f"{seat} packet candidate assumptions must equal preliminary underwrite")
            partition = packet.get("private_partition")
            root_partition = payload.get("private_partitions", {}).get(seat)
            if not isinstance(partition, dict) or not isinstance(root_partition, dict) or {
                "allowed_domains": partition.get("allowed_domains"),
                "evidence_ids": partition.get("evidence_ids"),
            } != root_partition:
                errors.append(f"{seat} packet partition must equal Council root partition")

        sealed, memo_sha = _descriptor_payload(
            artifact_root,
            memo_refs.get(seat),
            f"artifact_bindings.sealed_memos.{seat}",
            errors,
        )
        if memo_sha is not None:
            memo_hashes[seat] = memo_sha
        if sealed is not None:
            if sealed.get("seat") != seat:
                errors.append(f"{seat} sealed memo seat is invalid")
            declared_packet_sha = _normalized_sha(sealed.get("packet_sha256"))
            if declared_packet_sha != packet_sha:
                errors.append(f"{seat} sealed memo must bind its exact packet hash")
            if sealed.get("memo") != root_memos.get(seat):
                errors.append(f"{seat} sealed memo content must equal Council root memo")

    final_spec, final_spec_sha = _descriptor_payload(
        artifact_root,
        bindings.get("final_model_spec"),
        "artifact_bindings.final_model_spec",
        errors,
    )
    if final_spec is not None:
        final_identity = _identity_values(final_spec)
        if final_identity[:2] != root_identity[:2]:
            errors.append("final model spec identity must equal Council root")
        final_cutoff = _parse_time(
            final_identity[2], "final_model_spec.evidence_cutoff", errors
        )
        council_cutoff = _parse_time(
            root_identity[2], "Council evidence_cutoff", errors
        )
        if (
            final_cutoff is not None
            and council_cutoff is not None
            and final_cutoff > council_cutoff
        ):
            errors.append("final model spec cutoff cannot follow Council cutoff")
    adjudication, _ = _descriptor_payload(
        artifact_root,
        bindings.get("owner_adjudication"),
        "artifact_bindings.owner_adjudication",
        errors,
    )
    adjudicated_at = None
    if adjudication is not None:
        if _identity_values(adjudication) != root_identity:
            errors.append("owner adjudication identity/cutoff must equal Council root")
        if adjudication.get("packet_hashes") != packet_hashes:
            errors.append("owner adjudication packet_hashes must equal bound packets")
        if adjudication.get("memo_hashes") != memo_hashes:
            errors.append("owner adjudication memo_hashes must equal bound memos")
        if _normalized_sha(adjudication.get("final_model_spec_sha256")) != final_spec_sha:
            errors.append("owner adjudication must bind the final model spec hash")
        adjudicated_at = _parse_time(
            adjudication.get("adjudicated_at"),
            "owner_adjudication.adjudicated_at",
            errors,
        )

    committed_at = _parse_time(
        bindings.get("model_committed_at"),
        "artifact_bindings.model_committed_at",
        errors,
    )
    freeze, freeze_sha = _descriptor_payload(
        artifact_root,
        bindings.get("fv_freeze_receipt"),
        "artifact_bindings.fv_freeze_receipt",
        errors,
    )
    frozen_at = None
    if freeze is not None:
        if _identity_values(freeze) != root_identity:
            errors.append("FV freeze identity/cutoff must equal Council root")
        if _normalized_sha(freeze.get("model_spec_sha256")) != final_spec_sha:
            errors.append("FV freeze must bind the final model spec hash")
        for field in ("model_output_sha256", "independent_audit_sha256"):
            if _normalized_sha(freeze.get(field)) is None:
                errors.append(f"FV freeze {field} must be a lowercase SHA-256 digest")
        frozen_at = _parse_time(freeze.get("frozen_at"), "fv_freeze_receipt.frozen_at", errors)

    chair_receipt, _ = _descriptor_payload(
        artifact_root,
        bindings.get("pm_chair"),
        "artifact_bindings.pm_chair",
        errors,
    )
    if chair_receipt is not None:
        if _identity_values(chair_receipt) != root_identity:
            errors.append("PM Chair receipt identity/cutoff must equal Council root")
        if chair_receipt.get("chair") != payload.get("chair"):
            errors.append("PM Chair receipt content must equal Council root chair")
        if _normalized_sha(chair_receipt.get("model_spec_sha256")) != final_spec_sha:
            errors.append("PM Chair receipt must bind the final model spec hash")
        if _normalized_sha(chair_receipt.get("fv_freeze_receipt_sha256")) != freeze_sha:
            errors.append("PM Chair receipt must bind the FV freeze receipt hash")

    memo_times = [
        value
        for seat, memo in root_memos.items()
        if (value := _parse_time(memo.get("sealed_at"), f"{seat} memo sealed_at", errors))
        is not None
    ]
    latest_memo = max(memo_times, default=None)
    chair_started = _parse_time(
        payload.get("chair", {}).get("started_at"), "chair.started_at", errors
    )
    timeline = [latest_memo, adjudicated_at, committed_at, frozen_at, chair_started]
    if all(value is not None for value in timeline) and timeline != sorted(timeline):
        errors.append(
            "current Council timeline must be memos <= adjudication <= model commit <= FV freeze <= Chair"
        )


def _contains_forbidden_agent_output(value: Any) -> str | None:
    forbidden = {
        "action",
        "final_model",
        "gross_expected_return_pct",
        "implementation_readiness",
        "owner_fair_value",
        "participation",
        "position_size",
        "research_stance",
        "target_price",
        "trade_instruction",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in forbidden:
                return key
            found = _contains_forbidden_agent_output(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_forbidden_agent_output(child)
            if found:
                return found
    return None


def _validate_agent_council_v3(
    payload: dict[str, Any], *, artifact_dir: Path
) -> list[str]:
    """Validate only durable mechanics; investment judgment stays with PEI."""

    errors: list[str] = []
    _expect_keys(
        payload,
        {
            "schema_version",
            "council_runtime",
            "ticker",
            "security_identity",
            "current_price",
            "decision_horizon",
            "evidence_cutoff",
            "pei_input_receipt",
            "research_admission",
            "artifact_bindings",
        },
        "root",
        errors,
    )
    if payload.get("council_runtime") != "collaboration_available":
        errors.append("current formal Council requires collaboration_available")
    if not _nonempty_string(payload.get("ticker")):
        errors.append("ticker must be a non-empty string")
    if not _nonempty_string(payload.get("decision_horizon")):
        errors.append("decision_horizon must be a non-empty string")
    cutoff = _parse_time(payload.get("evidence_cutoff"), "evidence_cutoff", errors)

    identity = payload.get("security_identity")
    if not isinstance(identity, dict):
        errors.append("security_identity must be an object")
        identity = {}
    else:
        _expect_keys(
            identity,
            {"symbol", "issuer", "listing", "security_id", "source_id"},
            "security_identity",
            errors,
        )
        for field in ("symbol", "issuer", "listing", "security_id", "source_id"):
            if not _nonempty_string(identity.get(field)):
                errors.append(f"security_identity.{field} must be a non-empty string")
        if identity.get("symbol") != payload.get("ticker"):
            errors.append("security_identity.symbol must equal ticker")

    price = payload.get("current_price")
    if not isinstance(price, dict):
        errors.append("current_price must be an object")
        price = {}
    else:
        _expect_keys(
            price, {"value", "currency", "as_of", "source_id"}, "current_price", errors
        )
    if not _number(price.get("value")) or price.get("value", 0) <= 0:
        errors.append("current_price.value must be positive finite numeric")
    for field in ("currency", "source_id"):
        if not _nonempty_string(price.get(field)):
            errors.append(f"current_price.{field} must be a non-empty string")
    price_as_of = _parse_time(price.get("as_of"), "current_price.as_of", errors)
    if cutoff is not None and price_as_of is not None and price_as_of > cutoff:
        errors.append("current_price.as_of cannot be after evidence_cutoff")
    if payload.get("research_admission") not in {"PASS", "LIMITED"}:
        errors.append("research_admission must be PASS or LIMITED")

    root_identity = (
        payload.get("ticker"),
        identity.get("security_id"),
        payload.get("evidence_cutoff"),
    )
    receipt, _ = _descriptor_payload(
        artifact_dir, payload.get("pei_input_receipt"), "pei_input_receipt", errors
    )
    accepted_evidence: set[str] = set()
    accepted_evidence_natures: dict[str, str] = {}
    if receipt is not None:
        pei_errors, pei_posture = _validate_pei_admission_receipt(receipt)
        errors.extend(f"pei_input_receipt: {error}" for error in pei_errors)
        if payload.get("research_admission") != pei_posture:
            errors.append("research_admission must equal the PEI receipt posture")
        if _identity_values(receipt) != root_identity:
            errors.append("PEI input receipt identity/cutoff must equal Council root")
        registry = receipt.get("evidence_registry")
        if not isinstance(registry, list):
            errors.append("PEI input receipt evidence_registry must be a list")
        else:
            accepted_evidence = {
                item.get("id")
                for item in registry
                if isinstance(item, dict) and _nonempty_string(item.get("id"))
            }
            for index, item in enumerate(registry):
                if not isinstance(item, dict) or not _nonempty_string(item.get("id")):
                    continue
                nature = item.get("evidence_nature")
                if not _nonempty_string(nature):
                    errors.append(
                        f"pei_input_receipt.evidence_registry[{index}].evidence_nature must be non-empty"
                    )
                else:
                    accepted_evidence_natures[item["id"]] = nature

    bindings = payload.get("artifact_bindings")
    if not isinstance(bindings, dict):
        return errors + ["artifact_bindings must be an object"]
    _expect_keys(
        bindings,
        {
            "authority_version",
            "validator_sha256",
            "preliminary_underwrite",
            "seat_packets",
            "sealed_memos",
            "owner_adjudication",
            "final_model_spec",
            "model_committed_at",
            "fv_freeze_receipt",
        },
        "artifact_bindings",
        errors,
    )
    if bindings.get("authority_version") != AGENT_COUNCIL_AUTHORITY_VERSION:
        errors.append(
            f"artifact_bindings.authority_version must be {AGENT_COUNCIL_AUTHORITY_VERSION}"
        )
    if _normalized_sha(bindings.get("validator_sha256")) != _sha256(
        Path(__file__).resolve()
    ):
        errors.append("artifact_bindings.validator_sha256 does not match this validator")

    underwrite, _ = _descriptor_payload(
        artifact_dir,
        bindings.get("preliminary_underwrite"),
        "artifact_bindings.preliminary_underwrite",
        errors,
    )
    assumptions: list[dict[str, Any]] = []
    assumption_ids: set[str] = set()
    assumptions_by_id: dict[str, dict[str, Any]] = {}
    challenge_signal_evidence_ids: set[str] = set()
    if underwrite is not None:
        if _identity_values(underwrite) != root_identity:
            errors.append("preliminary underwrite identity/cutoff must equal Council root")
        candidate = underwrite.get("candidate_assumptions")
        if not isinstance(candidate, list) or not candidate:
            errors.append("preliminary underwrite candidate_assumptions must be non-empty")
        else:
            assumptions = [row for row in candidate if isinstance(row, dict)]
            assumption_ids = {
                row.get("assumption_id")
                for row in assumptions
                if _nonempty_string(row.get("assumption_id"))
            }
            assumptions_by_id = {
                row["assumption_id"]: row
                for row in assumptions
                if _nonempty_string(row.get("assumption_id"))
            }
            if len(assumptions) != len(candidate) or len(assumption_ids) != len(candidate):
                errors.append("preliminary assumption IDs must be unique non-empty strings")
            for index, assumption in enumerate(assumptions):
                label = f"preliminary assumption[{index}]"
                evidence_ids = assumption.get("evidence_ids")
                if not _string_list(evidence_ids) or not set(evidence_ids) <= accepted_evidence:
                    errors.append(
                        f"{label}.evidence_ids exceed accepted PEI evidence"
                    )
                parent_evidence_ids = (
                    set(evidence_ids) if _string_list(evidence_ids) else set()
                )
                if not _number(assumption.get("proposed_base")):
                    errors.append(f"{label}.proposed_base must be numeric")
                proposed_range = assumption.get("proposed_range")
                if (
                    not isinstance(proposed_range, list)
                    or len(proposed_range) != 2
                    or not all(_number(item) for item in proposed_range)
                    or proposed_range[0] > proposed_range[1]
                ):
                    errors.append(f"{label}.proposed_range must be an ordered numeric pair")
                for field in (
                    "period",
                    "unit",
                    "rationale",
                    "rejected_alternative",
                    "flip_condition",
                ):
                    if not _nonempty_string(assumption.get(field)):
                        errors.append(f"{label}.{field} must be non-empty")
                signals = assumption.get("challenge_signal_dispositions")
                if not isinstance(signals, list):
                    errors.append(
                        f"{label}.challenge_signal_dispositions must be a list"
                    )
                    continue
                signal_ids: set[str] = set()
                for signal_index, signal in enumerate(signals):
                    signal_label = f"{label} challenge signal[{signal_index}]"
                    if not isinstance(signal, dict):
                        errors.append(f"{signal_label} must be an object")
                        continue
                    _expect_keys(
                        signal,
                        {
                            "signal_id",
                            "source_kind",
                            "source_id",
                            "evidence_nature",
                            "finding",
                            "disposition",
                            "evidence_ids",
                            "reason",
                            "flip_condition",
                        },
                        signal_label,
                        errors,
                    )
                    signal_id = signal.get("signal_id")
                    if not _nonempty_string(signal_id) or signal_id in signal_ids:
                        errors.append(f"{signal_label}.signal_id must be unique and non-empty")
                    elif isinstance(signal_id, str):
                        signal_ids.add(signal_id)
                    source_kind = signal.get("source_kind")
                    if source_kind not in {"ask_sa", "analysis", "transcript"}:
                        errors.append(
                            f"{signal_label}.source_kind must be ask_sa, analysis, or transcript"
                        )
                    for field in (
                        "source_id",
                        "evidence_nature",
                        "finding",
                        "reason",
                        "flip_condition",
                    ):
                        if not _nonempty_string(signal.get(field)):
                            errors.append(f"{signal_label}.{field} must be non-empty")
                    if signal.get("disposition") not in {
                        "adopt",
                        "reject",
                        "not_material",
                    }:
                        errors.append(
                            f"{signal_label}.disposition must be adopt, reject, or not_material"
                        )
                    signal_evidence = signal.get("evidence_ids")
                    if not _string_list(signal_evidence) or not signal_evidence:
                        errors.append(f"{signal_label}.evidence_ids must be non-empty")
                        signal_evidence_ids: set[str] = set()
                    else:
                        signal_evidence_ids = set(signal_evidence)
                    if signal_evidence_ids and (
                        not signal_evidence_ids <= accepted_evidence
                        or not signal_evidence_ids <= parent_evidence_ids
                    ):
                        errors.append(
                            f"{signal_label}.evidence_ids must be accepted evidence on the parent assumption"
                        )
                    elif signal_evidence_ids:
                        challenge_signal_evidence_ids.update(signal_evidence_ids)
                    if source_kind == "ask_sa":
                        if signal.get("evidence_nature") != "provider_synthesis":
                            errors.append(
                                f"{signal_label}.evidence_nature must be provider_synthesis for Ask SA"
                            )
                        if signal.get("source_id") in signal_evidence_ids:
                            errors.append(
                                f"{signal_label} cannot use Ask SA provider synthesis as its own supporting evidence"
                            )
                        if signal_evidence_ids and all(
                            accepted_evidence_natures.get(evidence_id)
                            == "provider_synthesis"
                            for evidence_id in signal_evidence_ids
                        ):
                            errors.append(
                                f"{signal_label} requires non-synthesis supporting evidence"
                            )
        dispositions = underwrite.get("assumption_family_dispositions")
        disposition_families: set[str] = set()
        disposition_assumptions: set[str] = set()
        if not isinstance(dispositions, list):
            dispositions = []
        for index, disposition in enumerate(dispositions):
            label = f"preliminary assumption family disposition[{index}]"
            if not isinstance(disposition, dict):
                errors.append(f"{label} must be an object")
                continue
            _expect_keys(
                disposition,
                {"family", "status", "assumption_ids", "reason"},
                label,
                errors,
            )
            family = disposition.get("family")
            if family in disposition_families or family not in ASSUMPTION_FAMILIES:
                errors.append(f"{label}.family must be a unique recognized family")
            if isinstance(family, str):
                disposition_families.add(family)
            status = disposition.get("status")
            family_assumptions = disposition.get("assumption_ids")
            if status == "covered":
                if not _string_list(family_assumptions):
                    errors.append(f"{label}.assumption_ids must be non-empty when covered")
                else:
                    duplicate_ids = disposition_assumptions & set(family_assumptions)
                    if duplicate_ids or not set(family_assumptions) <= assumption_ids:
                        errors.append(f"{label}.assumption_ids must map once to candidates")
                    disposition_assumptions.update(family_assumptions)
            elif status == "not_material":
                if family_assumptions != []:
                    errors.append(f"{label}.assumption_ids must be empty when not_material")
            else:
                errors.append(f"{label}.status must be covered or not_material")
            if not _nonempty_string(disposition.get("reason")):
                errors.append(f"{label}.reason must be non-empty")
        if disposition_families != ASSUMPTION_FAMILIES:
            errors.append(
                "preliminary underwrite must disposition exactly all six assumption families"
            )
        if disposition_assumptions != assumption_ids:
            errors.append(
                "preliminary underwrite must assign every candidate assumption to one family"
            )

    packet_refs = bindings.get("seat_packets")
    memo_refs = bindings.get("sealed_memos")
    if not isinstance(packet_refs, dict) or set(packet_refs) != SEATS:
        errors.append("artifact_bindings.seat_packets must contain exactly the three seats")
        packet_refs = {}
    if not isinstance(memo_refs, dict) or set(memo_refs) != SEATS:
        errors.append("artifact_bindings.sealed_memos must contain exactly the three seats")
        memo_refs = {}

    packet_hashes: dict[str, str] = {}
    memo_hashes: dict[str, str] = {}
    memo_times: list[datetime] = []
    for seat in sorted(SEATS):
        packet, packet_sha = _descriptor_payload(
            artifact_dir,
            packet_refs.get(seat),
            f"artifact_bindings.seat_packets.{seat}",
            errors,
        )
        if packet_sha:
            packet_hashes[seat] = packet_sha
        if packet is not None:
            _expect_keys(
                packet,
                {
                    "schema_version",
                    "ticker",
                    "security_id",
                    "evidence_cutoff",
                    "seat",
                    "candidate_assumptions",
                    "evidence_ids",
                    "instructions",
                },
                f"{seat} packet",
                errors,
            )
            if (
                packet.get("schema_version") != "council-premodel-seat-packet-v2"
                or _identity_values(packet) != root_identity
                or packet.get("seat") != seat
            ):
                errors.append(f"{seat} packet identity/schema must equal Council root")
            if assumptions and packet.get("candidate_assumptions") != assumptions:
                errors.append(f"{seat} packet candidate assumptions must equal preliminary underwrite")
            evidence_ids = packet.get("evidence_ids")
            if not _string_list(evidence_ids):
                errors.append(f"{seat} packet evidence_ids must be a string list")
            elif not set(evidence_ids) <= accepted_evidence:
                errors.append(f"{seat} packet evidence_ids exceed accepted PEI evidence")
            elif not challenge_signal_evidence_ids <= set(evidence_ids):
                errors.append(
                    f"{seat} packet evidence_ids omit preliminary challenge-signal evidence"
                )
            if not _nonempty_string(packet.get("instructions")):
                errors.append(f"{seat} packet instructions must be non-empty")
            else:
                normalized_instructions = re.sub(
                    r"[_\s]+", "-", packet["instructions"].casefold()
                )
                if not all(
                    term in normalized_instructions
                    for term in (
                        "too-conservative",
                        "too-aggressive",
                        "uncertain",
                        "market-right",
                    )
                ):
                    errors.append(
                        f"{seat} packet instructions must test conservative, aggressive, uncertain, and market-right cases"
                    )
            leaked = _contains_forbidden_agent_output(packet)
            if leaked:
                errors.append(f"{seat} packet leaks forbidden field {leaked}")

        memo, memo_sha = _descriptor_payload(
            artifact_dir,
            memo_refs.get(seat),
            f"artifact_bindings.sealed_memos.{seat}",
            errors,
        )
        if memo_sha:
            memo_hashes[seat] = memo_sha
        if memo is None:
            continue
        _expect_keys(
            memo,
            {
                "schema_version",
                "seat",
                "sealed_at",
                "packet_sha256",
                "browsed",
                "added_evidence_ids",
                "summary",
                "challenges",
                "strongest_countercase",
                "limitations",
            },
            f"{seat} memo",
            errors,
        )
        if (
            memo.get("schema_version") != "council-sealed-memo-v2"
            or memo.get("seat") != seat
            or _normalized_sha(memo.get("packet_sha256")) != packet_sha
        ):
            errors.append(f"{seat} memo identity/schema or packet hash is invalid")
        if memo.get("browsed") is not False or memo.get("added_evidence_ids") != []:
            errors.append(f"{seat} memo must be evidence-closed")
        if not _nonempty_string(memo.get("summary")):
            errors.append(f"{seat} memo summary must be non-empty")
        if not _nonempty_string(memo.get("strongest_countercase")):
            errors.append(f"{seat} memo strongest_countercase must be non-empty")
        if not isinstance(memo.get("limitations"), list) or any(
            not _nonempty_string(item) for item in memo.get("limitations", [])
        ):
            errors.append(f"{seat} memo limitations must be a string list")
        sealed_at = _parse_time(memo.get("sealed_at"), f"{seat} memo sealed_at", errors)
        if sealed_at:
            memo_times.append(sealed_at)
        challenges = memo.get("challenges")
        if not isinstance(challenges, list):
            errors.append(f"{seat} memo challenges must be a list")
            challenges = []
        for index, challenge in enumerate(challenges):
            label = f"{seat} memo challenges[{index}]"
            if not isinstance(challenge, dict):
                errors.append(f"{label} must be an object")
                continue
            _expect_keys(
                challenge,
                {
                    "assumption_id",
                    "assessment",
                    "proposed_base",
                    "proposed_range",
                    "evidence_ids",
                    "reasoning",
                    "decision_impact",
                    "falsifier",
                },
                label,
                errors,
            )
            if challenge.get("assumption_id") not in assumption_ids:
                errors.append(f"{label}.assumption_id is not in preliminary underwrite")
            if challenge.get("assessment") not in {
                "supported",
                "too_conservative",
                "too_aggressive",
                "uncertain",
            }:
                errors.append(f"{label}.assessment is invalid")
            proposed_base = challenge.get("proposed_base")
            if proposed_base is not None and not _number(proposed_base):
                errors.append(f"{label}.proposed_base must be numeric or null")
            proposed_range = challenge.get("proposed_range")
            if proposed_range is not None and (
                not isinstance(proposed_range, list)
                or len(proposed_range) != 2
                or not all(_number(item) for item in proposed_range)
                or proposed_range[0] > proposed_range[1]
            ):
                errors.append(f"{label}.proposed_range must be an ordered numeric pair or null")
            challenge_evidence = challenge.get("evidence_ids")
            if not _string_list(challenge_evidence) or not set(challenge_evidence) <= accepted_evidence:
                errors.append(f"{label}.evidence_ids exceed accepted PEI evidence")
            for field in ("reasoning", "decision_impact", "falsifier"):
                if not _nonempty_string(challenge.get(field)):
                    errors.append(f"{label}.{field} must be non-empty")
        leaked = _contains_forbidden_agent_output(memo)
        if leaked:
            errors.append(f"{seat} memo leaks forbidden field {leaked}")

    final_spec, final_spec_sha = _descriptor_payload(
        artifact_dir,
        bindings.get("final_model_spec"),
        "artifact_bindings.final_model_spec",
        errors,
    )
    final_assumption_ids: set[str] = set()
    if final_spec is not None and _identity_values(final_spec)[:2] != root_identity[:2]:
        errors.append("final model spec identity must equal Council root")
    if final_spec is not None:
        assumption_values = final_spec.get("assumption_ids")
        if (
            not _string_list(assumption_values)
            or not assumption_values
            or len(set(assumption_values)) != len(assumption_values)
        ):
            errors.append(
                "final model spec assumption_ids must be a unique non-empty string list"
            )
        else:
            final_assumption_ids = set(assumption_values)

    adjudication, _ = _descriptor_payload(
        artifact_dir,
        bindings.get("owner_adjudication"),
        "artifact_bindings.owner_adjudication",
        errors,
    )
    adjudicated_at = None
    if adjudication is not None:
        _expect_keys(
            adjudication,
            {
                "schema_version",
                "ticker",
                "security_id",
                "evidence_cutoff",
                "adjudicated_at",
                "packet_hashes",
                "memo_hashes",
                "decisions",
                "final_model_spec_sha256",
            },
            "owner adjudication",
            errors,
        )
        if (
            adjudication.get("schema_version") != "pei-council-adjudication-v2"
            or _identity_values(adjudication) != root_identity
        ):
            errors.append("owner adjudication identity/schema must equal Council root")
        if adjudication.get("packet_hashes") != packet_hashes:
            errors.append("owner adjudication packet_hashes must equal bound packets")
        if adjudication.get("memo_hashes") != memo_hashes:
            errors.append("owner adjudication memo_hashes must equal bound memos")
        if _normalized_sha(adjudication.get("final_model_spec_sha256")) != final_spec_sha:
            errors.append("owner adjudication must bind the final model spec hash")
        decisions = adjudication.get("decisions")
        if not isinstance(decisions, list):
            errors.append("owner adjudication decisions must be a list")
            decisions = []
        decision_ids: set[str] = set()
        adjudicated_model_inputs: set[str] = set()
        for index, decision in enumerate(decisions):
            label = f"owner adjudication decisions[{index}]"
            if not isinstance(decision, dict):
                errors.append(f"{label} must be an object")
                continue
            _expect_keys(
                decision,
                {
                    "assumption_id",
                    "prior_base",
                    "prior_range",
                    "final_base",
                    "final_range",
                    "decision",
                    "council_sources",
                    "evidence_ids",
                    "reason",
                    "model_input_ids",
                },
                label,
                errors,
            )
            assumption_id = decision.get("assumption_id")
            if assumption_id in decision_ids or assumption_id not in assumption_ids:
                errors.append(f"{label}.assumption_id must map once to the preliminary underwrite")
            if _nonempty_string(assumption_id):
                decision_ids.add(assumption_id)
            preliminary = assumptions_by_id.get(assumption_id, {})
            prior_base = decision.get("prior_base")
            if not _number(prior_base):
                errors.append(f"{label}.prior_base must be numeric")
            elif prior_base != preliminary.get("proposed_base"):
                errors.append(f"{label}.prior_base must equal the preliminary Base")
            prior_range = decision.get("prior_range")
            if (
                not isinstance(prior_range, list)
                or len(prior_range) != 2
                or not all(_number(item) for item in prior_range)
                or prior_range[0] > prior_range[1]
            ):
                errors.append(f"{label}.prior_range must be an ordered numeric pair")
            elif prior_range != preliminary.get("proposed_range"):
                errors.append(f"{label}.prior_range must equal the preliminary range")
            final_base = decision.get("final_base")
            if not _number(final_base):
                errors.append(f"{label}.final_base must be numeric")
            final_range = decision.get("final_range")
            if (
                not isinstance(final_range, list)
                or len(final_range) != 2
                or not all(_number(item) for item in final_range)
                or final_range[0] > final_range[1]
            ):
                errors.append(f"{label}.final_range must be an ordered numeric pair")
            elif _number(final_base) and not final_range[0] <= final_base <= final_range[1]:
                errors.append(f"{label}.final_base must fall within final_range")
            if decision.get("decision") not in {"accept", "conditional", "reject"}:
                errors.append(f"{label}.decision is invalid")
            if not isinstance(decision.get("council_sources"), list) or not set(
                decision.get("council_sources", [])
            ) <= SEATS:
                errors.append(f"{label}.council_sources are invalid")
            if not _string_list(decision.get("evidence_ids")) or not set(
                decision.get("evidence_ids", [])
            ) <= accepted_evidence:
                errors.append(f"{label}.evidence_ids exceed accepted PEI evidence")
            if not _nonempty_string(decision.get("reason")):
                errors.append(f"{label}.reason must be non-empty")
            model_input_ids = decision.get("model_input_ids")
            if (
                not _string_list(model_input_ids)
                or not model_input_ids
                or len(set(model_input_ids)) != len(model_input_ids)
            ):
                errors.append(
                    f"{label}.model_input_ids must be a unique non-empty string list"
                )
            else:
                duplicate_inputs = adjudicated_model_inputs & set(model_input_ids)
                if duplicate_inputs:
                    errors.append(
                        "owner adjudication model_input_ids must have one owner: "
                        + ", ".join(sorted(duplicate_inputs))
                    )
                adjudicated_model_inputs.update(model_input_ids)
        if decision_ids != assumption_ids:
            errors.append("owner adjudication must decide every preliminary assumption once")
        missing_model_inputs = final_assumption_ids - adjudicated_model_inputs
        if missing_model_inputs:
            errors.append(
                "owner adjudication model_input_ids do not cover final model assumption_ids: "
                + ", ".join(sorted(missing_model_inputs))
            )
        unexpected_model_inputs = adjudicated_model_inputs - final_assumption_ids
        if unexpected_model_inputs:
            errors.append(
                "owner adjudication model_input_ids are not in final model assumption_ids: "
                + ", ".join(sorted(unexpected_model_inputs))
            )
        adjudicated_at = _parse_time(
            adjudication.get("adjudicated_at"), "owner_adjudication.adjudicated_at", errors
        )

    committed_at = _parse_time(
        bindings.get("model_committed_at"),
        "artifact_bindings.model_committed_at",
        errors,
    )
    freeze, _ = _descriptor_payload(
        artifact_dir,
        bindings.get("fv_freeze_receipt"),
        "artifact_bindings.fv_freeze_receipt",
        errors,
    )
    frozen_at = None
    if freeze is not None:
        if _identity_values(freeze) != root_identity:
            errors.append("FV freeze identity/cutoff must equal Council root")
        if _normalized_sha(freeze.get("model_spec_sha256")) != final_spec_sha:
            errors.append("FV freeze must bind the final model spec hash")
        for field in ("model_output_sha256", "independent_audit_sha256"):
            if _normalized_sha(freeze.get(field)) is None:
                errors.append(f"FV freeze {field} must be a lowercase SHA-256 digest")
        frozen_at = _parse_time(
            freeze.get("frozen_at"), "fv_freeze_receipt.frozen_at", errors
        )
    latest_memo = max(memo_times, default=None)
    timeline = [latest_memo, adjudicated_at, committed_at, frozen_at]
    if all(value is not None for value in timeline) and timeline != sorted(timeline):
        errors.append(
            "current Council timeline must be memos <= adjudication <= model commit <= FV freeze"
        )
    return errors


def _validate_pei_admission_receipt(payload: Any) -> tuple[list[str], str | None]:
    """Validate only the public Council-admission seam of a PEI receipt.

    Detailed provider, public-source, model, and plugin-contract validation stays
    upstream with iysl-equity-data. Council independently reopens the sealed
    receipt, checks identity/hash/cutoff at its own boundary, and derives the
    posture and evidence allowlists it needs for admission.
    """

    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["root must be an object"], None
    if payload.get("schema_version") not in PEI_RECEIPT_SCHEMA_VERSIONS:
        errors.append(
            "schema_version must be a supported PEI receipt version: "
            + ", ".join(str(version) for version in sorted(PEI_RECEIPT_SCHEMA_VERSIONS))
        )
    if not _nonempty_string(payload.get("ticker")):
        errors.append("ticker must be a non-empty string")
    if not isinstance(payload.get("security_identity"), dict):
        errors.append("security_identity must be an object")
    _parse_time(payload.get("evidence_cutoff"), "evidence_cutoff", errors)

    registry = payload.get("evidence_registry")
    if not isinstance(registry, list):
        errors.append("evidence_registry must be a list")
        registry = []
    evidence_ids: set[str] = set()
    for index, evidence in enumerate(registry):
        prefix = f"evidence_registry[{index}]"
        if not isinstance(evidence, dict):
            errors.append(f"{prefix} must be an object")
            continue
        evidence_id = evidence.get("id")
        if not _nonempty_string(evidence_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif evidence_id in evidence_ids:
            errors.append(f"duplicate evidence_registry id: {evidence_id}")
        else:
            evidence_ids.add(evidence_id)

    requirements = payload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty list")
        requirements = []
    requirement_ids: set[str] = set()
    has_hard_gap = False
    has_soft_gap = False
    for index, requirement in enumerate(requirements):
        prefix = f"requirements[{index}]"
        if not isinstance(requirement, dict):
            errors.append(f"{prefix} must be an object")
            continue
        requirement_id = requirement.get("id")
        if not _nonempty_string(requirement_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif requirement_id in requirement_ids:
            errors.append(f"duplicate requirement id: {requirement_id}")
        else:
            requirement_ids.add(requirement_id)
        requirement_class = requirement.get("requirement_class")
        if not _allowed_string(requirement_class, PEI_REQUIREMENT_CLASSES):
            errors.append(f"{prefix}.requirement_class is invalid")
        criticality = requirement.get("criticality")
        if not _allowed_string(criticality, PEI_CRITICALITIES):
            errors.append(f"{prefix}.criticality must be hard or soft")
        status = requirement.get("status")
        if not _allowed_string(status, PEI_REQUIREMENT_STATUSES):
            errors.append(f"{prefix}.status is invalid")
        refs = requirement.get("evidence_ids")
        if not _string_list(refs):
            errors.append(f"{prefix}.evidence_ids must be a string list")
            refs = []
        unknown = sorted(set(refs) - evidence_ids)
        if unknown:
            errors.append(f"{prefix} references unknown evidence: {', '.join(unknown)}")
        if status == "satisfied" and not refs:
            errors.append(f"{prefix}.satisfied requires evidence_ids")
        if status in {"gap", "not_required"} and refs:
            errors.append(f"{prefix}.{status} cannot contain evidence_ids")
        if status == "gap":
            if not _nonempty_string(requirement.get("gap_reason")):
                errors.append(f"{prefix}.gap_reason must explain the gap")
            if criticality == "hard":
                has_hard_gap = True
            else:
                has_soft_gap = True

    posture = "BLOCKED" if has_hard_gap else "LIMITED" if has_soft_gap else "PASS"
    if not _allowed_string(payload.get("output_posture"), PEI_POSTURES):
        errors.append("output_posture must be PASS, LIMITED, or BLOCKED")
    elif payload.get("output_posture") != posture:
        errors.append(f"output_posture must equal derived posture {posture}")
    return errors, posture


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _derive_mechanism_tags(mechanism: str) -> set[str]:
    normalized = _normalized(mechanism)
    return {
        tag
        for tag, patterns in MECHANISM_PATTERNS.items()
        if any(re.search(pattern, normalized) for pattern in patterns)
    }


def _find_forbidden_key(value: Any, *, path: str = "common_factual_spine") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in COMMON_FORBIDDEN_FIELDS:
                return f"{path} contains sealed field: {key}"
            found = _find_forbidden_key(child, path=f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden_key(child, path=f"{path}[{index}]")
            if found:
                return found
    return None


def _find_leaked_sealed_input(
    value: Any,
    *,
    path: str = "",
) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in SEALED_INPUTS:
                in_declaration = path == "sealed_inputs"
                in_allowed_output = child_path in SEALED_OUTPUT_PATHS
                if not in_declaration and not in_allowed_output:
                    return f"sealed input leaked outside its declaration: {child_path}"
            found = _find_leaked_sealed_input(child, path=child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_leaked_sealed_input(child, path=f"{path}[{index}]")
            if found:
                return found
    return None


def _validate_scenario_roles(
    rows: list[Any],
    *,
    label: str,
    payoff_field: str,
    errors: list[str],
) -> None:
    payoffs: dict[str, list[float]] = {role: [] for role in SCENARIO_ROLES}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        role = row.get("scenario_role")
        if not _allowed_string(role, SCENARIO_ROLES):
            errors.append(f"{label}[{index}].scenario_role is invalid")
            continue
        payoff = row.get(payoff_field)
        if _number(payoff):
            payoffs[role].append(payoff)
    missing = sorted(role for role, values in payoffs.items() if not values)
    if rows and missing:
        errors.append(
            f"{label} must include downside, base, and upside roles; missing: "
            + ", ".join(missing)
        )
        return
    if rows and (
        max(payoffs["downside"]) > min(payoffs["base"])
        or max(payoffs["base"]) > min(payoffs["upside"])
    ):
        errors.append(
            f"{label} scenario roles must be ordered downside <= base <= upside"
        )


def _convergence(
    contributions: dict[str, dict[str, Any]]
) -> tuple[bool, set[str]]:
    implicated: set[str] = set()
    for field in CONTRIBUTION_FIELDS:
        values: dict[str, list[str]] = {}
        for seat, contribution in contributions.items():
            value = contribution.get(field)
            if _nonempty_string(value):
                values.setdefault(_normalized(value), []).append(seat)
        for seats in values.values():
            if len(seats) > 1:
                implicated.update(seats)
    seats = sorted(contributions)
    for index, left_seat in enumerate(seats):
        left_tags = set(contributions[left_seat].get("mechanism_tags") or [])
        for right_seat in seats[index + 1 :]:
            right_tags = set(contributions[right_seat].get("mechanism_tags") or [])
            if left_tags & right_tags:
                implicated.update({left_seat, right_seat})
    return bool(implicated), implicated


def _validate_contribution(
    contribution: Any, prefix: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(contribution, dict):
        errors.append(f"{prefix} must be an object")
        return {}
    _expect_keys(
        contribution,
        CONTRIBUTION_TEXT_FIELDS | {"primary_mechanism_tag", "mechanism_tags"},
        prefix,
        errors,
    )
    for field in CONTRIBUTION_TEXT_FIELDS:
        if not _nonempty_string(contribution.get(field)):
            errors.append(f"{prefix}.{field} must be a non-empty string")
    if not _allowed_string(
        contribution.get("primary_mechanism_tag"), MECHANISM_TAGS
    ):
        errors.append(
            f"{prefix}.primary_mechanism_tag must use the canonical mechanism taxonomy"
        )
    mechanism_tags = contribution.get("mechanism_tags")
    if (
        not _string_list(mechanism_tags)
        or not mechanism_tags
        or len(set(mechanism_tags)) != len(mechanism_tags)
        or not set(mechanism_tags) <= MECHANISM_TAGS
    ):
        errors.append(
            f"{prefix}.mechanism_tags must be a unique non-empty canonical tag list"
        )
        mechanism_tags = []
    derived_tags = _derive_mechanism_tags(str(contribution.get("causal_mechanism") or ""))
    if set(mechanism_tags) != derived_tags:
        errors.append(
            f"{prefix}.mechanism_tags must equal validator-derived semantic tags: "
            + ", ".join(sorted(derived_tags))
        )
    if not _nonempty_string(contribution.get("primary_mechanism_tag")) or (
        contribution.get("primary_mechanism_tag") not in set(mechanism_tags)
    ):
        errors.append(
            f"{prefix}.primary_mechanism_tag must be included in mechanism_tags"
        )
    return contribution


def _driver_table(
    value: Any,
    *,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty list")
        return {}
    result: dict[str, dict[str, Any]] = {}
    expected = {"id", "value", "unit", "evidence_ids"}
    for index, row in enumerate(value):
        prefix = f"{label}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(row, expected, prefix, errors)
        driver_id = row.get("id")
        if not _nonempty_string(driver_id) or driver_id in result:
            errors.append(f"{prefix}.id must be non-empty and unique")
            continue
        if not _number(row.get("value")):
            errors.append(f"{prefix}.value must be finite numeric")
        if not _nonempty_string(row.get("unit")):
            errors.append(f"{prefix}.unit must be non-empty")
        result[driver_id] = row
    return result


def _validate_damodaran_artifact(
    artifact: Any,
    *,
    completion: str,
    price: dict[str, Any],
    horizon: Any,
    allowed_evidence: set[str],
    errors: list[str],
) -> None:
    if not isinstance(artifact, dict):
        if completion == "Complete":
            errors.append(
                "damodaran Complete requires its named structured method artifact"
            )
        else:
            errors.append(
                f"damodaran {completion} requires a structured gap artifact"
            )
        return
    if completion == "Partial" and not set(artifact) <= METHOD_GAP_FIELDS:
        errors.append("Damodaran Partial must use only a qualitative gap artifact")
    gap_only = completion != "Complete"
    allowed_fields = METHOD_GAP_FIELDS if gap_only else DAMODARAN_ARTIFACT_FIELDS
    _reject_unexpected_keys(
        artifact, allowed_fields, "Damodaran method artifact", errors
    )
    if artifact.get("artifact_type") != "damodaran_reverse_valuation_v1":
        errors.append("Damodaran method artifact_type is invalid")
    if artifact.get("requested_horizon") != horizon:
        errors.append("Damodaran requested_horizon must equal decision_horizon")
    if not _nonempty_string(artifact.get("proposition_id")):
        errors.append("Damodaran proposition_id must be a non-empty string")
    _validate_artifact_evidence(
        artifact, allowed=allowed_evidence, label="Damodaran", errors=errors
    )
    if gap_only:
        _expect_keys(
            artifact,
            METHOD_GAP_FIELDS,
            "Damodaran method gap artifact",
            errors,
        )
        if not _nonempty_string(artifact.get("method_gap")):
            errors.append("Damodaran Partial or Unavailable requires method_gap")
        return
    _expect_keys(
        artifact, DAMODARAN_ARTIFACT_FIELDS, "Damodaran method artifact", errors
    )
    archetype = artifact.get("company_archetype")
    required_drivers = (
        DAMODARAN_ARCHETYPE_DRIVERS.get(archetype)
        if _nonempty_string(archetype)
        else None
    )
    if required_drivers is None:
        errors.append("Damodaran company_archetype is invalid")
        required_drivers = set()
    valuation_frame = artifact.get("valuation_frame")
    valid_frames = (
        DAMODARAN_ARCHETYPE_FRAMES.get(archetype, set())
        if _nonempty_string(archetype)
        else set()
    )
    if not _allowed_string(valuation_frame, valid_frames):
        errors.append("Damodaran valuation_frame is not appropriate for its archetype")
    _require_text_fields(
        artifact,
        ("archetype_rationale", "requested_horizon_transmission"),
        "Damodaran method artifact",
        errors,
    )
    if completion == "Complete" and artifact.get("method_gap") is not None:
        errors.append("Damodaran Complete requires method_gap null")
    elif completion == "Partial" and not _nonempty_string(
        artifact.get("method_gap")
    ):
        errors.append("Damodaran Partial requires method_gap")
    anchor = artifact.get("anchor_price")
    price_value = price.get("value")
    if (
        not _number(anchor)
        or not _number(price_value)
        or not math.isclose(anchor, price_value, rel_tol=1e-9, abs_tol=1e-9)
    ):
        errors.append("Damodaran anchor_price must equal current_price")
    if artifact.get("currency") != price.get("currency"):
        errors.append("Damodaran currency must equal current_price.currency")
    implied = _driver_table(
        artifact.get("price_implied_drivers"),
        label="Damodaran price_implied_drivers",
        errors=errors,
    )
    owner = _driver_table(
        artifact.get("owner_case_drivers"),
        label="Damodaran owner_case_drivers",
        errors=errors,
    )
    if set(implied) != required_drivers:
        errors.append(
            f"Damodaran price-implied drivers must match the {archetype} archetype"
        )
    if set(owner) != required_drivers:
        errors.append(
            f"Damodaran owner-case drivers must match the {archetype} archetype"
        )
    bridge = artifact.get("story_to_numbers_bridge")
    bridge_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(bridge, list) or not bridge:
        errors.append("Damodaran story_to_numbers_bridge must be non-empty")
        bridge = []
    bridge_keys = {
        "driver_id",
        "story",
        "implied_value",
        "owner_value",
        "unit",
        "directional_effect",
        "evidence_ids",
        "falsifier",
    }
    for index, row in enumerate(bridge):
        prefix = f"Damodaran story_to_numbers_bridge[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(row, bridge_keys, prefix, errors)
        driver_id = row.get("driver_id")
        if not _nonempty_string(driver_id) or driver_id in bridge_by_id:
            errors.append(f"{prefix}.driver_id must be non-empty and unique")
            continue
        bridge_by_id[driver_id] = row
        _require_text_fields(row, ("story", "unit", "falsifier"), prefix, errors)
        if not _allowed_string(
            row.get("directional_effect"), {"upside", "downside", "neutral"}
        ):
            errors.append(f"{prefix}.directional_effect is invalid")
        if not _number(row.get("implied_value")) or not _number(
            row.get("owner_value")
        ):
            errors.append(f"{prefix} implied_value and owner_value must be numeric")
    if set(bridge_by_id) != required_drivers:
        errors.append("Damodaran story bridge must cover every archetype driver")
    for driver_id in set(bridge_by_id) & set(implied) & set(owner):
        row = bridge_by_id[driver_id]
        if (
            row.get("implied_value") != implied[driver_id].get("value")
            or row.get("owner_value") != owner[driver_id].get("value")
            or row.get("unit") != implied[driver_id].get("unit")
            or row.get("unit") != owner[driver_id].get("unit")
        ):
            errors.append(
                "Damodaran story bridge values must equal its driver tables"
            )
            break
    value_range = artifact.get("fundamental_value_range")
    if not isinstance(value_range, dict):
        errors.append("Damodaran fundamental_value_range must be an object")
    else:
        _expect_keys(
            value_range,
            {"low", "base", "high", "currency", "evidence_ids"},
            "Damodaran fundamental_value_range",
            errors,
        )
        low, base, high = (
            value_range.get("low"),
            value_range.get("base"),
            value_range.get("high"),
        )
        if not all(_number(row) and row > 0 for row in (low, base, high)):
            errors.append("Damodaran value range must contain positive numbers")
        elif not low <= base <= high:
            errors.append("Damodaran value range must be ordered low <= base <= high")
        if value_range.get("currency") != price.get("currency"):
            errors.append("Damodaran value-range currency must match current price")
    least_plausible = artifact.get("least_plausible_implied_driver")
    if not _allowed_string(least_plausible, required_drivers):
        errors.append(
            "Damodaran least_plausible_implied_driver must name an archetype driver"
        )


def _validate_soros_artifact(
    artifact: Any,
    *,
    completion: str,
    horizon: Any,
    allowed_evidence: set[str],
    errors: list[str],
) -> None:
    if not isinstance(artifact, dict):
        if completion == "Complete":
            errors.append("soros Complete requires its named structured method artifact")
        else:
            errors.append(f"soros {completion} requires a structured gap artifact")
        return
    if completion == "Partial" and not set(artifact) <= METHOD_GAP_FIELDS:
        errors.append("Soros Partial must use only a qualitative gap artifact")
    gap_only = completion != "Complete"
    allowed_fields = METHOD_GAP_FIELDS if gap_only else SOROS_ARTIFACT_FIELDS
    _reject_unexpected_keys(
        artifact, allowed_fields, "Soros method artifact", errors
    )
    if artifact.get("artifact_type") != "soros_reflexivity_chain_v1":
        errors.append("Soros method artifact_type is invalid")
    if artifact.get("requested_horizon") != horizon:
        errors.append("Soros requested_horizon must equal decision_horizon")
    if not _nonempty_string(artifact.get("proposition_id")):
        errors.append("Soros proposition_id must be a non-empty string")
    _validate_artifact_evidence(
        artifact, allowed=allowed_evidence, label="Soros", errors=errors
    )
    if gap_only:
        _expect_keys(
            artifact, METHOD_GAP_FIELDS, "Soros method gap artifact", errors
        )
        if not _nonempty_string(artifact.get("method_gap")):
            errors.append("Soros Partial or Unavailable requires method_gap")
        return
    _expect_keys(artifact, SOROS_ARTIFACT_FIELDS, "Soros method artifact", errors)
    if completion == "Complete" and artifact.get("method_gap") is not None:
        errors.append("Soros Complete requires method_gap null")
    elif completion == "Partial" and not _nonempty_string(
        artifact.get("method_gap")
    ):
        errors.append("Soros Partial requires method_gap")
    classification = artifact.get("classification")
    if not _allowed_string(classification, {"reflexive", "non_reflexive"}):
        errors.append("Soros classification must be reflexive or non_reflexive")
    trend = artifact.get("current_trend")
    if not isinstance(trend, dict):
        errors.append("Soros current_trend must be an object")
    else:
        _expect_keys(
            trend,
            {"direction", "observation", "evidence_ids"},
            "Soros current_trend",
            errors,
        )
        if not _allowed_string(
            trend.get("direction"), {"up", "down", "sideways", "mixed"}
        ):
            errors.append("Soros current_trend.direction is invalid")
        _require_text_fields(trend, ("observation",), "Soros current_trend", errors)
    bias = artifact.get("prevailing_bias")
    if not isinstance(bias, dict):
        errors.append("Soros prevailing_bias must be an object")
    else:
        _expect_keys(
            bias,
            {"belief", "reality_gap", "evidence_ids"},
            "Soros prevailing_bias",
            errors,
        )
        _require_text_fields(
            bias, ("belief", "reality_gap"), "Soros prevailing_bias", errors
        )
    actors = artifact.get("marginal_actors")
    if not isinstance(actors, list) or not actors:
        errors.append("Soros marginal_actors must be a non-empty list")
        actors = []
    for index, actor in enumerate(actors):
        prefix = f"Soros marginal_actors[{index}]"
        if not isinstance(actor, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            actor,
            {"actor", "incentive", "expected_action", "evidence_ids"},
            prefix,
            errors,
        )
        _require_text_fields(
            actor, ("actor", "incentive", "expected_action"), prefix, errors
        )
    chain = artifact.get("feedback_chain")
    tests = artifact.get("non_reflexive_tests")
    if classification == "reflexive":
        if not isinstance(chain, list) or [
            row.get("step") if isinstance(row, dict) else None for row in chain
        ] != SOROS_FEEDBACK_STEPS:
            errors.append("Soros reflexive chain must contain all five ordered links")
            chain = chain if isinstance(chain, list) else []
        if tests != []:
            errors.append("Soros reflexive classification requires empty non_reflexive_tests")
        if not _allowed_string(
            artifact.get("phase"), SOROS_PHASES - {"non_reflexive"}
        ):
            errors.append("Soros reflexive phase is invalid")
    elif classification == "non_reflexive":
        if chain != []:
            errors.append("Soros non_reflexive classification requires empty feedback_chain")
        if artifact.get("phase") != "non_reflexive":
            errors.append("Soros non_reflexive classification requires non_reflexive phase")
        if not isinstance(tests, list) or len(tests) < 2:
            errors.append("Soros non-reflexive proof requires at least two broken-link tests")
            tests = []
        tested_links: set[str] = set()
        for index, test in enumerate(tests):
            prefix = f"Soros non_reflexive_tests[{index}]"
            if not isinstance(test, dict):
                errors.append(f"{prefix} must be an object")
                continue
            _expect_keys(
                test,
                {"candidate_link", "failure_reason", "evidence_ids"},
                prefix,
                errors,
            )
            if test.get("candidate_link") not in SOROS_FEEDBACK_STEPS:
                errors.append(f"{prefix}.candidate_link is invalid")
            else:
                tested_links.add(test["candidate_link"])
            _require_text_fields(test, ("failure_reason",), prefix, errors)
        if len(tested_links) < 2:
            errors.append("Soros non-reflexive proof must test distinct chain links")
    if isinstance(chain, list):
        for index, row in enumerate(chain):
            prefix = f"Soros feedback_chain[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{prefix} must be an object")
                continue
            _expect_keys(row, {"step", "claim", "evidence_ids"}, prefix, errors)
            _require_text_fields(row, ("claim",), prefix, errors)
    if not _allowed_string(artifact.get("phase"), SOROS_PHASES):
        errors.append("Soros phase is invalid")
    _require_text_fields(
        artifact, ("phase_rationale",), "Soros method artifact", errors
    )
    trigger = artifact.get("reversal_trigger")
    if not isinstance(trigger, dict):
        errors.append("Soros reversal_trigger must be an object")
    else:
        _expect_keys(
            trigger,
            {"metric", "operator", "threshold", "unit", "observation_window", "evidence_ids"},
            "Soros reversal_trigger",
            errors,
        )
        _require_text_fields(
            trigger,
            ("metric", "unit", "observation_window"),
            "Soros reversal_trigger",
            errors,
        )
        if not _allowed_string(
            trigger.get("operator"), COMPARISON_OPERATORS
        ):
            errors.append("Soros reversal_trigger.operator is invalid")
        if not _number(trigger.get("threshold")):
            errors.append("Soros reversal_trigger.threshold must be numeric")
    paths = artifact.get("horizon_price_paths")
    if not isinstance(paths, list) or len(paths) < 3:
        errors.append("Soros horizon_price_paths must contain at least three states")
        paths = []
    probability_sum = 0.0
    expected_return = 0.0
    state_ids: set[str] = set()
    for index, state in enumerate(paths):
        prefix = f"Soros horizon_price_paths[{index}]"
        if not isinstance(state, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            state,
            {"state_id", "scenario_role", "condition", "probability_pct", "gross_return_pct", "mechanism", "evidence_ids"},
            prefix,
            errors,
        )
        state_id = state.get("state_id")
        if not _nonempty_string(state_id) or state_id in state_ids:
            errors.append(f"{prefix}.state_id must be non-empty and unique")
        else:
            state_ids.add(state_id)
        _require_text_fields(state, ("condition", "mechanism"), prefix, errors)
        probability = state.get("probability_pct")
        payoff = state.get("gross_return_pct")
        if not _number(probability) or not 0 < probability <= 100:
            errors.append(
                "Soros path probability must be greater than 0 and at most 100"
            )
            continue
        if not _number(payoff):
            errors.append(f"{prefix}.gross_return_pct must be numeric")
            continue
        probability_sum += probability
        expected_return += probability * payoff / 100
    _validate_scenario_roles(
        paths,
        label="Soros horizon_price_paths",
        payoff_field="gross_return_pct",
        errors=errors,
    )
    if paths and not math.isclose(probability_sum, 100.0, abs_tol=1e-6):
        errors.append("Soros path probabilities must sum to 100")
    if not _number(artifact.get("expected_path_return_pct")) or not math.isclose(
        artifact.get("expected_path_return_pct", math.inf),
        expected_return,
        abs_tol=1e-6,
    ):
        errors.append("Soros expected_path_return_pct must equal recomputed path EV")


def _validate_mauboussin_artifact(
    artifact: Any,
    *,
    completion: str,
    price: dict[str, Any],
    horizon: Any,
    allowed_evidence: set[str],
    errors: list[str],
) -> None:
    if not isinstance(artifact, dict):
        if completion == "Complete":
            errors.append(
                "mauboussin Complete requires its named structured method artifact"
            )
        else:
            errors.append(
                f"mauboussin {completion} requires a structured gap artifact"
            )
        return
    if completion == "Partial" and not set(artifact) <= METHOD_GAP_FIELDS:
        errors.append("Mauboussin Partial must use only a qualitative gap artifact")
    gap_only = completion != "Complete"
    allowed_fields = METHOD_GAP_FIELDS if gap_only else MAUBOUSSIN_ARTIFACT_FIELDS
    _reject_unexpected_keys(
        artifact, allowed_fields, "Mauboussin method artifact", errors
    )
    if artifact.get("artifact_type") != "mauboussin_expectations_distribution_v1":
        errors.append("Mauboussin method artifact_type is invalid")
    if artifact.get("requested_horizon") != horizon:
        errors.append("Mauboussin requested_horizon must equal decision_horizon")
    if not _nonempty_string(artifact.get("proposition_id")):
        errors.append("Mauboussin proposition_id must be a non-empty string")
    _validate_artifact_evidence(
        artifact, allowed=allowed_evidence, label="Mauboussin", errors=errors
    )
    if gap_only:
        _expect_keys(
            artifact,
            METHOD_GAP_FIELDS,
            "Mauboussin method gap artifact",
            errors,
        )
        if not _nonempty_string(artifact.get("method_gap")):
            errors.append("Mauboussin Partial or Unavailable requires method_gap")
        return
    _expect_keys(
        artifact, MAUBOUSSIN_ARTIFACT_FIELDS, "Mauboussin method artifact", errors
    )
    anchor = artifact.get("anchor_price")
    price_value = price.get("value")
    if (
        not _number(anchor)
        or not _number(price_value)
        or not math.isclose(anchor, price_value, rel_tol=1e-9, abs_tol=1e-9)
    ):
        errors.append("Mauboussin anchor_price must equal current_price")
    if artifact.get("currency") != price.get("currency"):
        errors.append("Mauboussin currency must equal current_price.currency")
    expectations = artifact.get("price_implied_expectations")
    if not isinstance(expectations, list) or not expectations:
        errors.append("Mauboussin price_implied_expectations must be non-empty")
        expectations = []
    for index, row in enumerate(expectations):
        prefix = f"Mauboussin price_implied_expectations[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            row,
            {"metric", "implied_value", "unit", "evidence_ids", "disconfirming_observation"},
            prefix,
            errors,
        )
        _require_text_fields(
            row, ("metric", "unit", "disconfirming_observation"), prefix, errors
        )
        if not _number(row.get("implied_value")):
            errors.append(f"{prefix}.implied_value must be numeric")
    reference = artifact.get("reference_class")
    reference_status = None
    base_rate: float | None = None
    if not isinstance(reference, dict):
        errors.append("Mauboussin reference_class must be an object")
    else:
        _expect_keys(
            reference,
            {
                "status",
                "definition",
                "inclusion_criteria",
                "exclusion_criteria",
                "sample_size",
                "base_rate_label",
                "base_rate_pct",
                "evidence_ids",
                "gap_reason",
            },
            "Mauboussin reference_class",
            errors,
        )
        reference_status = reference.get("status")
        if reference_status == "available":
            if completion != "Complete":
                errors.append(
                    "Mauboussin available reference class requires Complete completion"
                )
            _require_text_fields(
                reference,
                ("definition", "base_rate_label"),
                "Mauboussin reference_class",
                errors,
            )
            if (
                not _string_list(reference.get("inclusion_criteria"))
                or len(reference["inclusion_criteria"]) < 2
            ):
                errors.append(
                    "Mauboussin reference_class requires at least two inclusion criteria"
                )
            if not _string_list(reference.get("exclusion_criteria")):
                errors.append("Mauboussin exclusion_criteria must be a string list")
            if (
                not isinstance(reference.get("sample_size"), int)
                or isinstance(reference.get("sample_size"), bool)
                or reference["sample_size"] < 10
            ):
                errors.append("Mauboussin reference-class sample_size must be at least 10")
            if not _number(reference.get("base_rate_pct")) or not (
                0 <= reference.get("base_rate_pct", -1) <= 100
            ):
                errors.append("Mauboussin base_rate_pct must be between 0 and 100")
            else:
                base_rate = reference["base_rate_pct"]
            if reference.get("gap_reason") is not None:
                errors.append("Available Mauboussin reference class requires gap_reason null")
        elif reference_status == "gap":
            if completion != "Partial":
                errors.append("Mauboussin reference-class gap requires Partial completion")
            if not _nonempty_string(reference.get("gap_reason")):
                errors.append("Mauboussin reference-class gap requires gap_reason")
        else:
            errors.append("Mauboussin reference_class.status must be available or gap")
    posterior_mode = artifact.get("posterior_mode")
    if reference_status == "available" and posterior_mode != "base_rate_update":
        errors.append(
            "Mauboussin available reference class requires base_rate_update posterior mode"
        )
    if reference_status == "gap" and posterior_mode != "judgmental_override":
        errors.append(
            "Mauboussin reference-class gap requires judgmental_override posterior mode"
        )
    if completion == "Complete" and artifact.get("method_gap") is not None:
        errors.append("Mauboussin Complete requires method_gap null")
    if completion != "Complete" and not _nonempty_string(artifact.get("method_gap")):
        errors.append("Mauboussin Partial or Unavailable requires method_gap")
    updates = artifact.get("inside_view_updates")
    if not isinstance(updates, list) or not updates:
        errors.append("Mauboussin inside_view_updates must be non-empty")
        updates = []
    update_delta_sum = 0.0
    update_state_ids: list[set[str]] = []
    for index, row in enumerate(updates):
        prefix = f"Mauboussin inside_view_updates[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            row,
            {"signal", "direction", "probability_delta_pct", "affected_state_ids", "rationale", "evidence_ids"},
            prefix,
            errors,
        )
        _require_text_fields(row, ("signal", "rationale"), prefix, errors)
        delta = row.get("probability_delta_pct")
        affected = row.get("affected_state_ids")
        if (
            not _string_list(affected)
            or not affected
            or len(affected) != len(set(affected or []))
        ):
            errors.append(f"{prefix}.affected_state_ids must be unique and non-empty")
            affected = []
        update_state_ids.append(set(affected))
        if not _allowed_string(
            row.get("direction"), {"increase", "decrease", "unchanged"}
        ):
            errors.append(f"{prefix}.direction is invalid")
        if not _number(delta) or not -100 <= delta <= 100:
            errors.append(f"{prefix}.probability_delta_pct is invalid")
        elif (
            (row.get("direction") == "increase" and delta <= 0)
            or (row.get("direction") == "decrease" and delta >= 0)
            or (row.get("direction") == "unchanged" and delta != 0)
        ):
            errors.append(f"{prefix}.direction must match probability_delta_pct")
        else:
            update_delta_sum += delta
    states = artifact.get("probability_payoff_states")
    if not isinstance(states, list) or len(states) < 3:
        errors.append(
            "Mauboussin probability_payoff_states must contain at least three states"
        )
        states = []
    probability_sum = 0.0
    expected_return = 0.0
    state_ids: set[str] = set()
    state_probabilities: dict[str, float] = {}
    for index, state in enumerate(states):
        prefix = f"Mauboussin probability_payoff_states[{index}]"
        if not isinstance(state, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            state,
            {"state_id", "scenario_role", "definition", "probability_pct", "target_price", "gross_return_pct", "evidence_ids"},
            prefix,
            errors,
        )
        state_id = state.get("state_id")
        if not _nonempty_string(state_id) or state_id in state_ids:
            errors.append(f"{prefix}.state_id must be non-empty and unique")
        else:
            state_ids.add(state_id)
        _require_text_fields(state, ("definition",), prefix, errors)
        probability = state.get("probability_pct")
        target = state.get("target_price")
        gross = state.get("gross_return_pct")
        if not _number(probability) or not 0 < probability <= 100:
            errors.append(
                "Mauboussin state probability must be greater than 0 and at most 100"
            )
            continue
        if _nonempty_string(state_id) and state_id in state_ids:
            state_probabilities[state_id] = probability
        if not _number(target) or target <= 0:
            errors.append(f"{prefix}.target_price must be positive numeric")
            continue
        if not _number(gross):
            errors.append(f"{prefix}.gross_return_pct must be numeric")
            continue
        if _number(anchor) and anchor > 0:
            recomputed = (target / anchor - 1) * 100
            if not math.isclose(gross, recomputed, abs_tol=1e-6):
                errors.append(
                    "Mauboussin state gross return must equal target-price return"
                )
        probability_sum += probability
        expected_return += probability * gross / 100
    _validate_scenario_roles(
        states,
        label="Mauboussin probability_payoff_states",
        payoff_field="gross_return_pct",
        errors=errors,
    )
    if states and not math.isclose(probability_sum, 100.0, abs_tol=1e-6):
        errors.append("Mauboussin state probabilities must sum to 100")
    posterior = artifact.get("posterior_success_probability_pct")
    if not _number(posterior) or not 0 < posterior < 100:
        errors.append(
            "Mauboussin posterior_success_probability_pct must be between 0 and 100"
        )
    success_ids = artifact.get("success_state_ids")
    if (
        not _string_list(success_ids)
        or not success_ids
        or len(success_ids) != len(set(success_ids or []))
    ):
        errors.append("Mauboussin success_state_ids must be unique and non-empty")
        success_ids = []
    unknown_success_ids = sorted(set(success_ids) - state_ids)
    if unknown_success_ids:
        errors.append(
            "Mauboussin success_state_ids reference unknown states: "
            + ", ".join(unknown_success_ids)
        )
    for affected_ids in update_state_ids:
        if not affected_ids <= set(success_ids):
            errors.append(
                "Mauboussin inside-view updates must map only to success_state_ids"
            )
            break
    if (
        reference_status == "available"
        and _number(base_rate)
        and _number(posterior)
        and not math.isclose(
            posterior, base_rate + update_delta_sum, abs_tol=1e-6
        )
    ):
        errors.append(
            "Mauboussin posterior must equal base rate plus inside-view updates"
        )
    if not unknown_success_ids and _number(posterior) and success_ids:
        success_probability = sum(
            state_probabilities.get(state_id, 0.0) for state_id in success_ids
        )
        if not math.isclose(
            posterior, success_probability, abs_tol=1e-6
        ):
            errors.append(
                "Mauboussin success-state probability must equal posterior"
            )
    if not _number(artifact.get("expected_return_pct")) or not math.isclose(
        artifact.get("expected_return_pct", math.inf), expected_return, abs_tol=1e-6
    ):
        errors.append(
            "Mauboussin expected_return_pct must equal recomputed probability-payoff EV"
        )
    sensitivities = artifact.get("sign_sensitivity")
    if not isinstance(sensitivities, list) or not sensitivities:
        errors.append("Mauboussin sign_sensitivity must be non-empty")
        sensitivities = []
    for index, row in enumerate(sensitivities):
        prefix = f"Mauboussin sign_sensitivity[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            row,
            {"variable", "low_input", "base_input", "high_input", "unit", "low_expected_return_pct", "high_expected_return_pct", "sign_flips"},
            prefix,
            errors,
        )
        _require_text_fields(row, ("variable", "unit"), prefix, errors)
        numeric_fields = (
            "low_input",
            "base_input",
            "high_input",
            "low_expected_return_pct",
            "high_expected_return_pct",
        )
        if not all(_number(row.get(field)) for field in numeric_fields):
            errors.append(f"{prefix} numeric fields must be finite")
            continue
        if not row["low_input"] <= row["base_input"] <= row["high_input"]:
            errors.append(f"{prefix} inputs must be ordered low <= base <= high")
        recomputed_flip = (
            row["low_expected_return_pct"] < 0 < row["high_expected_return_pct"]
            or row["high_expected_return_pct"] < 0 < row["low_expected_return_pct"]
        )
        if row.get("sign_flips") is not recomputed_flip:
            errors.append(
                "Mauboussin sign_flips must equal the recomputed sign range"
            )


def _state_by_id(value: Any, state_id: Any) -> dict[str, Any] | None:
    if not isinstance(value, list) or not _nonempty_string(state_id):
        return None
    matches = [
        row
        for row in value
        if isinstance(row, dict) and row.get("state_id") == state_id
    ]
    return matches[0] if len(matches) == 1 else None


def _resolve_target_component(
    component: Any,
    *,
    prefix: str,
    method_artifacts: dict[str, dict[str, Any]],
    price: dict[str, Any],
    errors: list[str],
) -> tuple[float | None, float | None, set[str], str | None, str | None]:
    if not isinstance(component, dict):
        errors.append(f"{prefix} must be an object")
        return None, None, set(), None, None
    _expect_keys(
        component,
        {"seat", "proposition_id", "source_kind", "source_id", "weight_pct"},
        prefix,
        errors,
    )
    seat = component.get("seat")
    if not _allowed_string(seat, SEATS):
        errors.append(f"{prefix}.seat is invalid")
        return None, None, set(), None, None
    artifact = method_artifacts.get(seat)
    if not isinstance(artifact, dict):
        errors.append(f"{prefix} references an unavailable method artifact")
        return None, None, set(), seat, None
    if component.get("proposition_id") != artifact.get("proposition_id"):
        errors.append(
            "Chair target component proposition_id must match its method artifact"
        )
    weight = component.get("weight_pct")
    if not _number(weight) or not 0 < weight <= 100:
        errors.append(f"{prefix}.weight_pct must be greater than 0 and at most 100")
        weight = None

    source_kind = component.get("source_kind")
    source_id = component.get("source_id")
    target: float | None = None
    source_evidence: set[str] = set()
    source_role: str | None = None
    if seat == "damodaran":
        range_key = {
            "fundamental_value_low": "low",
            "fundamental_value_base": "base",
            "fundamental_value_high": "high",
        }.get(source_kind)
        if range_key is None or source_id is not None:
            errors.append(f"{prefix} has invalid Damodaran source selector")
        else:
            source_role = {
                "low": "downside",
                "base": "base",
                "high": "upside",
            }[range_key]
            value_range = artifact.get("fundamental_value_range")
            if isinstance(value_range, dict) and _number(value_range.get(range_key)):
                target = value_range[range_key]
                source_evidence = _collect_evidence_ids(value_range)
            else:
                errors.append(f"{prefix} cannot resolve Damodaran target input")
    elif seat == "soros":
        if source_kind != "horizon_path_return":
            errors.append(f"{prefix} has invalid Soros source selector")
        else:
            path = _state_by_id(artifact.get("horizon_price_paths"), source_id)
            price_value = price.get("value")
            if (
                isinstance(path, dict)
                and _number(path.get("gross_return_pct"))
                and _number(price_value)
                and price_value > 0
            ):
                target = price_value * (1 + path["gross_return_pct"] / 100)
                source_evidence = _collect_evidence_ids(path)
                if _allowed_string(path.get("scenario_role"), SCENARIO_ROLES):
                    source_role = path["scenario_role"]
                else:
                    errors.append(f"{prefix} source scenario_role is invalid")
            else:
                errors.append(f"{prefix} cannot resolve Soros path input")
    else:
        if source_kind != "probability_payoff_target":
            errors.append(f"{prefix} has invalid Mauboussin source selector")
        else:
            state = _state_by_id(
                artifact.get("probability_payoff_states"), source_id
            )
            if isinstance(state, dict) and _number(state.get("target_price")):
                target = state["target_price"]
                source_evidence = _collect_evidence_ids(state)
                if _allowed_string(state.get("scenario_role"), SCENARIO_ROLES):
                    source_role = state["scenario_role"]
                else:
                    errors.append(f"{prefix} source scenario_role is invalid")
            else:
                errors.append(f"{prefix} cannot resolve Mauboussin target input")
    if target is not None and target <= 0:
        errors.append(f"{prefix} resolved target must be positive")
        target = None
    if target is not None and not source_evidence:
        errors.append(f"{prefix} resolved method input must have evidence_ids")
    return target, weight, source_evidence, seat, source_role


def _resolve_probability_component(
    component: Any,
    *,
    prefix: str,
    method_artifacts: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[float | None, float | None, set[str], str | None, str | None]:
    if not isinstance(component, dict):
        errors.append(f"{prefix} must be an object")
        return None, None, set(), None, None
    _expect_keys(
        component,
        {
            "seat",
            "proposition_id",
            "source_kind",
            "source_id",
            "weight_pct",
            "scenario_probability_basis",
        },
        prefix,
        errors,
    )
    seat = component.get("seat")
    if not _allowed_string(seat, {"soros", "mauboussin"}):
        errors.append(f"{prefix}.seat must be soros or mauboussin")
        return None, None, set(), None, None
    artifact = method_artifacts.get(seat)
    if not isinstance(artifact, dict):
        errors.append(f"{prefix} references an unavailable method artifact")
        return None, None, set(), seat, None
    if component.get("proposition_id") != artifact.get("proposition_id"):
        errors.append(
            "Chair probability component proposition_id must match its method artifact"
        )
    weight = component.get("weight_pct")
    if not _number(weight) or not 0 < weight <= 100:
        errors.append(f"{prefix}.weight_pct must be greater than 0 and at most 100")
        weight = None
    if not _nonempty_string(component.get("scenario_probability_basis")):
        errors.append(
            f"{prefix}.scenario_probability_basis must be a non-empty string"
        )

    source_kind = component.get("source_kind")
    source_id = component.get("source_id")
    if seat == "soros" and source_kind == "horizon_path_probability":
        state = _state_by_id(artifact.get("horizon_price_paths"), source_id)
    elif (
        seat == "mauboussin"
        and source_kind == "probability_payoff_probability"
    ):
        state = _state_by_id(artifact.get("probability_payoff_states"), source_id)
    else:
        errors.append(f"{prefix} has invalid probability source selector")
        state = None
    if not isinstance(state, dict) or not _number(state.get("probability_pct")):
        errors.append(f"{prefix} cannot resolve method probability input")
        return None, weight, set(), seat, None
    probability = state["probability_pct"]
    evidence_ids = _collect_evidence_ids(state)
    if not evidence_ids:
        errors.append(f"{prefix} resolved method input must have evidence_ids")
    source_role = state.get("scenario_role")
    if not _allowed_string(source_role, SCENARIO_ROLES):
        errors.append(f"{prefix} source scenario_role is invalid")
        source_role = None
    return probability, weight, evidence_ids, seat, source_role


def _validate_chair_matrix(
    matrix: Any,
    *,
    chair: dict[str, Any],
    price: dict[str, Any],
    horizon: Any,
    accepted_evidence: set[str],
    method_artifacts: dict[str, dict[str, Any]],
    method_completions: dict[str, str],
    collaboration_available: bool,
    errors: list[str],
) -> None:
    if not isinstance(matrix, dict):
        errors.append("Chair requires a structured dominant-variable decision matrix")
        return
    expected = {
        "artifact_type",
        "requested_horizon",
        "dominant_variable",
        "dominant_variable_unit",
        "dominance_rationale",
        "transition",
        "states",
        "gross_expected_return_pct",
        "strongest_disconfirming_state_id",
        "reversal_triggers",
    }
    _expect_keys(matrix, expected, "Chair decision_matrix", errors)
    if matrix.get("artifact_type") != "dominant_variable_state_matrix_v1":
        errors.append("Chair decision_matrix.artifact_type is invalid")
    if matrix.get("requested_horizon") != horizon:
        errors.append("Chair matrix requested_horizon must equal decision_horizon")
    if matrix.get("dominant_variable") != chair.get("dominant_variable"):
        errors.append("Chair matrix dominant_variable must equal chair.dominant_variable")
    _require_text_fields(
        matrix,
        ("dominant_variable", "dominant_variable_unit", "dominance_rationale"),
        "Chair decision_matrix",
        errors,
    )
    transition = matrix.get("transition")
    if not isinstance(transition, dict):
        errors.append("Chair transition must be an object")
    else:
        _expect_keys(
            transition,
            {"from", "to", "mechanism", "timing"},
            "Chair transition",
            errors,
        )
        _require_text_fields(
            transition,
            ("from", "to", "mechanism", "timing"),
            "Chair transition",
            errors,
        )
    states = matrix.get("states")
    if not isinstance(states, list) or len(states) < 3:
        errors.append("Chair state matrix must contain at least three states")
        states = []
    state_ids: set[str] = set()
    state_returns: dict[str, float] = {}
    intervals: list[dict[str, Any]] = []
    probability_sum = 0.0
    expected_return = 0.0
    anchor = price.get("value")
    matrix_component_seats: set[str] = set()
    matrix_target_selectors: set[tuple[str, str, str, str]] = set()
    matrix_probability_selectors: set[tuple[str, str, str, str]] = set()
    chair_used_evidence = set(chair.get("used_evidence_ids") or [])
    state_keys = {
        "state_id",
        "scenario_role",
        "definition",
        "dominant_variable_interval",
        "probability_pct",
        "target_price",
        "gross_return_pct",
        "decisive_mechanism",
        "seat_inputs",
        "target_components",
        "probability_components",
        "evidence_ids",
    }
    interval_keys = {"lower", "lower_inclusive", "upper", "upper_inclusive"}
    for index, state in enumerate(states):
        prefix = f"Chair decision_matrix.states[{index}]"
        if not isinstance(state, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(state, state_keys, prefix, errors)
        state_id = state.get("state_id")
        if not _nonempty_string(state_id) or state_id in state_ids:
            errors.append(f"{prefix}.state_id must be non-empty and unique")
        else:
            state_ids.add(state_id)
        state_role = state.get("scenario_role")
        _require_text_fields(
            state, ("definition", "decisive_mechanism"), prefix, errors
        )
        interval = state.get("dominant_variable_interval")
        if not isinstance(interval, dict):
            errors.append(f"{prefix}.dominant_variable_interval must be an object")
            interval = {}
        else:
            _expect_keys(
                interval,
                interval_keys,
                f"{prefix}.dominant_variable_interval",
                errors,
            )
        lower, upper = interval.get("lower"), interval.get("upper")
        if lower is not None and not _number(lower):
            errors.append(f"{prefix} interval lower must be numeric or null")
        if upper is not None and not _number(upper):
            errors.append(f"{prefix} interval upper must be numeric or null")
        if not isinstance(interval.get("lower_inclusive"), bool) or not isinstance(
            interval.get("upper_inclusive"), bool
        ):
            errors.append(f"{prefix} interval inclusivity must be boolean")
        if _number(lower) and _number(upper) and lower >= upper:
            errors.append(f"{prefix} interval lower must be below upper")
        intervals.append(interval)

        state_evidence = state.get("evidence_ids")
        if not _string_list(state_evidence) or not state_evidence:
            errors.append(f"{prefix}.evidence_ids must be non-empty")
            state_evidence = []
        outside_evidence = sorted(set(state_evidence) - accepted_evidence)
        if outside_evidence:
            errors.append(
                "Chair state uses evidence outside accepted PEI inputs: "
                + ", ".join(outside_evidence)
            )
        undeclared_evidence = sorted(set(state_evidence) - chair_used_evidence)
        if undeclared_evidence:
            errors.append(
                "Chair state evidence must appear in chair.used_evidence_ids: "
                + ", ".join(undeclared_evidence)
            )

        components = state.get("target_components")
        if not isinstance(components, list):
            errors.append(f"{prefix}.target_components must be a list")
            components = []
        if collaboration_available and not components:
            errors.append(f"{prefix}.target_components must be non-empty")
        if not collaboration_available and components:
            errors.append("Unavailable Council cannot claim method target components")
        component_weight_sum = 0.0
        weighted_target = 0.0
        component_seats: set[str] = set()
        required_component_evidence: set[str] = set()
        resolved_component_count = 0
        target_component_selectors: set[tuple[str, str, str, str]] = set()
        for component_index, component in enumerate(components):
            if isinstance(component, dict):
                selector = (
                    repr(component.get("seat")),
                    repr(component.get("proposition_id")),
                    repr(component.get("source_kind")),
                    repr(component.get("source_id")),
                )
                if selector in target_component_selectors:
                    errors.append("Chair target components must use unique inputs")
                elif selector in matrix_target_selectors:
                    errors.append(
                        "Chair target source state may be used by only one matrix state"
                    )
                target_component_selectors.add(selector)
                matrix_target_selectors.add(selector)
            target_input, weight, evidence_ids, component_seat, source_role = (
                _resolve_target_component(
                    component,
                    prefix=f"{prefix}.target_components[{component_index}]",
                    method_artifacts=method_artifacts,
                    price=price,
                    errors=errors,
                )
            )
            if source_role is not None and source_role != state_role:
                errors.append(
                    f"{prefix} target component scenario_role must equal Chair state scenario_role"
                )
            if component_seat in SEATS:
                component_seats.add(component_seat)
                matrix_component_seats.add(component_seat)
            required_component_evidence.update(evidence_ids)
            if target_input is not None and weight is not None:
                component_weight_sum += weight
                weighted_target += target_input * weight / 100
                resolved_component_count += 1
        if collaboration_available and components and not math.isclose(
            component_weight_sum, 100.0, abs_tol=1e-6
        ):
            errors.append("Chair target-component weights must sum to 100")

        probability_components = state.get("probability_components")
        if not isinstance(probability_components, list):
            errors.append(f"{prefix}.probability_components must be a list")
            probability_components = []
        if collaboration_available and not probability_components:
            errors.append(f"{prefix}.probability_components must be non-empty")
        if not collaboration_available and probability_components:
            errors.append(
                "Unavailable Council cannot claim method probability components"
            )
        probability_weight_sum = 0.0
        weighted_probability = 0.0
        resolved_probability_count = 0
        probability_component_selectors: set[tuple[str, str, str, str]] = set()
        for component_index, component in enumerate(probability_components):
            if isinstance(component, dict):
                selector = (
                    repr(component.get("seat")),
                    repr(component.get("proposition_id")),
                    repr(component.get("source_kind")),
                    repr(component.get("source_id")),
                )
                if selector in probability_component_selectors:
                    errors.append(
                        "Chair probability components must use unique inputs"
                    )
                elif selector in matrix_probability_selectors:
                    errors.append(
                        "Chair probability source state may be used by only one matrix state"
                    )
                probability_component_selectors.add(selector)
                matrix_probability_selectors.add(selector)
            probability_input, weight, evidence_ids, component_seat, source_role = (
                _resolve_probability_component(
                    component,
                    prefix=(
                        f"{prefix}.probability_components[{component_index}]"
                    ),
                    method_artifacts=method_artifacts,
                    errors=errors,
                )
            )
            if source_role is not None and source_role != state_role:
                errors.append(
                    f"{prefix} probability component scenario_role must equal Chair state scenario_role"
                )
            if component_seat in SEATS:
                component_seats.add(component_seat)
                matrix_component_seats.add(component_seat)
            required_component_evidence.update(evidence_ids)
            if probability_input is not None and weight is not None:
                probability_weight_sum += weight
                weighted_probability += probability_input * weight / 100
                resolved_probability_count += 1
        if (
            collaboration_available
            and probability_components
            and not math.isclose(probability_weight_sum, 100.0, abs_tol=1e-6)
        ):
            errors.append("Chair probability-component weights must sum to 100")
        missing_component_evidence = sorted(
            required_component_evidence - set(state_evidence)
        )
        if missing_component_evidence:
            errors.append(
                "Chair state evidence must include its method-component evidence: "
                + ", ".join(missing_component_evidence)
            )

        seat_inputs = state.get("seat_inputs")
        if (
            not _string_list(seat_inputs)
            or len(seat_inputs) != len(set(seat_inputs or []))
            or not set(seat_inputs or []) <= SEATS
        ):
            errors.append(f"{prefix}.seat_inputs must be a unique Council seat list")
            seat_inputs = []
        elif collaboration_available and set(seat_inputs) != component_seats:
            errors.append(
                f"{prefix}.seat_inputs must equal its target-component seats"
            )
        elif not collaboration_available and seat_inputs:
            errors.append("Unavailable Council cannot claim member seat inputs")

        probability = state.get("probability_pct")
        target = state.get("target_price")
        gross = state.get("gross_return_pct")
        if not _number(probability) or not 0 < probability <= 100:
            errors.append(
                "Chair state probability must be greater than 0 and at most 100"
            )
            continue
        if (
            collaboration_available
            and resolved_probability_count
            and not math.isclose(
                probability, weighted_probability, abs_tol=1e-6
            )
        ):
            errors.append(
                "Chair state probability_pct must equal weighted method-artifact inputs"
            )
        if not _number(target) or target <= 0:
            errors.append(f"{prefix}.target_price must be positive numeric")
            continue
        if (
            collaboration_available
            and resolved_component_count
            and not math.isclose(target, weighted_target, abs_tol=1e-6)
        ):
            errors.append(
                "Chair state target_price must equal weighted method-artifact inputs"
            )
        if not _number(gross):
            errors.append(f"{prefix}.gross_return_pct must be numeric")
            continue
        if _number(anchor) and anchor > 0:
            recomputed = (target / anchor - 1) * 100
            if not math.isclose(gross, recomputed, abs_tol=1e-6):
                errors.append("Chair state gross return must equal target-price return")
        if _nonempty_string(state_id):
            state_returns[state_id] = gross
        probability_sum += probability
        expected_return += probability * gross / 100
    _validate_scenario_roles(
        states,
        label="Chair decision_matrix.states",
        payoff_field="gross_return_pct",
        errors=errors,
    )
    if collaboration_available:
        complete_seats = {
            seat
            for seat, completion in method_completions.items()
            if completion == "Complete"
        }
        missing_complete_seats = sorted(complete_seats - matrix_component_seats)
        if missing_complete_seats:
            errors.append(
                "Chair matrix must use every Complete method artifact: "
                + ", ".join(missing_complete_seats)
            )
    if intervals:
        mece = intervals[0].get("lower") is None and intervals[-1].get("upper") is None
        for left, right in zip(intervals, intervals[1:]):
            boundary_equal = (
                _number(left.get("upper"))
                and _number(right.get("lower"))
                and math.isclose(
                    left["upper"], right["lower"], rel_tol=0.0, abs_tol=1e-9
                )
            )
            exactly_one_inclusive = (
                isinstance(left.get("upper_inclusive"), bool)
                and isinstance(right.get("lower_inclusive"), bool)
                and left["upper_inclusive"] != right["lower_inclusive"]
            )
            mece = mece and boundary_equal and exactly_one_inclusive
        if not mece:
            errors.append("Chair state intervals must be contiguous and non-overlapping")
    if states and not math.isclose(probability_sum, 100.0, abs_tol=1e-6):
        errors.append("Chair state probabilities must sum to 100")
    matrix_ev = matrix.get("gross_expected_return_pct")
    if not _number(matrix_ev) or not math.isclose(
        matrix_ev, expected_return, abs_tol=1e-6
    ):
        errors.append(
            "Chair matrix gross expected return must equal recomputed state EV"
        )
    if not _number(chair.get("gross_expected_return_pct")) or not _number(matrix_ev) or not math.isclose(
        chair.get("gross_expected_return_pct", math.inf), matrix_ev, abs_tol=1e-6
    ):
        errors.append("Chair gross_expected_return_pct must equal decision matrix EV")
    disconfirming_id = matrix.get("strongest_disconfirming_state_id")
    if disconfirming_id not in state_returns:
        errors.append("Chair strongest_disconfirming_state_id must name a state")
    else:
        disconfirming_return = state_returns[disconfirming_id]
        stance = chair.get("research_stance")
        opposes = (
            (stance == "Long" and disconfirming_return < 0)
            or (stance == "Short" and disconfirming_return > 0)
            or (stance == "Avoid" and not math.isclose(disconfirming_return, 0.0))
        )
        if not opposes:
            errors.append(
                "Chair strongest disconfirming state must oppose the final stance"
            )
        elif stance == "Long":
            most_adverse = min(state_returns.values())
            if not math.isclose(disconfirming_return, most_adverse, abs_tol=1e-6):
                errors.append(
                    "Chair strongest disconfirming state must be the most adverse state"
                )
        elif stance == "Short":
            most_adverse = max(state_returns.values())
            if not math.isclose(disconfirming_return, most_adverse, abs_tol=1e-6):
                errors.append(
                    "Chair strongest disconfirming state must be the most adverse state"
                )
        elif stance == "Avoid":
            most_adverse = max(state_returns.values(), key=abs)
            if not math.isclose(disconfirming_return, most_adverse, abs_tol=1e-6):
                errors.append(
                    "Chair strongest disconfirming state must be the most adverse state"
                )
    triggers = matrix.get("reversal_triggers")
    if not isinstance(triggers, list) or not triggers:
        errors.append("Chair reversal_triggers must be non-empty")
        triggers = []
    observables: set[str] = set()
    for index, trigger in enumerate(triggers):
        prefix = f"Chair reversal_triggers[{index}]"
        if not isinstance(trigger, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            trigger,
            {"observable", "metric", "operator", "threshold", "unit", "observation_window", "resulting_stance", "evidence_ids"},
            prefix,
            errors,
        )
        _require_text_fields(
            trigger,
            ("observable", "metric", "unit", "observation_window"),
            prefix,
            errors,
        )
        if _nonempty_string(trigger.get("observable")):
            observables.add(trigger["observable"])
        if not _allowed_string(
            trigger.get("operator"), COMPARISON_OPERATORS
        ):
            errors.append(f"{prefix}.operator is invalid")
        if not _number(trigger.get("threshold")):
            errors.append(f"{prefix}.threshold must be numeric")
        if not _allowed_string(trigger.get("resulting_stance"), STANCES):
            errors.append(f"{prefix}.resulting_stance is invalid")
        evidence_ids = trigger.get("evidence_ids")
        if not _string_list(evidence_ids) or not evidence_ids:
            errors.append(f"{prefix}.evidence_ids must be non-empty")
        else:
            outside = sorted(set(evidence_ids) - accepted_evidence)
            if outside:
                errors.append(
                    "Chair reversal trigger uses evidence outside accepted PEI inputs: "
                    + ", ".join(outside)
                )
    if not _nonempty_string(chair.get("reversal_trigger")) or (
        chair.get("reversal_trigger") not in observables
    ):
        errors.append("chair.reversal_trigger must equal a structured observable trigger")


def validate(
    payload: Any,
    *,
    plugin_root: Path,
    artifact_dir: Path,
) -> list[str]:
    _ = plugin_root
    if not isinstance(payload, dict):
        return ["root must be a JSON object"]
    if payload.get("schema_version") == AGENT_COUNCIL_SCHEMA_VERSION:
        return _validate_agent_council_v3(payload, artifact_dir=Path(artifact_dir))
    errors: list[str] = []
    expected_root_fields = ROOT_FIELDS | (
        {"artifact_bindings"} if "artifact_bindings" in payload else set()
    )
    _expect_keys(payload, expected_root_fields, "root", errors)
    leaked_sealed_input = _find_leaked_sealed_input(payload)
    if leaked_sealed_input:
        errors.append(leaked_sealed_input)
    if payload.get("schema_version") != COUNCIL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {COUNCIL_SCHEMA_VERSION}")
    council_runtime = payload.get("council_runtime")
    if not _allowed_string(council_runtime, COUNCIL_RUNTIMES):
        errors.append(
            "council_runtime must be collaboration_available or unavailable"
        )
    collaboration_available = council_runtime != "unavailable"
    for field in ("ticker", "decision_horizon"):
        if not _nonempty_string(payload.get(field)):
            errors.append(f"{field} must be a non-empty string")
    cutoff = _parse_time(payload.get("evidence_cutoff"), "evidence_cutoff", errors)

    identity = payload.get("security_identity")
    if not isinstance(identity, dict):
        errors.append("security_identity must be an object")
    else:
        for field in ("symbol", "issuer", "listing", "security_id", "source_id"):
            if not _nonempty_string(identity.get(field)):
                errors.append(f"security_identity.{field} must be a non-empty string")
        if identity.get("symbol") != payload.get("ticker"):
            errors.append("security_identity.symbol must equal ticker")

    price = payload.get("current_price")
    if not isinstance(price, dict):
        errors.append("current_price must be an object")
        price = {}
    if not _number(price.get("value")) or price.get("value", 0) <= 0:
        errors.append("current_price.value must be positive finite numeric")
    for field in ("currency", "source_id"):
        if not _nonempty_string(price.get(field)):
            errors.append(f"current_price.{field} must be a non-empty string")
    if _nonempty_string(price.get("currency")) and not re.fullmatch(
        r"[A-Z]{3}", price["currency"]
    ):
        errors.append("current_price.currency must be an ISO-style currency code")
    price_as_of = _parse_time(price.get("as_of"), "current_price.as_of", errors)
    if price_as_of is not None and cutoff is not None and price_as_of > cutoff:
        errors.append("current_price.as_of cannot be after evidence_cutoff")

    receipt_ref = payload.get("pei_input_receipt")
    if not isinstance(receipt_ref, dict):
        errors.append("pei_input_receipt must be an object")
        receipt_ref = {}
    receipt_path = _safe_artifact_path(
        Path(artifact_dir),
        receipt_ref.get("artifact"),
        "pei_input_receipt.artifact",
        errors,
    )
    receipt_payload = _load_json(receipt_path, "PEI input receipt", errors)
    expected_hash = receipt_ref.get("sha256")
    if not _nonempty_string(expected_hash) or not HEX_SHA256.fullmatch(expected_hash):
        errors.append("pei_input_receipt.sha256 must be a lowercase SHA-256 digest")
    elif receipt_path is not None and receipt_path.is_file() and _sha256(receipt_path) != expected_hash:
        errors.append("pei_input_receipt.sha256 does not match artifact")

    accepted_evidence: set[str] = set()
    ambient_evidence: set[str] = set()
    hard_research_gaps: list[str] = []
    hard_implementation_gaps: list[str] = []
    if isinstance(receipt_payload, dict):
        pei_errors, pei_posture = _validate_pei_admission_receipt(receipt_payload)
        errors.extend(f"pei_input_receipt: {error}" for error in pei_errors)
        if receipt_payload.get("ticker") != payload.get("ticker"):
            errors.append("Council ticker must equal PEI ticker")
        pei_identity = receipt_payload.get("security_identity")
        if not isinstance(pei_identity, dict):
            errors.append("PEI security_identity is missing")
        else:
            for field in ("symbol", "issuer", "listing", "security_id"):
                if identity.get(field) != pei_identity.get(field):
                    errors.append(
                        f"Council security_identity.{field} must equal PEI security identity"
                    )
        if receipt_payload.get("evidence_cutoff") != payload.get("evidence_cutoff"):
            errors.append("Council evidence_cutoff must equal PEI evidence_cutoff")
        if receipt_ref.get("declared_posture") != receipt_payload.get(
            "output_posture"
        ):
            errors.append(
                "pei_input_receipt.declared_posture does not match referenced receipt"
            )
        if receipt_ref.get("declared_posture") != pei_posture:
            errors.append(
                "pei_input_receipt.declared_posture does not match derived posture"
            )
        for requirement in receipt_payload.get("requirements", []):
            if not isinstance(requirement, dict):
                continue
            requirement_class = requirement.get("requirement_class")
            if requirement.get("status") == "satisfied":
                target = (
                    ambient_evidence
                    if requirement_class == "ambient_context"
                    else accepted_evidence
                )
                target.update(requirement.get("evidence_ids") or [])
            if (
                requirement.get("status") == "gap"
                and requirement.get("criticality") == "hard"
            ):
                label = f"{requirement_class}:{requirement.get('id')}"
                if requirement_class in IMPLEMENTATION_ONLY_CLASSES:
                    hard_implementation_gaps.append(label)
                else:
                    hard_research_gaps.append(label)

    if hard_research_gaps:
        for gap in hard_research_gaps:
            requirement_class = gap.split(":", 1)[0]
            errors.append(
                f"research admission blocked by hard {requirement_class} gap: {gap}"
            )
        expected_admission = "BLOCKED"
    else:
        expected_admission = "ADMITTED"
    if payload.get("research_admission") != expected_admission:
        errors.append(f"research_admission must be {expected_admission}")

    if not _nonempty_string(price.get("source_id")) or (
        price.get("source_id") not in accepted_evidence
    ):
        errors.append("current_price.source_id must be an accepted PEI input")

    sealed_inputs = payload.get("sealed_inputs")
    if not isinstance(sealed_inputs, dict):
        errors.append("sealed_inputs must be an object")
    else:
        missing = sorted(SEALED_INPUTS - set(sealed_inputs))
        extra = sorted(set(sealed_inputs) - SEALED_INPUTS)
        if missing:
            errors.append("sealed_inputs is missing: " + ", ".join(missing))
        if extra:
            errors.append("sealed_inputs has unexpected fields: " + ", ".join(extra))
        for field in SEALED_INPUTS:
            if sealed_inputs.get(field) is not True:
                errors.append(f"sealed_inputs.{field} must be true")

    spine = payload.get("common_factual_spine")
    if not isinstance(spine, dict):
        errors.append("common_factual_spine must be an object")
        spine = {}
    else:
        _expect_keys(spine, {"fields"}, "common_factual_spine", errors)
    forbidden = _find_forbidden_key(spine)
    if forbidden:
        errors.append(forbidden)
    fields = spine.get("fields")
    if not isinstance(fields, list) or not fields:
        errors.append("common_factual_spine.fields must be a non-empty list")
        fields = []
    common_evidence: set[str] = set()
    for index, field in enumerate(fields):
        prefix = f"common_factual_spine.fields[{index}]"
        if not isinstance(field, dict):
            errors.append(f"{prefix} must be an object")
            continue
        field_id = field.get("id")
        if not _nonempty_string(field_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        enum_schema = COMMON_ENUM_FIELDS.get(field_id)
        expected_class = (
            COMMON_NUMERIC_FIELDS.get(field_id)
            or COMMON_TEXT_FIELDS.get(field_id)
            or (enum_schema[0] if enum_schema else None)
        )
        if expected_class is None:
            errors.append(f"{prefix}.id is not an allowed structured fact")
        elif field.get("field_class") != expected_class:
            errors.append(
                f"{prefix}.field_class must be {expected_class} for {field_id}"
            )
        expected_keys = {
            "id",
            "field_class",
            "value",
            "unit",
            "as_of",
            "evidence_ids",
        }
        unexpected_keys = sorted(set(field) - expected_keys)
        if unexpected_keys:
            errors.append(
                f"{prefix} has unexpected fields: {', '.join(unexpected_keys)}"
            )
        value = field.get("value")
        if isinstance(value, (dict, list)):
            errors.append("common factual spine values must be scalar")
        elif field_id in COMMON_NUMERIC_FIELDS and not _number(value):
            errors.append(f"{prefix}.value must be finite numeric for {field_id}")
        elif field_id == "current_price" and (
            not _number(price.get("value"))
            or not math.isclose(
                value, price["value"], rel_tol=1e-9, abs_tol=1e-9
            )
        ):
            errors.append(
                "common factual current_price must equal current_price.value"
            )
        elif field_id in COMMON_TEXT_FIELDS:
            if not _nonempty_string(value) or "\n" in value or "\r" in value:
                errors.append(f"{prefix}.value must be a single-line factual string")
            elif field_id == "issuer_name" and value != identity.get("issuer"):
                errors.append(f"{prefix}.value must equal security_identity.issuer")
            elif field_id == "ticker" and value != identity.get("symbol"):
                errors.append(f"{prefix}.value must equal security_identity.symbol")
            elif field_id == "listing" and value != identity.get("listing"):
                errors.append(f"{prefix}.value must equal security_identity.listing")
            elif field_id == "security_id" and value != identity.get("security_id"):
                errors.append(f"{prefix}.value must equal security_identity.security_id")
            elif field_id == "currency":
                if not re.fullmatch(r"[A-Z]{3}", value):
                    errors.append(f"{prefix}.value must be an ISO-style currency code")
                elif value != price.get("currency"):
                    errors.append(f"{prefix}.value must equal current_price.currency")
            elif field_id == "fiscal_calendar" and not re.fullmatch(
                r"(?:calendar_year|FY_month_(?:0[1-9]|1[0-2]))", value
            ):
                errors.append(f"{prefix}.value has invalid fiscal calendar format")
            elif field_id == "reporting_period" and not re.fullmatch(
                r"(?:FY|Q[1-4])\d{4}", value
            ):
                errors.append(f"{prefix}.value has invalid reporting period format")
            elif field_id == "event_date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    errors.append(f"{prefix}.value must be an ISO date")
        elif enum_schema is not None and value not in enum_schema[1]:
            errors.append(f"{prefix}.value is not an allowed provider enum")
        if not _nonempty_string(field.get("unit")):
            errors.append(f"{prefix}.unit must be a non-empty string")
        _parse_time(field.get("as_of"), f"{prefix}.as_of", errors)
        evidence_ids = field.get("evidence_ids")
        if not _string_list(evidence_ids) or (
            collaboration_available and not evidence_ids
        ):
            qualifier = "non-empty " if collaboration_available else ""
            errors.append(f"{prefix}.evidence_ids must be a {qualifier}string list")
            evidence_ids = []
        unknown = sorted(set(evidence_ids) - accepted_evidence)
        if unknown:
            errors.append(
                f"{prefix} uses non-established evidence: {', '.join(unknown)}"
            )
        common_evidence.update(evidence_ids)

    partitions = payload.get("private_partitions")
    if not isinstance(partitions, dict):
        errors.append("private_partitions must be an object")
        partitions = {}
    if set(partitions) != SEATS:
        errors.append("private_partitions must contain damodaran, soros, and mauboussin")
    partition_evidence: dict[str, set[str]] = {}
    for seat in sorted(SEATS):
        partition = partitions.get(seat)
        prefix = f"private_partitions.{seat}"
        if not isinstance(partition, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unexpected_partition_fields = sorted(
            set(partition) - {"allowed_domains", "evidence_ids"}
        )
        if unexpected_partition_fields:
            errors.append(
                f"{prefix} has unexpected fields: "
                + ", ".join(unexpected_partition_fields)
            )
        domains = partition.get("allowed_domains")
        if not _string_list(domains) or set(domains) != PARTITION_DOMAINS[seat]:
            errors.append(f"{seat}.allowed_domains must equal its method partition")
        evidence_ids = partition.get("evidence_ids")
        if not _string_list(evidence_ids) or not evidence_ids:
            errors.append(f"{prefix}.evidence_ids must be a non-empty string list")
            evidence_ids = []
        unknown = sorted(
            set(evidence_ids) - accepted_evidence - ambient_evidence
        )
        if unknown:
            errors.append(f"{prefix} uses unknown evidence: {', '.join(unknown)}")
        partition_evidence[seat] = set(evidence_ids)

    private_evidence_owners: dict[str, set[str]] = {}
    for seat, evidence_ids in partition_evidence.items():
        for evidence_id in evidence_ids - common_evidence:
            private_evidence_owners.setdefault(evidence_id, set()).add(seat)
    for evidence_id, owners in sorted(private_evidence_owners.items()):
        if len(owners) > 1:
            errors.append(
                "private evidence appears in multiple method partitions: "
                f"{evidence_id} -> {', '.join(sorted(owners))}"
            )

    first_round = payload.get("first_round")
    if not isinstance(first_round, dict):
        errors.append("first_round must be an object")
        first_round = {}
    else:
        _expect_keys(
            first_round, {"unavailable_seats", "memos"}, "first_round", errors
        )
    memos = first_round.get("memos")
    if not isinstance(memos, list):
        errors.append("first_round.memos must be a list")
        memos = []
    memos_by_seat: dict[str, dict[str, Any]] = {}
    contributions: dict[str, dict[str, Any]] = {}
    method_artifacts: dict[str, dict[str, Any]] = {}
    method_completions: dict[str, str] = {}
    proposition_owners: dict[str, str] = {}
    latest_sealed_at: datetime | None = None
    for index, memo in enumerate(memos):
        prefix = f"first_round.memos[{index}]"
        if not isinstance(memo, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            memo,
            {
                "seat",
                "method_completion",
                "work_product",
                "method_artifact",
                "sealed_at",
                "browsed",
                "added_evidence_ids",
                "accepted_evidence_ids",
                "research_lead_ids",
                "contribution",
                "provisional_direction",
            },
            prefix,
            errors,
        )
        seat = memo.get("seat")
        if not _allowed_string(seat, SEATS):
            errors.append(f"{prefix}.seat is invalid: {seat!r}")
            continue
        if seat in memos_by_seat:
            errors.append(f"duplicate first-round memo: {seat}")
        memos_by_seat[seat] = memo
        if not _allowed_string(memo.get("method_completion"), METHOD_COMPLETION):
            errors.append(f"{prefix}.method_completion is invalid")
        if not _nonempty_string(memo.get("work_product")):
            errors.append(f"{prefix}.work_product must be a non-empty string")
        if memo.get("browsed") is not False:
            errors.append(f"{prefix}.browsed must be false")
        if memo.get("added_evidence_ids") != []:
            errors.append(f"{prefix}.added_evidence_ids must be empty")
        sealed_at = _parse_time(memo.get("sealed_at"), f"{prefix}.sealed_at", errors)
        if sealed_at is not None and (
            latest_sealed_at is None or sealed_at > latest_sealed_at
        ):
            latest_sealed_at = sealed_at
        accepted_ids = memo.get("accepted_evidence_ids")
        if not _string_list(accepted_ids):
            errors.append(f"{prefix}.accepted_evidence_ids must be a string list")
            accepted_ids = []
        unknown_accepted = sorted(set(accepted_ids) - accepted_evidence)
        if unknown_accepted:
            errors.append(
                f"{prefix} uses unaccepted evidence: {', '.join(unknown_accepted)}"
            )
        packet_evidence = common_evidence | partition_evidence.get(seat, set())
        outside_packet = sorted(set(accepted_ids) - packet_evidence)
        if outside_packet:
            errors.append(
                f"{prefix} uses accepted evidence outside its sealed packet: "
                + ", ".join(outside_packet)
            )
        lead_ids = memo.get("research_lead_ids")
        if not _string_list(lead_ids):
            errors.append(f"{prefix}.research_lead_ids must be a string list")
            lead_ids = []
        unknown_leads = sorted(set(lead_ids) - ambient_evidence)
        if unknown_leads:
            errors.append(
                f"{prefix} uses research leads not accepted by PEI: "
                + ", ".join(unknown_leads)
            )
        outside_leads = sorted(set(lead_ids) - partition_evidence.get(seat, set()))
        if outside_leads:
            errors.append(
                f"{prefix} uses research leads outside its sealed packet: "
                + ", ".join(outside_leads)
            )
        contribution = _validate_contribution(
            memo.get("contribution"), f"{prefix}.contribution", errors
        )
        contributions[seat] = contribution
        method_artifact = memo.get("method_artifact")
        method_evidence = set(accepted_ids)
        completion = memo.get("method_completion")
        method_completions[seat] = completion
        if isinstance(method_artifact, dict):
            method_artifacts[seat] = method_artifact
            proposition_id = method_artifact.get("proposition_id")
            if _nonempty_string(proposition_id):
                prior_owner = proposition_owners.get(proposition_id)
                if prior_owner is not None and prior_owner != seat:
                    errors.append(
                        "method artifact proposition_id must be unique across seats"
                    )
                proposition_owners[proposition_id] = seat
        if seat == "damodaran":
            _validate_damodaran_artifact(
                method_artifact,
                completion=completion,
                price=price,
                horizon=payload.get("decision_horizon"),
                allowed_evidence=method_evidence,
                errors=errors,
            )
        elif seat == "soros":
            _validate_soros_artifact(
                method_artifact,
                completion=completion,
                horizon=payload.get("decision_horizon"),
                allowed_evidence=method_evidence,
                errors=errors,
            )
        else:
            _validate_mauboussin_artifact(
                method_artifact,
                completion=completion,
                price=price,
                horizon=payload.get("decision_horizon"),
                allowed_evidence=method_evidence,
                errors=errors,
            )
    unavailable_seats = first_round.get("unavailable_seats")
    if not _string_list(unavailable_seats):
        errors.append("first_round.unavailable_seats must be a string list")
        unavailable_seats = []
    if collaboration_available and unavailable_seats:
        errors.append(
            "collaboration_available runtime cannot declare unavailable seats"
        )
    if collaboration_available and set(memos_by_seat) != SEATS:
        errors.append("first_round must contain exactly the three named seat memos")
    if not collaboration_available:
        if memos:
            errors.append("unavailable runtime cannot contain member memos")
        if set(unavailable_seats) != SEATS:
            errors.append(
                "unavailable runtime must mark all three named seats unavailable"
            )

    first_converged, implicated = _convergence(contributions)
    convergence = payload.get("convergence")
    if not isinstance(convergence, dict):
        errors.append("convergence must be an object")
        convergence = {}
    else:
        _expect_keys(
            convergence,
            {
                "first_pass_status",
                "implicated_seats",
                "semantic_review",
                "corrective_pass_count",
                "corrective_memos",
                "final_status",
            },
            "convergence",
            errors,
        )
    implicated_declared = convergence.get("implicated_seats")
    semantic_review = convergence.get("semantic_review")
    if not isinstance(semantic_review, dict):
        errors.append("convergence.semantic_review must be an object")
        semantic_review = {}
    else:
        _expect_keys(
            semantic_review,
            {
                "reviewed",
                "first_overlap_detected",
                "final_overlap_detected",
                "rationale",
            },
            "convergence.semantic_review",
            errors,
        )
    first_semantic_overlap = semantic_review.get("first_overlap_detected")
    final_semantic_overlap = semantic_review.get("final_overlap_detected")
    if not isinstance(first_semantic_overlap, bool):
        errors.append(
            "convergence.semantic_review.first_overlap_detected must be boolean"
        )
        first_semantic_overlap = False
    if not isinstance(final_semantic_overlap, bool):
        errors.append(
            "convergence.semantic_review.final_overlap_detected must be boolean"
        )
        final_semantic_overlap = False
    if not _nonempty_string(semantic_review.get("rationale")):
        errors.append("convergence.semantic_review.rationale must be non-empty")
    if collaboration_available and semantic_review.get("reviewed") is not True:
        errors.append(
            "available Council requires a completed semantic convergence review"
        )
    if not collaboration_available and semantic_review.get("reviewed") is not False:
        errors.append(
            "unavailable Council requires semantic convergence review marked unreviewed"
        )
    corrective_count = convergence.get("corrective_pass_count")
    if (
        not isinstance(corrective_count, int)
        or isinstance(corrective_count, bool)
        or corrective_count not in {0, 1}
    ):
        errors.append("corrective_pass_count must be 0 or 1")

    corrective_memos = convergence.get("corrective_memos")
    if not isinstance(corrective_memos, list):
        errors.append("convergence.corrective_memos must be a list")
        corrective_memos = []
    declared_implicated_set = (
        set(implicated_declared) if _string_list(implicated_declared) else set()
    )
    effective = {
        seat: dict(contribution) for seat, contribution in contributions.items()
    }
    corrected_seats: set[str] = set()
    for index, memo in enumerate(corrective_memos):
        prefix = f"convergence.corrective_memos[{index}]"
        if not isinstance(memo, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            memo,
            {"seat", "browsed", "added_evidence_ids", "contribution"},
            prefix,
            errors,
        )
        seat = memo.get("seat")
        if seat not in declared_implicated_set:
            errors.append(f"{prefix}.seat must be implicated in convergence")
            continue
        if seat in corrected_seats:
            errors.append(f"duplicate corrective memo: {seat}")
        corrected_seats.add(seat)
        if memo.get("browsed") is not False:
            errors.append(f"{prefix}.browsed must be false")
        if memo.get("added_evidence_ids") != []:
            errors.append(f"{prefix}.added_evidence_ids must be empty")
        effective[seat] = _validate_contribution(
            memo.get("contribution"), f"{prefix}.contribution", errors
        )
    if collaboration_available:
        if first_converged and not first_semantic_overlap:
            errors.append(
                "semantic review must flag canonical contribution collisions"
            )
        detected_first_convergence = first_converged or first_semantic_overlap
        expected_first_status = (
            "persona_convergence" if detected_first_convergence else "distinct"
        )
        if convergence.get("first_pass_status") != expected_first_status:
            errors.append(
                f"convergence.first_pass_status must be {expected_first_status}"
            )
        if detected_first_convergence:
            if (
                not _string_list(implicated_declared)
                or len(declared_implicated_set) < 2
                or not declared_implicated_set <= SEATS
                or not implicated <= declared_implicated_set
            ):
                errors.append(
                    "convergence.implicated_seats must cover detected convergent seats"
                )
        elif implicated_declared != []:
            errors.append(
                "distinct contributions require empty convergence.implicated_seats"
            )
        if detected_first_convergence and corrective_count != 1:
            errors.append("persona_convergence requires exactly one corrective pass")
        if not detected_first_convergence and corrective_count != 0:
            errors.append("distinct first pass cannot run a corrective pass")
        if corrective_count == 0 and corrective_memos:
            errors.append(
                "corrective_memos must be empty when corrective_pass_count is 0"
            )
        if corrective_count == 1 and not corrective_memos:
            errors.append("one corrective pass requires at least one corrective memo")
        lexical_final_converged, _ = _convergence(effective)
        if lexical_final_converged and not final_semantic_overlap:
            errors.append(
                "final semantic review must flag canonical contribution collisions"
            )
        if corrective_count == 0 and (
            final_semantic_overlap != first_semantic_overlap
        ):
            errors.append(
                "semantic overlap cannot change without a corrective pass"
            )
        final_converged = lexical_final_converged or final_semantic_overlap
        expected_final_status = (
            "unresolved_convergence" if final_converged else "distinct"
        )
        if convergence.get("final_status") != expected_final_status:
            errors.append(
                f"convergence.final_status must be {expected_final_status}"
            )
    else:
        final_converged = False
        if first_semantic_overlap or final_semantic_overlap:
            errors.append(
                "unavailable runtime cannot claim semantic persona convergence"
            )
        if convergence.get("first_pass_status") != "unavailable":
            errors.append(
                "unavailable runtime requires convergence.first_pass_status unavailable"
            )
        if not _string_list(implicated_declared) or implicated_declared:
            errors.append(
                "unavailable runtime requires empty convergence.implicated_seats"
            )
        if corrective_count != 0:
            errors.append(
                "unavailable runtime requires corrective_pass_count 0"
            )
        if corrective_memos:
            errors.append(
                "unavailable runtime requires empty corrective_memos"
            )
        if convergence.get("final_status") != "unavailable":
            errors.append(
                "unavailable runtime requires convergence.final_status unavailable"
            )

    chair = payload.get("chair")
    if not isinstance(chair, dict):
        errors.append("chair must be an object")
        chair = {}
    else:
        _expect_keys(
            chair,
            {
                "name",
                "public_method_persona",
                "started_at",
                "finalized_at",
                "evidence_closed",
                "browsed",
                "added_evidence_ids",
                "used_evidence_ids",
                "seat_decisions",
                "dominant_variable",
                "strongest_disconfirming_path",
                "reversal_trigger",
                "decision_matrix",
                "gross_expected_return_pct",
                "research_stance",
                "confidence",
                "robustness",
                "participation",
                "implementation_readiness",
                "implementation_blockers",
                "independent_confirmation",
            },
            "chair",
            errors,
        )
    if chair.get("name") != "Stanley Druckenmiller — PM Chair":
        errors.append("chair.name must be Stanley Druckenmiller — PM Chair")
    if chair.get("public_method_persona") is not True:
        errors.append("chair.public_method_persona must be true")
    chair_started = _parse_time(chair.get("started_at"), "chair.started_at", errors)
    chair_finalized = _parse_time(
        chair.get("finalized_at"), "chair.finalized_at", errors
    )
    if (
        chair_started is not None
        and latest_sealed_at is not None
        and chair_started < latest_sealed_at
    ):
        errors.append("chair cannot start before all first-round memos are sealed")
    if (
        chair_started is not None
        and chair_finalized is not None
        and chair_finalized < chair_started
    ):
        errors.append("chair.finalized_at cannot precede chair.started_at")
    if chair.get("evidence_closed") is not True:
        errors.append("chair.evidence_closed must be true")
    if chair.get("browsed") is not False:
        errors.append("chair.browsed must be false")
    if chair.get("added_evidence_ids") != []:
        errors.append("chair.added_evidence_ids must be empty")
    used_evidence = chair.get("used_evidence_ids")
    if not _string_list(used_evidence):
        errors.append("chair.used_evidence_ids must be a string list")
        used_evidence = []
    unknown_chair_evidence = sorted(set(used_evidence) - accepted_evidence)
    if unknown_chair_evidence:
        errors.append(
            "chair used evidence outside accepted PEI inputs: "
            + ", ".join(unknown_chair_evidence)
        )
    if chair.get("independent_confirmation") is not False:
        errors.append("chair.independent_confirmation must be false")

    seat_decisions = chair.get("seat_decisions")
    if not isinstance(seat_decisions, list):
        errors.append("chair.seat_decisions must be a list")
        seat_decisions = []
    decision_seats: set[str] = set()
    for index, decision in enumerate(seat_decisions):
        prefix = f"chair.seat_decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _expect_keys(
            decision,
            {
                "seat",
                "decision",
                "proposition_id",
                "proposition",
                "reason",
                "retained_limitation",
                "impact",
            },
            prefix,
            errors,
        )
        decision_seat = decision.get("seat")
        if not _allowed_string(decision_seat, SEATS):
            errors.append(f"{prefix}.seat is invalid")
        elif decision_seat in decision_seats:
            errors.append(f"duplicate chair seat decision: {decision_seat}")
        else:
            decision_seats.add(decision_seat)
        if not _allowed_string(decision.get("decision"), CHAIR_DECISIONS):
            errors.append(f"{prefix}.decision is invalid")
        artifact = method_artifacts.get(decision_seat)
        if isinstance(artifact, dict) and decision.get(
            "proposition_id"
        ) != artifact.get("proposition_id"):
            errors.append(
                "chair seat decision proposition_id must match its method artifact"
            )
        _require_text_fields(
            decision, ("proposition", "reason", "retained_limitation"), prefix, errors
        )
        impact = decision.get("impact")
        if not isinstance(impact, dict):
            errors.append(f"{prefix}.impact must be an object")
        else:
            _expect_keys(
                impact,
                {"stance", "participation_effect", "refresh_route"},
                f"{prefix}.impact",
                errors,
            )
            _require_text_fields(
                impact,
                ("stance", "participation_effect", "refresh_route"),
                f"{prefix}.impact",
                errors,
            )
    if collaboration_available and decision_seats != SEATS:
        errors.append("chair.seat_decisions must cover all three seats")
    if not collaboration_available and seat_decisions:
        errors.append("unavailable runtime cannot contain member seat decisions")

    for field in (
        "dominant_variable",
        "strongest_disconfirming_path",
        "reversal_trigger",
    ):
        if not _nonempty_string(chair.get(field)):
            errors.append(f"chair.{field} must be a non-empty string")
    if not _allowed_string(chair.get("research_stance"), STANCES):
        errors.append("chair.research_stance must be Long, Short, or Avoid")
    if not _allowed_string(chair.get("confidence"), CONFIDENCE):
        errors.append("chair.confidence must be High, Medium, or Low")
    if not _allowed_string(chair.get("robustness"), ROBUSTNESS):
        errors.append("chair.robustness must be Robust, Conditional, or Fragile")
    if not _allowed_string(chair.get("participation"), PARTICIPATION):
        errors.append(
            "chair.participation must be Eligible, Conditional, or Stand aside"
        )
    if not _allowed_string(
        chair.get("implementation_readiness"), IMPLEMENTATION_READINESS
    ):
        errors.append(
            "chair.implementation_readiness must be Ready, Conditional, or Blocked"
        )
    if not _string_list(chair.get("implementation_blockers")):
        errors.append("chair.implementation_blockers must be a string list")

    numeric_eligible = collaboration_available and any(
        completion == "Complete" for completion in method_completions.values()
    )
    if numeric_eligible:
        _validate_chair_matrix(
            chair.get("decision_matrix"),
            chair=chair,
            price=price,
            horizon=payload.get("decision_horizon"),
            accepted_evidence=accepted_evidence,
            method_artifacts=method_artifacts,
            method_completions=method_completions,
            collaboration_available=collaboration_available,
            errors=errors,
        )

        gross_return = chair.get("gross_expected_return_pct")
        if not isinstance(gross_return, (int, float)) or isinstance(gross_return, bool):
            errors.append("chair.gross_expected_return_pct must be numeric")
        elif math.isclose(gross_return, 0.0, abs_tol=1e-9):
            if chair.get("research_stance") != "Avoid":
                errors.append("research_stance must be Avoid for zero gross expected return")
        elif gross_return > 0 and chair.get("research_stance") != "Long":
            errors.append("research_stance must be Long for positive gross expected return")
        elif gross_return < 0 and chair.get("research_stance") != "Short":
            errors.append("research_stance must be Short for negative gross expected return")
    else:
        qualitative_reason = (
            "all-Partial Council"
            if collaboration_available
            else "unavailable Council runtime"
        )
        if chair.get("decision_matrix") is not None:
            errors.append(
                f"{qualitative_reason} must not produce a numeric decision matrix"
            )
        if chair.get("gross_expected_return_pct") is not None:
            errors.append(
                f"{qualitative_reason} must not produce numeric expected return"
            )
        if chair.get("robustness") != "Fragile":
            errors.append(f"{qualitative_reason} requires Fragile robustness")

    if final_converged and chair.get("robustness") != "Fragile":
        errors.append("unresolved persona convergence requires Fragile robustness")
    if not collaboration_available and chair.get("robustness") != "Fragile":
        errors.append("unavailable Council runtime requires Fragile robustness")
    if hard_implementation_gaps:
        if chair.get("participation") != "Stand aside":
            errors.append(
                "hard implementation or portfolio gaps require participation Stand aside"
            )
        if chair.get("implementation_readiness") != "Blocked":
            errors.append(
                "hard implementation or portfolio gaps require implementation readiness Blocked"
            )

    _validate_current_artifact_bindings(payload, Path(artifact_dir), errors)

    return errors


def _default_artifact_root(council_path: Path) -> Path:
    return council_path.parent.parent if council_path.parent.name == "support" else council_path.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Equity Council run artifact.")
    parser.add_argument("--plugin-root", required=True, type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("council_run", type=Path)
    args = parser.parse_args()

    load_errors: list[str] = []
    payload = _load_json(args.council_run, "Council run", load_errors)
    if payload is None:
        for error in load_errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    errors = validate(
        payload,
        plugin_root=args.plugin_root,
        artifact_dir=args.artifact_root or _default_artifact_root(args.council_run),
    )
    if errors:
        print("FAIL: Council run is invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: Council run is valid: {args.council_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
