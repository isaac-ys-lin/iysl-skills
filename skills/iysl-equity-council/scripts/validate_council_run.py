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
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
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
        if requirement_class not in PEI_REQUIREMENT_CLASSES:
            errors.append(f"{prefix}.requirement_class is invalid")
        criticality = requirement.get("criticality")
        if criticality not in PEI_CRITICALITIES:
            errors.append(f"{prefix}.criticality must be hard or soft")
        status = requirement.get("status")
        if status not in PEI_REQUIREMENT_STATUSES:
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
    if payload.get("output_posture") not in PEI_POSTURES:
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
    for field in CONTRIBUTION_TEXT_FIELDS:
        if not _nonempty_string(contribution.get(field)):
            errors.append(f"{prefix}.{field} must be a non-empty string")
    if contribution.get("primary_mechanism_tag") not in MECHANISM_TAGS:
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
    if contribution.get("primary_mechanism_tag") not in set(mechanism_tags):
        errors.append(
            f"{prefix}.primary_mechanism_tag must be included in mechanism_tags"
        )
    return contribution


def validate(
    payload: Any,
    *,
    plugin_root: Path,
    artifact_dir: Path,
) -> list[str]:
    _ = plugin_root
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["root must be a JSON object"]
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    council_runtime = payload.get("council_runtime")
    if council_runtime not in COUNCIL_RUNTIMES:
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
    if not isinstance(price.get("value"), (int, float)) or isinstance(
        price.get("value"), bool
    ):
        errors.append("current_price.value must be numeric")
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

    if price.get("source_id") not in accepted_evidence:
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
        elif field_id in COMMON_NUMERIC_FIELDS and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            errors.append(f"{prefix}.value must be numeric for {field_id}")
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
    memos = first_round.get("memos")
    if not isinstance(memos, list):
        errors.append("first_round.memos must be a list")
        memos = []
    memos_by_seat: dict[str, dict[str, Any]] = {}
    contributions: dict[str, dict[str, Any]] = {}
    latest_sealed_at: datetime | None = None
    for index, memo in enumerate(memos):
        prefix = f"first_round.memos[{index}]"
        if not isinstance(memo, dict):
            errors.append(f"{prefix} must be an object")
            continue
        seat = memo.get("seat")
        if seat not in SEATS:
            errors.append(f"{prefix}.seat is invalid: {seat!r}")
            continue
        if seat in memos_by_seat:
            errors.append(f"duplicate first-round memo: {seat}")
        memos_by_seat[seat] = memo
        if memo.get("method_completion") not in METHOD_COMPLETION:
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
    implicated_declared = convergence.get("implicated_seats")
    semantic_review = convergence.get("semantic_review")
    if not isinstance(semantic_review, dict):
        errors.append("convergence.semantic_review must be an object")
        semantic_review = {}
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
    if corrective_count not in {0, 1}:
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
        if decision.get("seat") not in SEATS:
            errors.append(f"{prefix}.seat is invalid")
        else:
            decision_seats.add(decision["seat"])
        if decision.get("decision") not in CHAIR_DECISIONS:
            errors.append(f"{prefix}.decision is invalid")
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
    if chair.get("research_stance") not in STANCES:
        errors.append("chair.research_stance must be Long, Short, or Avoid")
    if chair.get("confidence") not in CONFIDENCE:
        errors.append("chair.confidence must be High, Medium, or Low")
    if chair.get("robustness") not in ROBUSTNESS:
        errors.append("chair.robustness must be Robust, Conditional, or Fragile")
    if chair.get("participation") not in PARTICIPATION:
        errors.append(
            "chair.participation must be Eligible, Conditional, or Stand aside"
        )
    if chair.get("implementation_readiness") not in IMPLEMENTATION_READINESS:
        errors.append(
            "chair.implementation_readiness must be Ready, Conditional, or Blocked"
        )
    if not _string_list(chair.get("implementation_blockers")):
        errors.append("chair.implementation_blockers must be a string list")

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
