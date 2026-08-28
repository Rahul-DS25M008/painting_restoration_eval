from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

try:
    from PIL import Image
except ImportError:  # Optional; failures are recorded per image.
    Image = None

try:
    import yaml
except ImportError:  # Optional; failures are recorded per YAML file.
    yaml = None

try:
    import pyarrow.parquet as parquet
except ImportError:  # Optional; failures are recorded per Parquet file.
    parquet = None


INVENTORY_SCHEMA_VERSION = "project_file_inventory.v1"
RUN_SCHEMA_VERSION = "inventory_run.v1"
DEFAULT_HASH_BYTES = 1024 * 1024
CSV_FIELD_SIZE_LIMIT = 16 * 1024 * 1024

# Validation and audit tables can legitimately contain serialized sets or
# dictionaries larger than Python's conservative default CSV field limit.
# Raising the parser limit keeps inventory metadata inspection read-only while
# allowing those normalized tables to be counted and described correctly.
csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
TABULAR_EXTENSIONS = {".csv", ".tsv", ".parquet"}
JSON_EXTENSIONS = {".json"}
YAML_EXTENSIONS = {".yaml", ".yml"}
NOTEBOOK_EXTENSIONS = {".ipynb"}

DEFAULT_SKIP_DIRS = {
    ".git",
    ".ipynb_checkpoints",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

# Excluded from scans when they occur inside the selected inventory directory.
# The legacy summary is excluded so the first new refresh does not inventory a
# retired artifact before it is removed from version control.
GENERATED_INVENTORY_FILENAMES = {
    "project_file_inventory.csv",
    "project_file_inventory_summary.csv",
    "inventory_run.json",
}

INVENTORY_FIELDNAMES = [
    "inventory_schema_version",
    "inventory_run_id",
    "file_id",
    "relative_path",
    "file_name",
    "parent_dir",
    "extension",
    "format",
    "file_kind",
    "size_bytes",
    "last_modified_utc",
    "depth",
    "tabular_row_count",
    "tabular_column_count",
    "tabular_columns_json",
    "structured_top_level_type",
    "structured_top_level_keys_json",
    "image_width",
    "image_height",
    "image_mode",
    "image_format",
    "notebook_cell_count",
    "notebook_code_cell_count",
    "notebook_markdown_cell_count",
    "notebook_raw_cell_count",
    "notebook_saved_output_count",
    "notebook_saved_error_output_count",
    "hash_mode",
    "hash_algorithm",
    "hash_bytes_read",
    "hash_value",
    "read_error_count",
    "read_errors_json",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def stable_file_id(relative_path: str) -> str:
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
    return f"file_{digest}"


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def top_level_description(value: Any) -> tuple[str, list[str]]:
    if value is None:
        return "null", []
    if isinstance(value, dict):
        return "object", sorted(str(key) for key in value.keys())
    if isinstance(value, list):
        return "array", []
    if isinstance(value, bool):
        return "boolean", []
    if isinstance(value, (int, float)):
        return "number", []
    if isinstance(value, str):
        return "string", []
    return type(value).__name__, []


def file_format(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".csv": "csv",
        ".tsv": "tsv",
        ".parquet": "parquet",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".ipynb": "notebook",
        ".html": "html",
        ".htm": "html",
        ".md": "markdown",
        ".txt": "text",
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".webp": "webp",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".bmp": "bmp",
        ".py": "python",
    }.get(suffix, suffix.lstrip(".") or "no_extension")


def classify_file(path: Path) -> str:
    text = path.as_posix().lower()
    suffix = path.suffix.lower()

    if suffix in TABULAR_EXTENSIONS:
        if "manifest" in text:
            return "manifest_table"
        if "validation" in text or "/checks" in text:
            return "validation_table"
        if "metric" in text or "lpips" in text or "similarity" in text:
            return "metric_table"
        if "summary" in text:
            return "summary_table"
        return "table"

    if suffix in IMAGE_EXTENSIONS:
        if "mask" in text:
            return "mask_image"
        if "clean" in text or "original" in text:
            return "clean_image"
        if "damaged" in text or "degraded" in text or "degradation" in text:
            return "damaged_image"
        if any(
            token in text
            for token in ("restored", "opencv", "lama", "sdxl", "stable_diffusion")
        ):
            return "restored_image"
        if any(
            token in text
            for token in ("figure", "plot", "report", "panel", "grid", "heatmap")
        ):
            return "figure_image"
        return "image"

    if suffix in NOTEBOOK_EXTENSIONS:
        return "notebook"
    if suffix in JSON_EXTENSIONS:
        return "json"
    if suffix in YAML_EXTENSIONS:
        return "yaml"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".md":
        return "markdown"
    if suffix == ".txt":
        return "text"
    if suffix == ".py":
        return "python"
    return "other"


def error_record(stage: str, exc: BaseException) -> dict[str, str]:
    return {
        "stage": stage,
        "error_type": type(exc).__name__,
        "message": str(exc),
    }


def inspect_delimited(path: Path, delimiter: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        columns = next(reader, [])
        row_count = sum(1 for _ in reader)
    return {
        "tabular_row_count": row_count,
        "tabular_column_count": len(columns),
        "tabular_columns_json": json_compact(columns),
    }


def inspect_parquet(path: Path) -> dict[str, Any]:
    if parquet is None:
        raise RuntimeError("pyarrow is not installed; Parquet metadata is unavailable")
    metadata = parquet.read_metadata(path)
    columns = list(parquet.read_schema(path).names)
    return {
        "tabular_row_count": metadata.num_rows,
        "tabular_column_count": len(columns),
        "tabular_columns_json": json_compact(columns),
    }


def inspect_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    value_type, keys = top_level_description(value)
    return {
        "structured_top_level_type": value_type,
        "structured_top_level_keys_json": json_compact(keys),
    }


def inspect_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is not installed; YAML metadata is unavailable")
    with path.open("r", encoding="utf-8-sig") as handle:
        value = yaml.safe_load(handle)
    value_type, keys = top_level_description(value)
    return {
        "structured_top_level_type": value_type,
        "structured_top_level_keys_json": json_compact(keys),
    }


def inspect_image(path: Path) -> dict[str, Any]:
    if Image is None:
        raise RuntimeError("Pillow is not installed; image metadata is unavailable")
    with Image.open(path) as image:
        return {
            "image_width": image.width,
            "image_height": image.height,
            "image_mode": image.mode,
            "image_format": image.format or "",
        }


def inspect_notebook(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        notebook = json.load(handle)

    cells = notebook.get("cells", [])
    code_count = 0
    markdown_count = 0
    raw_count = 0
    saved_output_count = 0
    saved_error_output_count = 0

    for cell in cells:
        cell_type = cell.get("cell_type")
        if cell_type == "code":
            code_count += 1
        elif cell_type == "markdown":
            markdown_count += 1
        elif cell_type == "raw":
            raw_count += 1

        outputs = cell.get("outputs", []) if cell_type == "code" else []
        saved_output_count += len(outputs)
        saved_error_output_count += sum(
            1 for output in outputs if output.get("output_type") == "error"
        )

    return {
        "notebook_cell_count": len(cells),
        "notebook_code_cell_count": code_count,
        "notebook_markdown_cell_count": markdown_count,
        "notebook_raw_cell_count": raw_count,
        "notebook_saved_output_count": saved_output_count,
        "notebook_saved_error_output_count": saved_error_output_count,
    }


def hash_file(path: Path, mode: str, partial_bytes: int) -> tuple[int, str]:
    if mode == "none":
        return 0, ""

    digest = hashlib.sha256()
    bytes_read = 0
    remaining = partial_bytes if mode == "partial" else None

    with path.open("rb") as handle:
        while True:
            read_size = 1024 * 1024
            if remaining is not None:
                if remaining <= 0:
                    break
                read_size = min(read_size, remaining)
            chunk = handle.read(read_size)
            if not chunk:
                break
            digest.update(chunk)
            bytes_read += len(chunk)
            if remaining is not None:
                remaining -= len(chunk)

    return bytes_read, digest.hexdigest()


def full_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path, out_dir: Path, skip_dirs: set[str]) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = sorted(
            directory for directory in dirnames if directory not in skip_dirs
        )

        for filename in sorted(filenames):
            path = current_path / filename
            if (
                path.parent == out_dir
                and filename in GENERATED_INVENTORY_FILENAMES
            ):
                continue
            yield path


def empty_inventory_row() -> dict[str, Any]:
    return {field: "" for field in INVENTORY_FIELDNAMES}


def inspect_file(
    path: Path,
    root: Path,
    run_id: str,
    hash_mode: str,
    hash_bytes: int,
) -> dict[str, Any]:
    relative_path = normalized_relative_path(path, root)
    row = empty_inventory_row()
    errors: list[dict[str, str]] = []

    row.update(
        {
            "inventory_schema_version": INVENTORY_SCHEMA_VERSION,
            "inventory_run_id": run_id,
            "file_id": stable_file_id(relative_path),
            "relative_path": relative_path,
            "file_name": path.name,
            "parent_dir": path.parent.relative_to(root).as_posix()
            if path.parent != root
            else "",
            "extension": path.suffix.lower(),
            "format": file_format(path),
            "file_kind": classify_file(path),
            "depth": len(Path(relative_path).parts) - 1,
            "tabular_columns_json": "[]",
            "structured_top_level_keys_json": "[]",
            "hash_mode": hash_mode,
            "hash_algorithm": ""
            if hash_mode == "none"
            else ("sha256_first_n_bytes" if hash_mode == "partial" else "sha256"),
        }
    )

    try:
        stat = path.stat()
        row["size_bytes"] = stat.st_size
        row["last_modified_utc"] = iso_utc(
            datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        )
    except Exception as exc:
        errors.append(error_record("stat", exc))

    suffix = path.suffix.lower()
    inspector = None
    stage = ""
    if suffix == ".csv":
        inspector = lambda: inspect_delimited(path, ",")
        stage = "csv_metadata"
    elif suffix == ".tsv":
        inspector = lambda: inspect_delimited(path, "\t")
        stage = "tsv_metadata"
    elif suffix == ".parquet":
        inspector = lambda: inspect_parquet(path)
        stage = "parquet_metadata"
    elif suffix in JSON_EXTENSIONS:
        inspector = lambda: inspect_json(path)
        stage = "json_metadata"
    elif suffix in YAML_EXTENSIONS:
        inspector = lambda: inspect_yaml(path)
        stage = "yaml_metadata"
    elif suffix in IMAGE_EXTENSIONS:
        inspector = lambda: inspect_image(path)
        stage = "image_metadata"
    elif suffix in NOTEBOOK_EXTENSIONS:
        inspector = lambda: inspect_notebook(path)
        stage = "notebook_metadata"

    if inspector is not None:
        try:
            row.update(inspector())
        except Exception as exc:
            errors.append(error_record(stage, exc))

    try:
        bytes_read, digest = hash_file(path, hash_mode, hash_bytes)
        row["hash_bytes_read"] = bytes_read
        row["hash_value"] = digest
    except Exception as exc:
        errors.append(error_record("hash", exc))

    row["read_error_count"] = len(errors)
    row["read_errors_json"] = json_compact(errors)
    return row


def atomic_write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=INVENTORY_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def counter_as_sorted_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def load_reusable_inventory(
    inventory_path: Path,
    run_path: Path,
    hash_mode: str,
    hash_bytes: int,
    enabled: bool,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    info: dict[str, Any] = {
        "cache_status": "disabled" if not enabled else "unavailable",
        "source_run_id": None,
    }
    if not enabled:
        return {}, info
    if not inventory_path.is_file() or not run_path.is_file():
        info["cache_status"] = "missing_previous_inventory"
        return {}, info

    try:
        with run_path.open("r", encoding="utf-8-sig") as handle:
            previous_run = json.load(handle)

        if previous_run.get("status") != "completed":
            raise ValueError("previous inventory run is not complete")
        if previous_run.get("inventory_schema_version") != INVENTORY_SCHEMA_VERSION:
            raise ValueError("previous inventory schema version differs")
        if previous_run.get("inventory_sha256") != full_sha256(inventory_path):
            raise ValueError("previous inventory checksum does not match")

        previous_hash = previous_run.get("hash_configuration", {})
        if previous_hash.get("mode") != hash_mode:
            raise ValueError("previous hash mode differs")
        if (
            hash_mode == "partial"
            and int(previous_hash.get("partial_bytes") or 0) != hash_bytes
        ):
            raise ValueError("previous partial-hash byte count differs")

        with inventory_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not set(INVENTORY_FIELDNAMES).issubset(reader.fieldnames or []):
                raise ValueError("previous inventory columns are incompatible")
            rows = {
                row["relative_path"]: row
                for row in reader
                if row.get("relative_path")
                and row.get("inventory_schema_version")
                == INVENTORY_SCHEMA_VERSION
            }

        info["cache_status"] = "verified"
        info["source_run_id"] = previous_run.get("inventory_run_id")
        return rows, info
    except Exception as exc:
        info["cache_status"] = "rejected"
        info["cache_rejection_reason"] = f"{type(exc).__name__}: {exc}"
        return {}, info


def reuse_unchanged_row(
    path: Path,
    root: Path,
    run_id: str,
    reusable_rows: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    relative_path = normalized_relative_path(path, root)
    previous = reusable_rows.get(relative_path)
    if previous is None or int(previous.get("read_error_count") or 0) != 0:
        return None

    try:
        stat = path.stat()
    except OSError:
        return None

    last_modified_utc = iso_utc(
        datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    )
    if (
        int(previous.get("size_bytes") or -1) != stat.st_size
        or previous.get("last_modified_utc") != last_modified_utc
    ):
        return None

    row: dict[str, Any] = {
        field: previous.get(field, "") for field in INVENTORY_FIELDNAMES
    }
    row["inventory_schema_version"] = INVENTORY_SCHEMA_VERSION
    row["inventory_run_id"] = run_id
    return row


def build_inventory(
    root: Path,
    out_dir: Path,
    hash_mode: str = "partial",
    hash_bytes: int = DEFAULT_HASH_BYTES,
    extra_skip_dirs: Iterable[str] = (),
    reuse_existing: bool = True,
) -> tuple[Path, Path]:
    started = utc_now()
    timer = perf_counter()
    root = root.resolve()
    out_dir = out_dir.resolve()

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository root does not exist or is not a directory: {root}"
        )
    if hash_bytes <= 0:
        raise ValueError("--hash-bytes must be a positive integer")
    try:
        out_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError("--out-dir must be located inside --root") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = out_dir / "project_file_inventory.csv"
    run_path = out_dir / "inventory_run.json"
    run_id = (
        f"inventory_{started.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    )
    skip_dirs = DEFAULT_SKIP_DIRS | {name for name in extra_skip_dirs if name}
    reusable_rows, reuse_info = load_reusable_inventory(
        inventory_path=inventory_path,
        run_path=run_path,
        hash_mode=hash_mode,
        hash_bytes=hash_bytes,
        enabled=reuse_existing,
    )

    file_rows: list[dict[str, Any]] = []
    reused_file_count = 0
    for path in iter_files(root, out_dir, skip_dirs):
        row = reuse_unchanged_row(path, root, run_id, reusable_rows)
        if row is None:
            row = inspect_file(
                path=path,
                root=root,
                run_id=run_id,
                hash_mode=hash_mode,
                hash_bytes=hash_bytes,
            )
        else:
            reused_file_count += 1
        file_rows.append(row)

    file_rows.sort(key=lambda row: str(row["relative_path"]))
    atomic_write_csv(inventory_path, file_rows)

    completed = utc_now()
    total_bytes = sum(int(row["size_bytes"] or 0) for row in file_rows)
    read_error_files = sum(
        int(row["read_error_count"] or 0) > 0 for row in file_rows
    )
    read_error_count = sum(
        int(row["read_error_count"] or 0) for row in file_rows
    )

    run_payload = {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "inventory_schema_version": INVENTORY_SCHEMA_VERSION,
        "inventory_run_id": run_id,
        "status": "completed",
        "generated_at_utc": iso_utc(started),
        "completed_at_utc": iso_utc(completed),
        "duration_seconds": round(perf_counter() - timer, 3),
        "repository_root": str(root),
        "inventory_relative_path": normalized_relative_path(inventory_path, root),
        "inventory_sha256": full_sha256(inventory_path),
        "inventory_size_bytes": inventory_path.stat().st_size,
        "hash_configuration": {
            "mode": hash_mode,
            "algorithm": "none"
            if hash_mode == "none"
            else (
                "sha256_first_n_bytes" if hash_mode == "partial" else "sha256"
            ),
            "partial_bytes": hash_bytes if hash_mode == "partial" else None,
        },
        "incremental_reuse": {
            "enabled": reuse_existing,
            **reuse_info,
            "reused_file_count": reused_file_count,
            "inspected_file_count": len(file_rows) - reused_file_count,
        },
        "scan_configuration": {
            "skipped_directory_names": sorted(skip_dirs),
            "excluded_generated_inventory_files": sorted(
                GENERATED_INVENTORY_FILENAMES
            ),
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "summary": {
            "file_count": len(file_rows),
            "total_size_bytes": total_bytes,
            "read_error_file_count": read_error_files,
            "read_error_count": read_error_count,
            "counts_by_format": counter_as_sorted_dict(
                Counter(str(row["format"]) for row in file_rows)
            ),
            "counts_by_file_kind": counter_as_sorted_dict(
                Counter(str(row["file_kind"]) for row in file_rows)
            ),
            "counts_by_extension": counter_as_sorted_dict(
                Counter(
                    str(row["extension"]) or "[none]" for row in file_rows
                )
            ),
        },
    }
    atomic_write_json(run_path, run_payload)

    print(f"Saved inventory: {inventory_path}")
    print(f"Saved run manifest: {run_path}")
    print(f"Inventory run ID: {run_id}")
    print(f"Files indexed: {len(file_rows)}")
    print(f"Files with read errors: {read_error_files}")
    print(f"Files reused unchanged: {reused_file_count}")
    print(f"Files inspected: {len(file_rows) - reused_file_count}")
    print(f"Duration seconds: {run_payload['duration_seconds']}")
    legacy_summary = out_dir / "project_file_inventory_summary.csv"
    if legacy_summary.exists():
        print(
            "Legacy summary still exists and is no longer generated: "
            f"{legacy_summary}"
        )
    return inventory_path, run_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the canonical project file inventory and inventory run manifest."
        )
    )
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument(
        "--out-dir",
        default="outputs/inventory",
        help="Canonical inventory output directory inside the repository root",
    )
    parser.add_argument(
        "--hash-mode",
        choices=("none", "partial", "full"),
        default="partial",
        help="Per-file hashing policy (default: partial)",
    )
    parser.add_argument(
        "--hash-bytes",
        type=int,
        default=DEFAULT_HASH_BYTES,
        help=(
            "Bytes read per file when --hash-mode=partial "
            "(default: 1048576)"
        ),
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Additional directory name to exclude; may be repeated",
    )
    parser.add_argument(
        "--no-reuse-existing",
        action="store_true",
        help=(
            "Disable verified reuse of unchanged rows from the previous "
            "inventory and force every file to be inspected again"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build_inventory(
            root=Path(args.root),
            out_dir=Path(args.out_dir),
            hash_mode=args.hash_mode,
            hash_bytes=args.hash_bytes,
            extra_skip_dirs=args.exclude_dir,
            reuse_existing=not args.no_reuse_existing,
        )
    except Exception as exc:
        print(
            f"Inventory build failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
