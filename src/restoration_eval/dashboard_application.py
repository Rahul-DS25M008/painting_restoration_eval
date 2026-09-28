"""Controlled-300 dashboard runtime and trust-boundary helpers.

The public application consumes the compact, immutable package produced by
Notebook 34. This module deliberately has no Streamlit dependency and never
performs a network request. It validates the package trust root, loads only
bootstrap material eagerly, and exposes explicit lazy loaders for one room,
one painting, or the report catalogue.

Scientific producers remain authoritative. The helpers only select and
present registered evidence; they do not run models, calculate metrics, fit
thresholds, or substitute a neighbouring identity when evidence is absent.
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml

from .dashboard_assets import (
    ASSET_LOCATOR_COLUMNS,
    ASSET_LOCATOR_SCHEMA,
    DASHBOARD_ASSET_COLUMNS,
    DASHBOARD_ASSET_SCHEMA,
    DASHBOARD_PACKAGE_SCHEMA,
    DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
    DISPLAY_BINDING_SCHEMA,
    DISPLAY_COMPONENT_COLUMNS,
    PAINTING_LOOKUP_COLUMNS,
    PRINCIPAL_ROOM_IDS,
    RENDITION_COLUMNS,
    RENDITION_SCHEMA,
    ROOM_PARTITION_COLUMNS,
    ROOM_PARTITION_SCHEMA,
)
from .manifests import sha256_file
from .paths import find_project_root, resolve_repo_path


DASHBOARD_APPLICATION_VERSION = "2.0.0"
DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION = "dashboard_validation_config.v2"
DASHBOARD_PACKAGE_SCHEMA_VERSION = DASHBOARD_PACKAGE_SCHEMA
DASHBOARD_RUNTIME_MANIFEST_SCHEMA_VERSION = DASHBOARD_RUNTIME_MANIFEST_SCHEMA

DEFAULT_PACKAGE_RELATIVE = Path("outputs/34_final_streamlit_dashboard_assets")
RUNTIME_MANIFEST_RELATIVE = "manifests/dashboard_runtime_manifest.json"

BOOTSTRAP_PATHS = {
    "bootstrap": "data/bootstrap/bootstrap.json",
    "room_catalogue": "data/bootstrap/room_catalogue.json",
    "glossary": "data/bootstrap/glossary.json",
    "filter_options": "data/bootstrap/filter_options.json",
    "painting_lookup": "data/bootstrap/painting_lookup.parquet",
}
MANIFEST_PATHS = {
    "display_components": "manifests/display_components.csv",
    "dashboard_assets": "manifests/dashboard_assets.parquet",
    "asset_locators": "manifests/asset_locators.parquet",
    "renditions": "manifests/renditions.csv",
    "room_partitions": "manifests/room_partitions.csv",
}
FINAL_RECORD_PATHS = {
    "artifacts": "manifests/artifacts.csv",
    "run_manifest": "manifests/run_manifest.json",
    "upstream_checks": "validation/checks.csv",
}

CHILD_ROOM_ID = "focused_portrait_review"
ALL_ROOM_IDS = (*PRINCIPAL_ROOM_IDS, CHILD_ROOM_ID)
SELECTION_FIELDS = (
    "room_id",
    "painting_id",
    "case_id",
    "candidate_id",
    "model_id",
    "seed",
    "prompt_variant_id",
    "metric_name",
    "region_id",
    "evidence_layer",
    "return_room",
    "annotation_id",
    "hand_control_id",
    "review_unit_id",
    "blind_review_code",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PAINTING_ID_RE = re.compile(r"^p(?:00[1-9]|0[1-9][0-9]|[12][0-9]{2}|300)$")
_NULL_STRINGS = {"", "nan", "none", "null", "<na>"}


class DashboardContractError(RuntimeError):
    """Raised when immutable dashboard evidence violates its contract."""


class DashboardSelectionError(DashboardContractError):
    """Raised when a requested identity is unavailable or internally mixed."""


def _blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().casefold() in _NULL_STRINGS


def _text_or_none(value: Any) -> str | None:
    return None if _blank(value) else str(value).strip()


def _json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DashboardContractError(f"Could not read JSON contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DashboardContractError(f"Expected a JSON object: {path}")
    return payload


def _frame(path: Path) -> pd.DataFrame:
    try:
        if path.suffix.casefold() == ".parquet":
            return pd.read_parquet(path)
        if path.suffix.casefold() == ".csv":
            return pd.read_csv(path, low_memory=False)
    except Exception as exc:
        raise DashboardContractError(f"Could not read dashboard table {path}: {exc}") from exc
    raise DashboardContractError(f"Unsupported dashboard table format: {path}")


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise DashboardContractError(f"{label} is missing required columns: {missing}")


def _require_unique(frame: pd.DataFrame, column: str, label: str) -> None:
    if frame[column].isna().any() or frame[column].astype(str).str.strip().eq("").any():
        raise DashboardContractError(f"{label}.{column} contains a blank identity")
    duplicates = frame.loc[frame[column].duplicated(keep=False), column].astype(str).tolist()
    if duplicates:
        raise DashboardContractError(
            f"{label}.{column} must be unique; duplicate examples: {duplicates[:5]}"
        )


def _require_ok(frame: pd.DataFrame, label: str) -> None:
    if "status" not in frame.columns:
        return
    failed = frame.loc[~frame["status"].fillna("").astype(str).str.casefold().eq("ok")]
    if not failed.empty:
        raise DashboardContractError(f"{label} contains {len(failed)} non-ok rows")


def _within(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    allowed = parent.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise DashboardContractError(
            f"Dashboard path escapes its package root: {resolved}"
        ) from exc
    return resolved


def _package_path(package_root: Path, relative_path: Any) -> Path:
    text = _text_or_none(relative_path)
    if text is None or "\\" in text:
        raise DashboardContractError(f"Invalid package-relative path: {relative_path!r}")
    candidate = Path(text)
    if candidate.is_absolute() or text.startswith("../") or "/../" in text:
        raise DashboardContractError(f"Invalid package-relative path: {relative_path!r}")
    return _within(package_root / candidate, package_root)


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DashboardSelection:
    """Canonical, identifier-only cross-room selection state."""

    room_id: str = "exhibition_foyer"
    painting_id: str | None = None
    case_id: str | None = None
    candidate_id: str | None = None
    model_id: str | None = None
    seed: str | int | None = None
    prompt_variant_id: str | None = None
    metric_name: str | None = None
    region_id: str | None = None
    evidence_layer: str | None = None
    return_room: str | None = None
    annotation_id: str | None = None
    hand_control_id: str | None = None
    review_unit_id: str | None = None
    blind_review_code: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "DashboardSelection":
        source = dict(value or {})
        return cls(**{field: source.get(field) for field in SELECTION_FIELDS if field in source})

    def as_identifiers(self) -> dict[str, Any]:
        """Return a JSON-safe state mapping without dataframes or binary data."""

        result: dict[str, Any] = {}
        for key, value in asdict(self).items():
            if not _blank(value):
                result[key] = int(value) if key == "seed" and str(value).isdigit() else value
        return result


@dataclass(frozen=True)
class DashboardPackage:
    """Verified, bootstrap-ready view of one Notebook 34 v2 release."""

    project_root: Path
    package_root: Path
    runtime_manifest: Mapping[str, Any]
    artifact_index: Mapping[str, Mapping[str, Any]]
    bootstrap: Mapping[str, Any]
    room_catalogue: Mapping[str, Any]
    glossary: Mapping[str, Any]
    filter_options: Mapping[str, Any]
    painting_lookup: pd.DataFrame
    display_components: pd.DataFrame
    dashboard_assets: pd.DataFrame
    asset_locators: pd.DataFrame
    renditions: pd.DataFrame
    room_partitions: pd.DataFrame
    upstream_checks: pd.DataFrame
    artifacts: pd.DataFrame
    run_manifest: Mapping[str, Any]

    @property
    def release_id(self) -> str:
        return str(self.runtime_manifest["release_id"])

    @property
    def population(self) -> Mapping[str, Any]:
        return self.runtime_manifest["population"]

    @property
    def principal_room_ids(self) -> tuple[str, ...]:
        return tuple(self.runtime_manifest["principal_room_ids"])

    @property
    def summary(self) -> Mapping[str, Any]:
        return self.bootstrap

    @property
    def filters(self) -> Mapping[str, Any]:
        return self.filter_options

    @property
    def upstream_manifest(self) -> Mapping[str, Any]:
        return self.runtime_manifest

    def package_path(self, relative_path: Any) -> Path:
        return _package_path(self.package_root, relative_path)

    def verify_relative_file(self, relative_path: str, *, checksum: bool = True) -> Path:
        """Verify one runtime-manifest file and return its local path."""

        record = self.artifact_index.get(str(relative_path))
        if record is None:
            raise DashboardContractError(
                f"File is not declared by the runtime manifest: {relative_path}"
            )
        path = self.package_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Declared dashboard file is missing: {relative_path}")
        expected_size = int(record.get("size_bytes", -1))
        if path.stat().st_size != expected_size:
            raise DashboardContractError(
                f"Size mismatch for {relative_path}: expected {expected_size}, "
                f"observed {path.stat().st_size}"
            )
        expected_sha = str(record.get("sha256", "")).casefold()
        if not _SHA256_RE.fullmatch(expected_sha):
            raise DashboardContractError(f"Invalid manifest SHA-256 for {relative_path}")
        if checksum:
            observed_sha = sha256_file(path)
            if observed_sha != expected_sha:
                raise DashboardContractError(
                    f"SHA-256 mismatch for {relative_path}: expected {expected_sha}, "
                    f"observed {observed_sha}"
                )
        return path

    def _load_compressed_json(self, relative_path: str) -> dict[str, Any]:
        path = self.verify_relative_file(relative_path)
        record = self.artifact_index[relative_path]
        compressed = path.read_bytes()
        metadata = record.get("compressed_payload")
        if not isinstance(metadata, Mapping):
            raise DashboardContractError(
                f"Compressed-payload metadata is missing for {relative_path}"
            )
        try:
            decoded = gzip.decompress(compressed)
        except (OSError, EOFError) as exc:
            raise DashboardContractError(f"Invalid gzip payload: {relative_path}") from exc
        expected_size = int(metadata.get("decoded_size_bytes", -1))
        expected_sha = str(metadata.get("decoded_sha256", "")).casefold()
        if len(decoded) != expected_size or _hash_bytes(decoded) != expected_sha:
            raise DashboardContractError(
                f"Decoded payload does not match the runtime manifest: {relative_path}"
            )
        try:
            payload = json.loads(decoded.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise DashboardContractError(f"Invalid decoded JSON: {relative_path}") from exc
        if not isinstance(payload, dict):
            raise DashboardContractError(f"Expected decoded JSON object: {relative_path}")
        return payload

    def load_room(self, room_id: str) -> pd.DataFrame:
        """Load and verify exactly one active room partition."""

        normalized = str(room_id).strip()
        if normalized not in ALL_ROOM_IDS:
            raise DashboardSelectionError(f"Unknown dashboard room: {room_id!r}")
        matches = self.room_partitions.loc[
            self.room_partitions["room_id"].astype(str).eq(normalized)
        ]
        if len(matches) != 1:
            raise DashboardContractError(
                f"Room partition index must contain one row for {normalized}; found {len(matches)}"
            )
        record = matches.iloc[0]
        relative_path = str(record["relative_path"])
        path = self.verify_relative_file(relative_path)
        if path.stat().st_size != int(record["size_bytes"]):
            raise DashboardContractError(f"Room partition size drift: {normalized}")
        if sha256_file(path) != str(record["sha256"]):
            raise DashboardContractError(f"Room partition checksum drift: {normalized}")
        frame = _frame(path)
        if len(frame) != int(record["row_count"]):
            raise DashboardContractError(f"Room partition row-count drift: {normalized}")
        if "room_id" not in frame or set(frame["room_id"].astype(str)) != {normalized}:
            raise DashboardContractError(f"Room partition identity drift: {normalized}")
        if "schema_version" not in frame or set(frame["schema_version"].astype(str)) != {
            ROOM_PARTITION_SCHEMA
        }:
            raise DashboardContractError(f"Room partition schema drift: {normalized}")
        _require_ok(frame, f"room[{normalized}]")
        expected_display_ids = set(json_list(record["display_ids_json"]))
        observed_display_ids = set(frame["display_id"].astype(str))
        if observed_display_ids != expected_display_ids:
            raise DashboardContractError(f"Room display-ID closure failed: {normalized}")
        return frame.copy()

    def load_painting(self, painting_id: str) -> dict[str, Any]:
        """Load one verified painting shard; never substitute another painting."""

        normalized = str(painting_id).strip()
        if not _PAINTING_ID_RE.fullmatch(normalized):
            raise DashboardSelectionError(f"Invalid painting ID: {painting_id!r}")
        matches = self.painting_lookup.loc[
            self.painting_lookup["painting_id"].astype(str).eq(normalized)
        ]
        if len(matches) != 1:
            raise DashboardSelectionError(
                f"Painting is not indexed in this release: {normalized}"
            )
        relative_path = str(matches.iloc[0]["painting_partition_path"])
        payload = self._load_compressed_json(relative_path)
        if payload.get("schema_version") != "dashboard_painting_partition.v1":
            raise DashboardContractError(f"Painting partition schema drift: {normalized}")
        if payload.get("release_id") != self.release_id:
            raise DashboardContractError(f"Painting partition release drift: {normalized}")
        if payload.get("painting_id") != normalized:
            raise DashboardContractError(f"Painting partition identity drift: {normalized}")
        if str(payload.get("status", "")).casefold() != "ok":
            raise DashboardContractError(f"Painting partition is not approved: {normalized}")
        return payload

    def load_reports(self) -> dict[str, Any]:
        """Load the compact verified report catalogue, not report bytes."""

        payload = self._load_compressed_json("data/reports/index.json.gz")
        if payload.get("schema_version") != "dashboard_report_index.v2":
            raise DashboardContractError("Report-index schema drift")
        if payload.get("release_id") != self.release_id:
            raise DashboardContractError("Report-index release drift")
        reports = payload.get("reports")
        if not isinstance(reports, list) or int(payload.get("report_count", -1)) != len(reports):
            raise DashboardContractError("Report-index count drift")
        if any(str(row.get("status", "")).casefold() != "ok" for row in reports):
            raise DashboardContractError("Report index contains a non-ok record")
        return payload

    def bindings_for(
        self,
        display_id: str | None = None,
        *,
        room_id: str | None = None,
        selection: DashboardSelection | Mapping[str, Any] | None = None,
    ) -> pd.DataFrame:
        """Return registered display bindings compatible with an identity state."""

        frame = self.display_components
        if display_id is not None:
            frame = frame.loc[frame["display_id"].astype(str).eq(str(display_id))]
        if room_id is not None:
            frame = frame.loc[frame["room_id"].astype(str).eq(str(room_id))]
        state = (
            selection
            if isinstance(selection, DashboardSelection)
            else DashboardSelection.from_mapping(selection)
        ) if selection is not None else None
        if state is not None:
            identities = state.as_identifiers()
            for field in SELECTION_FIELDS:
                if field not in frame.columns or field not in identities:
                    continue
                wanted = str(identities[field])
                values = frame[field]
                generic = values.map(_blank)
                frame = frame.loc[generic | values.astype(str).eq(wanted)]
        sort_columns = [column for column in ("display_order", "slot_id", "binding_id") if column in frame]
        return frame.sort_values(sort_columns, kind="stable").copy() if sort_columns else frame.copy()

    def asset_record(self, asset_id: str) -> pd.Series:
        matches = self.dashboard_assets.loc[
            self.dashboard_assets["asset_id"].astype(str).eq(str(asset_id))
        ]
        if len(matches) != 1:
            raise DashboardSelectionError(
                f"Dashboard asset is not registered exactly once: {asset_id!r}"
            )
        return matches.iloc[0].copy()

    def locator_candidates(self, asset_id: str) -> pd.DataFrame:
        """Return immutable routes only; this method never fetches them."""

        self.asset_record(asset_id)
        frame = self.asset_locators.loc[
            self.asset_locators["asset_id"].astype(str).eq(str(asset_id))
        ].copy()
        transport_order = {
            "local_package": 0,
            "github_git_blob": 1,
            "github_lfs_media": 2,
            "huggingface_object": 3,
            "huggingface_direct": 3,
            "huggingface_bundle_member": 4,
        }
        frame["_transport_order"] = frame["transport"].map(transport_order).fillna(99)
        return frame.sort_values(["_transport_order", "locator_id"], kind="stable").drop(
            columns=["_transport_order"]
        )

    def local_rendition(
        self,
        asset_id: str,
        profiles: Sequence[str] = ("standard", "diagnostic_preview", "thumb"),
        *,
        verify: bool = True,
    ) -> Path | None:
        """Resolve a registered local rendition, or return None without fallback."""

        self.asset_record(asset_id)
        candidates = self.renditions.loc[
            self.renditions["asset_id"].astype(str).eq(str(asset_id))
        ].copy()
        if candidates.empty:
            return None
        order = {str(profile): index for index, profile in enumerate(profiles)}
        candidates["_profile_order"] = candidates["profile"].map(order).fillna(len(order) + 1)
        candidates = candidates.sort_values(["_profile_order", "rendition_id"], kind="stable")
        for _, record in candidates.iterrows():
            if str(record["profile"]) not in order:
                continue
            relative_path = str(record["relative_path"])
            path = self.verify_relative_file(relative_path, checksum=verify)
            if path.stat().st_size != int(record["size_bytes"]):
                raise DashboardContractError(f"Rendition size drift: {record['rendition_id']}")
            if verify and sha256_file(path) != str(record["sha256"]):
                raise DashboardContractError(
                    f"Rendition checksum drift: {record['rendition_id']}"
                )
            return path
        return None

    def report_record(self, report_id: str) -> Mapping[str, Any]:
        reports = self.load_reports()["reports"]
        matches = [row for row in reports if str(row.get("report_id")) == str(report_id)]
        if len(matches) != 1:
            raise DashboardSelectionError(
                f"Report is not registered exactly once: {report_id!r}"
            )
        return dict(matches[0])

    def local_report_bytes(self, report_id: str) -> tuple[bytes, str] | None:
        """Read one explicitly selected local report and verify its producer hash."""

        record = self.report_record(report_id)
        path = safe_project_path(
            record.get("report_path"),
            self.project_root,
            allowed_suffixes={".html", ".md", ".pdf", ".csv", ".json"},
        )
        if path is None:
            return None
        payload = path.read_bytes()
        expected_sha = str(record.get("report_sha256", "")).casefold()
        if not _SHA256_RE.fullmatch(expected_sha) or _hash_bytes(payload) != expected_sha:
            raise DashboardContractError(f"Local report checksum mismatch: {report_id}")
        return payload, path.name

    def validate_selection(
        self,
        selection: DashboardSelection | Mapping[str, Any],
    ) -> DashboardSelection:
        return validate_selection(self, selection)


DashboardBundle = DashboardPackage


def _build_artifact_index(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    artifacts = manifest.get("local_artifacts")
    if not isinstance(artifacts, list):
        raise DashboardContractError("Runtime manifest local_artifacts must be a list")
    index: dict[str, Mapping[str, Any]] = {}
    for position, record in enumerate(artifacts):
        if not isinstance(record, Mapping):
            raise DashboardContractError(f"local_artifacts[{position}] is not an object")
        relative = _text_or_none(record.get("relative_path"))
        if relative is None or relative in index:
            raise DashboardContractError(f"Invalid or duplicate local artifact path: {relative!r}")
        if "\\" in relative or Path(relative).is_absolute() or relative.startswith("../"):
            raise DashboardContractError(f"Unsafe local artifact path: {relative}")
        if int(record.get("size_bytes", -1)) < 0:
            raise DashboardContractError(f"Invalid local artifact size: {relative}")
        if not _SHA256_RE.fullmatch(str(record.get("sha256", "")).casefold()):
            raise DashboardContractError(f"Invalid local artifact checksum: {relative}")
        index[relative] = dict(record)
    return index


def _validate_runtime_manifest(manifest: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
        "package_schema_version": DASHBOARD_PACKAGE_SCHEMA,
        "dataset_scope": "controlled_300",
        "status": "completed",
        "startup_network_requests": 0,
    }
    mismatches = {
        key: {"expected": value, "observed": manifest.get(key)}
        for key, value in expected.items()
        if manifest.get(key) != value
    }
    if mismatches:
        raise DashboardContractError(f"Runtime-manifest contract mismatch: {mismatches}")
    if tuple(manifest.get("principal_room_ids", ())) != tuple(PRINCIPAL_ROOM_IDS):
        raise DashboardContractError("Runtime manifest principal-room order is invalid")
    child = manifest.get("child_routes")
    if child != [{"room_id": CHILD_ROOM_ID, "parent_room_id": "trustworthiness"}]:
        raise DashboardContractError("Runtime manifest child-route contract is invalid")
    if not _text_or_none(manifest.get("release_id")):
        raise DashboardContractError("Runtime manifest release_id is missing")
    validation = manifest.get("validation_summary")
    if not isinstance(validation, Mapping):
        raise DashboardContractError("Runtime manifest validation summary is missing")
    if validation.get("status") != "passed" or int(validation.get("blocking_failure_count", -1)) != 0:
        raise DashboardContractError("Notebook 34 package did not pass its completion gate")


def _validate_loaded_package(package: DashboardPackage) -> None:
    schemas = {
        "bootstrap": (package.bootstrap, "dashboard_bootstrap.v1"),
        "room catalogue": (package.room_catalogue, "dashboard_room_catalogue.v1"),
        "glossary": (package.glossary, "dashboard_glossary.v1"),
        "filter options": (package.filter_options, "dashboard_filter_options.v2"),
    }
    release_bound_bootstrap = {"bootstrap", "room catalogue", "glossary"}
    for name, (payload, schema) in schemas.items():
        if payload.get("schema_version") != schema:
            raise DashboardContractError(f"{name} schema drift")
        if name in release_bound_bootstrap and payload.get("release_id") != package.release_id:
            raise DashboardContractError(f"{name} release drift")
        if str(payload.get("status", "")).casefold() != "ok":
            raise DashboardContractError(f"{name} is not approved")

    table_contracts = (
        (package.painting_lookup, PAINTING_LOOKUP_COLUMNS, "painting_lookup", "painting_id"),
        (package.display_components, DISPLAY_COMPONENT_COLUMNS, "display_components", "binding_id"),
        (package.dashboard_assets, DASHBOARD_ASSET_COLUMNS, "dashboard_assets", "asset_id"),
        (package.asset_locators, ASSET_LOCATOR_COLUMNS, "asset_locators", "locator_id"),
        (package.renditions, RENDITION_COLUMNS, "renditions", "rendition_id"),
        (package.room_partitions, ROOM_PARTITION_COLUMNS, "room_partitions", "partition_id"),
    )
    for frame, columns, label, identity in table_contracts:
        _require_columns(frame, columns, label)
        _require_unique(frame, identity, label)
        _require_ok(frame, label)
    for frame, expected, label in (
        (package.display_components, DISPLAY_BINDING_SCHEMA, "display_components"),
        (package.dashboard_assets, DASHBOARD_ASSET_SCHEMA, "dashboard_assets"),
        (package.asset_locators, ASSET_LOCATOR_SCHEMA, "asset_locators"),
        (package.renditions, RENDITION_SCHEMA, "renditions"),
    ):
        if set(frame["schema_version"].astype(str)) != {expected}:
            raise DashboardContractError(f"{label} schema drift")

    if len(package.painting_lookup) != int(package.population["painting_count"]):
        raise DashboardContractError("Painting-lookup population drift")
    room_ids = tuple(package.room_partitions["room_id"].astype(str))
    if set(room_ids) != set(ALL_ROOM_IDS) or len(room_ids) != len(ALL_ROOM_IDS):
        raise DashboardContractError("Room-partition coverage drift")
    expected_displays = set(map(str, package.runtime_manifest.get("display_ids", ())))
    observed_displays = set(package.display_components["display_id"].astype(str))
    if expected_displays != observed_displays:
        raise DashboardContractError("Display-binding closure failed")
    asset_refs = {
        value.split(":", 1)[1]
        for value in package.display_components["payload_ref"].astype(str)
        if value.startswith("asset:")
    }
    registered_assets = set(package.dashboard_assets["asset_id"].astype(str))
    if not asset_refs.issubset(registered_assets):
        raise DashboardContractError(
            f"Display bindings reference unknown assets: {sorted(asset_refs - registered_assets)}"
        )
    if not set(package.asset_locators["asset_id"].astype(str)).issubset(registered_assets):
        raise DashboardContractError("Asset locators reference unknown assets")
    if not set(package.renditions["asset_id"].astype(str)).issubset(registered_assets):
        raise DashboardContractError("Renditions reference unknown assets")


def open_dashboard_package(
    project_root: str | Path | None = None,
    *,
    package_root: str | Path | None = None,
    verify_bootstrap: bool = True,
) -> DashboardPackage:
    """Open the N34 v2 package without fetching or scanning producer data."""

    root = find_project_root(project_root)
    resolved_package = (
        resolve_repo_path(package_root, root)
        if package_root is not None
        else (root / DEFAULT_PACKAGE_RELATIVE).resolve()
    )
    try:
        resolved_package.relative_to(root.resolve())
    except ValueError as exc:
        raise DashboardContractError("Dashboard package root escapes the repository") from exc
    if not resolved_package.is_dir():
        raise FileNotFoundError(f"Dashboard package root is missing: {resolved_package}")

    runtime_path = _package_path(resolved_package, RUNTIME_MANIFEST_RELATIVE)
    if not runtime_path.is_file():
        raise FileNotFoundError(f"Dashboard runtime manifest is missing: {runtime_path}")
    runtime_manifest = _json_object(runtime_path)
    _validate_runtime_manifest(runtime_manifest)
    artifact_index = _build_artifact_index(runtime_manifest)

    def declared_path(relative: str) -> Path:
        record = artifact_index.get(relative)
        if record is None:
            raise DashboardContractError(f"Bootstrap file is not declared: {relative}")
        path = _package_path(resolved_package, relative)
        if not path.is_file():
            raise FileNotFoundError(f"Required dashboard file is missing: {relative}")
        if path.stat().st_size != int(record["size_bytes"]):
            raise DashboardContractError(f"Dashboard file size drift: {relative}")
        if verify_bootstrap and sha256_file(path) != str(record["sha256"]):
            raise DashboardContractError(f"Dashboard file checksum drift: {relative}")
        return path

    bootstrap = _json_object(declared_path(BOOTSTRAP_PATHS["bootstrap"]))
    room_catalogue = _json_object(declared_path(BOOTSTRAP_PATHS["room_catalogue"]))
    glossary = _json_object(declared_path(BOOTSTRAP_PATHS["glossary"]))
    filter_options = _json_object(declared_path(BOOTSTRAP_PATHS["filter_options"]))
    painting_lookup = _frame(declared_path(BOOTSTRAP_PATHS["painting_lookup"]))
    display_components = _frame(declared_path(MANIFEST_PATHS["display_components"]))
    dashboard_assets = _frame(declared_path(MANIFEST_PATHS["dashboard_assets"]))
    asset_locators = _frame(declared_path(MANIFEST_PATHS["asset_locators"]))
    renditions = _frame(declared_path(MANIFEST_PATHS["renditions"]))
    room_partitions = _frame(declared_path(MANIFEST_PATHS["room_partitions"]))

    artifacts = _frame(_package_path(resolved_package, FINAL_RECORD_PATHS["artifacts"]))
    run_manifest = _json_object(_package_path(resolved_package, FINAL_RECORD_PATHS["run_manifest"]))
    upstream_checks = _frame(_package_path(resolved_package, FINAL_RECORD_PATHS["upstream_checks"]))

    package = DashboardPackage(
        project_root=root,
        package_root=resolved_package,
        runtime_manifest=runtime_manifest,
        artifact_index=artifact_index,
        bootstrap=bootstrap,
        room_catalogue=room_catalogue,
        glossary=glossary,
        filter_options=filter_options,
        painting_lookup=painting_lookup,
        display_components=display_components,
        dashboard_assets=dashboard_assets,
        asset_locators=asset_locators,
        renditions=renditions,
        room_partitions=room_partitions,
        upstream_checks=upstream_checks,
        artifacts=artifacts,
        run_manifest=run_manifest,
    )
    _validate_loaded_package(package)
    return package


def load_dashboard_package(
    project_root: str | Path | None = None,
    *,
    package_root: str | Path | None = None,
    require_all_files: bool | None = None,
) -> DashboardPackage:
    """Compatibility alias for :func:`open_dashboard_package`.

    ``require_all_files`` is accepted for old call sites but intentionally does
    not trigger eager painting/report loading. Use ``audit_dashboard_package``
    with ``verify_all_files=True`` for a full local verification sweep.
    """

    del require_all_files
    return open_dashboard_package(project_root, package_root=package_root)


def validate_selection(
    package: DashboardPackage,
    selection: DashboardSelection | Mapping[str, Any],
) -> DashboardSelection:
    """Validate one identifier-only selection without silent substitution."""

    state = selection if isinstance(selection, DashboardSelection) else DashboardSelection.from_mapping(selection)
    room_id = _text_or_none(state.room_id) or "exhibition_foyer"
    if room_id not in ALL_ROOM_IDS:
        raise DashboardSelectionError(f"Unknown dashboard room: {room_id!r}")
    if state.return_room is not None and str(state.return_room) not in PRINCIPAL_ROOM_IDS:
        raise DashboardSelectionError(f"Invalid return room: {state.return_room!r}")
    if room_id == CHILD_ROOM_ID and state.return_room not in (None, "trustworthiness"):
        raise DashboardSelectionError("Focused portrait review must return to Trustworthiness")

    painting_id = _text_or_none(state.painting_id)
    dependent = (
        state.case_id,
        state.candidate_id,
        state.model_id,
        state.seed,
        state.prompt_variant_id,
        state.annotation_id,
        state.hand_control_id,
        state.review_unit_id,
        state.blind_review_code,
    )
    if painting_id is None:
        if any(not _blank(value) for value in dependent):
            raise DashboardSelectionError("A case/candidate selection requires painting_id")
        return DashboardSelection.from_mapping({**state.as_identifiers(), "room_id": room_id})

    payload = package.load_painting(painting_id)
    cases = {str(row.get("case_id")): row for row in payload.get("cases", [])}
    candidates = {str(row.get("candidate_id")): row for row in payload.get("candidates", [])}
    case_id = _text_or_none(state.case_id)
    candidate_id = _text_or_none(state.candidate_id)
    if case_id is not None and case_id not in cases:
        raise DashboardSelectionError(
            f"Case {case_id!r} is unavailable for painting {painting_id}"
        )
    if candidate_id is not None:
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise DashboardSelectionError(
                f"Candidate {candidate_id!r} is unavailable for painting {painting_id}"
            )
        if case_id is not None and str(candidate.get("case_id")) != case_id:
            raise DashboardSelectionError("Candidate and case identities do not match")
        for field, requested in {
            "model_id": state.model_id,
            "seed": state.seed,
            "prompt_variant_id": state.prompt_variant_id,
        }.items():
            if _blank(requested):
                continue
            observed = candidate.get(field)
            if str(observed) != str(requested):
                raise DashboardSelectionError(
                    f"Candidate {field} mismatch: requested {requested!r}, observed {observed!r}"
                )
    elif state.model_id is not None:
        available = set(map(str, payload.get("selectors", {}).get("model_ids", [])))
        if str(state.model_id) not in available:
            raise DashboardSelectionError(
                f"Model {state.model_id!r} is unavailable for painting {painting_id}"
            )
    if state.evidence_layer is not None:
        available_layers = set(map(str, payload.get("selectors", {}).get("evidence_layers", [])))
        if str(state.evidence_layer) not in available_layers:
            raise DashboardSelectionError(
                f"Evidence layer {state.evidence_layer!r} is unavailable for painting {painting_id}"
            )
    return DashboardSelection.from_mapping({**state.as_identifiers(), "room_id": room_id})


def load_dashboard_validation_config(
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load the strict Controlled-300 Notebook 35 configuration."""

    root = find_project_root(project_root)
    path = root / "config" / "evaluation" / "dashboard_validation.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Dashboard validation configuration is missing: {path}")
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = yaml.safe_load(handle)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise DashboardContractError(f"Could not load dashboard validation config: {exc}") from exc
    if not isinstance(payload, dict):
        raise DashboardContractError("Dashboard validation configuration must be a mapping")
    if payload.get("schema_version") != DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION:
        raise DashboardContractError(
            "Unsupported dashboard validation configuration schema: "
            f"{payload.get('schema_version')!r}"
        )
    for key in (
        "notebook",
        "application",
        "required_inputs",
        "expected_population",
        "runtime",
        "presentation",
        "scientific_boundaries",
        "outputs",
    ):
        if key not in payload:
            raise DashboardContractError(f"Configuration section is missing: {key}")
    return payload


def required_input_paths(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Path]:
    """Resolve declared Notebook 35 inputs and reject repository escapes."""

    root = find_project_root(project_root)
    required = config.get("required_inputs")
    if not isinstance(required, Mapping):
        raise DashboardContractError("required_inputs must be a mapping")
    result: dict[str, Path] = {}
    templates = validate_input_path_templates(config, root)
    # Templates are validated separately because they do not identify one
    # concrete input.  Their map value is the existing static shard directory,
    # never a brace-containing pseudo-file.
    for key, contract in required.items():
        if isinstance(contract, Mapping):
            value = contract.get("path")
            template = contract.get("path_template")
            if not _blank(template):
                if not _blank(value):
                    raise DashboardContractError(
                        f"Required input cannot declare both path and path_template: {key}"
                    )
                static_parent = templates[str(key)].split("{painting_id}", 1)[0].rstrip("/")
                parent = Path(static_parent)
                if parent.suffix:
                    parent = parent.parent
                result[str(key)] = resolve_repo_path(parent.as_posix(), root)
                continue
        else:
            value = contract
        if _blank(value):
            raise DashboardContractError(f"Invalid required-input contract: {key}")
        result[str(key)] = resolve_repo_path(str(value), root)
    return result


def validate_input_path_templates(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, str]:
    """Validate identifier templates without converting them to concrete paths.

    Notebook 35 declares the 300 painting shards with one ``{painting_id}``
    template.  The template is part of the package contract, but it is not a
    file and therefore is deliberately excluded from :func:`required_input_paths`.
    A safe sample substitution proves that both its static parent and expanded
    paths remain within the repository root.
    """

    root = find_project_root(project_root)
    required = config.get("required_inputs")
    if not isinstance(required, Mapping):
        raise DashboardContractError("required_inputs must be a mapping")
    templates: dict[str, str] = {}
    for key, contract in required.items():
        if not isinstance(contract, Mapping) or _blank(contract.get("path_template")):
            continue
        template = str(contract["path_template"]).strip()
        if template.count("{painting_id}") != 1:
            raise DashboardContractError(
                f"Required-input path_template must contain exactly one "
                f"{{painting_id}} placeholder: {key}"
            )
        # Reject all other formatting fields instead of allowing late string
        # interpolation to redirect reads.
        remainder = template.replace("{painting_id}", "")
        if "{" in remainder or "}" in remainder or "\\" in template:
            raise DashboardContractError(f"Unsafe required-input path_template: {key}")
        expanded = template.replace("{painting_id}", "p001")
        resolve_repo_path(expanded, root)
        static_parent = template.split("{painting_id}", 1)[0].rstrip("/")
        if not static_parent:
            raise DashboardContractError(f"Unsafe required-input path_template: {key}")
        parent = Path(static_parent)
        if parent.suffix:
            parent = parent.parent
        resolve_repo_path(parent.as_posix(), root)
        templates[str(key)] = template
    return templates


def json_list(value: Any) -> list[Any]:
    """Return a JSON-list cell as a list; malformed or empty values become []."""

    if isinstance(value, list):
        return value
    if _blank(value):
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def truthy(value: Any) -> bool:
    """Normalize CSV/JSON boolean representations."""

    return False if _blank(value) else str(value).strip().casefold() in {
        "1", "true", "yes", "y", "passed", "ok"
    }


def display_label(value: Any) -> str:
    """Turn stable identifiers into compact public labels."""

    text = str(value or "").strip()
    known = {
        "hint_places2": "HINT",
        "lama": "LaMa",
        "opencv_telea": "OpenCV Telea",
        "stable_diffusion_inpainting": "Stable Diffusion 1.5",
        "sdxl_inpainting": "SDXL",
        "lpips": "LPIPS",
        "clip": "CLIP",
        "dinov2": "DINOv2",
        "ssim": "SSIM",
        "psnr": "PSNR",
    }
    return known.get(text.casefold(), text.replace("_", " ").strip().title())


def safe_project_path(
    value: Any,
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
    allowed_suffixes: Iterable[str] | None = None,
) -> Path | None:
    """Resolve a repository path without allowing arbitrary file access."""

    if _blank(value):
        return None
    try:
        path = resolve_repo_path(str(value), project_root)
    except (ValueError, FileNotFoundError):
        return None
    if must_exist and not path.is_file():
        return None
    if allowed_suffixes:
        suffixes = {str(item).casefold() for item in allowed_suffixes}
        if path.suffix.casefold() not in suffixes:
            return None
    return path


def filter_frame(frame: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    """Apply exact scalar or membership filters while treating blanks as unset."""

    result = frame
    for column, selection in filters.items():
        if column not in result.columns or selection in (None, "", "All"):
            continue
        if isinstance(selection, (list, tuple, set, frozenset)):
            values = [item for item in selection if item not in (None, "", "All")]
            if values:
                result = result.loc[result[column].isin(values)]
        else:
            result = result.loc[result[column].eq(selection)]
    return result.copy()


def stable_options(frame: pd.DataFrame, column: str) -> list[str]:
    """Return sorted, non-empty string options from a dataframe column."""

    if column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str).str.strip()
    return sorted(value for value in values.unique().tolist() if value)


def default_case_rows(case_index: pd.DataFrame) -> pd.DataFrame:
    """Retained v1 utility: choose deterministic report-selected rows."""

    selected = case_index[
        case_index.get("report_selected", pd.Series(False, index=case_index.index)).map(truthy)
    ]
    if selected.empty:
        selected = case_index
    columns = [
        column for column in ("painting_id", "case_id", "model_id", "candidate_id")
        if column in selected.columns
    ]
    return selected.sort_values(columns, kind="stable") if columns else selected


def case_visual_paths(
    row: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, list[Path]]:
    """Retained local-only utility for legacy indexed rows."""

    result: dict[str, list[Path]] = {}
    for key in ("clean_path", "damaged_path", "mask_path", "restored_path"):
        path = safe_project_path(
            row.get(key), project_root, allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"}
        )
        result[key] = [path] if path is not None else []
    for key in (
        "difference_paths_json", "uncertainty_paths_json", "seam_paths_json",
        "colour_paths_json", "texture_paths_json", "semantic_paths_json",
        "mask_boundary_paths_json",
    ):
        result[key] = [
            path
            for value in json_list(row.get(key))
            if (path := safe_project_path(
                value, project_root, allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"}
            )) is not None
        ]
    return result


def report_bytes(
    relative_path: Any,
    project_root: str | Path | None = None,
) -> tuple[bytes, str] | None:
    """Read one explicit local report action; never called during package load."""

    path = safe_project_path(
        relative_path,
        project_root,
        allowed_suffixes={".html", ".md", ".pdf", ".csv", ".json"},
    )
    return None if path is None else (path.read_bytes(), path.name)


def _check(
    records: list[dict[str, Any]],
    *,
    stage: str,
    check_id: str,
    description: str,
    expected: Any,
    observed: Any,
    passed: bool,
    severity: str = "blocking",
    details: Any = "",
) -> None:
    def encode(value: Any) -> str:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            if isinstance(value, (dict, list, tuple, set)) else str(value)
        )

    records.append({
        "validation_stage": stage,
        "check_id": check_id,
        "check_description": description,
        "severity": severity,
        "expected": encode(expected),
        "observed": encode(observed),
        "passed": bool(passed),
        "details": encode(details),
    })


def audit_dashboard_package(
    project_root: str | Path | None = None,
    *,
    verify_all_files: bool = False,
) -> pd.DataFrame:
    """Audit the v2 package; full mode hashes every runtime-declared file."""

    records: list[dict[str, Any]] = []
    try:
        package = open_dashboard_package(project_root)
    except Exception as exc:
        _check(
            records,
            stage="package_open",
            check_id="package_open",
            description="Controlled-300 dashboard package opens under the v2 trust contract",
            expected="verified package",
            observed=f"{type(exc).__name__}: {exc}",
            passed=False,
        )
        return pd.DataFrame.from_records(records)

    facts = {
        "runtime_schema": (package.runtime_manifest.get("schema_version"), DASHBOARD_RUNTIME_MANIFEST_SCHEMA),
        "package_schema": (package.runtime_manifest.get("package_schema_version"), DASHBOARD_PACKAGE_SCHEMA),
        "principal_rooms": (list(package.principal_room_ids), list(PRINCIPAL_ROOM_IDS)),
        "child_rooms": (sorted(set(package.room_partitions["room_id"]) - set(PRINCIPAL_ROOM_IDS)), [CHILD_ROOM_ID]),
        "paintings": (len(package.painting_lookup), 300),
        "room_partitions": (len(package.room_partitions), 9),
        "display_ids": (package.display_components["display_id"].nunique(), 100),
        "display_bindings": (len(package.display_components), 170),
        "logical_assets": (len(package.dashboard_assets), 56),
        "renditions": (len(package.renditions), 48),
        "asset_locators": (len(package.asset_locators), 95),
        "runtime_local_artifacts": (len(package.artifact_index), 373),
        "n34_blocking_failures": (
            int((
                ~package.upstream_checks["passed"].map(truthy)
                & package.upstream_checks["severity"].astype(str).str.casefold().isin({"blocking", "error"})
            ).sum()),
            0,
        ),
    }
    for check_id, (observed, expected) in facts.items():
        _check(
            records,
            stage="package_contract",
            check_id=check_id,
            description=f"Controlled-300 package satisfies {check_id.replace('_', ' ')}",
            expected=expected,
            observed=observed,
            passed=observed == expected,
        )

    try:
        report_count: Any = int(package.load_reports()["report_count"])
    except Exception as exc:
        report_count = f"{type(exc).__name__}: {exc}"
    _check(
        records,
        stage="package_contract",
        check_id="report_index_count",
        description="Report catalogue preserves all registered reports",
        expected=337,
        observed=report_count,
        passed=report_count == 337,
    )
    physical_files = sum(1 for path in package.package_root.rglob("*") if path.is_file())
    _check(
        records,
        stage="package_contract",
        check_id="physical_file_count",
        description="Promoted package contains the exact canonical file population",
        expected=377,
        observed=physical_files,
        passed=physical_files == 377,
    )
    work_exists = (package.package_root / "work").exists()
    _check(
        records,
        stage="package_contract",
        check_id="no_work_directory",
        description="No temporary work directory remains after N34 promotion",
        expected=False,
        observed=work_exists,
        passed=not work_exists,
    )
    if verify_all_files:
        failures: list[str] = []
        for relative_path in sorted(package.artifact_index):
            try:
                package.verify_relative_file(relative_path)
            except Exception as exc:
                failures.append(f"{relative_path}: {type(exc).__name__}: {exc}")
        _check(
            records,
            stage="package_integrity",
            check_id="all_runtime_artifacts",
            description="Every runtime-declared local artifact matches size and SHA-256",
            expected=0,
            observed=len(failures),
            passed=not failures,
            details=failures[:10],
        )
    return pd.DataFrame.from_records(records)


def audit_indexed_paths(
    package: DashboardPackage,
    *,
    include_all_visuals: bool = True,
) -> pd.DataFrame:
    """Compatibility audit for local N34 renditions and optional exact paths."""

    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for relative_path in package.renditions["relative_path"].astype(str):
        try:
            package.verify_relative_file(relative_path)
        except Exception as exc:
            failures.append(f"{relative_path}: {type(exc).__name__}: {exc}")
    _check(
        records,
        stage="indexed_paths",
        check_id="registered_renditions",
        description="Every registered local rendition exists and matches the trust root",
        expected=0,
        observed=len(failures),
        passed=not failures,
        details=failures[:10],
    )
    if include_all_visuals:
        local_exact = package.asset_locators.loc[
            package.asset_locators["transport"].astype(str).eq("local_package")
        ]
        missing: list[str] = []
        for _, locator in local_exact.iterrows():
            relative_path = str(locator["relative_path"])
            try:
                path = package.verify_relative_file(relative_path)
                expected_size = int(locator.get("expected_size_bytes", path.stat().st_size))
                expected_sha = str(locator.get("expected_sha256", "")).casefold()
                if path.stat().st_size != expected_size:
                    raise DashboardContractError("locator size drift")
                if _SHA256_RE.fullmatch(expected_sha) and sha256_file(path) != expected_sha:
                    raise DashboardContractError("locator checksum drift")
            except Exception as exc:
                missing.append(f"{relative_path}: {type(exc).__name__}: {exc}")
        _check(
            records,
            stage="indexed_paths",
            check_id="local_exact_assets",
            description="Registered local exact assets remain repository-contained",
            expected=0,
            observed=len(missing),
            passed=not missing,
            details=missing[:10],
        )
    return pd.DataFrame.from_records(records)


def audit_streamlit_source(
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Perform network-free static checks without importing Streamlit."""

    root = find_project_root(project_root)
    try:
        config = load_dashboard_validation_config(root)
        app_value = config["application"].get("entrypoint", "streamlit_app.py")
        prohibited = config.get("scientific_boundaries", {}).get("prohibited_source_fragments", [])
    except (DashboardContractError, FileNotFoundError, KeyError):
        app_value = "streamlit_app.py"
        prohibited = []
    app_path = resolve_repo_path(app_value, root)
    source = app_path.read_text(encoding="utf-8") if app_path.is_file() else ""
    records: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source, filename=str(app_path))
        syntax_error = ""
    except SyntaxError as exc:
        tree = None
        syntax_error = f"{exc.msg} at line {exc.lineno}"
    _check(
        records,
        stage="application_static",
        check_id="python_syntax",
        description="Streamlit entrypoint parses as Python",
        expected="valid",
        observed=syntax_error or "valid",
        passed=not syntax_error,
    )
    for fragment in prohibited:
        present = str(fragment).casefold() in source.casefold()
        _check(
            records,
            stage="application_static",
            check_id=f"prohibited__{re.sub(r'[^a-z0-9]+', '_', str(fragment).casefold())}",
            description=f"Application excludes prohibited source fragment: {fragment}",
            expected=False,
            observed=present,
            passed=not present,
        )
    writes: list[str] = []
    if tree is not None:
        forbidden = {
            "to_csv", "to_json", "to_parquet", "write_text", "write_bytes",
            "mkdir", "makedirs", "remove", "unlink", "rename",
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else (
                node.func.id if isinstance(node.func, ast.Name) else ""
            )
            if name in forbidden:
                writes.append(f"{name}@{getattr(node, 'lineno', '?')}")
    _check(
        records,
        stage="application_boundaries",
        check_id="read_only_application",
        description="Application source contains no filesystem/dataframe writes",
        expected=[],
        observed=writes,
        passed=not writes,
    )
    return pd.DataFrame.from_records(records)


def configuration_checksum(project_root: str | Path | None = None) -> str:
    """Return the current Notebook 35 configuration checksum."""

    root = find_project_root(project_root)
    return sha256_file(root / "config" / "evaluation" / "dashboard_validation.yaml")


__all__ = [
    "ALL_ROOM_IDS", "CHILD_ROOM_ID", "DASHBOARD_APPLICATION_VERSION",
    "DASHBOARD_PACKAGE_SCHEMA_VERSION", "DASHBOARD_RUNTIME_MANIFEST_SCHEMA_VERSION",
    "DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION", "DashboardBundle",
    "DashboardContractError", "DashboardPackage", "DashboardSelection",
    "DashboardSelectionError", "PRINCIPAL_ROOM_IDS", "audit_dashboard_package",
    "audit_indexed_paths", "audit_streamlit_source", "case_visual_paths",
    "configuration_checksum", "default_case_rows", "display_label", "filter_frame",
    "json_list", "load_dashboard_package", "load_dashboard_validation_config",
    "open_dashboard_package", "report_bytes", "required_input_paths",
    "safe_project_path", "stable_options", "truthy", "validate_selection",
    "validate_input_path_templates",
]
