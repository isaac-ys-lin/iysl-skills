import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = SKILL_DIR / "scripts" / "validate_sa_coverage.py"

SPEC = importlib.util.spec_from_file_location("validate_sa_coverage", VALIDATOR_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


def valid_payload():
    groups = {}
    for name in VALIDATOR.GROUPS:
        groups[name] = {
            "status": "retrieved",
            "attempted": True,
            "source_ids": [f"SA:{name}"],
            "fields_retrieved": ["sample field"],
            "gap_reason": None,
        }
    return {
        "schema_version": 1,
        "ticker": "EXAMPLE",
        "retrieved_at": "2026-08-20T12:00:00+08:00",
        "timezone": "Asia/Taipei",
        "workflow_class": "formal_initial_coverage",
        "owning_workflow": "initiating-coverage",
        "collection_mode": "completeness_first",
        "fair_value_freeze": {
            "status": "post_freeze",
            "frozen_at": "2026-08-20T11:00:00+08:00",
        },
        "ask_sa": {
            "status": "retrieved",
            "artifact": "project/ask_sa_raw.md",
            "gap_reason": None,
        },
        "groups": groups,
    }


def test_complete_artifact_passes():
    assert VALIDATOR.validate(valid_payload()) == []


def test_missing_group_fails():
    payload = valid_payload()
    del payload["groups"]["valuation"]
    assert any("missing groups: valuation" in error for error in VALIDATOR.validate(payload))


def test_core_group_cannot_be_not_material():
    payload = valid_payload()
    payload["groups"]["quant"] = {
        "status": "not_material",
        "attempted": False,
        "source_ids": [],
        "fields_retrieved": [],
        "gap_reason": "owner did not use factor grades",
    }
    assert any("quant is core" in error for error in VALIDATOR.validate(payload))


def test_gap_requires_reason_and_attempt():
    payload = valid_payload()
    payload["groups"]["earnings_surprises"] = {
        "status": "not_covered",
        "attempted": False,
        "source_ids": [],
        "fields_retrieved": [],
        "gap_reason": None,
    }
    errors = VALIDATOR.validate(payload)
    assert any("attempted must be true" in error for error in errors)
    assert any("gap_reason is required" in error for error in errors)


def test_pre_freeze_wall_street_defer_passes():
    payload = valid_payload()
    payload["fair_value_freeze"] = {"status": "pre_freeze", "frozen_at": None}
    payload["groups"]["wall_street"] = {
        "status": "deferred_until_owner_fv_freeze",
        "attempted": False,
        "source_ids": [],
        "fields_retrieved": [],
        "gap_reason": "independent fair value is not frozen",
    }
    assert VALIDATOR.validate(payload) == []


def test_post_freeze_wall_street_cannot_remain_deferred():
    payload = valid_payload()
    payload["groups"]["wall_street"] = {
        "status": "deferred_until_owner_fv_freeze",
        "attempted": False,
        "source_ids": [],
        "fields_retrieved": [],
        "gap_reason": "independent fair value is not frozen",
    }
    assert any("cannot remain deferred" in error for error in VALIDATOR.validate(payload))


def test_cli_returns_nonzero_for_invalid_artifact(tmp_path):
    payload = copy.deepcopy(valid_payload())
    payload["groups"]["analyst_views"]["source_ids"] = []
    artifact = tmp_path / "coverage.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), str(artifact)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "analyst_views.source_ids" in completed.stderr
