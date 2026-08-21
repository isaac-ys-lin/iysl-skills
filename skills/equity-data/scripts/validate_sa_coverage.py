#!/usr/bin/env python3
"""Validate the formal Seeking Alpha coverage support artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


GROUPS = (
    "market_snapshot",
    "street_estimates",
    "estimate_revisions",
    "earnings_surprises",
    "wall_street",
    "quant",
    "valuation",
    "peer_comparison",
    "analyst_views",
    "transcripts",
    "positioning",
    "normalized_financials",
)

CORE_GROUPS = {
    "street_estimates",
    "estimate_revisions",
    "earnings_surprises",
    "wall_street",
    "quant",
    "valuation",
    "analyst_views",
}

STATUSES = {
    "retrieved",
    "not_covered",
    "unavailable",
    "unauthorized",
    "stale",
    "deferred_until_owner_fv_freeze",
    "not_material",
}

ASK_SA_STATUSES = {"retrieved", "not_covered", "unavailable", "unauthorized"}
FORMAL_WORKFLOWS = {"formal_initial_coverage", "formal_research_refresh"}
FREEZE_STATUSES = {"pre_freeze", "post_freeze", "not_applicable"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_nonempty_string(item) for item in value)
    )


def validate(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["root must be a JSON object"]

    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for field in ("ticker", "retrieved_at", "timezone", "owning_workflow"):
        if not _nonempty_string(payload.get(field)):
            errors.append(f"{field} must be a non-empty string")
    if payload.get("workflow_class") not in FORMAL_WORKFLOWS:
        errors.append(
            "workflow_class must be formal_initial_coverage or formal_research_refresh"
        )
    if payload.get("collection_mode") != "completeness_first":
        errors.append("collection_mode must be completeness_first")

    freeze = payload.get("fair_value_freeze")
    freeze_status = None
    if not isinstance(freeze, dict):
        errors.append("fair_value_freeze must be an object")
    else:
        freeze_status = freeze.get("status")
        if freeze_status not in FREEZE_STATUSES:
            errors.append(
                "fair_value_freeze.status must be pre_freeze, post_freeze, or not_applicable"
            )
        if freeze_status == "post_freeze" and not _nonempty_string(
            freeze.get("frozen_at")
        ):
            errors.append(
                "fair_value_freeze.frozen_at is required when status is post_freeze"
            )

    ask_sa = payload.get("ask_sa")
    if not isinstance(ask_sa, dict):
        errors.append("ask_sa must be an object")
    else:
        ask_status = ask_sa.get("status")
        if ask_status not in ASK_SA_STATUSES:
            errors.append(
                "ask_sa.status must be retrieved, not_covered, unavailable, or unauthorized"
            )
        elif ask_status == "retrieved":
            if not _nonempty_string(ask_sa.get("artifact")):
                errors.append("ask_sa.artifact is required when Ask SA was retrieved")
        elif not _nonempty_string(ask_sa.get("gap_reason")):
            errors.append("ask_sa.gap_reason is required when Ask SA was not retrieved")

    groups = payload.get("groups")
    if not isinstance(groups, dict):
        errors.append("groups must be an object")
        return errors

    missing = [group for group in GROUPS if group not in groups]
    extra = sorted(set(groups) - set(GROUPS))
    if missing:
        errors.append(f"missing groups: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected groups: {', '.join(extra)}")

    for name in GROUPS:
        entry = groups.get(name)
        if not isinstance(entry, dict):
            if name in groups:
                errors.append(f"groups.{name} must be an object")
            continue

        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"groups.{name}.status is invalid: {status!r}")
            continue
        if status == "not_material" and name in CORE_GROUPS:
            errors.append(f"groups.{name} is core and cannot be not_material")
        if status == "deferred_until_owner_fv_freeze":
            if name != "wall_street":
                errors.append(
                    f"groups.{name} cannot use deferred_until_owner_fv_freeze"
                )
            if freeze_status != "pre_freeze":
                errors.append(
                    "groups.wall_street cannot remain deferred after fair value freeze"
                )

        attempted = entry.get("attempted")
        if not isinstance(attempted, bool):
            errors.append(f"groups.{name}.attempted must be boolean")
        elif status not in {"not_material", "deferred_until_owner_fv_freeze"} and not attempted:
            errors.append(f"groups.{name}.attempted must be true for status {status}")

        if status == "retrieved":
            if not _nonempty_string_list(entry.get("source_ids")):
                errors.append(
                    f"groups.{name}.source_ids must contain evidence locators when retrieved"
                )
            if not _nonempty_string_list(entry.get("fields_retrieved")):
                errors.append(
                    f"groups.{name}.fields_retrieved must be non-empty when retrieved"
                )
        elif not _nonempty_string(entry.get("gap_reason")):
            errors.append(f"groups.{name}.gap_reason is required for status {status}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a formal Seeking Alpha coverage artifact."
    )
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: artifact not found: {args.artifact}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON: {exc}", file=sys.stderr)
        return 1

    errors = validate(payload)
    if errors:
        print("FAIL: Seeking Alpha coverage artifact is invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"PASS: Seeking Alpha coverage artifact is complete: {args.artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
