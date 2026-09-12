"""Plan, publish, and verify externally hosted notebook artifacts.

The tool is deliberately conservative:

* ``plan`` only reads notebook output files and writes a publication registry.
* ``upload-test`` refuses more than ten rows and requires an explicit phrase.
* ``upload`` publishes one explicitly named notebook in bounded commits.
* ``verify`` performs a remote read and checks both byte count and SHA-256.
* no command deletes, moves, untracks, stages, or commits local files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "external_artifact_publication.v1"
FIELDNAMES = [
    "publication_schema_version",
    "publication_run_id",
    "artifact_id",
    "producer_notebook",
    "local_relative_path",
    "storage_tier",
    "provider",
    "repository_id",
    "revision",
    "path_in_repository",
    "remote_uri",
    "sha256",
    "size_bytes",
    "media_role",
    "publication_status",
    "publication_commit_url",
    "published_at_utc",
    "verification_status",
    "verified_at_utc",
    "verification_error",
]


@dataclass(frozen=True)
class PublicationTarget:
    tier: str
    repo_id: str
    revision: str
    resolve_base_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "outputs").exists():
            return candidate
    raise RuntimeError("Could not locate the project root containing .git and outputs.")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-specific message
        raise RuntimeError(
            "PyYAML is required. Install requirements_publication.txt first."
        ) from exc
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}.")
    return value


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_id(relative_path: str) -> str:
    token = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:20]
    return f"external_{token}"


def parse_notebook_number(output_root: Path) -> int | None:
    prefix = output_root.name.split("_", 1)[0]
    if len(prefix) == 2 and prefix.isdigit():
        return int(prefix)
    return None


def image_group(relative_path: str) -> str | None:
    parts = relative_path.split("/")
    try:
        index = parts.index("images")
    except ValueError:
        return None
    if index + 1 >= len(parts):
        return None
    return parts[index + 1]


def encoded_remote_uri(base_url: str, path_in_repo: str) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in path_in_repo.split("/"))
    return f"{base_url.rstrip('/')}/{encoded}"


def configured_targets(config: dict[str, Any]) -> dict[str, PublicationTarget]:
    store = config["interactive_store"]
    revision = str(store.get("revision", "main"))
    provider = str(store["provider"])
    if provider != "huggingface_dataset":
        raise ValueError(f"Unsupported interactive provider: {provider}")
    targets: dict[str, PublicationTarget] = {}
    for tier, values in store["repositories"].items():
        targets[tier] = PublicationTarget(
            tier=tier,
            repo_id=str(values["repo_id"]),
            revision=revision,
            resolve_base_url=str(values["resolve_base_url"]),
        )
    return targets


def discover_rows(
    root: Path,
    config: dict[str, Any],
    through_notebook: int | None,
    exact_notebook: int | None = None,
) -> list[dict[str, str]]:
    rules = config["classification"]
    extensions = {str(value).lower() for value in rules["media_extensions"]}
    candidate_groups = {str(value) for value in rules["candidate_image_groups"]}
    diagnostic_groups = {str(value) for value in rules["diagnostic_image_groups"]}
    targets = configured_targets(config)
    run_id = f"external_publication_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    rows: list[dict[str, str]] = []
    unclassified: list[str] = []

    output_roots = sorted(path for path in (root / "outputs").iterdir() if path.is_dir())
    for output_root in output_roots:
        number = parse_notebook_number(output_root)
        if number is None:
            continue
        if exact_notebook is not None and number != exact_notebook:
            continue
        if exact_notebook is None and through_notebook is not None and number > through_notebook:
            continue
        for path in sorted(output_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            relative = path.relative_to(root).as_posix()
            group = image_group(relative)
            if group is None:
                # Canonical figures remain part of the compact Git publication.
                continue
            if group in candidate_groups:
                tier = "candidates"
            elif group in diagnostic_groups:
                tier = "diagnostics"
            else:
                unclassified.append(relative)
                continue
            target = targets[tier]
            rows.append(
                {
                    "publication_schema_version": SCHEMA_VERSION,
                    "publication_run_id": run_id,
                    "artifact_id": artifact_id(relative),
                    "producer_notebook": output_root.name,
                    "local_relative_path": relative,
                    "storage_tier": tier,
                    "provider": "huggingface_dataset",
                    "repository_id": target.repo_id,
                    "revision": target.revision,
                    "path_in_repository": relative,
                    "remote_uri": encoded_remote_uri(target.resolve_base_url, relative),
                    "sha256": "",
                    "size_bytes": str(path.stat().st_size),
                    "media_role": group,
                    "publication_status": "planned",
                    "publication_commit_url": "",
                    "published_at_utc": "",
                    "verification_status": "not_verified",
                    "verified_at_utc": "",
                    "verification_error": "",
                }
            )

    if unclassified and rules.get("unclassified_image_policy") == "block":
        preview = "\n".join(f"  - {value}" for value in unclassified[:20])
        raise RuntimeError(
            f"Found {len(unclassified)} unclassified image paths. Update the "
            f"controlled classification before planning:\n{preview}"
        )
    return rows


def deterministic_test_subset(
    rows: list[dict[str, str]], limit_per_tier: int
) -> list[dict[str, str]]:
    if limit_per_tier <= 0:
        return rows
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["storage_tier"]].append(row)
    selected: list[dict[str, str]] = []
    for tier in sorted(grouped):
        tier_rows = sorted(
            grouped[tier],
            key=lambda row: (int(row["size_bytes"]), row["local_relative_path"]),
        )
        if limit_per_tier == 1 or len(tier_rows) == 1:
            selected.append(tier_rows[-1])
            continue
        # Exercise both a small object and a large image during the guarded
        # smoke test instead of selecting adjacent alphabetical paths.
        indexes = {
            round(position * (len(tier_rows) - 1) / (limit_per_tier - 1))
            for position in range(limit_per_tier)
        }
        selected.extend(tier_rows[index] for index in sorted(indexes))
    return selected


def write_manifest(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in FIELDNAMES if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Manifest is missing required fields: {missing}")
        return [dict(row) for row in reader]


def command_plan(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    config_path = (root / args.config).resolve()
    config = load_yaml(config_path)
    rows = discover_rows(
        root,
        config,
        args.through_notebook,
        exact_notebook=args.notebook,
    )
    rows = deterministic_test_subset(rows, args.limit_per_tier)
    if args.require_test_limit and len(rows) > 10:
        raise RuntimeError(f"Test manifest contains {len(rows)} rows; maximum is 10.")
    if args.full_hash:
        for row in rows:
            row["sha256"] = sha256_file(root / row["local_relative_path"])
    manifest_path = (root / args.manifest).resolve()
    if args.merge_existing and manifest_path.is_file():
        existing = read_manifest(manifest_path)
        replaced_producers = {row["producer_notebook"] for row in rows}
        rows = [
            row
            for row in existing
            if row["producer_notebook"] not in replaced_producers
        ] + rows
        rows.sort(
            key=lambda row: (
                row["producer_notebook"],
                row["local_relative_path"],
            )
        )
    write_manifest(manifest_path, rows)
    total_bytes = sum(int(row["size_bytes"]) for row in rows)
    print(f"Publication plan: {manifest_path}")
    print(f"Rows: {len(rows)}")
    print(f"Bytes: {total_bytes}")
    print(f"Full SHA-256 recorded: {all(bool(row['sha256']) for row in rows)}")
    for tier, count in sorted(
        (tier, sum(row["storage_tier"] == tier for row in rows))
        for tier in {row["storage_tier"] for row in rows}
    ):
        print(f"{tier}: {count}")
    return 0


def command_upload_test(args: argparse.Namespace) -> int:
    if args.confirm != "UPLOAD_MAXIMUM_TEN_TEST_FILES":
        raise RuntimeError(
            "Refusing upload. Pass --confirm UPLOAD_MAXIMUM_TEN_TEST_FILES exactly."
        )
    root = find_project_root(Path.cwd())
    manifest_path = (root / args.manifest).resolve()
    rows = read_manifest(manifest_path)
    if not rows or len(rows) > 10:
        raise RuntimeError("A guarded test upload must contain between 1 and 10 rows.")
    if any(not row["sha256"] for row in rows):
        raise RuntimeError("Every test row must contain a full SHA-256 before upload.")
    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ImportError as exc:  # pragma: no cover - environment-specific message
        raise RuntimeError(
            "huggingface_hub is required. Install requirements_publication.txt first."
        ) from exc

    api = HfApi()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["repository_id"]].append(row)
    published_at = utc_now()
    for repo_id, repo_rows in grouped.items():
        operations = [
            CommitOperationAdd(
                path_in_repo=row["path_in_repository"],
                path_or_fileobj=str(root / row["local_relative_path"]),
            )
            for row in repo_rows
        ]
        info = api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message="Guarded external-publication smoke test",
        )
        commit_url = str(getattr(info, "commit_url", ""))
        for row in repo_rows:
            row["publication_status"] = "uploaded_unverified"
            row["publication_commit_url"] = commit_url
            row["published_at_utc"] = published_at
    write_manifest(manifest_path, rows)
    print(f"Uploaded {len(rows)} test files. Remote verification is still required.")
    return 0


def _selected_manifest_rows(
    rows: list[dict[str, str]],
    producer_notebook: str | None,
) -> list[dict[str, str]]:
    selected = (
        rows
        if producer_notebook is None
        else [
            row
            for row in rows
            if row["producer_notebook"] == producer_notebook
        ]
    )
    if not selected:
        label = producer_notebook or "the requested selection"
        raise RuntimeError(f"No publication rows found for {label!r}.")
    return selected


def command_upload(args: argparse.Namespace) -> int:
    """Publish one notebook's fully hashed rows in bounded resumable commits."""
    if args.confirm != "UPLOAD_VERIFIED_NOTEBOOK_ARTIFACTS":
        raise RuntimeError(
            "Refusing bulk upload. Pass --confirm "
            "UPLOAD_VERIFIED_NOTEBOOK_ARTIFACTS exactly."
        )
    chunk_size = int(args.chunk_size)
    if not 1 <= chunk_size <= 100:
        raise ValueError("chunk-size must be between 1 and 100")

    root = find_project_root(Path.cwd())
    manifest_path = (root / args.manifest).resolve()
    rows = read_manifest(manifest_path)
    selected = _selected_manifest_rows(rows, args.producer_notebook)
    producers = {row["producer_notebook"] for row in selected}
    if len(producers) != 1:
        raise RuntimeError("Bulk upload requires exactly one producer notebook.")
    if any(not row["sha256"] for row in selected):
        raise RuntimeError("Every selected row must contain a full SHA-256.")

    for row in selected:
        local = root / row["local_relative_path"]
        if not local.is_file():
            raise FileNotFoundError(local)
        if local.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError(f"Local byte count changed after planning: {local}")
        if sha256_file(local) != row["sha256"]:
            raise RuntimeError(f"Local SHA-256 changed after planning: {local}")

    pending = [
        row
        for row in selected
        if row["publication_status"] not in {
            "uploaded_unverified",
            "published_verified",
        }
    ]
    if not pending:
        verified = sum(
            row["publication_status"] == "published_verified"
            for row in selected
        )
        print(
            f"No upload-pending rows remain: {verified} verified and "
            f"{len(selected) - verified} awaiting remote verification."
        )
        return 0

    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ImportError as exc:  # pragma: no cover - environment-specific message
        raise RuntimeError(
            "huggingface_hub is required. Install requirements_publication.txt first."
        ) from exc

    api = HfApi()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pending:
        grouped[row["repository_id"]].append(row)

    completed = 0
    producer = next(iter(producers))
    for repo_id, repo_rows in sorted(grouped.items()):
        repo_rows.sort(key=lambda row: row["local_relative_path"])
        for start in range(0, len(repo_rows), chunk_size):
            chunk = repo_rows[start : start + chunk_size]
            operations = [
                CommitOperationAdd(
                    path_in_repo=row["path_in_repository"],
                    path_or_fileobj=str(root / row["local_relative_path"]),
                )
                for row in chunk
            ]
            info = api.create_commit(
                repo_id=repo_id,
                repo_type="dataset",
                operations=operations,
                commit_message=(
                    f"Publish {producer} artifacts "
                    f"{start + 1}-{start + len(chunk)}"
                ),
            )
            commit_url = str(getattr(info, "commit_url", ""))
            published_at = utc_now()
            for row in chunk:
                row["publication_status"] = "uploaded_unverified"
                row["publication_commit_url"] = commit_url
                row["published_at_utc"] = published_at
                row["verification_status"] = "not_verified"
                row["verified_at_utc"] = ""
                row["verification_error"] = ""
            write_manifest(manifest_path, rows)
            completed += len(chunk)
            print(
                f"Uploaded {completed}/{len(pending)} pending rows to {repo_id}; "
                "remote verification remains required."
            )
    return 0


def remote_sha256(uri: str, chunk_size: int = 4 * 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(uri, headers={"User-Agent": "painting-restoration-eval/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        while chunk := response.read(chunk_size):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def command_verify(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    manifest_path = (root / args.manifest).resolve()
    rows = read_manifest(manifest_path)
    selected = _selected_manifest_rows(rows, args.producer_notebook)
    failures = 0
    for index, row in enumerate(selected, start=1):
        try:
            remote_hash, remote_size = remote_sha256(row["remote_uri"])
            expected_size = int(row["size_bytes"])
            if remote_size != expected_size:
                raise ValueError(
                    f"byte mismatch: expected {expected_size}, received {remote_size}"
                )
            if remote_hash != row["sha256"]:
                raise ValueError(
                    f"SHA-256 mismatch: expected {row['sha256']}, received {remote_hash}"
                )
            row["publication_status"] = "published_verified"
            row["verification_status"] = "verified"
            row["verified_at_utc"] = utc_now()
            row["verification_error"] = ""
            print(f"[{index}/{len(selected)}] verified {row['local_relative_path']}")
        except Exception as exc:  # preserve every row and report the exact failure
            failures += 1
            row["verification_status"] = "failed"
            row["verified_at_utc"] = utc_now()
            row["verification_error"] = f"{type(exc).__name__}: {exc}"
            print(
                f"[{index}/{len(selected)}] FAILED "
                f"{row['local_relative_path']}: {exc}"
            )
    write_manifest(manifest_path, rows)
    print(f"Verification failures: {failures}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Create a local publication plan.")
    plan.add_argument(
        "--config",
        default="config/publication/external_storage.yaml",
    )
    plan.add_argument("--through-notebook", type=int, default=11)
    plan.add_argument(
        "--notebook",
        type=int,
        help="Plan only one numbered notebook output root.",
    )
    plan.add_argument(
        "--manifest",
        default="outputs/inventory/external_artifact_publication_test.csv",
    )
    plan.add_argument("--limit-per-tier", type=int, default=2)
    plan.add_argument("--full-hash", action="store_true")
    plan.add_argument("--require-test-limit", action="store_true")
    plan.add_argument(
        "--merge-existing",
        action="store_true",
        help="Preserve rows for other producer notebooks in the target manifest.",
    )
    plan.set_defaults(function=command_plan)

    upload = subparsers.add_parser(
        "upload-test", help="Upload at most ten fully hashed test files."
    )
    upload.add_argument(
        "--manifest",
        default="outputs/inventory/external_artifact_publication_test.csv",
    )
    upload.add_argument("--confirm", required=True)
    upload.set_defaults(function=command_upload_test)

    bulk = subparsers.add_parser(
        "upload",
        help="Upload one fully hashed producer notebook in bounded commits.",
    )
    bulk.add_argument(
        "--manifest",
        default="outputs/inventory/external_artifact_publication.csv",
    )
    bulk.add_argument("--producer-notebook", required=True)
    bulk.add_argument("--chunk-size", type=int, default=50)
    bulk.add_argument("--confirm", required=True)
    bulk.set_defaults(function=command_upload)

    verify = subparsers.add_parser(
        "verify", help="Download test files and verify size and SHA-256."
    )
    verify.add_argument(
        "--manifest",
        default="outputs/inventory/external_artifact_publication_test.csv",
    )
    verify.add_argument("--producer-notebook")
    verify.set_defaults(function=command_verify)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.function(args))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
