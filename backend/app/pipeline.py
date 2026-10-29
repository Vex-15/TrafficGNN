"""Analysis pipeline: raw evidence -> structured records -> validation."""

from pathlib import Path

from .schema import CATEGORIES, category_label
from .store import project_dir
from .validation import build_record, record_summary, run_validation


def _evidence_url(project_id: str, raw: dict):
    path = raw.get("image_path")
    if not path:
        return None
    name = Path(path).name
    return f"/api/projects/{project_id}/evidence/{name}"


def summarize(project: dict) -> dict:
    records = [r for r in project.get("records", []) if not r.get("duplicate_of")]
    by_category = {}
    for record in records:
        key = record["category"]
        by_category[key] = by_category.get(key, 0) + 1

    sections = (project.get("template") or {}).get("analysis", {}).get("sections", [])
    mapped = [s for s in sections if s.get("category")]
    covered = {r["category"] for r in records}

    return {
        "sources": len(project.get("sources", [])),
        "records": len(records),
        "images": len([r for r in records if r.get("image_url")]),
        "by_category": [
            {
                "category": cat,
                "label": category_label(cat),
                "count": by_category.get(cat, 0),
            }
            for cat in CATEGORIES
        ],
        "unclassified": by_category.get("unclassified", 0),
        "mapped_sections": len(mapped),
        "covered_sections": len([s for s in mapped if s["category"] in covered]),
        "pending_review": len([r for r in records if not r.get("approved")]),
    }


def analyze_project(project: dict):
    sections = ((project.get("template") or {}).get("analysis") or {}).get("sections", [])
    records = []
    for source in project.get("sources", []):
        for raw in source.get("records", []):
            record = build_record(raw, sections)
            record["image_url"] = _evidence_url(project["id"], raw)
            record["display"] = record_summary(record)
            records.append(record)

    project["records"] = records
    project["validation"] = run_validation(records, sections)
    project["summary"] = summarize(project)
    project["stage"] = "review" if records else "sources"
    return project
