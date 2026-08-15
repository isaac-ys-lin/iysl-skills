import json
import subprocess
import sys
from pathlib import Path

from tools.verify_behavior_evals import (
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
    assert evaluate_results(ROOT, passing_results(packet)) == []


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


def test_structured_results_require_current_packet_and_evaluator_provenance():
    packet, errors = build_case_packet(ROOT)
    assert errors == []
    results = passing_results(packet)
    results["packet_sha256"] = "0" * 64
    assert any("packet_sha256" in error for error in evaluate_results(ROOT, results))

    results = passing_results(packet)
    del results["evaluator"]
    assert any("evaluator" in error for error in evaluate_results(ROOT, results))


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
