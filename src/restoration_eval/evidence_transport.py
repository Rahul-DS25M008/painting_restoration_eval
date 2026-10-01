"""Lazy, byte-verified deployment reads. No scientific computation or identity fallback.

Only explicitly registered immutable public objects may be fetched. Importing this
module does not create a cache, read a catalogue, or make a network request.
"""
from __future__ import annotations

from contextlib import contextmanager
from collections import OrderedDict
from functools import wraps
from functools import lru_cache
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

from .bundled_assets import safe_relative

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "streamlit_assets/evidence/deployment"
MIB = 1024 * 1024
REQUESTS = threading.BoundedSemaphore(2)
BUNDLES = threading.BoundedSemaphore(1)


def image_cache(function):
    """Bound encoded image memory by bytes as well as entries, across room calls."""
    cache = OrderedDict()
    lock = threading.RLock()
    @wraps(function)
    def wrapped(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        with lock:
            if key in cache:
                cache.move_to_end(key)
                return cache[key]
        value = function(*args, **kwargs)
        with lock:
            if len(value) <= 64 * MIB:
                cache[key] = value
                while len(cache) > 16 or sum(map(len, cache.values())) > 64 * MIB:
                    cache.popitem(last=False)
        return value
    def clear():
        with lock: cache.clear()
    wrapped.cache_clear = clear
    wrapped.cache_bytes = lambda: sum(map(len, cache.values()))
    return wrapped


@contextmanager
def capacity(semaphore, deadline):
    if not semaphore.acquire(timeout=max(0, deadline - time.monotonic())):
        raise EvidenceUnavailable("Evidence loader is busy; please retry")
    try: yield
    finally: semaphore.release()


class EvidenceUnavailable(ValueError):
    """A safe, user-visible failure; never replace evidence with a different ID."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(raw, meta):
    if len(raw) != int(meta["size_bytes"]) or digest(raw) != meta["sha256"]:
        raise EvidenceUnavailable("Saved evidence failed its size/checksum check; no substitute used")
    return raw


@lru_cache(maxsize=1)
def manifest():
    return json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def partition(name):
    safe_relative(name)
    meta = manifest()["files"][name]
    raw = checked((INDEX / name).read_bytes(), meta)
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded = stream.read(16 * MIB + 1)
    if len(decoded) > 16 * MIB:
        raise EvidenceUnavailable("Deployment index exceeds its bounded size")
    return json.loads(decoded)


def routes(relative):
    safe_relative(relative)
    name = "routes/" + digest(relative.encode())[:2] + ".json.gz"
    return partition(name).get(relative, [])


def available(relative):
    return (ROOT / safe_relative(relative)).is_file() or bool(routes(relative))


class Reader:
    def __init__(self, cache=None, opener=None, max_cache=512 * MIB, low_water=384 * MIB):
        self.cache = Path(cache or os.environ.get("PAINTING_EVIDENCE_CACHE", Path(tempfile.gettempdir()) / "painting-evidence-v1"))
        self.opener = opener or urlopen
        self.max_cache, self.low_water = max_cache, min(low_water, max_cache)
        self.request_count = self.downloaded_bytes = 0

    @staticmethod
    def url(route):
        if not re.fullmatch(r"[0-9a-f]{40}", route["revision"]):
            raise EvidenceUnavailable("Evidence requires a full immutable revision")
        if route["repo"] not in {"RahulMaddineni264/painting-restoration-eval-candidates", "RahulMaddineni264/painting-restoration-eval-diagnostics"}:
            raise EvidenceUnavailable("Unregistered evidence repository")
        path = safe_relative(route["path"])
        return f'https://huggingface.co/datasets/{route["repo"]}/resolve/{route["revision"]}/' + quote(path, safe="/")

    @contextmanager
    def lock(self, target, deadline):
        lock = target.with_suffix(".lock")
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                try:
                    if time.time() - lock.stat().st_mtime > 120:
                        lock.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise EvidenceUnavailable("Evidence cache is busy; please retry")
                time.sleep(.05)
        try:
            yield
        finally:
            lock.unlink(missing_ok=True)

    def evict(self, protected):
        files = [p for p in self.cache.iterdir() if re.fullmatch(r"[0-9a-f]{64}", p.name)]
        total = sum(p.stat().st_size for p in files)
        if total <= self.max_cache:
            return
        for path in sorted(files, key=lambda p: p.stat().st_mtime):
            if total <= self.low_water:
                break
            if path != protected and not path.with_suffix(".lock").exists():
                total -= path.stat().st_size
                path.unlink(missing_ok=True)

    def object(self, route, *, bundle=False, deadline=None):
        deadline = deadline or time.monotonic() + 60
        url = self.url(route)
        cap = (32 if bundle else 4) * MIB
        size = int(route["size_bytes"])
        if not 0 <= size <= cap or not re.fullmatch(r"[0-9a-f]{64}", route["sha256"]):
            raise EvidenceUnavailable("Evidence exceeds the bounded download size")
        self.cache.mkdir(parents=True, exist_ok=True)
        target = self.cache / digest(url.encode())
        with self.lock(target, deadline):
            if target.exists():
                try:
                    checked(target.read_bytes(), route)
                    os.utime(target, None)
                    return target
                except EvidenceUnavailable:
                    target.unlink()
            temp = target.with_suffix(".partial")
            temp.unlink(missing_ok=True)
            try:
                for attempt in range(2):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise EvidenceUnavailable("Evidence load timed out; please retry")
                    try:
                        with capacity(REQUESTS, deadline):
                            self.request_count += 1
                            request = Request(url, headers={"User-Agent": "painting-evidence/1"})
                            with self.opener(request, timeout=min(5, remaining)) as response, temp.open("wb") as output:
                                count = 0
                                while True:
                                    if time.monotonic() >= deadline:
                                        raise TimeoutError("Evidence deadline exceeded")
                                    data = response.read(min(65536, size + 1 - count))
                                    if not data:
                                        break
                                    count += len(data)
                                    self.downloaded_bytes += len(data)
                                    if count > size:
                                        raise EvidenceUnavailable("Remote evidence size mismatch")
                                    output.write(data)
                        checked(temp.read_bytes(), route)
                        os.replace(temp, target)
                        self.evict(target)
                        return target
                    except HTTPError as exc:
                        if exc.code not in (408, 429, 500, 502, 503, 504) or attempt:
                            raise EvidenceUnavailable(f"Saved evidence unavailable (HTTP {exc.code}); no substitute used") from None
                        delay = min(float(exc.headers.get("Retry-After", "1")) if exc.headers.get("Retry-After", "1").isdigit() else 1, 3)
                    except (TimeoutError, URLError, OSError):
                        if attempt:
                            raise EvidenceUnavailable("Evidence is not cached and could not be reached; please retry") from None
                        delay = .25
                    time.sleep(min(delay, max(0, deadline - time.monotonic())))
            finally:
                temp.unlink(missing_ok=True)

    def read(self, route):
        if "member_path" not in route:
            return self.object(route).read_bytes()
        deadline = time.monotonic() + 60
        with capacity(BUNDLES, deadline):
            path = self.object({**route, **route["bundle"]}, bundle=True, deadline=deadline)
            try:
                with zipfile.ZipFile(path) as archive:
                    name = safe_relative(route["member_path"])
                    matches = [i for i in archive.infolist() if i.filename == name]
                    if len(matches) != 1:
                        raise EvidenceUnavailable("Exact bundle member is missing or ambiguous")
                    info = matches[0]
                    if info.file_size != route["size_bytes"] or info.file_size > 8 * MIB or info.flag_bits & 1 or info.compress_type != zipfile.ZIP_STORED:
                        raise EvidenceUnavailable("Invalid evidence bundle member")
                    return checked(archive.read(info), route)
            except (zipfile.BadZipFile, KeyError):
                raise EvidenceUnavailable("Saved evidence bundle is invalid; no substitute used") from None


READER = Reader()


def read_bytes(path, expected_hash=None, expected_size=None, *, root=ROOT):
    path = Path(path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise EvidenceUnavailable("Evidence path escapes the project")
    relative = path.relative_to(root).as_posix()
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        matches = [r for r in routes(relative) if not expected_hash or r["sha256"] == expected_hash]
        if not matches:
            raise EvidenceUnavailable("Exact saved evidence is unavailable; no substitute used") from None
        raw = READER.read(matches[0])
    if expected_hash and digest(raw) != expected_hash:
        # Git text checkout may change only newlines. Accept ONLY a byte-exact
        # reconstruction of the recorded checksum, never a normalized checksum.
        lf = raw.replace(b"\r\n", b"\n")
        variants = (lf, lf.replace(b"\n", b"\r\n")) if path.suffix in {".csv", ".json", ".html", ".md", ".yaml"} else ()
        raw = next((r for r in variants if digest(r) == expected_hash), raw)
        if digest(raw) != expected_hash:
            raise EvidenceUnavailable("Saved evidence checksum mismatch; no substitute used")
    if expected_size is not None and len(raw) != expected_size:
        raise EvidenceUnavailable("Saved evidence size mismatch; no substitute used")
    return raw


def verified_path(path, expected_hash, expected_size=None):
    """Path adapter for existing CSV/report consumers, including Git text bytes."""
    path = Path(path)
    raw = read_bytes(path, expected_hash, expected_size)
    if path.is_file() and digest(path.read_bytes()) == expected_hash:
        return path
    READER.cache.mkdir(parents=True, exist_ok=True)
    target = READER.cache / expected_hash
    with READER.lock(target, time.monotonic() + 60):
        if not target.is_file() or digest(target.read_bytes()) != expected_hash:
            temp = target.with_suffix(".partial")
            temp.write_bytes(raw)
            os.replace(temp, target)
            READER.evict(target)
    return target


def table(name, **kwargs):
    """Read a checksum-pinned compact CSV; never scan a producer table at runtime."""
    import pandas as pd
    safe_relative(name)
    entry = manifest()["files"][name]
    raw = checked((INDEX / name).read_bytes(), entry)
    return pd.read_csv(io.BytesIO(raw), compression="gzip", **kwargs)
