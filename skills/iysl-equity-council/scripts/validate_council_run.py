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
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
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


SOURCE_CHECK_TOOLS = {
    "codex-in-app-browser",
    "mcp__codex_apps__exa_web_search_exa",
    "mcp__codex_apps__exa_web_fetch_exa",
    "WebSearch", "WebFetch",
}


def validate_source_checks(packet: Any, memo: Any) -> list[str]:
    """Check an opt-in packet/memo pair before the full Council root exists.

    This checks declarations, not whether the host actually made the tool calls.
    """
    errors: list[str] = []
    if not isinstance(packet, dict) or packet.get("search_required") is not True:
        return ["packet.search_required must be true for source-check validation"]
    if not isinstance(memo, dict) or not isinstance(memo.get("challenges"), list):
        return ["memo.challenges must be a list"]
    candidates = packet.get("candidate_assumptions")
    if not isinstance(candidates, list) or any(not isinstance(row, dict) or not _nonempty_string(row.get("assumption_id")) for row in candidates):
        return ["packet.candidate_assumptions must name assumption IDs"]
    expected_ids = [row["assumption_id"] for row in candidates]
    seen_ids: list[str] = []
    for index, challenge in enumerate(memo["challenges"]):
        label = f"memo.challenges[{index}]"
        if not isinstance(challenge, dict):
            errors.append(f"{label} must be an object")
            continue
        seen_ids.append(challenge.get("assumption_id"))
        checks = challenge.get("source_checks")
        if not isinstance(checks, list):
            errors.append(f"{label}.source_checks must be a list")
            continue
        if challenge.get("estimation_status") == "not_estimable" and not checks:
            errors.append(f"{label} not_estimable requires source_checks")
        for check_index, check in enumerate(checks):
            check_label = f"{label}.source_checks[{check_index}]"
            if not isinstance(check, dict):
                errors.append(f"{check_label} must be an object")
                continue
            _expect_keys(check, {"tool", "query_or_url", "result", "still_insufficient_reason"}, check_label, errors)
            tool = check.get("tool")
            if not isinstance(tool, str) or tool not in SOURCE_CHECK_TOOLS:
                errors.append(f"{check_label}.tool is not an allowed source channel")
            for field in ("query_or_url", "result", "still_insufficient_reason"):
                if not _nonempty_string(check.get(field)):
                    errors.append(f"{check_label}.{field} must be non-empty")
    if sorted(seen_ids, key=str) != sorted(expected_ids):
        errors.append("memo.challenges must cover each packet assumption exactly once")
    return errors


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


def _historical_correction_facts(
    value: Any, label: str, errors: list[str]
) -> list[dict[str, Any]] | None:
    start = len(errors)
    expected_periods = ["FY2023A", "FY2024A", "FY2025A"]
    value_field_sets = (
        ("revenue", "operating_income"),
        ("cash_from_operations", "capital_expenditure", "depreciation_and_amortization"),
    )
    if not isinstance(value, list) or len(value) != len(expected_periods):
        errors.append(f"{label} must contain exactly three annual rows")
        return None
    normalized: list[dict[str, Any]] = []
    selected_fields: tuple[str, ...] | None = None
    for index, row in enumerate(value):
        row_label = f"{label}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{row_label} is invalid")
            continue
        row_fields = set(row) - {"period", "unit"}
        matching_fields = next(
            (fields for fields in value_field_sets if row_fields == set(fields)), None
        )
        if matching_fields is None or (
            selected_fields is not None and matching_fields != selected_fields
        ):
            errors.append(f"{row_label} is invalid")
            continue
        selected_fields = matching_fields
        if row.get("period") != expected_periods[index]:
            errors.append(f"{row_label}.period is invalid")
        if row.get("unit") != "USD millions":
            errors.append(f"{row_label}.unit must be USD millions")
        if any(not _number(row.get(field)) for field in matching_fields):
            errors.append(f"{row_label} financial values must be finite numeric")
            continue
        normalized.append(
            {
                "period": row["period"],
                **{field: float(row[field]) for field in matching_fields},
                "unit": row["unit"],
            }
        )
    return normalized if len(errors) == start else None


def _validated_correction_evidence(
    artifact_root: Path,
    descriptor: Any,
    *,
    root_identity: tuple[Any, Any, Any],
    reference_price: Any,
    errors: list[str],
) -> set[str]:
    """Reopen the narrow post-cutoff correction chain before admitting its IDs."""

    start = len(errors)
    correction_set, _ = _descriptor_payload(
        artifact_root,
        descriptor,
        "correction_validation_set",
        errors,
    )
    if correction_set is None:
        return set()
    _expect_keys(
        correction_set,
        {
            "schema_version",
            "receipt_type",
            "ticker",
            "security_id",
            "evidence_cutoff",
            "reference_price_usd",
            "validation_status",
            "corrections",
        },
        "correction validation set",
        errors,
    )
    if (
        correction_set.get("schema_version")
        != "formal-correction-validation-set-v1"
        or correction_set.get("receipt_type") != "formal_correction_validation_set"
        or _identity_values(correction_set) != root_identity
        or correction_set.get("validation_status") != "PASS"
    ):
        errors.append("correction validation set schema or identity is invalid")
    if (
        not _number(reference_price)
        or not _number(correction_set.get("reference_price_usd"))
        or not math.isclose(
            float(correction_set.get("reference_price_usd", 0)),
            float(reference_price or 0),
            rel_tol=0,
            abs_tol=1e-12,
        )
    ):
        errors.append("correction validation set reference price must equal Council price")

    cutoff = _parse_time(root_identity[2], "correction validation cutoff", errors)
    corrections = correction_set.get("corrections")
    if not isinstance(corrections, list) or not corrections:
        errors.append("correction validation set corrections must be non-empty")
        return set()

    accepted_ids: set[str] = set()
    correction_fields = {
        "accepted_evidence_id",
        "allowed_use",
        "observation_timing",
        "acceptance_receipt",
        "accepted_fields",
    }
    receipt_fields = {
        "schema_version",
        "receipt_type",
        "security_id",
        "observation",
        "accepted_evidence_id",
        "accepted_fields",
        "scope_controls",
        "validation_status",
    }
    expected_controls = {
        "evidence_cutoff_preserved": root_identity[2],
        "reference_price_usd_preserved": reference_price,
        "new_provider_data_used": False,
        "seeking_alpha_refreshed": False,
        "new_consensus_or_price_data_used": False,
        "accepted_evidence_ids_changed_outside_scoped_primary_historical_receipt": False,
    }
    for index, correction in enumerate(corrections):
        label = f"correction validation set corrections[{index}]"
        if not isinstance(correction, dict):
            errors.append(f"{label} must be an object")
            continue
        _expect_keys(correction, correction_fields, label, errors)
        evidence_id = correction.get("accepted_evidence_id")
        if not _nonempty_string(evidence_id) or not evidence_id.startswith("SEC:"):
            errors.append(f"{label}.accepted_evidence_id must be an SEC evidence ID")
        elif evidence_id in accepted_ids:
            errors.append(f"{label}.accepted_evidence_id is duplicated")
        else:
            accepted_ids.add(evidence_id)
        if (
            correction.get("allowed_use") != "historical_field_correction_only"
            or correction.get("observation_timing") != "post_cutoff_validation_only"
        ):
            errors.append(f"{label} scope is invalid")
        corrected_facts = _historical_correction_facts(
            correction.get("accepted_fields"), f"{label}.accepted_fields", errors
        )

        receipt_descriptor = correction.get("acceptance_receipt")
        receipt_path = _safe_artifact_path(
            artifact_root,
            receipt_descriptor.get("path")
            if isinstance(receipt_descriptor, dict)
            else None,
            f"{label}.acceptance_receipt.path",
            errors,
        )
        receipt, _ = _descriptor_payload(
            artifact_root,
            receipt_descriptor,
            f"{label}.acceptance_receipt",
            errors,
        )
        if receipt is None or receipt_path is None:
            continue
        if not receipt_fields <= set(receipt):
            errors.append(f"{label}.acceptance_receipt is missing required fields")
            continue
        if (
            receipt.get("schema_version")
            != "scoped-primary-historical-acceptance-receipt-v1"
            or receipt.get("receipt_type") != "scoped_primary_historical_acceptance"
            or receipt.get("security_id") != root_identity[1]
            or receipt.get("accepted_evidence_id") != evidence_id
            or receipt.get("validation_status") != "PASS"
        ):
            errors.append(f"{label}.acceptance_receipt schema or identity is invalid")
        receipt_facts = _historical_correction_facts(
            receipt.get("accepted_fields"),
            f"{label}.acceptance_receipt.accepted_fields",
            errors,
        )
        if corrected_facts is not None and receipt_facts != corrected_facts:
            errors.append(f"{label}.accepted_fields do not match the acceptance receipt")

        controls = receipt.get("scope_controls")
        if not isinstance(controls, dict) or set(controls) != set(expected_controls):
            errors.append(f"{label}.acceptance_receipt.scope_controls are invalid")
        elif any(
            controls.get(field) != expected
            for field, expected in expected_controls.items()
            if field != "reference_price_usd_preserved"
        ) or (
            not _number(controls.get("reference_price_usd_preserved"))
            or not math.isclose(
                float(controls["reference_price_usd_preserved"]),
                float(reference_price),
                rel_tol=0,
                abs_tol=1e-12,
            )
        ):
            errors.append(f"{label}.acceptance_receipt.scope_controls drift")

        observation_descriptor = receipt.get("observation")
        observation_path = _safe_artifact_path(
            receipt_path.parent,
            observation_descriptor.get("path")
            if isinstance(observation_descriptor, dict)
            else None,
            f"{label}.acceptance_receipt.observation.path",
            errors,
        )
        observation, _ = _descriptor_payload(
            receipt_path.parent,
            observation_descriptor,
            f"{label}.acceptance_receipt.observation",
            errors,
        )
        if observation is None or observation_path is None:
            continue
        if observation_path.parent != receipt_path.parent.resolve():
            errors.append(f"{label}.acceptance_receipt.observation must be sibling-contained")
        retrieval = observation.get("retrieval")
        if (
            observation.get("schema_version")
            != "issuer-primary-visible-dom-observation-v1"
            or observation.get("receipt_type") != "issuer_primary_visible_dom_observation"
            or observation.get("security_id") != root_identity[1]
            or not isinstance(retrieval, dict)
            or retrieval.get("surface") != "codex_in_app_browser_visible_dom"
            or retrieval.get("form") != "10-K"
            or retrieval.get("evidence_cutoff") != root_identity[2]
            or retrieval.get("underlying_document_predates_evidence_cutoff") is not True
            or not isinstance(retrieval.get("document_url"), str)
            or not retrieval["document_url"].startswith("https://www.sec.gov/Archives/")
        ):
            errors.append(f"{label}.acceptance_receipt.observation authority is invalid")
        observation_facts = _historical_correction_facts(
            observation.get("observed_facts"),
            f"{label}.acceptance_receipt.observation.observed_facts",
            errors,
        )
        if receipt_facts is not None and observation_facts != receipt_facts:
            errors.append(f"{label}.acceptance_receipt facts differ from observation")
        try:
            filed = date.fromisoformat(retrieval.get("filed_date"))
        except (AttributeError, TypeError, ValueError):
            errors.append(f"{label}.acceptance_receipt.observation filed_date is invalid")
        else:
            if cutoff is not None and filed > cutoff.date():
                errors.append(f"{label}.acceptance_receipt.observation postdates cutoff")

    return accepted_ids if len(errors) == start else set()


def _validate_model_mapping(preliminary, family, decision, final_spec, label, errors):
    """Check model field meaning using the owner's dependency graph, not ID spelling."""
    leaves = final_spec.get('dependency_graph', {}).get('leaves', {})
    if not leaves:
        return  # Historical minimal model specs retain their existing ID coverage check.
    fields = {key: value for key, value in leaves.items()
              if isinstance(value, dict) and value.get('provenance_id') in decision['model_input_ids']}
    patterns = {
        'revenue_orders_capex_recognition': r'\.(growth|revenue|premium_growth|investment_income_growth)(\.|$)',
        'product_mix_and_margins': r'\.(margin|loss_ratio|expense_ratio|annual_fee_rate)(\.|$)',
        'reinvestment_and_fcff': r'\.(capex(?:_percent_revenue)?|da_percent(?:_revenue)?|nwc(?:_percent(?:_revenue)?)?|cash_conversion|roic|reinvestment|reserve_growth|roe|book_growth)(\.|$)',
        'capital_structure_and_wacc': r'\.(wacc|discount|risk_free|erp|beta|shares|.*shares|cash|debt|cost_of(?:_(?:equity|debt))?)($|\.)',
        'duration_fade_and_terminal': r'\.(terminal|fade|duration|holding_days|terminal_growth|terminal_roe)(\.|$)',
        'twelve_month_market_expectations': r'\.(growth|revenue|multiple|expectations|asset_return|investment_income_growth)(\.|$)',
    }
    pattern = patterns.get(family)
    if pattern is None:
        return
    compatible = {key: value for key, value in fields.items() if re.search(pattern, key)}
    if not compatible or (any('.downside.' in key or '.upside.' in key for key in compatible)
                          and not any('.base.' in key for key in compatible)):
        errors.append(f'{label}.model_input_ids do not map to the Base {family} model fields')
    if family == 'product_mix_and_margins' and compatible:
        base = [value.get('value') for key, value in compatible.items() if '.base.' in key]
        final_base = decision.get('final_base')
        matches_base = any(
            _number(value) and _number(final_base)
            and math.isclose(value, final_base, rel_tol=1e-9, abs_tol=1e-9)
            for value in base
        )
        insurer_combined_ratio = (
            final_spec.get('formula_version')
            in {'insurer-residual-income-v1', 'insurer-residual-income-v2', 'insurer-residual-income-v3'}
        )
        base_loss = compatible.get('input.base.loss_ratio', {}).get('value')
        base_expense = compatible.get('input.base.expense_ratio', {}).get('value')
        matches_insurer_combined = (
            insurer_combined_ratio
            and _number(base_loss)
            and _number(base_expense)
            and _number(final_base)
            and math.isclose(base_loss + base_expense, final_base, rel_tol=1e-9, abs_tol=1e-9)
        )
        if base and not matches_base and not matches_insurer_combined:
            errors.append(f'{label}.final_base does not match its mapped Base margin values')


def _contains_forbidden_agent_output(value: Any, *, blind_packet: bool = False) -> str | None:
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
    if blind_packet:
        forbidden |= {
            "proposed_base", "proposed_range", "prior_base", "prior_range",
            "owner_base", "owner_range", "fair_value", "final_fair_value",
            "stance", "execution_instruction", "final_owner_model",
            "other_seat_outputs", "other_seat_memo", "sealed_memos",
        }
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in forbidden:
                return key
            found = _contains_forbidden_agent_output(child, blind_packet=blind_packet)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_forbidden_agent_output(child, blind_packet=blind_packet)
            if found:
                return found
    return None


def _ordered_range(value: Any) -> bool:
    return (
        isinstance(value, list) and len(value) == 2
        and all(_number(item) for item in value) and value[0] <= value[1]
    )


def _validate_blind_case(value: Any, label: str, errors: list[str], *, soros_upside: bool = False) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    fields = {"mechanism", "joint_conditions", "observable_triggers", "falsifier"}
    if soros_upside:
        fields.add("missed_entry_cost")
    _expect_keys(value, fields, label, errors)
    for field in fields - {"joint_conditions", "observable_triggers"}:
        if not _nonempty_string(value.get(field)):
            errors.append(f"{label}.{field} must be non-empty")
    for field in ("joint_conditions", "observable_triggers"):
        if not _string_list(value.get(field)) or not value[field]:
            errors.append(f"{label}.{field} must be a non-empty string list")


def _validate_agent_council_v3(
    payload: dict[str, Any], *, artifact_dir: Path,
    comparison_output: dict[str, dict[str, str]] | None = None,
) -> list[str]:
    """Validate only durable mechanics; investment judgment stays with PEI."""

    errors: list[str] = []
    blind = payload.get("schema_version") == 5
    discovery = payload.get("schema_version") in {4, 5}
    root_fields = {
        "schema_version",
        "council_runtime",
        "ticker",
        "security_identity",
        "current_price",
        "decision_horizon",
        "pei_input_receipt",
        "research_admission",
        "artifact_bindings",
    }
    if not blind or "evidence_cutoff" in payload:
        root_fields.add("evidence_cutoff")
    if discovery:
        root_fields.add("council_input_pei_receipt")
    split_cutoff_fields = {
        "owner_model_evidence_cutoff",
        "final_research_evidence_cutoff",
    }
    present_split_cutoff_fields = split_cutoff_fields & set(payload)
    root_fields.update(present_split_cutoff_fields)
    if present_split_cutoff_fields:
        root_fields.add("owner_model_pei_input_receipt")
    if "correction_validation_set" in payload:
        root_fields.add("correction_validation_set")
    _expect_keys(
        payload,
        root_fields,
        "root",
        errors,
    )
    if payload.get("council_runtime") != "collaboration_available":
        errors.append("current formal Council requires collaboration_available")
    if not _nonempty_string(payload.get("ticker")):
        errors.append("ticker must be a non-empty string")
    if not _nonempty_string(payload.get("decision_horizon")):
        errors.append("decision_horizon must be a non-empty string")
    receipt, _ = _descriptor_payload(
        artifact_dir, payload.get("pei_input_receipt"), "pei_input_receipt", errors
    )
    # A v5 root may omit evidence_cutoff; the final PEI receipt cutoff anchors identity.
    root_cutoff = payload.get("evidence_cutoff", _identity_values(receipt or {})[2])
    cutoff = _parse_time(root_cutoff, "evidence_cutoff", errors)
    owner_model_cutoff = root_cutoff
    if present_split_cutoff_fields:
        if present_split_cutoff_fields != split_cutoff_fields:
            errors.append("Council split cutoff fields must be complete")
        owner_model_cutoff = payload.get("owner_model_evidence_cutoff")
        owner_cutoff = _parse_time(
            owner_model_cutoff, "owner_model_evidence_cutoff", errors
        )
        final_cutoff = _parse_time(
            payload.get("final_research_evidence_cutoff"),
            "final_research_evidence_cutoff",
            errors,
        )
        if root_cutoff != payload.get("final_research_evidence_cutoff"):
            errors.append("Council evidence_cutoff must equal final research cutoff")
        if (
            owner_cutoff is not None
            and final_cutoff is not None
            and final_cutoff < owner_cutoff
        ):
            errors.append("Council final research cutoff cannot precede owner model cutoff")

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
        root_cutoff,
    )
    owner_model_identity = (
        payload.get("ticker"),
        identity.get("security_id"),
        owner_model_cutoff,
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
    final_accepted_evidence = set(accepted_evidence)
    if present_split_cutoff_fields == split_cutoff_fields:
        owner_receipt, _ = _descriptor_payload(
            artifact_dir,
            payload.get("owner_model_pei_input_receipt"),
            "owner_model_pei_input_receipt",
            errors,
        )
        if owner_receipt is not None:
            owner_errors, owner_posture = _validate_pei_admission_receipt(owner_receipt)
            errors.extend(
                f"owner_model_pei_input_receipt: {error}"
                for error in owner_errors
            )
            if owner_posture != payload.get("research_admission"):
                errors.append(
                    "owner model PEI receipt posture must equal Council research_admission"
                )
            if _identity_values(owner_receipt) != owner_model_identity:
                errors.append(
                    "owner model PEI receipt identity/cutoff must equal Council owner model"
                )
            owner_registry = owner_receipt.get("evidence_registry")
            if not isinstance(owner_registry, list):
                errors.append(
                    "owner_model_pei_input_receipt.evidence_registry must be a list"
                )
            else:
                accepted_evidence = {
                    item.get("id")
                    for item in owner_registry
                    if isinstance(item, dict) and _nonempty_string(item.get("id"))
                }
                accepted_evidence_natures = {
                    item["id"]: item["evidence_nature"]
                    for item in owner_registry
                    if isinstance(item, dict)
                    and _nonempty_string(item.get("id"))
                    and _nonempty_string(item.get("evidence_nature"))
                }
    if "correction_validation_set" in payload:
        correction_ids = _validated_correction_evidence(
            artifact_dir,
            payload.get("correction_validation_set"),
            root_identity=root_identity,
            reference_price=price.get("value"),
            errors=errors,
        )
        overlap = correction_ids & (accepted_evidence | final_accepted_evidence)
        if overlap:
            errors.append(
                "correction evidence must be additive to PEI evidence: "
                + ", ".join(sorted(overlap))
            )
        else:
            accepted_evidence.update(correction_ids)
            final_accepted_evidence.update(correction_ids)

    final_registry = (receipt or {}).get("evidence_registry", [])
    admitted_sources = {
        row["id"]: row
        for row in (final_registry if isinstance(final_registry, list) else [])
        if isinstance(row, dict) and _nonempty_string(row.get("id"))
    }

    # The starting packet stays immutable; Data may admit discoveries before
    # the owner's final receipt without sending the Council through another round.
    input_evidence = accepted_evidence
    input_natures = accepted_evidence_natures
    input_identity = owner_model_identity
    input_registry: list[Any] = []
    if discovery:
        initial, _ = _descriptor_payload(artifact_dir, payload.get("council_input_pei_receipt"), "council_input_pei_receipt", errors)
        input_evidence, input_natures = set(), {}
        if initial is not None:
            initial_errors, _ = _validate_pei_admission_receipt(initial)
            errors.extend(f"council_input_pei_receipt: {error}" for error in initial_errors)
            input_identity = _identity_values(initial)
            initial_cutoff = _parse_time(input_identity[2], "Council input cutoff", errors)
            final_cutoff = _parse_time(owner_model_identity[2], "owner model cutoff", errors)
            if input_identity[:2] != owner_model_identity[:2] or (initial_cutoff and final_cutoff and initial_cutoff > final_cutoff):
                errors.append("Council input identity/cutoff must precede the same owner model")
            registry = initial.get("evidence_registry", [])
            if not isinstance(registry, list):
                errors.append("Council input evidence_registry must be a list")
                registry = []
            input_natures = {row["id"]: row.get("evidence_nature", "") for row in registry if isinstance(row, dict) and _nonempty_string(row.get("id"))}
            input_evidence = set(input_natures)
            input_registry = registry
    source_candidates: dict[str, dict[str, Any]] = {}

    bindings = payload.get("artifact_bindings")
    if not isinstance(bindings, dict):
        return errors + ["artifact_bindings must be an object"]
    _expect_keys(
        bindings,
        {
            "authority_version",
            "preliminary_underwrite",
            "seat_packets",
            "sealed_memos",
            "owner_adjudication",
            "final_model_spec",
            "model_committed_at",
        } | ({"fv_freeze_receipt"} if not blind or "fv_freeze_receipt" in bindings else set())
        | ({"validator_sha256"} & set(bindings)),
        "artifact_bindings",
        errors,
    )
    authority_version = 4 if blind else (3 if discovery else AGENT_COUNCIL_AUTHORITY_VERSION)
    if bindings.get("authority_version") != authority_version:
        errors.append(
            f"artifact_bindings.authority_version must be {authority_version}"
        )
    # Tolerated for sealed runs; not compared, so validator edits do not void them.
    if "validator_sha256" in bindings and _normalized_sha(bindings["validator_sha256"]) is None:
        errors.append("artifact_bindings.validator_sha256 must be a SHA-256 digest when present")

    if blind:
        # Admission is not permission to show a model artifact to a blind seat.
        private_refs = [bindings.get(key) for key in (
            "preliminary_underwrite", "final_model_spec", "owner_adjudication",
        )]
        if isinstance(bindings.get("sealed_memos"), dict):
            private_refs.extend(bindings["sealed_memos"].values())
        private_paths = {
            (artifact_dir / ref["path"]).resolve() for ref in private_refs
            if isinstance(ref, dict) and _nonempty_string(ref.get("path"))
        }
        private_hashes = {
            ref["sha256"] for ref in private_refs
            if isinstance(ref, dict) and _normalized_sha(ref.get("sha256"))
        }
        private_ids = {
            row["id"] for row in input_registry
            if isinstance(row, dict) and _nonempty_string(row.get("id")) and (
                row.get("source_kind") == "model" or row.get("requirement_class") == "model"
                or (_normalized_sha(row.get("sha256")) in private_hashes)
                or any(
                    _nonempty_string(row.get(field)) and (artifact_dir / row[field]).resolve() in private_paths
                    for field in ("artifact", "path")
                )
            )
        }
        input_evidence = input_evidence - private_ids
        input_natures = {key: value for key, value in input_natures.items() if key not in private_ids}

    underwrite, underwrite_sha = _descriptor_payload(
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
        if _identity_values(underwrite) != input_identity:
            errors.append("preliminary underwrite identity/cutoff must equal Council owner model")
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
                if not _string_list(evidence_ids) or not set(evidence_ids) <= input_evidence:
                    errors.append(
                        f"{label}.evidence_ids exceed accepted PEI evidence"
                    )
                if not _number(assumption.get("proposed_base")):
                    errors.append(f"{label}.proposed_base must be numeric")
                if blind and _ordered_range(assumption.get("proposed_range")) and _number(assumption.get("proposed_base")):
                    if not assumption["proposed_range"][0] <= assumption["proposed_base"] <= assumption["proposed_range"][1]:
                        errors.append(f"{label}.proposed_base must fall within proposed_range")
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
                    if signal_evidence_ids and not signal_evidence_ids <= input_evidence:
                        errors.append(
                            f"{signal_label}.evidence_ids must be accepted PEI evidence"
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
                            input_natures.get(evidence_id)
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
                    if blind:
                        for assumption_id in family_assumptions:
                            if assumptions_by_id.get(assumption_id, {}).get("family") != family:
                                errors.append(f"{label} candidate family must equal its disposition family")
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
    dispatch_times: list[datetime] = []
    range_comparisons: dict[str, dict[str, str]] = {key: {} for key in assumption_ids}
    blind_fields = {
        "assumption_id", "family", "period", "unit", "evidence_ids",
        "flip_condition", "rationale", "rejected_alternative", "challenge_signal_dispositions",
    }
    blind_assumptions = [
        {key: row.get(key) for key in blind_fields} for row in assumptions
    ]
    for seat in sorted(SEATS):
        packet, packet_sha = _descriptor_payload(
            artifact_dir,
            packet_refs.get(seat),
            f"artifact_bindings.seat_packets.{seat}",
            errors,
        )
        if packet_sha:
            packet_hashes[seat] = packet_sha
        search_required = False
        if packet is not None:
            search_required = blind and packet.get("search_required") is True
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
                } | ({"preliminary_underwrite_sha256", "dispatched_at"} if blind else set())
                | ({"search_required"} if "search_required" in packet else set()),
                f"{seat} packet",
                errors,
            )
            if "search_required" in packet and not search_required:
                errors.append(f"{seat} packet search_required must be true on a blind packet")
            if (
                packet.get("schema_version") != ("council-premodel-seat-packet-v4" if blind else "council-premodel-seat-packet-v2")
                or _identity_values(packet) != input_identity
                or packet.get("seat") != seat
            ):
                errors.append(f"{seat} packet identity/schema must equal Council owner model")
            if assumptions and packet.get("candidate_assumptions") != (blind_assumptions if blind else assumptions):
                errors.append(f"{seat} packet candidate assumptions must equal {'blind projection of ' if blind else ''}preliminary underwrite")
            if blind:
                if _normalized_sha(packet.get("preliminary_underwrite_sha256")) != underwrite_sha:
                    errors.append(f"{seat} packet must bind the original preliminary underwrite hash")
                dispatched_at = _parse_time(packet.get("dispatched_at"), f"{seat} packet dispatched_at", errors)
                if dispatched_at:
                    dispatch_times.append(dispatched_at)
                    input_cutoff = _parse_time(input_identity[2], "Council input cutoff", errors)
                    if input_cutoff and dispatched_at < input_cutoff:
                        errors.append(f"{seat} packet dispatched_at cannot precede Council input cutoff")
            evidence_ids = packet.get("evidence_ids")
            if not _string_list(evidence_ids):
                errors.append(f"{seat} packet evidence_ids must be a string list")
            elif not set(evidence_ids) <= input_evidence:
                errors.append(f"{seat} packet evidence_ids exceed accepted PEI evidence")
            elif not challenge_signal_evidence_ids <= set(evidence_ids):
                errors.append(
                    f"{seat} packet evidence_ids omit preliminary challenge-signal evidence"
                )
            if blind and _string_list(evidence_ids):
                candidate_evidence = _collect_evidence_ids(blind_assumptions)
                if not candidate_evidence <= set(evidence_ids):
                    errors.append(f"{seat} packet evidence_ids must cover all candidate evidence")
            if not _nonempty_string(packet.get("instructions")):
                errors.append(f"{seat} packet instructions must be non-empty")
            elif not blind:
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
            leaked = _contains_forbidden_agent_output(packet, blind_packet=blind)
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
                "limitations",
            } | ({"source_candidates"} if discovery else set())
            | ({"strongest_upside_case", "strongest_downside_case"} if blind else {"strongest_countercase"}),
            f"{seat} memo",
            errors,
        )
        if (
            memo.get("schema_version") != ("council-sealed-memo-v4" if blind else ("council-sealed-memo-v3" if discovery else "council-sealed-memo-v2"))
            or memo.get("seat") != seat
            or _normalized_sha(memo.get("packet_sha256")) != packet_sha
        ):
            errors.append(f"{seat} memo identity/schema or packet hash is invalid")
        if memo.get("added_evidence_ids") != [] or (not discovery and memo.get("browsed") is not False):
            errors.append(f"{seat} memo must not self-admit evidence" if discovery else f"{seat} memo must be evidence-closed")
        if discovery and not isinstance(memo.get("browsed"), bool):
            errors.append(f"{seat} memo browsed must be boolean")
        if not _nonempty_string(memo.get("summary")):
            errors.append(f"{seat} memo summary must be non-empty")
        if blind:
            for case in ("strongest_upside_case", "strongest_downside_case"):
                _validate_blind_case(memo.get(case), f"{seat} memo {case}", errors,
                                     soros_upside=seat == "soros" and case == "strongest_upside_case")
        elif not _nonempty_string(memo.get("strongest_countercase")):
            errors.append(f"{seat} memo strongest_countercase must be non-empty")
        if not isinstance(memo.get("limitations"), list) or any(
            not _nonempty_string(item) for item in memo.get("limitations", [])
        ):
            errors.append(f"{seat} memo limitations must be a string list")
        sealed_at = _parse_time(memo.get("sealed_at"), f"{seat} memo sealed_at", errors)
        if sealed_at:
            memo_times.append(sealed_at)
        seat_candidates: set[str] = set()
        if discovery:
            candidates = memo.get("source_candidates")
            if not isinstance(candidates, list):
                errors.append(f"{seat} source_candidates must be a list")
                candidates = []
            if candidates and memo.get("browsed") is not True:
                errors.append(f"{seat} source candidates require truthful browsing")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    errors.append(f"{seat} source candidate must be an object")
                    continue
                _expect_keys(candidate, {"candidate_id", "url", "source_locator", "as_of", "retrieved_at", "assumption_ids", "finding", "evidence_nature"}, f"{seat} source candidate", errors)
                candidate_id = candidate.get("candidate_id")
                if not _nonempty_string(candidate_id) or candidate_id in source_candidates or candidate_id in final_accepted_evidence or candidate_id in input_evidence:
                    errors.append(f"{seat} candidate_id must be unique and distinct from evidence IDs")
                    continue
                if not isinstance(candidate.get("url"), str) or not re.match(r"https?://[^/\s]+", candidate["url"]):
                    errors.append(f"{seat} source candidate must have an original HTTP(S) URL")
                for field in ("finding", "evidence_nature", "source_locator"):
                    if not _nonempty_string(candidate.get(field)):
                        errors.append(f"{seat} source candidate {field} must be non-empty")
                as_of = candidate.get("as_of")
                published_at = _parse_time(as_of + "T00:00:00Z" if isinstance(as_of, str) and len(as_of) == 10 else as_of, f"{seat} candidate as_of", errors)
                discovered_at = _parse_time(candidate.get("retrieved_at"), f"{seat} candidate retrieved_at", errors)
                if published_at and discovered_at and published_at.date() > discovered_at.date():
                    errors.append(f"{seat} candidate publication cannot follow discovery")
                if discovered_at and sealed_at and discovered_at > sealed_at:
                    errors.append(f"{seat} source discovery cannot follow its sealed memo")
                affected = candidate.get("assumption_ids")
                if not _string_list(affected) or not affected or not set(affected) <= assumption_ids:
                    errors.append(f"{seat} source candidate must name affected assumptions")
                source_candidates[candidate_id] = candidate
                seat_candidates.add(candidate_id)
        challenges = memo.get("challenges")
        if not isinstance(challenges, list):
            errors.append(f"{seat} memo challenges must be a list")
            challenges = []
        if search_required:
            errors.extend(f"{seat} {error}" for error in validate_source_checks(packet, memo))
        challenged_ids: set[str] = set()
        for index, challenge in enumerate(challenges):
            label = f"{seat} memo challenges[{index}]"
            if not isinstance(challenge, dict):
                errors.append(f"{label} must be an object")
                continue
            _expect_keys(
                challenge,
                {
                    "assumption_id",
                    "proposed_base",
                    "proposed_range",
                    "evidence_ids",
                    "reasoning",
                    "decision_impact",
                    "falsifier",
                } | ({"candidate_source_ids"} if discovery else set())
                | ({"estimation_status", "period", "unit", "not_estimable_reason", "missing_evidence"} if blind else {"assessment"})
                | ({"source_checks"} if search_required else set()),
                label,
                errors,
            )
            assumption_id = challenge.get("assumption_id")
            if not _nonempty_string(assumption_id) or assumption_id not in assumption_ids:
                errors.append(f"{label}.assumption_id is not in preliminary underwrite")
                continue
            if blind and assumption_id in challenged_ids:
                errors.append(f"{label}.assumption_id must be covered exactly once per seat")
            challenged_ids.add(assumption_id)
            if not blind and challenge.get("assessment") not in {
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
            if blind:
                preliminary = assumptions_by_id[assumption_id]
                for field in ("period", "unit"):
                    if challenge.get(field) != preliminary.get(field):
                        errors.append(f"{label}.{field} must equal the candidate {field}")
                if challenge.get("estimation_status") == "estimated":
                    if not _number(proposed_base) or not _ordered_range(proposed_range):
                        errors.append(f"{label} estimated requires numeric proposed_base and ordered proposed_range")
                    elif not proposed_range[0] <= proposed_base <= proposed_range[1]:
                        errors.append(f"{label}.proposed_base must fall within proposed_range")
                    elif _number(preliminary.get("proposed_base")):
                        owner_base = preliminary["proposed_base"]
                        range_comparisons[assumption_id][seat] = (
                            "owner_below_range" if owner_base < proposed_range[0]
                            else "owner_above_range" if owner_base > proposed_range[1]
                            else "within_range"
                        )
                    if challenge.get("not_estimable_reason") is not None or challenge.get("missing_evidence") is not None:
                        errors.append(f"{label} estimated must use null not_estimable_reason and missing_evidence")
                    if not challenge.get("evidence_ids") and not challenge.get("candidate_source_ids"):
                        errors.append(f"{label} estimated requires evidence or source candidates")
                elif challenge.get("estimation_status") == "not_estimable":
                    if proposed_base is not None or proposed_range is not None:
                        errors.append(f"{label} not_estimable must use null proposed_base and proposed_range")
                    for field in ("not_estimable_reason", "missing_evidence"):
                        if not _nonempty_string(challenge.get(field)):
                            errors.append(f"{label} not_estimable requires concrete {field}")
                    range_comparisons[assumption_id][seat] = "not_estimable"
                else:
                    errors.append(f"{label}.estimation_status must be estimated or not_estimable")
            challenge_evidence = challenge.get("evidence_ids")
            if not _string_list(challenge_evidence) or not set(challenge_evidence) <= input_evidence:
                errors.append(f"{label}.evidence_ids exceed accepted PEI evidence")
            if discovery:
                candidates = challenge.get("candidate_source_ids")
                if not _string_list(candidates) or not set(candidates) <= seat_candidates:
                    errors.append(f"{label}.candidate_source_ids must refer only to this seat's discoveries")
                elif any(challenge.get("assumption_id") not in source_candidates[c]["assumption_ids"] for c in candidates if _string_list(source_candidates[c].get("assumption_ids"))):
                    errors.append(f"{label} candidate does not address this assumption")
            for field in ("reasoning", "decision_impact", "falsifier"):
                if not _nonempty_string(challenge.get(field)):
                    errors.append(f"{label}.{field} must be non-empty")
        if blind and challenged_ids != assumption_ids:
            errors.append(f"{seat} memo must cover every candidate assumption exactly once")
        leaked = _contains_forbidden_agent_output(memo)
        if leaked:
            errors.append(f"{seat} memo leaks forbidden field {leaked}")

    if blind and dispatch_times and memo_times and max(dispatch_times) > min(memo_times):
        errors.append("all blind packets must be dispatched before the first sealed memo")
    if comparison_output is not None:
        comparison_output.update(range_comparisons)
        return errors

    final_spec, final_spec_sha = _descriptor_payload(
        artifact_dir,
        bindings.get("final_model_spec"),
        "artifact_bindings.final_model_spec",
        errors,
    )
    final_assumption_ids: set[str] = set()
    if final_spec is not None and _identity_values(final_spec) != owner_model_identity:
        errors.append("final model spec identity/cutoff must equal Council owner model")
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
            } | ({"source_dispositions"} if discovery else set())
            | ({"preliminary_underwrite_sha256"} if blind else set()),
            "owner adjudication",
            errors,
        )
        if (
            adjudication.get("schema_version") != ("pei-council-adjudication-v4" if blind else ("pei-council-adjudication-v3" if discovery else "pei-council-adjudication-v2"))
            or _identity_values(adjudication) != owner_model_identity
        ):
            errors.append("owner adjudication identity/schema must equal Council owner model")
        if blind and _normalized_sha(adjudication.get("preliminary_underwrite_sha256")) != underwrite_sha:
            errors.append("owner adjudication must bind the original preliminary underwrite hash")
        if adjudication.get("packet_hashes") != packet_hashes:
            errors.append("owner adjudication packet_hashes must equal bound packets")
        if adjudication.get("memo_hashes") != memo_hashes:
            errors.append("owner adjudication memo_hashes must equal bound memos")
        if _normalized_sha(adjudication.get("final_model_spec_sha256")) != final_spec_sha:
            errors.append("owner adjudication must bind the final model spec hash")
        if discovery:
            dispositions = adjudication.get("source_dispositions")
            if not isinstance(dispositions, list):
                errors.append("owner source_dispositions must be a list")
                dispositions = []
            disposed: set[str] = set()
            for row in dispositions:
                if not isinstance(row, dict):
                    errors.append("source disposition must be an object")
                    continue
                _expect_keys(row, {"candidate_id", "disposition", "evidence_ids", "reason"}, "source disposition", errors)
                candidate_id = row.get("candidate_id")
                if not _nonempty_string(candidate_id) or candidate_id not in source_candidates or candidate_id in disposed:
                    errors.append("source disposition must map each candidate exactly once")
                    continue
                disposed.add(candidate_id)
                evidence_ids = row.get("evidence_ids")
                if row.get("disposition") == "accepted":
                    if not _string_list(evidence_ids) or not evidence_ids or not set(evidence_ids) <= final_accepted_evidence:
                        errors.append("accepted source requires evidence admitted in the final PEI receipt")
                    else:
                        candidate = source_candidates[candidate_id]
                        for evidence_id in evidence_ids:
                            admitted = admitted_sources.get(evidence_id, {})
                            provenances = [admitted.get(field) for field in ("primary_provenance", "public_provenance")]
                            same_source = any(
                                isinstance(provenance, dict)
                                and provenance.get("source_url") == candidate.get("url")
                                and provenance.get("source_locator") == candidate.get("source_locator")
                                for provenance in provenances
                            )
                            candidate_date = candidate.get("as_of")
                            date_only = isinstance(candidate_date, str) and len(candidate_date) == 10
                            candidate_at = _parse_time(candidate_date + "T00:00:00Z" if date_only else candidate_date, "candidate source provenance publication", errors)
                            admitted_at = _parse_time(admitted.get("as_of"), "candidate source provenance admitted publication", errors)
                            same_date = candidate_at is not None and admitted_at is not None and (
                                candidate_at.date() == admitted_at.date() if date_only else candidate_at == admitted_at
                            )
                            if not same_source or not same_date or admitted.get("evidence_nature") != candidate.get("evidence_nature"):
                                errors.append("accepted candidate source provenance must match its admitted URL, locator, date and evidence nature")
                elif row.get("disposition") not in {"rejected", "not_material"} or evidence_ids != []:
                    errors.append("unaccepted source disposition must not admit evidence")
                if not _nonempty_string(row.get("reason")):
                    errors.append("source disposition reason must be non-empty")
            if disposed != set(source_candidates):
                errors.append("owner must disposition every discovered source")
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
                    "council_sources",
                    "evidence_ids",
                    "reason",
                    "model_input_ids",
                } | ({"range_comparisons", "retention_basis"} if blind else set())
                | ({"decision"} if not blind or "decision" in decision else set()),
                label,
                errors,
            )
            assumption_id = decision.get("assumption_id")
            if not _nonempty_string(assumption_id) or assumption_id in decision_ids or assumption_id not in assumption_ids:
                errors.append(f"{label}.assumption_id must map once to the preliminary underwrite")
                continue
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
            final_range = decision.get("final_range")
            withdrawn = blind and final_base is None and final_range is None
            if not withdrawn and not _number(final_base):
                errors.append(f"{label}.final_base must be numeric")
            if not withdrawn and (
                not isinstance(final_range, list)
                or len(final_range) != 2
                or not all(_number(item) for item in final_range)
                or final_range[0] > final_range[1]
            ):
                errors.append(f"{label}.final_range must be an ordered numeric pair")
            elif _number(final_base) and not final_range[0] <= final_base <= final_range[1]:
                errors.append(f"{label}.final_base must fall within final_range")
            if (not blind or "decision" in decision) and decision.get("decision") not in {"accept", "conditional", "reject"}:
                errors.append(f"{label}.decision is invalid")
            if not isinstance(decision.get("council_sources"), list) or not set(
                decision.get("council_sources", [])
            ) <= SEATS:
                errors.append(f"{label}.council_sources are invalid")
            if not _string_list(decision.get("evidence_ids")) or not set(
                decision.get("evidence_ids", [])
            ) <= final_accepted_evidence:
                errors.append(f"{label}.evidence_ids exceed accepted PEI evidence")
            if not _nonempty_string(decision.get("reason")):
                errors.append(f"{label}.reason must be non-empty")
            if blind:
                comparisons = range_comparisons.get(assumption_id, {})
                if decision.get("range_comparisons") != comparisons:
                    errors.append(f"{label}.range_comparisons must equal validator-derived comparisons")
                same_side = any(
                    list(comparisons.values()).count(direction) >= 2
                    for direction in ("owner_below_range", "owner_above_range")
                )
                retention_basis = decision.get("retention_basis")
                needs_basis = same_side and final_base == prior_base
                if withdrawn and retention_basis is not None:
                    errors.append(f"{label}.retention_basis must be null for a withdrawn assumption")
                if needs_basis and not isinstance(retention_basis, dict):
                    errors.append(f"{label} retaining the original Base outside two same-side seat ranges requires retention_basis")
                elif retention_basis is not None:
                    if not isinstance(retention_basis, dict):
                        errors.append(f"{label}.retention_basis must be an object or null")
                    else:
                        _expect_keys(retention_basis, {"omitted_evidence_ids", "omitted_mechanism"}, f"{label}.retention_basis", errors)
                        omitted_ids = retention_basis.get("omitted_evidence_ids")
                        mechanism = retention_basis.get("omitted_mechanism")
                        if not _string_list(omitted_ids) or not set(omitted_ids) <= final_accepted_evidence:
                            errors.append(f"{label}.retention_basis evidence must be final-receipt accepted evidence")
                        if not isinstance(mechanism, str):
                            errors.append(f"{label}.retention_basis omitted_mechanism must be a string")
                        if not omitted_ids and not _nonempty_string(mechanism):
                            errors.append(f"{label}.retention_basis must identify omitted evidence or mechanism")
            model_input_ids = decision.get("model_input_ids")
            if withdrawn and model_input_ids != []:
                errors.append(f"{label}.model_input_ids must be empty for a withdrawn assumption")
            elif not withdrawn and (
                not _string_list(model_input_ids)
                or not model_input_ids
                or len(set(model_input_ids)) != len(model_input_ids)
            ):
                errors.append(
                    f"{label}.model_input_ids must be a unique non-empty string list"
                )
            elif not withdrawn:
                duplicate_inputs = adjudicated_model_inputs & set(model_input_ids)
                if duplicate_inputs and not (final_spec or {}).get('dependency_graph'):
                    errors.append(
                        "owner adjudication model_input_ids must have one owner: "
                        + ", ".join(sorted(duplicate_inputs))
                    )
                adjudicated_model_inputs.update(model_input_ids)
                family = next((item.get('family') for item in (underwrite or {}).get('assumption_family_dispositions', []) if assumption_id in item.get('assumption_ids', [])), None)
                _validate_model_mapping(preliminary, family, decision, final_spec or {}, label, errors)
        if decision_ids != assumption_ids:
            errors.append("owner adjudication must decide every preliminary assumption once")
        missing_model_inputs = final_assumption_ids - adjudicated_model_inputs
        if missing_model_inputs and not (final_spec or {}).get('dependency_graph'):
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
    freeze_bound = "fv_freeze_receipt" in bindings
    freeze, _ = _descriptor_payload(
        artifact_dir,
        bindings.get("fv_freeze_receipt"),
        "artifact_bindings.fv_freeze_receipt",
        errors,
    ) if freeze_bound else (None, None)
    frozen_at = None
    if freeze is not None:
        if _identity_values(freeze) != owner_model_identity:
            errors.append("FV freeze identity/cutoff must equal Council owner model")
        if _normalized_sha(freeze.get("model_spec_sha256")) != final_spec_sha:
            errors.append("FV freeze must bind the final model spec hash")
        for field in ("model_output_sha256", "independent_audit_sha256"):
            if _normalized_sha(freeze.get(field)) is None:
                errors.append(f"FV freeze {field} must be a lowercase SHA-256 digest")
        frozen_at = _parse_time(
            freeze.get("frozen_at"), "fv_freeze_receipt.frozen_at", errors
        )
    latest_memo = max(memo_times, default=None)
    timeline = [latest_memo, adjudicated_at, committed_at] + ([frozen_at] if freeze_bound else [])
    if all(value is not None for value in timeline) and timeline != sorted(timeline):
        errors.append(
            "current Council timeline must be memos <= adjudication <= model commit (<= FV freeze when bound)"
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


def validate_pre_dispatch_admission(
    *,
    artifact_dir: Path,
    owner_model_pei_input: Path,
    preliminary_underwrite: Path,
) -> list[str]:
    """Validate the narrow evidence boundary required before Council dispatch.

    This is intentionally separate from a completed Council run: full validation
    still requires its canonical final PEI receipt and split owner-model receipt.
    """

    errors: list[str] = []
    owner_path = _safe_artifact_path(
        artifact_dir, str(owner_model_pei_input), "owner_model_pei_input", errors
    )
    preliminary_path = _safe_artifact_path(
        artifact_dir, str(preliminary_underwrite), "preliminary_underwrite", errors
    )
    owner = _load_json(owner_path, "owner model PEI input", errors)
    preliminary = _load_json(preliminary_path, "preliminary underwrite", errors)
    if not isinstance(owner, dict) or not isinstance(preliminary, dict):
        return errors

    receipt_errors, _ = _validate_pei_admission_receipt(owner)
    errors.extend(f"owner_model_pei_input: {error}" for error in receipt_errors)
    if owner.get("schema_version") != 2:
        errors.append("owner_model_pei_input.schema_version must be 2 before Council dispatch")
    declaration = owner.get("owner_declaration")
    declared = declaration.get("declared_receipt_kinds") if isinstance(declaration, dict) else None
    if not isinstance(declared, list) or "model" not in declared:
        errors.append("owner_model_pei_input must declare a model owner receipt")

    owner_identity = owner.get("security_identity")
    owner_security_id = (
        owner_identity.get("security_id") if isinstance(owner_identity, dict) else None
    )
    for field, expected in (
        ("ticker", owner.get("ticker")),
        ("security_id", owner_security_id),
        ("evidence_cutoff", owner.get("evidence_cutoff")),
    ):
        if preliminary.get(field) != expected:
            errors.append(
                f"preliminary_underwrite.{field} must equal owner model PEI input"
            )
    if preliminary.get("schema_version") != "pei-preliminary-underwrite-v2":
        errors.append("preliminary_underwrite.schema_version must be pei-preliminary-underwrite-v2")
    if not _nonempty_string(preliminary.get("owner")):
        errors.append("preliminary_underwrite.owner must be a non-empty string")
    if not _nonempty_string(preliminary.get("decision_horizon")):
        errors.append("preliminary_underwrite.decision_horizon must be a non-empty string")
    if not isinstance(preliminary.get("candidate_assumptions"), list) or not preliminary["candidate_assumptions"]:
        errors.append("preliminary_underwrite.candidate_assumptions must be non-empty")

    model_subordinates = [
        item
        for item in owner.get("subordinate_receipts", [])
        if isinstance(item, dict) and item.get("kind") == "model"
    ]
    if len(model_subordinates) != 1:
        errors.append("owner_model_pei_input must contain exactly one model subordinate receipt")
        return errors
    model_subordinate = model_subordinates[0]
    model_path = _safe_artifact_path(
        artifact_dir,
        model_subordinate.get("artifact"),
        "owner_model_pei_input model subordinate",
        errors,
    )
    if model_path is None or not model_path.is_file():
        return errors
    if model_subordinate.get("sha256") != _sha256(model_path):
        errors.append("owner_model_pei_input model subordinate hash does not match artifact")
        return errors
    model = _load_json(model_path, "model owner receipt", errors)
    if not isinstance(model, dict):
        return errors
    for field, expected in (
        ("schema_version", 1),
        ("kind", "model"),
        ("ticker", owner.get("ticker")),
        ("security_id", owner_security_id),
        ("evidence_cutoff", owner.get("evidence_cutoff")),
        ("validation_status", "PASS"),
    ):
        if model.get(field) != expected:
            errors.append(f"model owner receipt {field} does not match pre-dispatch boundary")

    if preliminary_path is None:
        return errors
    preliminary_artifact = preliminary_path.relative_to(artifact_dir.resolve()).as_posix()
    preliminary_hash = _sha256(preliminary_path)
    model_entries = {
        item.get("id"): item
        for item in model.get("evidence_registry", [])
        if isinstance(item, dict) and _nonempty_string(item.get("id"))
    }
    matching_ids = {
        evidence_id
        for evidence_id, item in model_entries.items()
        if item.get("artifact") == preliminary_artifact
        and item.get("sha256") == preliminary_hash
    }
    if not matching_ids:
        errors.append("model owner receipt does not exact-bind the preliminary underwrite")
        return errors
    if not matching_ids & set(model.get("evidence_ids") or []):
        errors.append("model owner receipt does not declare the bound preliminary underwrite")
    owner_entries = {
        item.get("id"): item
        for item in owner.get("evidence_registry", [])
        if isinstance(item, dict) and _nonempty_string(item.get("id"))
    }
    for evidence_id in matching_ids:
        item = owner_entries.get(evidence_id)
        if not isinstance(item, dict) or item.get("artifact") != preliminary_artifact or item.get("sha256") != preliminary_hash:
            errors.append("owner model PEI input does not carry the bound preliminary underwrite")
    return errors


def validate(
    payload: Any,
    *,
    plugin_root: Path,
    artifact_dir: Path,
) -> list[str]:
    _ = plugin_root
    if not isinstance(payload, dict):
        return ["root must be a JSON object"]
    version = payload.get("schema_version")
    if version in {AGENT_COUNCIL_SCHEMA_VERSION, 4, 5}:
        return _validate_agent_council_v3(payload, artifact_dir=Path(artifact_dir))
    if isinstance(version, int) and not isinstance(version, bool) and version < AGENT_COUNCIL_SCHEMA_VERSION:
        return [f"legacy council schema {version} is read-only and is not revalidated"]
    return ["schema_version must be 3, 4, or 5"]


def _default_artifact_root(council_path: Path) -> Path:
    return council_path.parent.parent if council_path.parent.name == "support" else council_path.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Equity Council run artifact.")
    parser.add_argument("--plugin-root", required=True, type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument(
        "--pre-dispatch",
        action="store_true",
        help="validate only the owner-model input and bound preliminary underwrite",
    )
    parser.add_argument("--owner-model-pei-input", type=Path)
    parser.add_argument("--preliminary-underwrite", type=Path)
    parser.add_argument(
        "--compare-ranges", action="store_true",
        help="validate v5 bound inputs, packets and memos, then print range comparisons as JSON before adjudication",
    )
    parser.add_argument("council_run", nargs="?", type=Path)
    args = parser.parse_args()

    if args.pre_dispatch:
        if (
            args.artifact_root is None
            or args.owner_model_pei_input is None
            or args.preliminary_underwrite is None
            or args.council_run is not None
            or args.compare_ranges
        ):
            parser.error(
                "--pre-dispatch requires --artifact-root, --owner-model-pei-input, and --preliminary-underwrite only"
            )
        errors = validate_pre_dispatch_admission(
            artifact_dir=args.artifact_root,
            owner_model_pei_input=args.owner_model_pei_input,
            preliminary_underwrite=args.preliminary_underwrite,
        )
        if errors:
            print("FAIL: Council pre-dispatch admission is invalid", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("PASS: Council pre-dispatch admission is valid")
        return 0

    if args.council_run is None:
        parser.error("council_run is required unless --pre-dispatch is used")

    load_errors: list[str] = []
    payload = _load_json(args.council_run, "Council run", load_errors)
    if payload is None:
        for error in load_errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if args.compare_ranges:
        if payload.get("schema_version") != 5:
            parser.error("--compare-ranges requires Council schema_version 5")
        comparisons: dict[str, dict[str, str]] = {}
        errors = _validate_agent_council_v3(
            payload,
            artifact_dir=args.artifact_root or _default_artifact_root(args.council_run),
            comparison_output=comparisons,
        )
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            return 1
        print(json.dumps(comparisons, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
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
