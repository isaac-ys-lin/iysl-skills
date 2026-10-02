import hashlib
import importlib.util
import json
import pytest
import subprocess
import sys
from pathlib import Path, PureWindowsPath


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
                "evidence_nature": "provider_signal",
            },
            {
                "id": "IR:earnings-release:2026Q2",
                "requirement_class": "primary",
                "source_kind": "primary",
                "evidence_nature": "company_claim",
            },
            {
                "id": ambient_claim_id,
                "requirement_class": "ambient_context",
                "source_kind": "study_flow",
                "evidence_nature": "research_lead",
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


def _descriptor(path, artifact_dir):
    return {
        "path": path.relative_to(artifact_dir).as_posix(),
        "sha256": _sha256(path),
    }


def _pre_dispatch_fixture(artifact_dir, pei_receipt):
    preliminary_path = artifact_dir / "support" / "council" / "preliminary_underwrite.json"
    preliminary = {
        "schema_version": "pei-preliminary-underwrite-v2",
        "ticker": pei_receipt["ticker"],
        "security_id": pei_receipt["security_identity"]["security_id"],
        "evidence_cutoff": pei_receipt["evidence_cutoff"],
        "owner": "equity-model-update",
        "decision_horizon": "12 months",
        "candidate_assumptions": [{"assumption_id": "PRE:EXAMPLE:ONE"}],
    }
    _write_json(preliminary_path, preliminary)
    evidence_id = "MODEL:EXAMPLE:PRECOUNCIL-UNDERWRITE"
    model_path = artifact_dir / "support" / "model_owner_pre_council_receipt_v2.json"
    _write_json(
        model_path,
        {
            "schema_version": 1,
            "kind": "model",
            "ticker": preliminary["ticker"],
            "security_id": preliminary["security_id"],
            "evidence_cutoff": preliminary["evidence_cutoff"],
            "validation_status": "PASS",
            "evidence_ids": [evidence_id],
            "evidence_registry": [
                {
                    "id": evidence_id,
                    "artifact": "support/council/preliminary_underwrite.json",
                    "sha256": _sha256(preliminary_path),
                    "as_of": preliminary["evidence_cutoff"],
                    "evidence_nature": "model_output",
                }
            ],
        },
    )
    pei_receipt["owner_declaration"] = {"declared_receipt_kinds": ["model"]}
    pei_receipt["subordinate_receipts"].append(
        {
            "kind": "model",
            "artifact": "support/model_owner_pre_council_receipt_v2.json",
            "sha256": _sha256(model_path),
            "validation_status": "PASS",
        }
    )
    pei_receipt["evidence_registry"].append(
        {
            "id": evidence_id,
            "requirement_class": "model",
            "source_kind": "model",
            "artifact": "support/council/preliminary_underwrite.json",
            "sha256": _sha256(preliminary_path),
        }
    )
    return preliminary_path, model_path


@pytest.mark.parametrize("windows_relative_path", [False, True])
def test_pre_dispatch_admits_only_an_exact_underwrite_bound_owner_model_input(
    tmp_path, monkeypatch, windows_relative_path
):
    _, artifact_dir, pei_path, pei_receipt = _build_chain(tmp_path)
    _pre_dispatch_fixture(artifact_dir, pei_receipt)
    _write_json(pei_path, pei_receipt)

    if windows_relative_path:
        relative_to = Path.relative_to
        preliminary_path = artifact_dir / "support/council/preliminary_underwrite.json"

        def platform_relative_path(path, *args, **kwargs):
            result = relative_to(path, *args, **kwargs)
            return PureWindowsPath(result.as_posix()) if path == preliminary_path else result

        monkeypatch.setattr(Path, "relative_to", platform_relative_path)

    errors = VALIDATOR.validate_pre_dispatch_admission(
        artifact_dir=artifact_dir,
        owner_model_pei_input=Path("support/pei_input_receipt.json"),
        preliminary_underwrite=Path("support/council/preliminary_underwrite.json"),
    )

    assert errors == []


def test_pre_dispatch_rejects_model_receipt_that_is_not_bound_to_underwrite(tmp_path):
    _, artifact_dir, pei_path, pei_receipt = _build_chain(tmp_path)
    _, model_path = _pre_dispatch_fixture(artifact_dir, pei_receipt)
    model = json.loads(model_path.read_text(encoding="utf-8"))
    model["evidence_registry"][0]["sha256"] = "0" * 64
    _write_json(model_path, model)
    pei_receipt["subordinate_receipts"][-1]["sha256"] = _sha256(model_path)
    _write_json(pei_path, pei_receipt)

    errors = VALIDATOR.validate_pre_dispatch_admission(
        artifact_dir=artifact_dir,
        owner_model_pei_input=Path("support/pei_input_receipt.json"),
        preliminary_underwrite=Path("support/council/preliminary_underwrite.json"),
    )

    assert any("does not exact-bind the preliminary underwrite" in error for error in errors)


def _validate(council, plugin_root, artifact_dir):
    return VALIDATOR.validate(
        council, plugin_root=plugin_root, artifact_dir=artifact_dir
    )


def test_legacy_council_schema_is_read_only(tmp_path):
    assert _validate({"schema_version": 2}, tmp_path, tmp_path) == [
        "legacy council schema 2 is read-only and is not revalidated"
    ]


def test_cli_validates_the_public_artifact_seam(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    council_path = artifact_dir / "support" / "council_run.json"
    _write_json(council_path, council)
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


def _v3_fixture(tmp_path):
    plugin_root, artifact_dir, pei_path, pei_receipt = _build_chain(tmp_path)
    support = artifact_dir / "support" / "current-council-v3"
    identity = {
        "ticker": "EXAMPLE",
        "security_id": "SEC-CIK-0000001",
        "evidence_cutoff": pei_receipt["evidence_cutoff"],
    }
    assumption_families = {
        "revenue_orders_capex_recognition": "revenue_growth",
        "product_mix_and_margins": "operating_margin",
        "reinvestment_and_fcff": "sales_to_capital",
        "capital_structure_and_wacc": "wacc",
        "duration_fade_and_terminal": "terminal_growth",
        "twelve_month_market_expectations": "forward_multiple",
    }
    assumptions = [
        {
            "assumption_id": assumption_id,
            "proposed_base": 20.0,
            "proposed_range": [10.0, 30.0],
            "evidence_ids": ["IR:earnings-release:2026Q2"],
            "period": "FY2027E",
            "unit": "percent",
            "rationale": "Reported growth and guidance anchor the initial range.",
            "rejected_alternative": "Do not replace the observed range with an arbitrary haircut.",
            "flip_condition": "Sustained growth below 10 percent.",
            "challenge_signal_dispositions": [],
        }
        for assumption_id in assumption_families.values()
    ]
    assumptions[0]["challenge_signal_dispositions"] = [
        {
            "signal_id": "ask-sa-growth-debate",
            "source_kind": "ask_sa",
            "source_id": "ASK_SA:EXAMPLE:2026-08-22",
            "evidence_nature": "provider_synthesis",
            "finding": "Ask SA surfaced a debate over whether reported growth is durable.",
            "disposition": "adopt",
            "evidence_ids": ["IR:earnings-release:2026Q2"],
            "reason": "The primary release supports keeping the question in the range calibration.",
            "flip_condition": "Sustained reported growth below 10 percent.",
        }
    ]
    underwrite = {
        "schema_version": "pei-preliminary-underwrite-v2",
        **identity,
        "candidate_assumptions": assumptions,
        "assumption_family_dispositions": [
            {
                "family": family,
                "status": "covered",
                "assumption_ids": [assumption_id],
                "reason": "The family is decision-material and represented by this candidate.",
            }
            for family, assumption_id in assumption_families.items()
        ],
    }
    underwrite_path = support / "preliminary_underwrite.json"
    _write_json(underwrite_path, underwrite)

    packet_refs = {}
    memo_refs = {}
    for minute, seat in enumerate(sorted(VALIDATOR.SEATS), start=20):
        packet = {
            "schema_version": "council-premodel-seat-packet-v2",
            **identity,
            "seat": seat,
            "candidate_assumptions": assumptions,
            "evidence_ids": ["IR:earnings-release:2026Q2"],
            "instructions": "Test too_conservative, too_aggressive, uncertain, and the market-right countercase; do not browse or choose an action.",
        }
        packet_path = support / "packets" / f"{seat}.json"
        _write_json(packet_path, packet)
        packet_refs[seat] = _descriptor(packet_path, artifact_dir)
        memo = {
            "schema_version": "council-sealed-memo-v2",
            "seat": seat,
            "sealed_at": f"2026-08-22T10:{minute}:00+08:00",
            "packet_sha256": packet_refs[seat]["sha256"],
            "browsed": False,
            "added_evidence_ids": [],
            "summary": "The proposed assumption is supported within the stated range.",
            "challenges": [
                {
                    "assumption_id": "revenue_growth",
                    "assessment": "supported",
                    "proposed_base": 20.0,
                    "proposed_range": [10.0, 30.0],
                    "evidence_ids": ["IR:earnings-release:2026Q2"],
                    "reasoning": "The accepted evidence supports the current calibration.",
                    "decision_impact": "No model change is required.",
                    "falsifier": "Sustained reported growth below 10 percent.",
                }
            ],
            "strongest_countercase": "The reported period may not represent durable demand.",
            "limitations": ["Only accepted evidence through the cutoff was reviewed."],
        }
        memo_path = support / "memos" / f"{seat}.json"
        _write_json(memo_path, memo)
        memo_refs[seat] = _descriptor(memo_path, artifact_dir)

    final_spec = {
        "schema_version": "owner-model-spec-v1",
        "identity": identity,
        "evidence_cutoff": identity["evidence_cutoff"],
        "owner": "PEI owner",
        "formula_version": "test-formula-v1",
        "assumption_ids": list(assumption_families.values()),
    }
    final_spec_path = artifact_dir / "support" / "owner-model" / "model.json"
    _write_json(final_spec_path, final_spec)
    final_spec_ref = _descriptor(final_spec_path, artifact_dir)

    adjudication = {
        "schema_version": "pei-council-adjudication-v2",
        **identity,
        "adjudicated_at": "2026-08-22T10:24:00+08:00",
        "packet_hashes": {seat: packet_refs[seat]["sha256"] for seat in sorted(VALIDATOR.SEATS)},
        "memo_hashes": {seat: memo_refs[seat]["sha256"] for seat in sorted(VALIDATOR.SEATS)},
        "decisions": [
            {
                "assumption_id": assumption_id,
                "prior_base": 20.0,
                "prior_range": [10.0, 30.0],
                "final_base": 20.0,
                "final_range": [10.0, 30.0],
                "decision": "accept",
                "council_sources": sorted(VALIDATOR.SEATS),
                "evidence_ids": ["IR:earnings-release:2026Q2"],
                "reason": "All three lenses found no evidence-backed reason to change it.",
                "model_input_ids": [assumption_id],
            }
            for assumption_id in assumption_families.values()
        ],
        "final_model_spec_sha256": final_spec_ref["sha256"],
    }
    adjudication_path = support / "owner_adjudication.json"
    _write_json(adjudication_path, adjudication)
    freeze = {
        "schema_version": "owner-fv-freeze-v1",
        **identity,
        "frozen_at": "2026-08-22T10:26:00+08:00",
        "model_spec_sha256": final_spec_ref["sha256"],
        "model_output_sha256": "1" * 64,
        "independent_audit_sha256": "2" * 64,
    }
    freeze_path = support / "fv_freeze_receipt.json"
    _write_json(freeze_path, freeze)

    council = {
        "schema_version": 3,
        "council_runtime": "collaboration_available",
        "ticker": "EXAMPLE",
        "security_identity": {
            "symbol": "EXAMPLE",
            "issuer": "Example Corporation",
            "listing": "NASDAQ",
            "security_id": "SEC-CIK-0000001",
            "source_id": "IR:earnings-release:2026Q2",
        },
        "current_price": {
            "value": 100.0,
            "currency": "USD",
            "as_of": "2026-08-22T09:00:00+08:00",
            "source_id": "SA:market:2026-08-22",
        },
        "decision_horizon": "12 months",
        "evidence_cutoff": identity["evidence_cutoff"],
        "pei_input_receipt": _descriptor(pei_path, artifact_dir),
        "research_admission": "PASS",
        "artifact_bindings": {
            "authority_version": 2,
            "validator_sha256": _sha256(VALIDATOR_PATH),
            "preliminary_underwrite": _descriptor(underwrite_path, artifact_dir),
            "seat_packets": packet_refs,
            "sealed_memos": memo_refs,
            "owner_adjudication": _descriptor(adjudication_path, artifact_dir),
            "final_model_spec": final_spec_ref,
            "model_committed_at": "2026-08-22T10:25:00+08:00",
            "fv_freeze_receipt": _descriptor(freeze_path, artifact_dir),
        },
    }
    return plugin_root, artifact_dir, council


def _bind_v3_historical_correction(artifact_dir, council):
    correction_id = "SEC:EXAMPLE:2025-10-K:CONSOLIDATED-INCOME"
    facts = [
        {
            "period": period,
            "revenue": revenue,
            "operating_income": operating_income,
            "unit": "USD millions",
        }
        for period, revenue, operating_income in (
            ("FY2023A", 1000.0, 150.0),
            ("FY2024A", 1100.0, 176.0),
            ("FY2025A", 1200.0, 204.0),
        )
    ]
    corrections = artifact_dir / "support" / "corrections"
    observation_path = corrections / "primary-historical-observation.json"
    _write_json(
        observation_path,
        {
            "schema_version": "issuer-primary-visible-dom-observation-v1",
            "receipt_type": "issuer_primary_visible_dom_observation",
            "security_id": "SEC-CIK-0000001",
            "retrieval": {
                "surface": "codex_in_app_browser_visible_dom",
                "document_url": "https://www.sec.gov/Archives/example.htm",
                "form": "10-K",
                "filed_date": "2026-02-03",
                "underlying_document_predates_evidence_cutoff": True,
                "evidence_cutoff": council["evidence_cutoff"],
            },
            "observed_facts": facts,
        },
    )
    receipt_path = corrections / "primary-historical-acceptance-receipt.json"
    _write_json(
        receipt_path,
        {
            "schema_version": "scoped-primary-historical-acceptance-receipt-v1",
            "receipt_type": "scoped_primary_historical_acceptance",
            "security_id": "SEC-CIK-0000001",
            "observation": {
                "path": observation_path.name,
                "sha256": _sha256(observation_path),
            },
            "accepted_evidence_id": correction_id,
            "accepted_fields": facts,
            "scope_controls": {
                "evidence_cutoff_preserved": council["evidence_cutoff"],
                "reference_price_usd_preserved": council["current_price"]["value"],
                "new_provider_data_used": False,
                "seeking_alpha_refreshed": False,
                "new_consensus_or_price_data_used": False,
                "accepted_evidence_ids_changed_outside_scoped_primary_historical_receipt": False,
            },
            "validation_status": "PASS",
        },
    )
    set_path = artifact_dir / "support" / "correction_validation_set.json"
    _write_json(
        set_path,
        {
            "schema_version": "formal-correction-validation-set-v1",
            "receipt_type": "formal_correction_validation_set",
            "ticker": council["ticker"],
            "security_id": council["security_identity"]["security_id"],
            "evidence_cutoff": council["evidence_cutoff"],
            "reference_price_usd": council["current_price"]["value"],
            "validation_status": "PASS",
            "corrections": [
                {
                    "accepted_evidence_id": correction_id,
                    "allowed_use": "historical_field_correction_only",
                    "observation_timing": "post_cutoff_validation_only",
                    "acceptance_receipt": _descriptor(receipt_path, artifact_dir),
                    "accepted_fields": facts,
                }
            ],
        },
    )
    council["correction_validation_set"] = _descriptor(set_path, artifact_dir)

    bindings = council["artifact_bindings"]
    underwrite_path = artifact_dir / bindings["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    underwrite["candidate_assumptions"][0]["evidence_ids"].append(correction_id)
    _write_json(underwrite_path, underwrite)
    bindings["preliminary_underwrite"]["sha256"] = _sha256(underwrite_path)

    for seat in sorted(VALIDATOR.SEATS):
        packet_ref = bindings["seat_packets"][seat]
        packet_path = artifact_dir / packet_ref["path"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["candidate_assumptions"] = underwrite["candidate_assumptions"]
        packet["evidence_ids"].append(correction_id)
        _write_json(packet_path, packet)
        packet_ref["sha256"] = _sha256(packet_path)

        memo_ref = bindings["sealed_memos"][seat]
        memo_path = artifact_dir / memo_ref["path"]
        memo = json.loads(memo_path.read_text(encoding="utf-8"))
        memo["packet_sha256"] = packet_ref["sha256"]
        memo["challenges"][0]["evidence_ids"].append(correction_id)
        _write_json(memo_path, memo)
        memo_ref["sha256"] = _sha256(memo_path)

    adjudication_ref = bindings["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"] = {
        seat: bindings["seat_packets"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    adjudication["memo_hashes"] = {
        seat: bindings["sealed_memos"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    adjudication["decisions"][0]["evidence_ids"].append(correction_id)
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)
    return correction_id, observation_path


def test_agent_council_v3_accepts_minimal_complete_chain(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    assert _validate(council, plugin_root, artifact_dir) == []


def test_model_mapping_rejects_margin_to_tax_and_allows_shared_margin_path():
    spec = {'dependency_graph': {'leaves': {
        'input.base.margin.0': {'provenance_id': 'margin', 'value': 0.08},
        'input.base.margin.1': {'provenance_id': 'margin', 'value': 0.22},
        'input.base.tax_rate': {'provenance_id': 'tax', 'value': 0.22},
    }}}
    errors = []
    VALIDATOR._validate_model_mapping({}, 'product_mix_and_margins', {'model_input_ids': ['tax'], 'final_base': 0.22}, spec, 'decision', errors)
    assert any('Base product_mix_and_margins' in error for error in errors)
    for value in (0.08, 0.22):
        errors = []
        VALIDATOR._validate_model_mapping({}, 'product_mix_and_margins', {'model_input_ids': ['margin'], 'final_base': value}, spec, 'decision', errors)
        assert errors == []


def test_model_mapping_admits_base_reinvestment_path_fields_only():
    spec = {'dependency_graph': {'leaves': {
        'input.base.capex_percent_revenue.0': {'provenance_id': 'reinvestment', 'value': .30},
        'input.base.da_percent_revenue.0': {'provenance_id': 'reinvestment', 'value': .06},
        'input.base.nwc_percent.0': {'provenance_id': 'reinvestment', 'value': .35},
        'input.downside.capex_percent_revenue.0': {'provenance_id': 'downside_reinvestment', 'value': .45},
        'input.base.tax_rate': {'provenance_id': 'tax', 'value': .20},
    }}}
    errors = []
    VALIDATOR._validate_model_mapping(
        {}, 'reinvestment_and_fcff',
        {'model_input_ids': ['reinvestment'], 'final_base': .30}, spec, 'decision', errors,
    )
    assert errors == []

    for input_id in ('tax', 'downside_reinvestment'):
        errors = []
        VALIDATOR._validate_model_mapping(
            {}, 'reinvestment_and_fcff',
            {'model_input_ids': [input_id], 'final_base': .20}, spec, 'decision', errors,
        )
        assert any('Base reinvestment_and_fcff' in error for error in errors)


def test_insurer_model_mapping_requires_both_base_ratio_components_and_exact_sum():
    spec = {'formula_version': 'insurer-residual-income-v3', 'dependency_graph': {'leaves': {
        'input.base.loss_ratio': {'provenance_id': 'loss', 'value': .692},
        'input.base.expense_ratio': {'provenance_id': 'expense', 'value': .202},
        'input.insurer.book_growth': {'provenance_id': 'book_growth', 'value': .03},
        'input.base.terminal_roe': {'provenance_id': 'terminal_roe', 'value': .23},
    }}}
    valid = {'model_input_ids': ['loss', 'expense'], 'final_base': .894}
    errors = []
    VALIDATOR._validate_model_mapping({}, 'product_mix_and_margins', valid, spec, 'decision', errors)
    assert errors == []
    for decision in (
        {'model_input_ids': ['loss'], 'final_base': .894},
        {'model_input_ids': ['loss', 'expense'], 'final_base': .893},
        {'model_input_ids': ['book_growth'], 'final_base': .03},
    ):
        errors = []
        VALIDATOR._validate_model_mapping({}, 'product_mix_and_margins', decision, spec, 'decision', errors)
        assert any('Base product_mix_and_margins' in error or 'mapped Base margin' in error for error in errors)
    for family, input_id, value in (
        ('reinvestment_and_fcff', 'book_growth', .03),
        ('duration_fade_and_terminal', 'terminal_roe', .23),
    ):
        errors = []
        VALIDATOR._validate_model_mapping({}, family, {'model_input_ids': [input_id], 'final_base': value}, spec, 'decision', errors)
        assert errors == []


def _bind_v3_split_cutoff_wrapper(artifact_dir, council):
    owner_cutoff = council["evidence_cutoff"]
    final_cutoff = "2026-08-25T01:00:00+00:00"
    receipt_ref = council["pei_input_receipt"]
    receipt_path = artifact_dir / receipt_ref["path"]
    owner_receipt_path = artifact_dir / "support" / "pei_input_receipt.owner-model.json"
    owner_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _write_json(owner_receipt_path, owner_receipt)
    council.update(
        {
            "evidence_cutoff": final_cutoff,
            "owner_model_evidence_cutoff": owner_cutoff,
            "final_research_evidence_cutoff": final_cutoff,
            "owner_model_pei_input_receipt": _descriptor(
                owner_receipt_path, artifact_dir
            ),
        }
    )
    receipt = dict(owner_receipt)
    receipt["evidence_cutoff"] = final_cutoff
    _write_json(receipt_path, receipt)
    receipt_ref["sha256"] = _sha256(receipt_path)
    return final_cutoff


def test_agent_council_v3_accepts_split_wrapper_with_owner_model_artifacts(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    _bind_v3_split_cutoff_wrapper(artifact_dir, council)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_agent_council_v3_rejects_split_packet_at_publication_cutoff(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    final_cutoff = _bind_v3_split_cutoff_wrapper(artifact_dir, council)
    packet_ref = council["artifact_bindings"]["seat_packets"]["damodaran"]
    packet_path = artifact_dir / packet_ref["path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["evidence_cutoff"] = final_cutoff
    _write_json(packet_path, packet)
    packet_ref["sha256"] = _sha256(packet_path)

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("packet identity/schema must equal Council owner model" in error for error in errors)


def test_agent_council_v3_rejects_undispositioned_material_challenge_signal(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    underwrite_ref = council["artifact_bindings"]["preliminary_underwrite"]
    underwrite_path = artifact_dir / underwrite_ref["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    del underwrite["candidate_assumptions"][0]["challenge_signal_dispositions"][0][
        "disposition"
    ]
    _write_json(underwrite_path, underwrite)
    underwrite_ref["sha256"] = _sha256(underwrite_path)

    errors = _validate(council, plugin_root, artifact_dir)

    assert any(
        "challenge signal[0] is missing fields: disposition" in error
        for error in errors
    )


def test_agent_council_v3_rejects_ask_sa_supported_only_by_provider_synthesis(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    receipt_ref = council["pei_input_receipt"]
    receipt_path = artifact_dir / receipt_ref["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["evidence_registry"][1]["evidence_nature"] = "provider_synthesis"
    _write_json(receipt_path, receipt)
    receipt_ref["sha256"] = _sha256(receipt_path)

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("requires non-synthesis supporting evidence" in error for error in errors)


def _rebind_v3_packets_and_memos(artifact_dir, council):
    bindings = council["artifact_bindings"]
    underwrite_path = artifact_dir / bindings["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    for seat in sorted(VALIDATOR.SEATS):
        packet_ref = bindings["seat_packets"][seat]
        packet_path = artifact_dir / packet_ref["path"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["candidate_assumptions"] = underwrite["candidate_assumptions"]
        _write_json(packet_path, packet)
        packet_ref["sha256"] = _sha256(packet_path)

        memo_ref = bindings["sealed_memos"][seat]
        memo_path = artifact_dir / memo_ref["path"]
        memo = json.loads(memo_path.read_text(encoding="utf-8"))
        memo["packet_sha256"] = packet_ref["sha256"]
        _write_json(memo_path, memo)
        memo_ref["sha256"] = _sha256(memo_path)

    adjudication_ref = bindings["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"] = {
        seat: bindings["seat_packets"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    adjudication["memo_hashes"] = {
        seat: bindings["sealed_memos"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)


def test_agent_council_v3_accepts_signal_evidence_not_duplicated_on_parent(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    bindings = council["artifact_bindings"]
    underwrite_path = artifact_dir / bindings["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    signal = underwrite["candidate_assumptions"][0]["challenge_signal_dispositions"][0]
    signal["evidence_ids"].append("SA:market:2026-08-22")
    _write_json(underwrite_path, underwrite)
    bindings["preliminary_underwrite"]["sha256"] = _sha256(underwrite_path)

    for seat in sorted(VALIDATOR.SEATS):
        packet_path = artifact_dir / bindings["seat_packets"][seat]["path"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["evidence_ids"].append("SA:market:2026-08-22")
        _write_json(packet_path, packet)
    _rebind_v3_packets_and_memos(artifact_dir, council)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_agent_council_v3_rejects_unaccepted_signal_evidence(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    underwrite_ref = council["artifact_bindings"]["preliminary_underwrite"]
    underwrite_path = artifact_dir / underwrite_ref["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    underwrite["candidate_assumptions"][0]["challenge_signal_dispositions"][0][
        "evidence_ids"
    ] = ["UNACCEPTED"]
    _write_json(underwrite_path, underwrite)
    underwrite_ref["sha256"] = _sha256(underwrite_path)

    assert (
        "preliminary assumption[0] challenge signal[0].evidence_ids must be accepted PEI evidence"
        in _validate(council, plugin_root, artifact_dir)
    )


def test_agent_council_v3_rejects_packet_omitting_signal_evidence(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    bindings = council["artifact_bindings"]
    packet_ref = bindings["seat_packets"]["damodaran"]
    packet_path = artifact_dir / packet_ref["path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["evidence_ids"] = []
    _write_json(packet_path, packet)
    packet_ref["sha256"] = _sha256(packet_path)

    memo_ref = bindings["sealed_memos"]["damodaran"]
    memo_path = artifact_dir / memo_ref["path"]
    memo = json.loads(memo_path.read_text(encoding="utf-8"))
    memo["packet_sha256"] = packet_ref["sha256"]
    _write_json(memo_path, memo)
    memo_ref["sha256"] = _sha256(memo_path)

    adjudication_ref = bindings["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"]["damodaran"] = packet_ref["sha256"]
    adjudication["memo_hashes"]["damodaran"] = memo_ref["sha256"]
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)

    assert (
        "damodaran packet evidence_ids omit preliminary challenge-signal evidence"
        in _validate(council, plugin_root, artifact_dir)
    )


def test_agent_council_v3_admits_exact_historical_correction_chain(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    _bind_v3_historical_correction(artifact_dir, council)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_agent_council_v3_admits_annual_cash_flow_correction_fields(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    _bind_v3_historical_correction(artifact_dir, council)
    set_path = artifact_dir / council["correction_validation_set"]["path"]
    correction_set = json.loads(set_path.read_text(encoding="utf-8"))
    cash_flow_facts = [
        {
            "period": period,
            "cash_from_operations": cfo,
            "capital_expenditure": capex,
            "depreciation_and_amortization": depreciation,
            "unit": "USD millions",
        }
        for period, cfo, capex, depreciation in (
            ("FY2023A", 4843, 623, 1072),
            ("FY2024A", 7450, 683, 1032),
            ("FY2025A", 6416, 852, 963),
        )
    ]
    correction = correction_set["corrections"][0]
    receipt_path = artifact_dir / correction["acceptance_receipt"]["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    observation_path = receipt_path.parent / receipt["observation"]["path"]
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    observation["observed_facts"] = cash_flow_facts
    _write_json(observation_path, observation)
    cash_flow_id = "SEC:EXAMPLE:2025-10-K:CONSOLIDATED-CASH-FLOWS"
    receipt["observation"]["sha256"] = _sha256(observation_path)
    receipt["accepted_evidence_id"] = cash_flow_id
    receipt["accepted_fields"] = cash_flow_facts
    _write_json(receipt_path, receipt)
    correction["acceptance_receipt"]["sha256"] = _sha256(receipt_path)
    correction["accepted_evidence_id"] = cash_flow_id
    correction["accepted_fields"] = cash_flow_facts
    _write_json(set_path, correction_set)
    council["correction_validation_set"]["sha256"] = _sha256(set_path)

    underwrite_path = artifact_dir / council["artifact_bindings"]["preliminary_underwrite"]["path"]
    underwrite = json.loads(underwrite_path.read_text(encoding="utf-8"))
    underwrite["candidate_assumptions"][0]["evidence_ids"][-1] = cash_flow_id
    _write_json(underwrite_path, underwrite)
    council["artifact_bindings"]["preliminary_underwrite"]["sha256"] = _sha256(underwrite_path)
    for seat in sorted(VALIDATOR.SEATS):
        packet_path = artifact_dir / council["artifact_bindings"]["seat_packets"][seat]["path"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["candidate_assumptions"] = underwrite["candidate_assumptions"]
        packet["evidence_ids"][-1] = cash_flow_id
        _write_json(packet_path, packet)
        council["artifact_bindings"]["seat_packets"][seat]["sha256"] = _sha256(packet_path)

        memo_path = artifact_dir / council["artifact_bindings"]["sealed_memos"][seat]["path"]
        memo = json.loads(memo_path.read_text(encoding="utf-8"))
        memo["packet_sha256"] = _sha256(packet_path)
        memo["challenges"][0]["evidence_ids"][-1] = cash_flow_id
        _write_json(memo_path, memo)
        council["artifact_bindings"]["sealed_memos"][seat]["sha256"] = _sha256(memo_path)

    adjudication_path = artifact_dir / council["artifact_bindings"]["owner_adjudication"]["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"] = {
        seat: council["artifact_bindings"]["seat_packets"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    adjudication["memo_hashes"] = {
        seat: council["artifact_bindings"]["sealed_memos"][seat]["sha256"]
        for seat in sorted(VALIDATOR.SEATS)
    }
    adjudication["decisions"][0]["evidence_ids"][-1] = cash_flow_id
    _write_json(adjudication_path, adjudication)
    council["artifact_bindings"]["owner_adjudication"]["sha256"] = _sha256(adjudication_path)

    assert _validate(council, plugin_root, artifact_dir) == []


def test_agent_council_v3_rejects_correction_hash_drift_and_unbound_id(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    _, observation_path = _bind_v3_historical_correction(artifact_dir, council)
    observation_path.write_text(observation_path.read_text(encoding="utf-8") + " ")

    errors = _validate(council, plugin_root, artifact_dir)

    assert any("observation.sha256 does not match artifact" in error for error in errors)
    assert any("exceed accepted PEI evidence" in error for error in errors)


def test_agent_council_v3_rejects_unaccepted_preliminary_evidence(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    ref = council["artifact_bindings"]["preliminary_underwrite"]
    path = artifact_dir / ref["path"]
    underwrite = json.loads(path.read_text(encoding="utf-8"))
    underwrite["candidate_assumptions"][0]["evidence_ids"].append("UNACCEPTED")
    _write_json(path, underwrite)
    ref["sha256"] = _sha256(path)
    errors = _validate(council, plugin_root, artifact_dir)
    assert (
        "preliminary assumption[0].evidence_ids exceed accepted PEI evidence"
        in errors
    )


def test_agent_council_v3_requires_all_assumption_family_dispositions(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    ref = council["artifact_bindings"]["preliminary_underwrite"]
    path = artifact_dir / ref["path"]
    underwrite = json.loads(path.read_text(encoding="utf-8"))
    underwrite["assumption_family_dispositions"].pop()
    _write_json(path, underwrite)
    ref["sha256"] = _sha256(path)

    assert (
        "preliminary underwrite must disposition exactly all six assumption families"
        in _validate(council, plugin_root, artifact_dir)
    )


def test_agent_council_v3_rejects_one_sided_packet_instructions(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    bindings = council["artifact_bindings"]
    packet_ref = bindings["seat_packets"]["damodaran"]
    packet_path = artifact_dir / packet_ref["path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["instructions"] = "Test only whether assumptions are too conservative."
    _write_json(packet_path, packet)
    packet_ref["sha256"] = _sha256(packet_path)

    memo_ref = bindings["sealed_memos"]["damodaran"]
    memo_path = artifact_dir / memo_ref["path"]
    memo = json.loads(memo_path.read_text(encoding="utf-8"))
    memo["packet_sha256"] = packet_ref["sha256"]
    _write_json(memo_path, memo)
    memo_ref["sha256"] = _sha256(memo_path)

    adjudication_ref = bindings["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"]["damodaran"] = packet_ref["sha256"]
    adjudication["memo_hashes"]["damodaran"] = memo_ref["sha256"]
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)

    assert (
        "damodaran packet instructions must test conservative, aggressive, uncertain, and market-right cases"
        in _validate(council, plugin_root, artifact_dir)
    )


def test_agent_council_v3_rejects_inconsistent_owner_ranges(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    ref = council["artifact_bindings"]["owner_adjudication"]
    path = artifact_dir / ref["path"]
    adjudication = json.loads(path.read_text(encoding="utf-8"))
    decision = adjudication["decisions"][0]
    decision["prior_base"] = 19.0
    decision["prior_range"] = [9.0, 30.0]
    decision["final_base"] = 40.0
    _write_json(path, adjudication)
    ref["sha256"] = _sha256(path)
    errors = _validate(council, plugin_root, artifact_dir)

    assert "owner adjudication decisions[0].prior_base must equal the preliminary Base" in errors
    assert "owner adjudication decisions[0].prior_range must equal the preliminary range" in errors
    assert "owner adjudication decisions[0].final_base must fall within final_range" in errors


def test_agent_council_v3_blocks_without_collaboration(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    council["council_runtime"] = "unavailable"
    assert "current formal Council requires collaboration_available" in _validate(
        council, plugin_root, artifact_dir
    )


def test_agent_council_v3_rejects_final_action_leak_in_packet(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    ref = council["artifact_bindings"]["seat_packets"]["damodaran"]
    packet_path = artifact_dir / ref["path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["candidate_assumptions"][0]["action"] = "buy"
    _write_json(packet_path, packet)
    ref["sha256"] = _sha256(packet_path)
    memo_ref = council["artifact_bindings"]["sealed_memos"]["damodaran"]
    memo_path = artifact_dir / memo_ref["path"]
    memo = json.loads(memo_path.read_text(encoding="utf-8"))
    memo["packet_sha256"] = ref["sha256"]
    _write_json(memo_path, memo)
    memo_ref["sha256"] = _sha256(memo_path)
    adjudication_ref = council["artifact_bindings"]["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["packet_hashes"]["damodaran"] = ref["sha256"]
    adjudication["memo_hashes"]["damodaran"] = memo_ref["sha256"]
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)
    errors = _validate(council, plugin_root, artifact_dir)
    assert "damodaran packet leaks forbidden field action" in errors


def test_agent_council_v3_does_not_require_probabilities(tmp_path):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    serialized = json.dumps(council)
    assert "probability" not in serialized
    assert _validate(council, plugin_root, artifact_dir) == []


def test_agent_council_v3_rejects_final_model_assumption_without_owner_adjudication(
    tmp_path,
):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    bindings = council["artifact_bindings"]

    final_ref = bindings["final_model_spec"]
    final_path = artifact_dir / final_ref["path"]
    final_spec = json.loads(final_path.read_text(encoding="utf-8"))
    final_spec["assumption_ids"].append("customer_retention")
    _write_json(final_path, final_spec)
    final_ref["sha256"] = _sha256(final_path)

    adjudication_ref = bindings["owner_adjudication"]
    adjudication_path = artifact_dir / adjudication_ref["path"]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["final_model_spec_sha256"] = final_ref["sha256"]
    _write_json(adjudication_path, adjudication)
    adjudication_ref["sha256"] = _sha256(adjudication_path)

    freeze_ref = bindings["fv_freeze_receipt"]
    freeze_path = artifact_dir / freeze_ref["path"]
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze["model_spec_sha256"] = final_ref["sha256"]
    _write_json(freeze_path, freeze)
    freeze_ref["sha256"] = _sha256(freeze_path)

    assert (
        "owner adjudication model_input_ids do not cover final model assumption_ids: customer_retention"
        in _validate(council, plugin_root, artifact_dir)
    )


def test_agent_council_v3_rejects_preliminary_assumption_without_flip_condition(
    tmp_path,
):
    plugin_root, artifact_dir, council = _v3_fixture(tmp_path)
    ref = council["artifact_bindings"]["preliminary_underwrite"]
    path = artifact_dir / ref["path"]
    underwrite = json.loads(path.read_text(encoding="utf-8"))
    del underwrite["candidate_assumptions"][0]["flip_condition"]
    _write_json(path, underwrite)
    ref["sha256"] = _sha256(path)

    assert (
        "preliminary assumption[0].flip_condition must be non-empty"
        in _validate(council, plugin_root, artifact_dir)
    )


def _v4_fixture(tmp_path):
    plugin_root, root, council = _v3_fixture(tmp_path)
    council['schema_version'] = 4
    council['artifact_bindings']['authority_version'] = 3
    receipt_path = root / council['pei_input_receipt']['path']
    receipt = json.loads(receipt_path.read_text())
    initial = root / 'support/council-input-pei.json'
    _write_json(initial, receipt)
    council['council_input_pei_receipt'] = _descriptor(initial, root)
    receipt['evidence_registry'].append({
        'id': 'IR:new-product-guidance', 'requirement_class': 'primary',
        'source_kind': 'primary', 'evidence_nature': 'company_claim',
        'as_of': '2026-08-22T00:00:00+08:00',
        'primary_provenance': {'source_url': 'https://example.com/ir/product-guidance', 'source_locator': 'Product guidance, paragraph 2'},
    })
    _write_json(receipt_path, receipt)
    council['pei_input_receipt'] = _descriptor(receipt_path, root)
    bindings = council['artifact_bindings']
    for seat, ref in bindings['sealed_memos'].items():
        path = root / ref['path']
        memo = json.loads(path.read_text())
        memo['schema_version'] = 'council-sealed-memo-v3'
        memo['source_candidates'] = []
        for challenge in memo['challenges']:
            challenge['candidate_source_ids'] = []
        if seat == 'damodaran':
            memo['browsed'] = True
            memo['source_candidates'] = [{
                'candidate_id': 'damodaran:new-product',
                'url': 'https://example.com/ir/product-guidance',
                'source_locator': 'Product guidance, paragraph 2',
                'as_of': '2026-08-22', 'retrieved_at': '2026-08-22T10:19:00+08:00',
                'assumption_ids': ['revenue_growth'],
                'finding': 'The new product guidance changes the revenue bridge.',
                'evidence_nature': 'company_claim',
            }]
            memo['challenges'][0]['candidate_source_ids'] = ['damodaran:new-product']
        _write_json(path, memo)
        bindings['sealed_memos'][seat] = _descriptor(path, root)
    path = root / bindings['owner_adjudication']['path']
    adjudication = json.loads(path.read_text())
    adjudication['schema_version'] = 'pei-council-adjudication-v3'
    adjudication['memo_hashes'] = {seat: ref['sha256'] for seat, ref in bindings['sealed_memos'].items()}
    adjudication['source_dispositions'] = [{
        'candidate_id': 'damodaran:new-product', 'disposition': 'accepted',
        'evidence_ids': ['IR:new-product-guidance'],
        'reason': 'Data checked the original company document; PEI uses the guidance as a forecast, not an actual.',
    }]
    adjudication['decisions'][0]['evidence_ids'] = ['IR:new-product-guidance']
    _write_json(path, adjudication)
    bindings['owner_adjudication'] = _descriptor(path, root)
    return plugin_root, root, council


def test_v4_split_cutoff_checks_new_accepted_source_against_final_receipt(tmp_path):
    plugin, root, council = _v4_fixture(tmp_path)
    _bind_v3_split_cutoff_wrapper(root, council)
    owner_path = root / council['owner_model_pei_input_receipt']['path']
    initial_path = root / council['council_input_pei_receipt']['path']
    _write_json(owner_path, json.loads(initial_path.read_text(encoding='utf-8')))
    council['owner_model_pei_input_receipt'] = _descriptor(owner_path, root)

    assert VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root) == []
    final_path = root / council['pei_input_receipt']['path']
    final_receipt = json.loads(final_path.read_text(encoding='utf-8'))
    final_receipt['evidence_registry'][-1]['primary_provenance']['source_url'] = 'https://example.com/ir/unrelated-release'
    _write_json(final_path, final_receipt)
    council['pei_input_receipt'] = _descriptor(final_path, root)
    assert any('candidate source provenance' in error for error in VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root))


def _rebind_v4_memo(root, council, seat, mutate):
    bindings = council['artifact_bindings']
    path = root / bindings['sealed_memos'][seat]['path']
    memo = json.loads(path.read_text())
    mutate(memo)
    _write_json(path, memo)
    bindings['sealed_memos'][seat] = _descriptor(path, root)
    path = root / bindings['owner_adjudication']['path']
    adjudication = json.loads(path.read_text())
    adjudication['memo_hashes'][seat] = bindings['sealed_memos'][seat]['sha256']
    _write_json(path, adjudication)
    bindings['owner_adjudication'] = _descriptor(path, root)


def test_v4_discovery_admitted_by_data_reaches_owner_without_second_council(tmp_path):
    plugin, root, council = _v4_fixture(tmp_path)
    assert VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root) == []


@pytest.mark.parametrize('mutation, expected', [
    ('self_admission', 'exceed accepted PEI evidence'),
    ('cross_seat', 'only to this seat'),
    ('late_discovery', 'cannot follow its sealed memo'),
    ('hidden_browsing', 'truthful browsing'),
    ('unadmitted', 'accepted source requires evidence'),
    ('missing_disposition', 'disposition every discovered source'),
    ('unvalidated_receipt', 'pei_input_receipt'),
    ('future_input', 'input identity/cutoff'),
])
def test_v4_rejects_discovery_boundary_violations(tmp_path, mutation, expected):
    plugin, root, council = _v4_fixture(tmp_path)
    bindings = council['artifact_bindings']
    if mutation == 'self_admission':
        _rebind_v4_memo(root, council, 'damodaran', lambda m: m['challenges'][0].update(evidence_ids=['IR:new-product-guidance']))
    elif mutation == 'cross_seat':
        _rebind_v4_memo(root, council, 'soros', lambda m: m['challenges'][0].update(candidate_source_ids=['damodaran:new-product']))
    elif mutation == 'late_discovery':
        _rebind_v4_memo(root, council, 'damodaran', lambda m: m['source_candidates'][0].update(retrieved_at='2026-08-22T11:00:00+08:00'))
    elif mutation == 'hidden_browsing':
        _rebind_v4_memo(root, council, 'damodaran', lambda m: m.update(browsed=False))
    elif mutation in {'unadmitted', 'missing_disposition'}:
        path = root / bindings['owner_adjudication']['path']
        value = json.loads(path.read_text())
        if mutation == 'unadmitted':
            value['source_dispositions'][0]['evidence_ids'] = ['candidate-not-admitted']
        else:
            value['source_dispositions'] = []
        _write_json(path, value)
        bindings['owner_adjudication'] = _descriptor(path, root)
    elif mutation == 'unvalidated_receipt':
        council['pei_input_receipt']['sha256'] = '0' * 64
    else:
        path = root / council['council_input_pei_receipt']['path']
        value = json.loads(path.read_text())
        value['evidence_cutoff'] = '2026-08-23T10:00:00+08:00'
        _write_json(path, value)
        council['council_input_pei_receipt'] = _descriptor(path, root)
    assert any(expected in error for error in VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root))


@pytest.mark.parametrize("mismatch", ["url", "nature", "date", "invalid_date", "locator"])
def test_v4_rejects_candidate_laundered_through_unrelated_admitted_source(tmp_path, mismatch):
    plugin, root, council = _v4_fixture(tmp_path)
    path = root / council["pei_input_receipt"]["path"]
    receipt = json.loads(path.read_text())
    row = receipt["evidence_registry"][-1]
    if mismatch == "url":
        row["primary_provenance"]["source_url"] = "https://example.com/ir/unrelated-release"
    elif mismatch == "nature":
        row["evidence_nature"] = "historical_fact"
    elif mismatch == "date":
        row["as_of"] = "2026-08-21T00:00:00+08:00"
    elif mismatch == "invalid_date":
        row["as_of"] = "2026-08-22junk"
    else:
        row["primary_provenance"]["source_locator"] = "Different document, paragraph 2"
    _write_json(path, receipt)
    council["pei_input_receipt"] = _descriptor(path, root)
    errors = VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root)
    assert any("candidate source provenance" in error for error in errors)


def test_v4_public_analyst_inference_can_reach_owner_as_context(tmp_path):
    plugin, root, council = _v4_fixture(tmp_path)
    path = root / council["pei_input_receipt"]["path"]
    receipt = json.loads(path.read_text())
    row = receipt["evidence_registry"][-1]
    row.update(requirement_class="public", source_kind="public_web", evidence_nature="corroborating_context")
    row["public_provenance"] = row.pop("primary_provenance")
    _write_json(path, receipt)
    council["pei_input_receipt"] = _descriptor(path, root)
    def analyst(memo):
        memo["source_candidates"][0].update(as_of="2026-08-21T16:00:00Z", evidence_nature="corroborating_context", finding="Analyst estimate: product adoption may lift revenue; this is an inference, not company guidance.")
    _rebind_v4_memo(root, council, "damodaran", analyst)
    assert VALIDATOR.validate(council, plugin_root=plugin, artifact_dir=root) == []
