#!/usr/bin/env python3
"""Validate and score repository-owned behavior evaluation artifacts.

The default command is a blocking, deterministic contract check.
``--emit-case-packet`` produces prompts and declared checks for a human or
model evaluator. ``--results`` reads that evaluator's structured observations
and checks every declared criterion. No model, network, or semantic judge is
called by this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools.skill_manifest import load_manifest, implicit_repo_skill_names
except ModuleNotFoundError:  # direct execution from a checkout
    from skill_manifest import load_manifest, implicit_repo_skill_names


ALLOWED_KINDS = {
    "simple",
    "negative",
    "ambiguity",
    "failure",
    "complex",
    "compatibility",
    "idempotence",
    "quality",
}
EXPECTED_FIELDS = {
    "must_do",
    "must_not_do",
    "max_questions",
    "max_subagents",
    "required_validation",
    "must_stop",
    "expected_route",
    "expected_status",
    "source_fidelity",
}
OBSERVATION_FIELDS = {
    "questions",
    "subagents",
    "must_stop",
    "route",
    "status",
    "source_fidelity",
}
VERDICT_FIELDS = {"must_do", "must_not_do", "required_validation"}


def _load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON ({exc})")
        return None


def _validate_trigger(path: Path, errors: list[str]) -> None:
    payload = _load_json(path, errors)
    if not isinstance(payload, dict):
        errors.append(f"{path}: expected an object")
        return
    seen: dict[str, str] = {}
    for key in ("should_trigger", "should_not_trigger"):
        cases = payload.get(key)
        if not isinstance(cases, list) or not cases:
            errors.append(f"{path}: {key} must be a non-empty list")
            continue
        for index, case in enumerate(cases):
            if isinstance(case, str):
                text = case
            elif isinstance(case, dict):
                text = case.get("text")
                for field in ("family", "expected_route"):
                    if field in case and (
                        not isinstance(case[field], str) or not case[field].strip()
                    ):
                        errors.append(
                            f"{path}: {key}[{index}].{field} must be a non-empty string"
                        )
            else:
                text = None
            if not isinstance(text, str) or not text.strip():
                errors.append(f"{path}: {key}[{index}].text must be a non-empty string")
                continue
            normalized = text.strip()
            previous = seen.get(normalized)
            if previous:
                errors.append(
                    f"{path}: duplicate trigger case in {previous} and {key}: {normalized!r}"
                )
            else:
                seen[normalized] = key


def _validate_behavior(path: Path, errors: list[str]) -> None:
    payload = _load_json(path, errors)
    if not isinstance(payload, dict):
        errors.append(f"{path}: expected an object")
        return
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{path}: cases must be a non-empty list")
        return

    ids: set[str] = set()
    kinds: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"{path}: cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        elif case_id in ids:
            errors.append(f"{prefix}.id duplicates {case_id!r}")
        else:
            ids.add(case_id)

        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{prefix}.prompt must be a non-empty string")

        kind = case.get("kind")
        if kind not in ALLOWED_KINDS:
            errors.append(f"{prefix}.kind must be one of {sorted(ALLOWED_KINDS)}")
        else:
            kinds.add(kind)

        expected = case.get("expected")
        if not isinstance(expected, dict) or not (EXPECTED_FIELDS & expected.keys()):
            errors.append(f"{prefix}.expected must contain a supported field")
            continue
        unknown = set(expected) - EXPECTED_FIELDS
        if unknown:
            errors.append(f"{prefix}.expected has unknown fields: {sorted(unknown)}")

        for field in ("must_do", "must_not_do", "required_validation"):
            if field in expected and (
                not isinstance(expected[field], list)
                or any(not isinstance(item, str) or not item.strip() for item in expected[field])
            ):
                errors.append(f"{prefix}.expected.{field} must be a list of non-empty strings")
        for field in ("max_questions", "max_subagents"):
            if field in expected and (
                not isinstance(expected[field], int) or isinstance(expected[field], bool) or expected[field] < 0
            ):
                errors.append(f"{prefix}.expected.{field} must be a non-negative integer")
        if "must_stop" in expected and not isinstance(expected["must_stop"], bool):
            errors.append(f"{prefix}.expected.must_stop must be boolean")
        for field in ("expected_route", "expected_status", "source_fidelity"):
            if field in expected and (not isinstance(expected[field], str) or not expected[field].strip()):
                errors.append(f"{prefix}.expected.{field} must be a non-empty string")

    if not kinds & {"simple", "negative", "ambiguity", "failure"}:
        errors.append(f"{path}: include at least one routing/negative/failure case")


def validate_repository(root: Path) -> list[str]:
    """Return deterministic contract errors for all implicit repo skills."""

    errors: list[str] = []
    manifest = load_manifest(root)
    skills = manifest["skills"]
    for name in sorted(implicit_repo_skill_names(manifest)):
        entry = skills[name]
        required = set(entry.get("required_gates", []))
        skill_dir = root / "skills" / name
        if not skill_dir.is_dir():
            errors.append(f"{name}: manifest skill directory is missing")
            continue
        if "trigger" in required:
            path = skill_dir / "evals" / "trigger_cases.json"
            if not path.is_file():
                errors.append(f"{name}: required trigger eval is missing ({path})")
            else:
                _validate_trigger(path, errors)
        if "behavior" in required:
            path = skill_dir / "evals" / "behavior_cases.json"
            if not path.is_file():
                errors.append(f"{name}: required behavior eval is missing ({path})")
            else:
                _validate_behavior(path, errors)
    return errors


def _behavior_cases(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Return all declared behavior cases and deterministic contract errors."""

    errors = validate_repository(root)
    if errors:
        return [], errors
    manifest = load_manifest(root)
    cases: list[dict[str, Any]] = []
    for name in sorted(implicit_repo_skill_names(manifest)):
        path = root / "skills" / name / "evals" / "behavior_cases.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for case in payload["cases"]:
            cases.append(
                {
                    "skill": name,
                    "case_id": case["id"],
                    "kind": case["kind"],
                    "prompt": case["prompt"],
                    "expected": case["expected"],
                }
            )
    return cases, []


def build_case_packet(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Build a review packet without invoking a model or a network."""

    cases, errors = _behavior_cases(root)
    if errors:
        return None, errors
    packet = {
        "schema_version": 1,
        "kind": "behavior-eval-case-packet",
        "semantic_judgment": "external-human-or-model",
        "result_schema": {
            "packet_sha256": "copy the digest from this emitted case packet",
            "evaluator": "object with kind, name, and evaluated_at provenance",
            "results": "one object per case with skill, case_id, observations, and verdicts",
            "observations": {
                "questions": "integer when max_questions is declared",
                "subagents": "integer when max_subagents is declared",
                "must_stop": "boolean when must_stop is declared",
                "route": "string when expected_route is declared",
                "status": "string when expected_status is declared",
                "source_fidelity": "string when source_fidelity is declared",
            },
            "verdicts": {
                "must_do": "item -> true when the action was observed",
                "must_not_do": "item -> true when the prohibited action was not observed",
                "required_validation": "item -> true when the validation was performed",
            },
        },
        "cases": cases,
    }
    packet["packet_sha256"] = _packet_sha256(packet)
    return packet, []


def _packet_sha256(packet: dict[str, Any]) -> str:
    """Hash the case packet without its self-referential digest field."""

    payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_observation(
    case: dict[str, Any], result: dict[str, Any], errors: list[str]
) -> None:
    label = f"{case['skill']}/{case['case_id']}"
    expected = case["expected"]
    observations = result.get("observations")
    verdicts = result.get("verdicts")
    if not isinstance(observations, dict):
        errors.append(f"{label}: missing observations object")
        observations = {}
    if not isinstance(verdicts, dict):
        errors.append(f"{label}: missing verdicts object")
        verdicts = {}

    unknown_observations = set(observations) - OBSERVATION_FIELDS
    if unknown_observations:
        errors.append(f"{label}: unknown observation fields {sorted(unknown_observations)}")
    unknown_verdicts = set(verdicts) - VERDICT_FIELDS
    if unknown_verdicts:
        errors.append(f"{label}: unknown verdict groups {sorted(unknown_verdicts)}")

    for expected_field, observed_field in (
        ("max_questions", "questions"),
        ("max_subagents", "subagents"),
    ):
        if expected_field not in expected:
            continue
        if observed_field not in observations:
            errors.append(f"{label}: missing observations.{observed_field}")
        elif not _is_int(observations[observed_field]):
            errors.append(f"{label}: observations.{observed_field} must be an integer")
        elif observations[observed_field] < 0:
            errors.append(f"{label}: observations.{observed_field} must be non-negative")
        elif observations[observed_field] > expected[expected_field]:
            errors.append(
                f"{label}: {observed_field}={observations[observed_field]} exceeds "
                f"max {expected[expected_field]}"
            )

    for expected_field, observed_field in (
        ("must_stop", "must_stop"),
        ("expected_route", "route"),
        ("expected_status", "status"),
        ("source_fidelity", "source_fidelity"),
    ):
        if expected_field not in expected:
            continue
        if observed_field not in observations:
            errors.append(f"{label}: missing observations.{observed_field}")
            continue
        actual = observations[observed_field]
        target = expected[expected_field]
        if expected_field == "must_stop":
            if not isinstance(actual, bool):
                errors.append(f"{label}: observations.must_stop must be boolean")
            elif actual != target:
                errors.append(f"{label}: must_stop={actual!r}, expected {target!r}")
        elif not isinstance(actual, str) or not actual.strip():
            errors.append(f"{label}: observations.{observed_field} must be a non-empty string")
        elif actual != target:
            errors.append(f"{label}: {observed_field}={actual!r}, expected {target!r}")

    for group, expected_result in (
        ("must_do", True),
        ("must_not_do", True),
        ("required_validation", True),
    ):
        expected_items = expected.get(group, [])
        if not expected_items:
            continue
        actual_group = verdicts.get(group)
        if not isinstance(actual_group, dict):
            errors.append(f"{label}: missing verdicts.{group} object")
            continue
        for item in expected_items:
            if item not in actual_group:
                errors.append(f"{label}: missing verdicts.{group}[{item!r}]")
            elif not isinstance(actual_group[item], bool):
                errors.append(f"{label}: verdicts.{group}[{item!r}] must be boolean")
            elif actual_group[item] is not expected_result:
                errors.append(
                    f"{label}: verdicts.{group}[{item!r}]={actual_group[item]!r} failed"
                )


def evaluate_results(root: Path, payload: Any) -> list[str]:
    """Evaluate structured human/model observations against every case."""

    cases, errors = _behavior_cases(root)
    if errors:
        return errors
    if not isinstance(payload, dict):
        return ["results: expected a JSON object"]
    if payload.get("schema_version") != 1:
        return ["results.schema_version must be 1"]
    packet, packet_errors = build_case_packet(root)
    if packet_errors or packet is None:
        return packet_errors or ["results: could not build current case packet"]
    if payload.get("packet_sha256") != packet["packet_sha256"]:
        return [
            "results.packet_sha256 must match the current emitted case packet; "
            "re-emit cases and preserve its digest in evaluator results"
        ]
    evaluator = payload.get("evaluator")
    if not isinstance(evaluator, dict):
        return ["results.evaluator must be an object"]
    for field in ("kind", "name", "evaluated_at"):
        if not isinstance(evaluator.get(field), str) or not evaluator[field].strip():
            return [f"results.evaluator.{field} must be a non-empty string"]
    results = payload.get("results")
    if not isinstance(results, list):
        return ["results.results must be a list"]

    expected_by_key = {(case["skill"], case["case_id"]): case for case in cases}
    seen: set[tuple[str, str]] = set()
    result_errors: list[str] = []
    for index, result in enumerate(results):
        prefix = f"results[{index}]"
        if not isinstance(result, dict):
            result_errors.append(f"{prefix}: expected an object")
            continue
        skill = result.get("skill")
        case_id = result.get("case_id")
        if not isinstance(skill, str) or not isinstance(case_id, str):
            result_errors.append(f"{prefix}: skill and case_id must be strings")
            continue
        key = (skill, case_id)
        if key not in expected_by_key:
            result_errors.append(f"{prefix}: unknown case {skill}/{case_id}")
            continue
        if key in seen:
            result_errors.append(f"{prefix}: duplicate case {skill}/{case_id}")
            continue
        seen.add(key)
        _check_observation(expected_by_key[key], result, result_errors)

    missing = sorted(set(expected_by_key) - seen)
    result_errors.extend(f"results: missing case {skill}/{case_id}" for skill, case_id in missing)
    return result_errors


def _read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path == "-":
        sys.stdout.write(text)
    else:
        Path(path).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-case-packet",
        metavar="PATH",
        help="write a JSON packet for external human/model evaluation; use - for stdout",
    )
    parser.add_argument(
        "--results",
        metavar="PATH",
        help="read structured observations/verdicts JSON; use - for stdin",
    )
    args = parser.parse_args()
    if args.emit_case_packet and args.results:
        parser.error("--emit-case-packet and --results are mutually exclusive")

    root = Path(__file__).resolve().parents[1]
    try:
        if args.emit_case_packet:
            packet, errors = build_case_packet(root)
            if errors:
                raise ValueError("; ".join(errors))
            assert packet is not None
            _write_json(args.emit_case_packet, packet)
            print(
                f"emitted {len(packet['cases'])} behavior case(s) to {args.emit_case_packet}",
                file=sys.stderr if args.emit_case_packet == "-" else sys.stdout,
            )
            return 0
        if args.results:
            errors = evaluate_results(root, _read_json(args.results))
            if errors:
                print("behavior eval results failed:", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print(
                "behavior eval results passed for all declared cases; "
                "evaluated supplied human/model observations without invoking a model"
            )
            return 0
        errors = validate_repository(root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"behavior eval contract failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("behavior eval contract failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    implicit = len(implicit_repo_skill_names(load_manifest(root)))
    print(
        f"deterministic behavior eval contract passed for {implicit} implicit repo skill(s); "
        "semantic model/human judgment was not executed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
