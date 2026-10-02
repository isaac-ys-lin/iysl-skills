"""Contract tests for the v5 blind first-round Council artifacts."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_council_run.py"
LEGACY_TESTS = ROOT / "tests" / "test_council_run_validator.py"


def _load_legacy_tests():
    spec = importlib.util.spec_from_file_location("council_legacy_tests", LEGACY_TESTS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


LEGACY = _load_legacy_tests()
VALIDATOR = LEGACY.VALIDATOR
SEATS = sorted(VALIDATOR.SEATS)
FAMILIES = [
    "revenue_orders_capex_recognition",
    "product_mix_and_margins",
    "reinvestment_and_fcff",
    "capital_structure_and_wacc",
    "duration_fade_and_terminal",
    "twelve_month_market_expectations",
]


def _case(*, soros=False):
    value = {
        "mechanism": "Evidence changes the calibrated assumption through the operating bridge.",
        "joint_conditions": ["The observed trend persists through the estimate period."],
        "observable_triggers": ["The next reported result confirms the trend."],
        "falsifier": "The next reported result reverses the observed trend.",
    }
    if soros:
        value["missed_entry_cost"] = "A confirmed re-rating would make waiting for a cheaper entry costly."
    return value


def _v5_fixture(tmp_path):
    plugin, artifact_root, council = LEGACY._v4_fixture(tmp_path)
    council["schema_version"] = 5
    bindings = council["artifact_bindings"]
    bindings["authority_version"] = 4

    underwrite_path = artifact_root / bindings["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text())
    for index, assumption in enumerate(underwrite["candidate_assumptions"]):
        assumption["family"] = FAMILIES[index]
    LEGACY._write_json(underwrite_path, underwrite)
    bindings["preliminary_underwrite"] = LEGACY._descriptor(underwrite_path, artifact_root)

    for seat in SEATS:
        packet_path = artifact_root / bindings["seat_packets"][seat]["path"]
        packet = json.loads(packet_path.read_text())
        packet.update(
            schema_version="council-premodel-seat-packet-v4",
            preliminary_underwrite_sha256=bindings["preliminary_underwrite"]["sha256"],
            dispatched_at="2026-08-22T10:10:00+08:00",
            candidate_assumptions=[
                {
                    key: assumption[key]
                    for key in (
                        "assumption_id", "family", "period", "unit", "evidence_ids",
                        "flip_condition", "rationale", "rejected_alternative",
                        "challenge_signal_dispositions",
                    )
                }
                for assumption in underwrite["candidate_assumptions"]
            ],
        )
        LEGACY._write_json(packet_path, packet)
        bindings["seat_packets"][seat] = LEGACY._descriptor(packet_path, artifact_root)

        memo_path = artifact_root / bindings["sealed_memos"][seat]["path"]
        memo = json.loads(memo_path.read_text())
        memo.update(
            schema_version="council-sealed-memo-v4",
            packet_sha256=bindings["seat_packets"][seat]["sha256"],
            challenges=[
                {
                    "assumption_id": assumption["assumption_id"],
                    "period": assumption["period"],
                    "unit": assumption["unit"],
                    "estimation_status": "estimated",
                    "proposed_base": assumption["proposed_base"],
                    "proposed_range": assumption["proposed_range"],
                    "evidence_ids": ["IR:earnings-release:2026Q2"],
                    "candidate_source_ids": [],
                    "reasoning": "The accepted primary evidence supports this estimate.",
                    "decision_impact": "Use the estimate in the mechanical range comparison.",
                    "falsifier": assumption["flip_condition"],
                    "not_estimable_reason": None,
                    "missing_evidence": None,
                }
                for assumption in underwrite["candidate_assumptions"]
            ],
            strongest_upside_case=_case(soros=seat == "soros"),
            strongest_downside_case=_case(),
        )
        memo.pop("strongest_countercase", None)
        LEGACY._write_json(memo_path, memo)
        bindings["sealed_memos"][seat] = LEGACY._descriptor(memo_path, artifact_root)

    adjudication_path = artifact_root / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication.update(
        schema_version="pei-council-adjudication-v4",
        preliminary_underwrite_sha256=bindings["preliminary_underwrite"]["sha256"],
        packet_hashes={seat: bindings["seat_packets"][seat]["sha256"] for seat in SEATS},
        memo_hashes={seat: bindings["sealed_memos"][seat]["sha256"] for seat in SEATS},
    )
    for decision in adjudication["decisions"]:
        decision["range_comparisons"] = {seat: "within_range" for seat in SEATS}
        decision["retention_basis"] = None
    LEGACY._write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"] = LEGACY._descriptor(adjudication_path, artifact_root)
    return plugin, artifact_root, council


def _rebind_memo(root, council, seat, mutate):
    bindings = council["artifact_bindings"]
    path = root / bindings["sealed_memos"][seat]["path"]
    memo = json.loads(path.read_text())
    mutate(memo)
    LEGACY._write_json(path, memo)
    bindings["sealed_memos"][seat] = LEGACY._descriptor(path, root)
    adjudication_path = root / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication["memo_hashes"][seat] = bindings["sealed_memos"][seat]["sha256"]
    LEGACY._write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"] = LEGACY._descriptor(adjudication_path, root)


def _rebind_packet(root, council, seat, mutate):
    bindings = council["artifact_bindings"]
    path = root / bindings["seat_packets"][seat]["path"]
    packet = json.loads(path.read_text())
    mutate(packet)
    LEGACY._write_json(path, packet)
    bindings["seat_packets"][seat] = LEGACY._descriptor(path, root)
    _rebind_memo(root, council, seat, lambda memo: memo.update(packet_sha256=bindings["seat_packets"][seat]["sha256"]))
    adjudication_path = root / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication["packet_hashes"][seat] = bindings["seat_packets"][seat]["sha256"]
    LEGACY._write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"] = LEGACY._descriptor(adjudication_path, root)


def _errors(council, plugin, root):
    return VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root)


def _adjudication(root, council):
    return root / council["artifact_bindings"]["owner_adjudication"]["path"]


def _write_adjudication(root, council, adjudication):
    path = _adjudication(root, council)
    LEGACY._write_json(path, adjudication)
    council["artifact_bindings"]["owner_adjudication"] = LEGACY._descriptor(path, root)


def _same_side(root, council, *, above=False):
    proposed_range = [5.0, 15.0] if above else [35.0, 45.0]
    direction = "owner_above_range" if above else "owner_below_range"
    for seat in SEATS[:2]:
        _rebind_memo(root, council, seat, lambda memo: memo["challenges"][0].update(proposed_base=sum(proposed_range) / 2, proposed_range=proposed_range))
    path = _adjudication(root, council)
    adjudication = json.loads(path.read_text())
    adjudication["memo_hashes"] = {seat: council["artifact_bindings"]["sealed_memos"][seat]["sha256"] for seat in SEATS}
    adjudication["decisions"][0]["range_comparisons"] = {seat: (direction if seat in SEATS[:2] else "within_range") for seat in SEATS}
    return adjudication


def test_v5_accepts_blind_packet_numeric_memos_and_symmetric_cases(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    assert _errors(council, plugin, root) == []


def test_v5_withdrawn_assumption_has_no_compatibility_value_or_model_input(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    bindings = council["artifact_bindings"]
    spec_path = root / bindings["final_model_spec"]["path"]
    spec = json.loads(spec_path.read_text())
    spec["assumption_ids"].remove("revenue_growth")
    LEGACY._write_json(spec_path, spec)
    bindings["final_model_spec"] = LEGACY._descriptor(spec_path, root)
    bindings.pop("fv_freeze_receipt")
    adjudication = json.loads(_adjudication(root, council).read_text())
    decision = adjudication["decisions"][0]
    decision.pop("decision")
    decision.update(final_base=None, final_range=None, model_input_ids=[],
                    reason="The acquisition-only EBIT estimate was withdrawn; the consolidated model supersedes it.")
    adjudication["final_model_spec_sha256"] = bindings["final_model_spec"]["sha256"]
    _write_adjudication(root, council, adjudication)
    assert _errors(council, plugin, root) == []


@pytest.mark.parametrize("changes, expected", [
    ({"final_base": None}, "final_base must be numeric"),
    ({"final_range": None}, "final_range must be an ordered numeric pair"),
    ({"final_base": None, "final_range": None}, "model_input_ids must be empty"),
    ({"final_base": True}, "final_base must be numeric"),
    ({"final_base": float("nan")}, "final_base must be numeric"),
])
def test_v5_rejects_ambiguous_withdrawal_or_invalid_scalar(tmp_path, changes, expected):
    plugin, root, council = _v5_fixture(tmp_path)
    adjudication = json.loads(_adjudication(root, council).read_text())
    adjudication["decisions"][0].update(changes)
    _write_adjudication(root, council, adjudication)
    assert any(expected in error for error in _errors(council, plugin, root))


def test_v5_lean_root_anchors_on_final_receipt_and_keeps_model_timeline(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    council.pop("evidence_cutoff")
    council["artifact_bindings"].pop("fv_freeze_receipt")
    adjudication = json.loads(_adjudication(root, council).read_text())
    for decision in adjudication["decisions"]:
        decision.pop("decision")
    _write_adjudication(root, council, adjudication)
    assert _errors(council, plugin, root) == []
    council["artifact_bindings"]["model_committed_at"] = "2026-08-22T10:22:00+08:00"
    assert any("current Council timeline" in error for error in _errors(council, plugin, root))


@pytest.mark.parametrize("fixture", [LEGACY._v3_fixture, LEGACY._v4_fixture])
def test_legacy_adjudication_still_requires_numeric_final_value(tmp_path, fixture):
    plugin, root, council = fixture(tmp_path)
    assert _errors(council, plugin, root) == []
    adjudication = json.loads(_adjudication(root, council).read_text())
    adjudication["decisions"][0].update(decision="reject", final_base=None, final_range=None, model_input_ids=[])
    _write_adjudication(root, council, adjudication)
    assert any("final_base must be numeric" in error for error in _errors(council, plugin, root))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda root, council: _rebind_packet(root, council, "damodaran", lambda packet: packet["candidate_assumptions"][0].update(proposed_base=20.0)), "leaks"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(estimation_status="uncertain")), "estimation_status"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(period="FY2028E")), "period"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(unit="USD")), "unit"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(proposed_base=float("nan"))), "numeric"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(proposed_base=True)), "numeric"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(proposed_base=None, proposed_range=None)), "estimated requires numeric"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"].pop()), "exactly once"),
        (lambda root, council: _rebind_memo(root, council, "soros", lambda memo: memo["strongest_upside_case"].pop("missed_entry_cost")), "missed_entry_cost"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo.pop("strongest_downside_case")), "strongest_downside_case"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["strongest_upside_case"].update(joint_conditions=[])), "joint_conditions"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo.update(strongest_downside_case={})), "strongest_downside_case"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(evidence_ids=[], candidate_source_ids=[])), "evidence"),
        (lambda root, council: _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(assessment="too_aggressive")), "unexpected"),
        (lambda root, council: _rebind_packet(root, council, "damodaran", lambda packet: packet.update(dispatched_at="2026-08-22T10:21:00+08:00")), "blind packets"),
    ],
)
def test_v5_rejects_blind_contract_violations(tmp_path, mutate, expected):
    plugin, root, council = _v5_fixture(tmp_path)
    mutate(root, council)
    assert any(expected in error for error in _errors(council, plugin, root))


def test_v5_rejects_post_memo_underwrite_rewrite_that_breaks_packet_commitment(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    bindings = council["artifact_bindings"]
    underwrite_path = root / bindings["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text())
    underwrite["candidate_assumptions"][0]["proposed_base"] = 21.0
    LEGACY._write_json(underwrite_path, underwrite)
    bindings["preliminary_underwrite"] = LEGACY._descriptor(underwrite_path, root)
    adjudication_path = root / bindings["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text())
    adjudication["preliminary_underwrite_sha256"] = bindings["preliminary_underwrite"]["sha256"]
    adjudication["decisions"][0]["prior_base"] = 21.0
    LEGACY._write_json(adjudication_path, adjudication)
    bindings["owner_adjudication"] = LEGACY._descriptor(adjudication_path, root)
    assert any("original preliminary underwrite hash" in error for error in _errors(council, plugin, root))


def test_v5_requires_retention_basis_for_two_same_side_ranges(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    adjudication = _same_side(root, council)
    adjudication["decisions"][0]["final_range"] = [5.0, 25.0]
    _write_adjudication(root, council, adjudication)
    assert any("retention_basis" in error for error in _errors(council, plugin, root))


def test_v5_accepts_not_estimable_and_evidence_backed_retention(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_memo(
        root, council, "mauboussin",
        lambda memo: memo["challenges"][1].update(
            estimation_status="not_estimable", proposed_base=None, proposed_range=None,
            not_estimable_reason="The available evidence does not isolate this driver.",
            missing_evidence="A disclosed segment bridge would make this estimable.",
        ),
    )
    for seat in SEATS[:2]:
        _rebind_memo(root, council, seat, lambda memo: memo["challenges"][0].update(proposed_base=40.0, proposed_range=[35.0, 45.0]))
    path = root / council["artifact_bindings"]["owner_adjudication"]["path"]
    adjudication = json.loads(path.read_text())
    adjudication["memo_hashes"] = {seat: council["artifact_bindings"]["sealed_memos"][seat]["sha256"] for seat in SEATS}
    adjudication["decisions"][0].update(
        range_comparisons={seat: ("owner_below_range" if seat in SEATS[:2] else "within_range") for seat in SEATS},
        retention_basis={"omitted_evidence_ids": ["IR:earnings-release:2026Q2"], "omitted_mechanism": ""},
    )
    adjudication["decisions"][1]["range_comparisons"]["mauboussin"] = "not_estimable"
    LEGACY._write_json(path, adjudication)
    council["artifact_bindings"]["owner_adjudication"] = LEGACY._descriptor(path, root)
    assert _errors(council, plugin, root) == []


def test_v5_not_estimable_requires_concrete_reason_and_missing_evidence(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_memo(
        root, council, "damodaran",
        lambda memo: memo["challenges"][0].update(
            estimation_status="not_estimable", proposed_base=None, proposed_range=None,
            not_estimable_reason="", missing_evidence="",
        ),
    )
    assert any("not_estimable" in error for error in _errors(council, plugin, root))


def test_v5_search_required_needs_source_checks_for_not_estimable(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_packet(root, council, "damodaran", lambda packet: packet.update(search_required=True))
    _rebind_memo(root, council, "damodaran", lambda memo: [
        challenge.update(source_checks=[]) for challenge in memo["challenges"]
    ])
    _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(
        estimation_status="not_estimable", proposed_base=None, proposed_range=None,
        not_estimable_reason="The filings do not isolate this driver.",
        missing_evidence="A segment bridge is needed.",
    ))
    adjudication = json.loads(_adjudication(root, council).read_text())
    adjudication["decisions"][0]["range_comparisons"]["damodaran"] = "not_estimable"
    _write_adjudication(root, council, adjudication)
    assert any("source_checks" in error for error in _errors(council, plugin, root))

    _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0]["source_checks"].append({
        "tool": "WebFetch", "query_or_url": "https://www.sec.gov/Archives/example",
        "result": "The filing has aggregate revenue but no segment bridge.",
        "still_insufficient_reason": "The missing segment bridge prevents a standalone estimate.",
    }))
    assert _errors(council, plugin, root) == []


def test_v5_search_required_rejects_disallowed_source_tool(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_packet(root, council, "soros", lambda packet: packet.update(search_required=True))
    _rebind_memo(root, council, "soros", lambda memo: [
        challenge.update(source_checks=[]) for challenge in memo["challenges"]
    ])
    _rebind_memo(root, council, "soros", lambda memo: memo["challenges"][0]["source_checks"].append({
        "tool": "curl", "query_or_url": "https://example.com", "result": "blocked",
        "still_insufficient_reason": "The source was unavailable.",
    }))
    assert any("source_checks" in error for error in _errors(council, plugin, root))


def test_source_check_only_cli_binds_opt_in_packet(tmp_path):
    packet_path = tmp_path / "packet.json"
    memo_path = tmp_path / "memo.json"
    packet = {"schema_version": "council-premodel-seat-packet-v4", "search_required": True, "seat": "soros", "candidate_assumptions": [{"assumption_id": "A1"}], "instructions": "Estimate each candidate independently."}
    packet_path.write_text(json.dumps(packet))
    memo = {
        "seat": "soros", "packet_sha256": LEGACY._sha256(packet_path),
        "challenges": [{"assumption_id": "A1", "estimation_status": "not_estimable", "source_checks": [{
            "tool": "mcp__codex_apps__exa_web_search_exa", "query_or_url": "ONDS backlog disclosure",
            "result": "No quarterly conversion bridge found.",
            "still_insufficient_reason": "The target-period conversion remains unknown.",
        }]}],
    }
    memo_path.write_text(json.dumps(memo))
    script = ROOT / "scripts" / "validate_council_source_checks.py"
    command = [sys.executable, str(script), str(packet_path), str(memo_path)]
    assert subprocess.run(command, capture_output=True, text=True).returncode == 0
    memo["packet_sha256"] = "0" * 64
    memo_path.write_text(json.dumps(memo))
    assert "exact packet bytes" in subprocess.run(command, capture_output=True, text=True).stdout
    assert subprocess.run(command[:-1], capture_output=True, text=True).returncode == 0
    packet_path.write_text(json.dumps({**packet, "instructions": ["Estimate each candidate independently."]}))
    assert "packet.instructions must be a non-empty string" in subprocess.run(command[:-1], capture_output=True, text=True).stdout
    packet_path.write_text(json.dumps(packet))
    for missing in ("schema_version", "search_required"):
        packet_path.write_text(json.dumps({key: value for key, value in packet.items() if key != missing}))
        assert subprocess.run(command[:-1], capture_output=True, text=True).returncode == 1


def test_v5_accepts_source_only_challenge_candidate(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_memo(
        root, council, "damodaran",
        lambda memo: memo["challenges"][0].update(
            evidence_ids=[], candidate_source_ids=["damodaran:new-product"]
        ),
    )
    assert _errors(council, plugin, root) == []


@pytest.mark.parametrize("private_row", [
    {"source_kind": "model", "requirement_class": "primary"},
    {"source_kind": "primary", "requirement_class": "model"},
    {"source_kind": "primary", "requirement_class": "primary", "path": "support/current-council-v3/preliminary_underwrite.json"},
    {"source_kind": "primary", "requirement_class": "primary", "sha256": True},
])
def test_v5_rejects_owner_private_evidence_in_packet(tmp_path, private_row):
    plugin, root, council = _v5_fixture(tmp_path)
    receipt_path = root / council["council_input_pei_receipt"]["path"]
    receipt = json.loads(receipt_path.read_text())
    row = {
        "id": "OWNER:private-model", "source_kind": "primary",
        "requirement_class": "primary", "evidence_nature": "company_claim",
    } | private_row
    if row.get("sha256") is True:
        row["sha256"] = council["artifact_bindings"]["preliminary_underwrite"]["sha256"]
    receipt["evidence_registry"].append(row)
    LEGACY._write_json(receipt_path, receipt)
    council["council_input_pei_receipt"] = LEGACY._descriptor(receipt_path, root)
    _rebind_packet(root, council, "damodaran", lambda packet: packet["evidence_ids"].append("OWNER:private-model"))
    assert any("packet evidence_ids exceed accepted PEI evidence" in error for error in _errors(council, plugin, root))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda packet: packet.update(evidence_ids=["SA:market:2026-08-22"]), "cover all candidate evidence"),
        (lambda packet: packet.update(dispatched_at="2026-08-22T09:59:00+08:00"), "cannot precede Council input cutoff"),
    ],
)
def test_v5_packet_evidence_and_dispatch_guards(tmp_path, mutate, expected):
    plugin, root, council = _v5_fixture(tmp_path)
    _rebind_packet(root, council, "damodaran", mutate)
    assert any(expected in error for error in _errors(council, plugin, root))


def test_v5_range_comparisons_respect_boundaries_and_opposite_sides(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    ranges = {"damodaran": [20.0, 30.0], "mauboussin": [10.0, 20.0], "soros": [21.0, 30.0]}
    for seat, proposed_range in ranges.items():
        _rebind_memo(root, council, seat, lambda memo, proposed_range=proposed_range: memo["challenges"][0].update(proposed_base=sum(proposed_range) / 2, proposed_range=proposed_range))
    path = _adjudication(root, council)
    adjudication = json.loads(path.read_text())
    adjudication["memo_hashes"] = {seat: council["artifact_bindings"]["sealed_memos"][seat]["sha256"] for seat in SEATS}
    adjudication["decisions"][0]["range_comparisons"] = {"damodaran": "within_range", "mauboussin": "within_range", "soros": "owner_below_range"}
    _write_adjudication(root, council, adjudication)
    assert _errors(council, plugin, root) == []
    _rebind_memo(root, council, "damodaran", lambda memo: memo["challenges"][0].update(proposed_base=10.0, proposed_range=[5.0, 15.0]))
    adjudication = json.loads(path.read_text())
    adjudication["decisions"][0]["range_comparisons"]["damodaran"] = "owner_above_range"
    _write_adjudication(root, council, adjudication)
    assert _errors(council, plugin, root) == []


@pytest.mark.parametrize("basis", [
    {"omitted_evidence_ids": [], "omitted_mechanism": ""},
    {"omitted_evidence_ids": ["NOT:accepted"], "omitted_mechanism": ""},
])
def test_v5_rejects_empty_or_unaccepted_retention_basis(tmp_path, basis):
    plugin, root, council = _v5_fixture(tmp_path)
    adjudication = _same_side(root, council, above=True)
    adjudication["decisions"][0]["retention_basis"] = basis
    _write_adjudication(root, council, adjudication)
    assert any("retention_basis" in error for error in _errors(council, plugin, root))


def test_v5_accepts_mechanism_retention_basis_for_same_side_above(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    adjudication = _same_side(root, council, above=True)
    adjudication["decisions"][0]["retention_basis"] = {
        "omitted_evidence_ids": [], "omitted_mechanism": "The seat ranges omit the owner’s durable demand mechanism."
    }
    _write_adjudication(root, council, adjudication)
    assert _errors(council, plugin, root) == []


def test_v5_rejects_adjudication_range_comparison_lie(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    path = _adjudication(root, council)
    adjudication = json.loads(path.read_text())
    adjudication["decisions"][0]["range_comparisons"]["damodaran"] = "owner_above_range"
    _write_adjudication(root, council, adjudication)
    assert any("validator-derived comparisons" in error for error in _errors(council, plugin, root))


def test_v5_compare_ranges_emits_mechanical_map_without_adjudication(tmp_path):
    plugin, root, council = _v5_fixture(tmp_path)
    council_path = root / "support" / "council-run.json"
    council["artifact_bindings"]["owner_adjudication"] = {
        "path": "support/pending-owner-adjudication.json", "sha256": "0" * 64
    }
    LEGACY._write_json(council_path, council)
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--compare-ranges", "--plugin-root", str(plugin), "--artifact-root", str(root), str(council_path)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["revenue_growth"] == {seat: "within_range" for seat in SEATS}
