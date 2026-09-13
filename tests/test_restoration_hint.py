from pathlib import Path

import pandas as pd
import pytest

from restoration_eval.restoration_hint import (
    CONFIG_SCHEMA_VERSION,
    MODEL_ID,
    configuration_fingerprint,
    load_hint_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "experiments" / "hint.yaml"


def test_hint_config_loads_with_exact_production_contract() -> None:
    config = load_hint_config(CONFIG)
    assert config["config_schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["model"]["model_id"] == MODEL_ID
    assert config["dataset"]["dataset_scope"] == "controlled_300"
    assert config["expected"]["eligible_case_count"] == 2620
    assert config["expected"]["zero_control_case_count"] == 300
    assert sum(config["expected"]["eligible_case_count_by_experiment"].values()) == 2620


def test_hint_contract_preserves_d01_native_adapter() -> None:
    config = load_hint_config(CONFIG)
    assert config["model"]["inference_width"] == 768
    assert config["model"]["inference_height"] == 768
    assert config["model"]["adapter_policy"] == "native_768_validated_by_d01.v1"
    assert config["external_asset"]["repository_revision"] == (
        "15e867d8c8689b9d5050383fc3884537ae876145"
    )


def test_hint_execution_is_resumable_and_progress_bounded() -> None:
    execution = load_hint_config(CONFIG)["execution"]
    assert execution["resume_enabled"] is True
    assert execution["retry_failed_attempts"] is False
    assert execution["progress_interval_cases"] <= 10
    assert execution["checkpoint_interval_cases"] <= 10
    assert execution["progress_poll_seconds"] <= 1.0
    assert execution["full_run_budget_seconds"] == 28800


def test_configuration_fingerprint_is_stable() -> None:
    config = load_hint_config(CONFIG)
    assert configuration_fingerprint(config) == configuration_fingerprint(config)
    changed = dict(config)
    changed["config_version"] = "different"
    assert configuration_fingerprint(config) != configuration_fingerprint(changed)


def test_hint_config_rejects_wrong_eligible_count(tmp_path: Path) -> None:
    yaml = pytest.importorskip("yaml")
    config = load_hint_config(CONFIG)
    config["expected"]["eligible_case_count"] = 1
    path = tmp_path / "hint.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="2,620"):
        load_hint_config(path)
