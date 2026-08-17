"""Consolidated validation checks for notebooks and reusable helpers."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from .schemas import VALIDATION_CHECK_COLUMNS, VALIDATION_CHECKS_SCHEMA, validate_dataframe


VALIDATION_MODULE_VERSION = "1.0.0"
VALIDATION_SCHEMA_VERSION = VALIDATION_CHECKS_SCHEMA.version
ALLOWED_SEVERITIES = frozenset({"info", "warning", "error", "blocking"})
FAILING_SEVERITIES = frozenset({"error", "blocking"})


class ValidationFailure(RuntimeError):
    """Raised when one or more blocking validation checks fail."""


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (Mapping, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


@dataclass(frozen=True)
class ValidationCheck:
    validation_stage: str
    check_id: str
    check_description: str
    severity: str
    expected: str
    observed: str
    passed: bool
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValidationCollector:
    """Collect unique checks and persist one compact validation table."""

    def __init__(self) -> None:
        self._checks: list[ValidationCheck] = []
        self._keys: set[tuple[str, str]] = set()

    def add(
        self,
        *,
        validation_stage: str,
        check_id: str,
        check_description: str,
        severity: str,
        expected: Any,
        observed: Any,
        passed: bool,
        details: Any = "",
    ) -> ValidationCheck:
        stage = str(validation_stage).strip()
        identifier = str(check_id).strip()
        normalized_severity = str(severity).strip().lower()
        if not stage or not identifier or not str(check_description).strip():
            raise ValueError("Validation stage, ID, and description must be non-empty")
        if normalized_severity not in ALLOWED_SEVERITIES:
            raise ValueError(f"Unsupported validation severity: {severity!r}")
        key = (stage, identifier)
        if key in self._keys:
            raise ValueError(f"Duplicate validation check key: {key}")

        check = ValidationCheck(
            validation_stage=stage,
            check_id=identifier,
            check_description=str(check_description).strip(),
            severity=normalized_severity,
            expected=_serialize(expected),
            observed=_serialize(observed),
            passed=bool(passed),
            details=_serialize(details),
        )
        self._checks.append(check)
        self._keys.add(key)
        return check

    def extend(self, checks: Iterable[ValidationCheck]) -> None:
        for check in checks:
            self.add(**check.to_dict())

    @property
    def checks(self) -> tuple[ValidationCheck, ...]:
        return tuple(self._checks)

    @property
    def overall_passed(self) -> bool:
        return all(
            check.passed or check.severity not in FAILING_SEVERITIES
            for check in self._checks
        )

    @property
    def blocking_failures(self) -> tuple[ValidationCheck, ...]:
        return tuple(
            check
            for check in self._checks
            if not check.passed and check.severity == "blocking"
        )

    def summary(self) -> dict[str, Any]:
        failed = [check for check in self._checks if not check.passed]
        return {
            "check_count": len(self._checks),
            "passed_count": sum(check.passed for check in self._checks),
            "failed_count": len(failed),
            "blocking_failure_count": len(self.blocking_failures),
            "overall_passed": self.overall_passed,
            "failed_check_ids": [
                f"{check.validation_stage}:{check.check_id}" for check in failed
            ],
        }

    def to_dataframe(self) -> pd.DataFrame:
        frame = pd.DataFrame(
            [check.to_dict() for check in self._checks],
            columns=VALIDATION_CHECK_COLUMNS,
        )
        result = validate_dataframe(frame, VALIDATION_CHECKS_SCHEMA)
        if not result.passed:
            raise ValueError(f"Internal validation table violates schema: {result.to_dict()}")
        return frame

    def raise_for_blocking(self) -> None:
        if self.blocking_failures:
            identifiers = [
                f"{check.validation_stage}:{check.check_id}"
                for check in self.blocking_failures
            ]
            raise ValidationFailure(
                f"Blocking validation checks failed: {identifiers}"
            )

    def write_csv(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            self.to_dataframe().to_csv(temporary, index=False)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path
