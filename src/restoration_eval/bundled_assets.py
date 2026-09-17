"""Byte-exact, indexed ZIP transport for published diagnostic images.

This module has no notebook, Streamlit, or Hugging Face client dependency.
Scientific producer outputs are read but never changed.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

SCHEMA = "bundle_assets.v1"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
MAX_BUNDLE_BYTES = 32 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> str:
    if not value or "\\" in value or "\x00" in value or ":" in value:
        raise ValueError(f"Unsafe archive path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"Unsafe archive path: {value!r}")
    return value


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, sort_keys=True, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(temp, path)


def json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def verify_source(asset: dict, root: Path) -> Path:
    relative = safe_relative(asset["original_relative_path"])
    source = (root / relative).resolve()
    if not source.is_relative_to(root.resolve()) or not source.is_file():
        raise ValueError(f"Missing or escaped source: {relative}")
    if source.stat().st_size != int(asset["size_bytes"]):
        raise ValueError(f"Source size changed: {relative}")
    if sha256_file(source) != asset["sha256"]:
        raise ValueError(f"Source SHA-256 changed: {relative}")
    return source


def _zip_info(member: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(safe_relative(member), date_time=ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits = 0
    return info


def build_bundle(assets: list[dict], root: Path, destination: Path,
                 max_bytes: int = MAX_BUNDLE_BYTES) -> dict:
    if not assets:
        raise ValueError("Empty bundle")
    ordered = sorted(assets, key=lambda row: row["original_relative_path"])
    names = [safe_relative(row["original_relative_path"]) for row in ordered]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate archive member")
    if destination.exists():
        for row in ordered:
            verify_source(row, root)
        if destination.stat().st_size > max_bytes:
            raise ValueError(f"Existing bundle exceeds {max_bytes} bytes: {destination}")
        verify_bundle(destination, ordered)
        return {
            "path": destination.as_posix(), "size_bytes": destination.stat().st_size,
            "sha256": sha256_file(destination), "member_count": len(ordered),
        }
    sources = []
    for row in ordered:
        source = (root / row["original_relative_path"]).resolve()
        if not source.is_relative_to(root.resolve()) or not source.is_file():
            raise ValueError(f"Missing or escaped source: {row['original_relative_path']}")
        if source.stat().st_size != int(row["size_bytes"]):
            raise ValueError(f"Source size changed: {row['original_relative_path']}")
        sources.append((row, source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".tmp")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_STORED,
                             allowZip64=True) as archive:
            for row, source in sources:
                # A streaming write prevents holding full source images in RAM.
                with source.open("rb") as src, archive.open(
                    _zip_info(row["original_relative_path"]), "w"
                ) as target:
                    digest = hashlib.sha256()
                    copied = 0
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        target.write(chunk)
                        digest.update(chunk)
                        copied += len(chunk)
                if copied != int(row["size_bytes"]) or digest.hexdigest() != row["sha256"]:
                    raise ValueError(f"Source SHA-256 changed: {row['original_relative_path']}")
        if temp.stat().st_size > max_bytes:
            raise ValueError(f"Bundle exceeds {max_bytes} bytes: {destination}")
        verify_bundle(temp, ordered)
        if destination.exists():
            if sha256_file(destination) != sha256_file(temp):
                raise ValueError(f"Immutable bundle differs: {destination}")
            temp.unlink()
        else:
            os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "path": destination.as_posix(), "size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination), "member_count": len(ordered),
    }


def verify_bundle(path: Path, assets: list[dict]) -> None:
    expected = {row["original_relative_path"]: row for row in assets}
    if len(expected) != len(assets):
        raise ValueError("Duplicate expected members")
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [safe_relative(info.filename) for info in infos]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Bundle member set differs from manifest")
        for info in infos:
            if info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1:
                raise ValueError(f"Compressed or encrypted member: {info.filename}")
            row = expected[info.filename]
            if info.file_size != int(row["size_bytes"]):
                raise ValueError(f"Member size differs: {info.filename}")
            digest = hashlib.sha256()
            count = 0
            with archive.open(info, "r") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(chunk)
                    digest.update(chunk)
            if count != int(row["size_bytes"]) or digest.hexdigest() != row["sha256"]:
                raise ValueError(f"Member SHA-256 differs: {info.filename}")


def split_by_size(assets: list[dict], max_bytes: int = MAX_BUNDLE_BYTES) -> list[list[dict]]:
    """Conservative size partition; final ZIP size is still checked exactly."""
    parts: list[list[dict]] = []
    current: list[dict] = []
    used = 64 * 1024
    for row in sorted(assets, key=lambda x: x["original_relative_path"]):
        # ZIP headers/central directory and UTF-8 paths are covered generously.
        cost = int(row["size_bytes"]) + 4096 + 4 * len(row["original_relative_path"].encode("utf-8"))
        if cost + 64 * 1024 > max_bytes:
            raise ValueError(f"One asset cannot fit the bundle cap: {row['original_relative_path']}")
        if current and used + cost > max_bytes:
            parts.append(current)
            current, used = [], 64 * 1024
        current.append(row)
        used += cost
    if current:
        parts.append(current)
    return parts


class RemoteBundleReader:
    """Public, pinned-revision reader; no local-source fallback exists."""

    def __init__(self, repo_id: str, revision: str, prefix: str, cache_dir: Path,
                 max_cache_bytes: int = 512 * 1024 * 1024,
                 fetcher: Callable[[str, Path], None] | None = None):
        if not revision or revision == "main" or not prefix:
            raise ValueError("An immutable revision and prefix are required")
        self.repo_id = repo_id
        self.revision = revision
        self.prefix = safe_relative(prefix.rstrip("/"))
        self.cache_dir = cache_dir
        self.max_cache_bytes = max_cache_bytes
        self.fetcher = fetcher or self._public_fetch
        self.download_count = 0
        self.download_bytes = 0
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _url(self, path: str) -> str:
        safe_relative(path)
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        return f"https://huggingface.co/datasets/{self.repo_id}/resolve/{self.revision}/{encoded}"

    @staticmethod
    def _public_fetch(url: str, destination: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "painting-eval-bundle-reader/1"})
        with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output, 1024 * 1024)

    def _cache_path(self, path: str) -> Path:
        key = sha256_bytes(f"{self.repo_id}\n{self.revision}\n{path}".encode("utf-8"))
        return self.cache_dir / key

    def _download(self, path: str, expected_sha: str | None = None,
                  expected_size: int | None = None) -> Path:
        safe_relative(path)
        target = self._cache_path(path)
        if target.exists():
            if (expected_size is None or target.stat().st_size == expected_size) and (
                expected_sha is None or sha256_file(target) == expected_sha
            ):
                os.utime(target, None)
                return target
            target.unlink()
        lock = target.with_suffix(".lock")
        acquired = False
        for _ in range(600):
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(descriptor)
                acquired = True
                break
            except FileExistsError:
                if target.exists() and (expected_sha is None or sha256_file(target) == expected_sha):
                    return target
                time.sleep(0.1)
        if not acquired:
            raise TimeoutError(f"Cache lock remained busy for {path}")
        temp = target.with_suffix(".partial")
        try:
            if target.exists():
                return target
            self.fetcher(self._url(path), temp)
            size = temp.stat().st_size
            if expected_size is not None and size != expected_size:
                raise ValueError(f"Remote size differs: {path}")
            if expected_sha is not None and sha256_file(temp) != expected_sha:
                raise ValueError(f"Remote SHA-256 differs: {path}")
            os.replace(temp, target)
            self.download_count += 1
            self.download_bytes += size
            self._evict(protected=target)
            return target
        finally:
            if temp.exists():
                temp.unlink()
            lock.unlink(missing_ok=True)

    def _evict(self, protected: Path) -> None:
        files = [p for p in self.cache_dir.iterdir() if p.is_file() and len(p.name) == 64]
        used = sum(p.stat().st_size for p in files)
        for path in sorted(files, key=lambda p: p.stat().st_mtime):
            if used <= self.max_cache_bytes:
                break
            if path != protected and not path.with_suffix(".lock").exists():
                used -= path.stat().st_size
                path.unlink()

    def catalogue(self) -> dict:
        path = self._download(f"{self.prefix}/indexes/catalogue.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA:
            raise ValueError("Unknown catalogue schema")
        return payload

    def painting(self, painting_id: str, catalogue: dict) -> dict:
        if painting_id not in catalogue["paintings"]:
            raise KeyError(painting_id)
        entry = catalogue["paintings"][painting_id]
        path = self._download(entry["path"], entry["sha256"], entry["size_bytes"])
        return json.loads(path.read_text(encoding="utf-8"))

    def read_asset(self, painting_id: str, asset_id: str) -> tuple[bytes, dict]:
        catalogue = self.catalogue()
        painting = self.painting(painting_id, catalogue)
        matches = [row for row in painting["assets"] if row["asset_id"] == asset_id]
        if len(matches) != 1:
            raise KeyError(asset_id)
        row = matches[0]
        bundle = catalogue["bundles"][row["bundle_path"]]
        zip_path = self._download(row["bundle_path"], bundle["sha256"], bundle["size_bytes"])
        member = safe_relative(row["member_path"])
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = archive.infolist()
            names = [safe_relative(info.filename) for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate members in remote bundle")
            info = archive.getinfo(member)
            if info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1:
                raise ValueError("Unexpected compression/encryption")
            if info.file_size != row["size_bytes"]:
                raise ValueError("Indexed member size differs")
            data = archive.read(info)
        if len(data) != row["size_bytes"] or sha256_bytes(data) != row["sha256"]:
            raise ValueError("Indexed member SHA-256 differs")
        return data, row
