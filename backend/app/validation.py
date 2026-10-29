"""Validation engine: confidence tiers, duplicate detection, conflicts, gaps."""

import uuid

from .extract import looks_similar
from .schema import CATEGORIES, REQUIRED_FIELDS, category_label
from .util import clean, format_range, similarity

AUTO_THRESHOLD = 0.9
REVIEW_THRESHOLD = 0.75


def status_for(confidence: float, category) -> str:
    if not category:
        return "unverified"
    if confidence >= AUTO_THRESHOLD:
        return "auto"
    if confidence >= REVIEW_THRESHOLD:
        return "review"
    return "manual"


def build_record(raw: dict, sections: list) -> dict:
    category = raw.get("category")
    fields = {k: clean(v) for k, v in raw.get("fields", {}).items() if clean(v)}
    confidence = float(raw.get("confidence") or 0.6)
    section = next((s for s in sections if s.get("category") == category), None)
    status = status_for(confidence, category)
    record = {
        "id": f"rec_{uuid.uuid4().hex[:10]}",
        "category": category or "unclassified",
        "category_label": category_label(category) if category else "Unclassified",
        "fields": fields,
        "source": {
            "file": raw.get("source_file", "unknown"),
            "locator": raw.get("locator", ""),
            "kind": raw.get("kind", "text"),
        },
        "confidence": round(confidence, 2),
        "status": status,
        "approved": status == "auto",
        "duplicate_of": None,
        "conflict": None,
        "section_id": section["id"] if section else None,
        "image_url": f"/api/evidence/{raw['image_path'].split('media')[-1].lstrip('/\\\\')}"
        if raw.get("image_path")
        else None,
        "image_path": raw.get("image_path"),
        "edited": False,
    }
    return record


def record_title(record: dict) -> str:
    fields = record.get("fields", {})
    return fields.get("title") or fields.get("caption") or "Untitled record"


def detect_duplicates(records: list):
    duplicates = []
    for i, a in enumerate(records):
        if a.get("duplicate_of"):
            continue
        for b in records[i + 1 :]:
            if b.get("duplicate_of"):
                continue
            if a["category"] != b["category"]:
                continue
            score = looks_similar(a, b)
            date_a = a["fields"].get("start_date") or a["fields"].get("date")
            date_b = b["fields"].get("start_date") or b["fields"].get("date")
            if date_a and date_b:
                score = max(score, similarity(a["fields"].get("title", ""), b["fields"].get("title", "")))
                if date_a == date_b:
                    score = min(1.0, score + 0.08)
            if score >= 0.82:
                b["duplicate_of"] = a["id"]
                b["approved"] = False
                b["status"] = "duplicate"
                duplicates.append(
                    {
                        "id": f"dup_{uuid.uuid4().hex[:8]}",
                        "record_ids": [a["id"], b["id"]],
                        "title": record_title(a),
                        "sources": [a["source"]["file"], b["source"]["file"]],
                        "reason": f"{round(min(1.0, score) * 100)}% title/entity similarity within {category_label(a['category'])}",
                    }
                )
                break
    return duplicates


def detect_conflicts(records: list):
    conflicts = []
    compared = set()
    for i, a in enumerate(records):
        if a.get("duplicate_of"):
            continue
        for b in records[i + 1 :]:
            if b.get("duplicate_of") or a["category"] != b["category"]:
                continue
            pair = tuple(sorted([a["id"], b["id"]]))
            if pair in compared:
                continue
            compared.add(pair)
            base = similarity(a["fields"].get("title", ""), b["fields"].get("title", ""))
            if base < 0.6:
                continue
            spec = CATEGORIES.get(a["category"], {})
            for field in spec.get("critical", []):
                va, vb = clean(a["fields"].get(field)), clean(b["fields"].get(field))
                if not va or not vb or va == vb:
                    continue
                if field in ("start_date", "date") and va[:4] == vb[:4]:
                    pass
                conflicts.append(
                    {
                        "id": f"cnf_{uuid.uuid4().hex[:8]}",
                        "record_ids": [a["id"], b["id"]],
                        "title": record_title(a),
                        "field": field,
                        "values": [
                            {"record_id": a["id"], "value": va, "source": a["source"]["file"]},
                            {"record_id": b["id"], "value": vb, "source": b["source"]["file"]},
                        ],
                        "reason": f"Conflicting '{field}' for the same activity",
                    }
                )
                break
    return conflicts


def detect_missing(records: list, sections: list):
    missing = []
    for section in sections:
        if not section.get("category"):
            continue
        matching = [r for r in records if r["category"] == section["category"]]
        if not matching:
            missing.append(
                {
                    "id": f"mis_{uuid.uuid4().hex[:8]}",
                    "type": "section",
                    "section_id": section["id"],
                    "title": section["title"],
                    "detail": "No source evidence was found for this template section.",
                    "field": None,
                    "record_id": None,
                }
            )
    for record in records:
        if record.get("duplicate_of"):
            continue
        for field in REQUIRED_FIELDS.get(record["category"], []):
            if record["fields"].get(field):
                continue
            missing.append(
                {
                    "id": f"mis_{uuid.uuid4().hex[:8]}",
                    "type": "field",
                    "section_id": record.get("section_id"),
                    "title": record_title(record),
                    "detail": f"Required field '{field}' has no evidence in {record['source']['file']}.",
                    "field": field,
                    "record_id": record["id"],
                }
            )
    return missing


def run_validation(records: list, sections: list):
    duplicates = detect_duplicates(records)
    conflicts = detect_conflicts(records)
    missing = detect_missing(records, sections)

    conflict_ids = {rid for c in conflicts for rid in c["record_ids"]}
    for record in records:
        record["conflict"] = record["id"] in conflict_ids
        if record["conflict"] and record["status"] != "duplicate":
            record["status"] = "conflict"
            record["approved"] = False

    return {
        "duplicates": duplicates,
        "conflicts": conflicts,
        "missing": missing,
        "stats": {
            "records": len([r for r in records if not r.get("duplicate_of")]),
            "duplicates": len(duplicates),
            "conflicts": len(conflicts),
            "missing_fields": len([m for m in missing if m["type"] == "field"]),
            "missing_sections": len([m for m in missing if m["type"] == "section"]),
        },
    }


def record_summary(record: dict) -> dict:
    fields = record["fields"]
    date = format_range(fields.get("start_date"), fields.get("end_date")) or fields.get("date", "")
    secondary = " · ".join(
        part
        for part in [
            fields.get("faculty_name") or fields.get("student_name") or fields.get("resource_person"),
            fields.get("organizer") or fields.get("journal") or fields.get("conference"),
            date,
            f"{fields.get('participants')} participants" if fields.get("participants") else "",
        ]
        if part
    )
    return {"primary": record_title(record), "secondary": secondary}
