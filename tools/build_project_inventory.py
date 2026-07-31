from __future__ import annotations

import argparse
import csv
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
CSV_EXTENSIONS = {".csv", ".tsv"}
SKIP_DIRS = {
    ".git",
    ".ipynb_checkpoints",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


def classify_file(path: Path) -> str:
    text = str(path).lower()
    suffix = path.suffix.lower()

    if suffix in CSV_EXTENSIONS:
        if "manifest" in text:
            return "manifest_csv"
        if "validation" in text:
            return "validation_csv"
        if "metric" in text or "lpips" in text or "similarity" in text:
            return "metric_csv"
        if "summary" in text:
            return "summary_csv"
        return "csv"

    if suffix in IMAGE_EXTENSIONS:
        if "mask" in text:
            return "mask_image"
        if "clean" in text or "original" in text:
            return "clean_image"
        if "damaged" in text or "degraded" in text or "degradation" in text:
            return "damaged_image"
        if "restored" in text or "opencv" in text or "lama" in text or "sdxl" in text:
            return "restored_image"
        if "figure" in text or "plot" in text or "report" in text or "contact_sheet" in text:
            return "figure_image"
        return "image"

    if suffix == ".ipynb":
        return "notebook"

    if suffix in {".json", ".md", ".html", ".txt"}:
        return suffix.lstrip(".")

    return "other"


def count_csv_rows_and_columns(path: Path, delimiter: str | None = None) -> tuple[int | None, list[str], str]:
    try:
        if delimiter is None:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","

        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)

        return row_count, header, ""
    except Exception as exc:
        return None, [], repr(exc)


def image_metadata(path: Path) -> tuple[int | None, int | None, str, str]:
    if Image is None:
        return None, None, "", "Pillow not installed"

    try:
        with Image.open(path) as img:
            return img.width, img.height, img.mode, ""
    except Exception as exc:
        return None, None, "", repr(exc)


def small_hash(path: Path, bytes_to_read: int = 1024 * 1024) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            h.update(f.read(bytes_to_read))
        return h.hexdigest()
    except Exception:
        return ""


def iter_files(root: Path):
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            yield Path(current_root) / filename


def build_inventory(root: Path, out_dir: Path) -> None:
    root = root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    file_rows = []

    for path in sorted(iter_files(root)):
        try:
            rel_path = path.relative_to(root).as_posix()
        except ValueError:
            rel_path = str(path)

        stat = path.stat()
        suffix = path.suffix.lower()
        file_kind = classify_file(path)

        csv_row_count = None
        csv_columns = []
        csv_error = ""

        image_width = None
        image_height = None
        image_mode = ""
        image_error = ""

        if suffix in CSV_EXTENSIONS:
            csv_row_count, csv_columns, csv_error = count_csv_rows_and_columns(path)

        if suffix in IMAGE_EXTENSIONS:
            image_width, image_height, image_mode, image_error = image_metadata(path)

        file_rows.append(
            {
                "relative_path": rel_path,
                "file_name": path.name,
                "parent_dir": path.parent.relative_to(root).as_posix() if path.parent != root else "",
                "extension": suffix,
                "file_kind": file_kind,
                "size_bytes": stat.st_size,
                "last_modified_iso": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "depth": len(Path(rel_path).parts) - 1,
                "csv_row_count": csv_row_count if csv_row_count is not None else "",
                "csv_column_count": len(csv_columns) if csv_columns else "",
                "csv_columns": " | ".join(csv_columns),
                "csv_error": csv_error,
                "image_width": image_width if image_width is not None else "",
                "image_height": image_height if image_height is not None else "",
                "image_mode": image_mode,
                "image_error": image_error,
                "sha256_first_1mb": small_hash(path),
            }
        )

    inventory_path = out_dir / "project_file_inventory.csv"
    summary_path = out_dir / "project_file_inventory_summary.csv"

    with inventory_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(file_rows[0].keys()) if file_rows else [])
        writer.writeheader()
        writer.writerows(file_rows)

    summary = {}
    for row in file_rows:
        key = row["file_kind"]
        summary.setdefault(key, {"file_kind": key, "file_count": 0, "total_size_bytes": 0})
        summary[key]["file_count"] += 1
        summary[key]["total_size_bytes"] += int(row["size_bytes"])

    with summary_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["file_kind", "file_count", "total_size_bytes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(summary.values(), key=lambda x: x["file_kind"]))

    print(f"Saved inventory: {inventory_path}")
    print(f"Saved summary:   {summary_path}")
    print(f"Files indexed:   {len(file_rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root to scan")
    parser.add_argument("--out-dir", default="outputs/inventory", help="Directory for inventory CSVs")
    args = parser.parse_args()

    build_inventory(Path(args.root), Path(args.out_dir))