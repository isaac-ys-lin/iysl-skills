import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.verify_behavior_evals import (
    _skill_source_sha256,
    _validate_behavior,
    _validate_semantic_config,
    _validate_trigger,
    build_case_packet,
    evaluate_results,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "verify_behavior_evals.py"


def passing_results(packet):
    results = []
    for case in packet["cases"]:
        expected = case["expected"]
        observations = {}
        if "max_questions" in expected:
            observations["questions"] = expected["max_questions"]
        if "max_subagents" in expected:
            observations["subagents"] = expected["max_subagents"]
        if "must_stop" in expected:
            observations["must_stop"] = expected["must_stop"]
        if "expected_route" in expected:
            observations["route"] = expected["expected_route"]
        if "expected_status" in expected:
            observations["status"] = expected["expected_status"]
        if "source_fidelity" in expected:
            observations["source_fidelity"] = expected["source_fidelity"]

        verdicts = {}
        for group in ("must_do", "must_not_do", "required_validation"):
            if group in expected:
                verdicts[group] = {item: True for item in expected[group]}
        results.append(
            {
                "skill": case["skill"],
                "case_id": case["case_id"],
                "observations": observations,
                "verdicts": verdicts,
            }
        )
    return {
        "schema_version": 1,
        "packet_sha256": packet["packet_sha256"],
        "evaluator": {
            "kind": "test-fixture",
            "name": "behavior-eval-runner-tests",
            "evaluated_at": "2026-08-12T00:00:00Z",
        },
        "results": results,
    }


def test_case_packet_and_structured_results_pass():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    assert packet is not None
    assert packet["cases"]
    assert len(packet["packet_sha256"]) == 64
    assert all(len(case["skill_source_sha256"]) == 64 for case in packet["cases"])
    assert evaluate_results(ROOT, passing_results(packet)) == []


def test_skill_source_digest_changes_with_runtime_input(tmp_path):
    skill_dir = tmp_path / "example-skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text("first\n", encoding="utf-8")
    before = _skill_source_sha256(skill_dir)
    skill.write_text("second\n", encoding="utf-8")
    assert _skill_source_sha256(skill_dir) != before


@pytest.mark.skipif(os.name == "nt", reason="Windows does not expose POSIX execute bits")
def test_skill_source_digest_changes_with_executable_mode(tmp_path):
    skill_dir = tmp_path / "example-skill"
    scripts = skill_dir / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    before = _skill_source_sha256(skill_dir)
    script.chmod(0o644)
    assert _skill_source_sha256(skill_dir) != before


def test_explicit_skill_required_gate_is_not_ignored(tmp_path):
    (tmp_path / "skills" / "explicit-skill").mkdir(parents=True)
    (tmp_path / "skills-manifest.json").write_text(
        json.dumps(
            {
                "skills": {
                    "explicit-skill": {
                        "maintainer": "iysl",
                        "origin": "forked",
                        "visibility": "explicit",
                        "license": "bundled-upstream",
                        "required_gates": ["behavior"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    from tools.verify_behavior_evals import validate_repository

    errors = validate_repository(tmp_path)
    assert any("required behavior eval is missing" in error for error in errors)


def test_unknown_required_gate_is_rejected(tmp_path):
    (tmp_path / "skills" / "explicit-skill").mkdir(parents=True)
    (tmp_path / "skills-manifest.json").write_text(
        json.dumps(
            {
                "skills": {
                    "explicit-skill": {
                        "required_gates": ["behaviour"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    from tools.verify_behavior_evals import validate_repository

    errors = validate_repository(tmp_path)
    assert any("unsupported required gates" in error for error in errors)


def test_trigger_gate_requires_semantic_config(tmp_path):
    skill_dir = tmp_path / "skills" / "explicit-skill"
    evals = skill_dir / "evals"
    evals.mkdir(parents=True)
    (evals / "trigger_cases.json").write_text(
        json.dumps(
            {
                "should_trigger": ["trigger me"],
                "should_not_trigger": ["do not trigger me"],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "skills-manifest.json").write_text(
        json.dumps(
            {
                "skills": {
                    "explicit-skill": {
                        "required_gates": ["trigger"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    from tools.verify_behavior_evals import validate_repository

    errors = validate_repository(tmp_path)
    assert any("required trigger semantic config is missing" in error for error in errors)


def test_trigger_contract_rejects_empty_and_duplicate_cases(tmp_path):
    path = tmp_path / "trigger_cases.json"
    path.write_text(
        json.dumps(
            {
                "should_trigger": ["same prompt", ""],
                "should_not_trigger": ["same prompt", 42],
            }
        ),
        encoding="utf-8",
    )
    errors = []
    _validate_trigger(path, errors)
    assert any("non-empty string" in error for error in errors)
    assert any("duplicate trigger case" in error for error in errors)


def test_trigger_contract_validates_near_neighbors_and_threshold(tmp_path):
    path = tmp_path / "trigger_cases.json"
    path.write_text(
        json.dumps(
            {
                "recommended_threshold": 2,
                "should_trigger": ["trigger me"],
                "should_not_trigger": ["do not trigger me"],
                "near_neighbor": [42],
            }
        ),
        encoding="utf-8",
    )
    errors = []
    _validate_trigger(path, errors)
    assert any("recommended_threshold" in error for error in errors)
    assert any("near_neighbor[0].text" in error for error in errors)


def test_semantic_config_must_be_valid_nonempty_json(tmp_path):
    path = tmp_path / "semantic_config.json"
    path.write_text("{broken", encoding="utf-8")
    errors = []
    _validate_semantic_config(path, errors)
    assert any("invalid JSON" in error for error in errors)

    path.write_text("{}", encoding="utf-8")
    errors = []
    _validate_semantic_config(path, errors)
    assert any("non-empty object" in error for error in errors)

    path.write_text(
        json.dumps(
            {
                "recommended_threshold": 99,
                "fallback_positive_concepts": ["missing"],
                "positive_concepts": {"known": {"weight": "high", "phrases": []}},
                "negative_concepts": {"bad": {"weight": 0.5, "phrases": ["bad"]}},
                "exclusive_negative_concepts": ["missing"],
            }
        ),
        encoding="utf-8",
    )
    errors = []
    _validate_semantic_config(path, errors)
    assert any("recommended_threshold" in error for error in errors)
    assert any("unknown concepts" in error for error in errors)
    assert any("exclusive_negative_concepts reference unknown" in error for error in errors)
    assert any("weight must be" in error for error in errors)
    assert any("phrases must be" in error for error in errors)


def test_behavior_contract_rejects_duplicate_and_contradictory_criteria(tmp_path):
    path = tmp_path / "behavior_cases.json"
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "contradictory",
                        "kind": "failure",
                        "prompt": "exercise the contract",
                        "expected": {
                            "must_do": ["same action", "same action"],
                            "must_not_do": [" same action "],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    errors = []
    _validate_behavior(path, errors)
    assert any("must not contain duplicates" in error for error in errors)
    assert any("must not have outer whitespace" in error for error in errors)
    assert any("contradictory must_do/must_not_do" in error for error in errors)


def test_behavior_contract_rejects_empty_criterion_lists(tmp_path):
    path = tmp_path / "behavior_cases.json"
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "vacuous",
                        "kind": "failure",
                        "prompt": "exercise the contract",
                        "expected": {"must_do": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    errors = []
    _validate_behavior(path, errors)
    assert any("non-empty list" in error for error in errors)


def test_structured_results_fail_on_observation_and_verdict():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    results = passing_results(packet)
    first = results["results"][0]
    first["observations"]["questions"] = 999
    failures = evaluate_results(ROOT, results)
    assert any("exceeds max" in error for error in failures)

    case_index = next(
        index
        for index, case in enumerate(packet["cases"])
        if case["expected"].get("must_do")
    )
    verdict_results = passing_results(packet)
    verdict_case = verdict_results["results"][case_index]
    expected_item = packet["cases"][case_index]["expected"]["must_do"][0]
    verdict_case["verdicts"]["must_do"][expected_item] = False
    verdict_failures = evaluate_results(ROOT, verdict_results)
    assert any("failed" in error for error in verdict_failures)

    negative_results = passing_results(packet)
    negative_results["results"][0]["observations"]["questions"] = -1
    negative_failures = evaluate_results(ROOT, negative_results)
    assert any("must be non-negative" in error for error in negative_failures)


def test_structured_results_fail_when_case_is_missing():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    results = passing_results(packet)
    results["results"].pop()
    failures = evaluate_results(ROOT, results)
    assert any("missing case" in error for error in failures)


def test_structured_results_reject_excess_entries():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    results = passing_results(packet)
    results["results"].append(dict(results["results"][0]))
    failures = evaluate_results(ROOT, results)
    assert any("expected at most" in error for error in failures)


def test_structured_results_require_current_packet_and_evaluator_provenance():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    results = passing_results(packet)
    results["packet_sha256"] = "0" * 64
    assert any("packet_sha256" in error for error in evaluate_results(ROOT, results))

    results = passing_results(packet)
    del results["evaluator"]
    assert any("evaluator" in error for error in evaluate_results(ROOT, results))

    results = passing_results(packet)
    results["evaluator"]["evaluated_at"] = "not-a-time"
    assert any("ISO 8601" in error for error in evaluate_results(ROOT, results))


def test_results_input_size_is_bounded(tmp_path, monkeypatch):
    from tools import verify_behavior_evals as runner_module

    path = tmp_path / "oversized.json"
    path.write_bytes(b"12345")
    monkeypatch.setattr(runner_module, "MAX_RESULTS_BYTES", 4)
    with pytest.raises(ValueError, match="exceeds"):
        runner_module._read_json(str(path))


def test_case_packet_size_is_bounded(monkeypatch):
    from tools import verify_behavior_evals as runner_module

    monkeypatch.setattr(runner_module, "MAX_CASE_PACKET_BYTES", 1)
    packet, errors = runner_module.build_case_packet(ROOT)
    assert packet is None
    assert any("maximum is 1" in error for error in errors)


def test_cli_emits_packet_and_blocks_bad_results(tmp_path):
    packet_path = tmp_path / "packet.json"
    emitted = subprocess.run(
        [sys.executable, str(RUNNER), "--emit-case-packet", str(packet_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert emitted.returncode == 0, emitted.stderr
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    result_path = tmp_path / "results.json"
    result_path.write_text(json.dumps(passing_results(packet)), encoding="utf-8")
    passed = subprocess.run(
        [sys.executable, str(RUNNER), "--results", str(result_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert passed.returncode == 0, passed.stderr

    bad = passing_results(packet)
    bad["results"].pop()
    result_path.write_text(json.dumps(bad), encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, str(RUNNER), "--results", str(result_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert failed.returncode != 0
    assert "missing case" in failed.stderr
