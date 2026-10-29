"""Shared ingestion helper used by both the upload API and the demo seeder."""

import shutil
import uuid
from pathlib import Path

from .extract import copy_evidence, extract_file
from .store import project_dir, save

SOURCE_EXTENSIONS = {".docx", ".xlsx", ".xlsm", ".csv", ".pdf", ".txt", ".md"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_EXTENSIONS = SOURCE_EXTENSIONS | IMAGE_EXTENSIONS


def ingest_file(project: dict, uploaded_path: Path, filename: str) -> dict:
    directory = project_dir(project["id"])
    ext = Path(filename).suffix.lower()
    target = directory / "sources" / f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(uploaded_path, target)

    source = {
        "id": f"src_{uuid.uuid4().hex[:8]}",
        "filename": Path(filename).name,
        "ext": ext,
        "size": target.stat().st_size,
        "kind": "image" if ext in IMAGE_EXTENSIONS else "document",
        "status": "processed",
        "error": None,
        "record_count": 0,
        "detected_category": None,
        "path": str(target),
        "records": [],
    }

    try:
        media_dir = directory / "media"
        raw_records = extract_file(target, source["filename"], media_dir)
        for raw in raw_records:
            if raw.get("image_path"):
                raw["image_path"] = copy_evidence(target, media_dir, source["filename"])
        source["records"] = raw_records
        source["record_count"] = len(raw_records)
        categories = [r["category"] for r in raw_records if r.get("category")]
        if categories:
            source["detected_category"] = max(set(categories), key=categories.count)
        if not raw_records:
            source["status"] = "no-data"
    except Exception as exc:  # keep bad files from breaking the whole batch
        source["status"] = "error"
        source["error"] = f"{type(exc).__name__}: {exc}"

    project.setdefault("sources", []).append(source)
    save(project)
    return source
