"""Document ingestion + heuristic extraction.

The prototype deliberately keeps extraction explainable: every record carries
the source file, a locator (page / sheet row / paragraph) and a confidence
score.  Structured files are read natively (DOCX, XLSX, CSV, PDF text) and
images are kept as evidence records.  An LLM can later replace the heuristics
without changing the shape of the data layer.
"""

import csv
import io
import os
import re
import shutil
import uuid
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from .schema import CATEGORIES, FIELD_SYNONYMS, IMAGE_EXTENSIONS
from .util import (
    clean,
    initials_name,
    parse_date,
    parse_date_range,
    parse_number,
    similarity,
)

MAX_TEXT = 8000
LABEL_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /&().'-]{1,42})\s*[:\-\u2013]\s*(.+)$")

_SYNONYM_LOOKUP = {}
for _field, _words in FIELD_SYNONYMS.items():
    for _w in _words:
        _SYNONYM_LOOKUP[_w] = _field


def map_header(text: str):
    key = re.sub(r"[^a-z0-9 /.]", " ", (text or "").lower())
    key = re.sub(r"\s+", " ", key).strip()
    if not key:
        return None
    if key in _SYNONYM_LOOKUP:
        return _SYNONYM_LOOKUP[key]
    for synonym in sorted(_SYNONYM_LOOKUP, key=len, reverse=True):
        if synonym in key:
            return _SYNONYM_LOOKUP[synonym]
    return None


def classify(text: str, filename: str):
    """Keyword + filename scoring across the six supported categories."""
    blob = f"{filename} {text[:MAX_TEXT]}".lower().replace("_", " ").replace("-", " ")
    name_blob = filename.lower().replace("_", " ").replace("-", " ")

    best, best_score = None, 0.0
    for cat, spec in CATEGORIES.items():
        score = 0.0
        for kw in spec["keywords"]:
            if kw in name_blob:
                score += 3.0
            score += min(blob.count(kw), 4) * 0.6
        if score > best_score:
            best, best_score = cat, score

    if not best:
        return None, 0.0
    confidence = min(0.95, 0.55 + best_score * 0.05)
    return best, round(confidence, 2)


def _normalise_fields(raw: dict, category: str, text: str) -> dict:
    fields = {}
    for key, value in raw.items():
        value = clean(value)
        if not value:
            continue
        if key in ("start_date", "end_date", "date"):
            start, end = parse_date_range(value)
            if key == "start_date":
                value = start or clean(value)
            elif key == "end_date":
                value = end or start or clean(value)
            else:
                value = start or clean(value)
        if key == "participants":
            number = parse_number(value)
            if number is not None:
                value = str(number)
        if key == "year":
            number = parse_number(value)
            if number is not None:
                value = str(number)
        fields[key] = value

    # If only a range was supplied, keep both ends.
    if fields.get("start_date") and not fields.get("end_date"):
        start, end = parse_date_range(fields["start_date"])
        if end:
            fields["end_date"] = end
            fields["start_date"] = start

    if "title" not in fields and text:
        first = clean(text.split("\n")[0]).strip(" .")
        if first:
            fields["title"] = first[:180]

    if "date" not in fields and "start_date" not in fields:
        iso = parse_date(text)
        if iso:
            fields["date"] = iso
    if "start_date" not in fields and fields.get("date"):
        fields["start_date"] = fields["date"]

    if "participants" not in fields:
        m = re.search(r"(\d{1,5})\s+(?:students|participants|beneficiaries|attendees|faculty)", text, re.I)
        if not m:
            m = re.search(r"(?:participants|beneficiaries|attendees)\s*[:\-]?\s*(\d{1,5})", text, re.I)
        if m:
            fields["participants"] = m.group(1)

    if "faculty_name" not in fields and "student_name" not in fields and "resource_person" not in fields:
        name = initials_name(text)
        if name:
            if category == "student_achievement":
                fields["student_name"] = name
            elif category in ("faculty_fdp", "research_publication", "conference"):
                fields["faculty_name"] = name
            elif category == "guest_lecture":
                fields["resource_person"] = name

    return fields


def _confidence(fields: dict, category: str, filename: str, structured: bool) -> float:
    base = 0.86 if structured else 0.55
    filled = len([v for v in fields.values() if v])
    base += min(0.09, 0.02 * filled)
    if category and category.replace("_", " ") in filename.lower().replace("_", " "):
        base += 0.04
    if fields.get("title"):
        base += 0.02
    return round(min(0.98, base), 2)


def _table_records(rows, filename, locator_prefix, image_dir=None):
    rows = [[clean(c) for c in row] for row in rows if any(clean(c) for c in row)]
    if len(rows) < 2:
        return []
    header = rows[0]
    mapping = [map_header(h) for h in header]
    records = []
    for idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue
        raw = {}
        for col, cell in enumerate(row):
            field = mapping[col] if col < len(mapping) else None
            if field and cell and field not in raw:
                raw[field] = cell
        text = " | ".join(row)
        category, _ = classify(text, filename)
        if not raw:
            continue
        fields = _normalise_fields(raw, category or "", text)
        if len([v for v in fields.values() if v]) < 2:
            continue
        records.append(
            {
                "category": category,
                "fields": fields,
                "source_file": filename,
                "locator": f"{locator_prefix} row {idx}",
                "confidence": _confidence(fields, category or "", filename, True),
                "kind": "table",
                "structured": True,
            }
        )
    return records


def _docx_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


def _records_from_lines(lines, filename, locator_prefix, page_label=None):
    """Group 'Label: value' lines into records; fall back to paragraph records."""
    records = []
    current = {}
    buffer = []
    extra = []

    def flush():
        nonlocal current, buffer
        if current:
            text = "\n".join(buffer)
            category, _ = classify(text, filename)
            fields = _normalise_fields(current, category or "", text)
            if fields:
                loc = page_label or locator_prefix
                records.append(
                    {
                        "category": category,
                        "fields": fields,
                        "source_file": filename,
                        "locator": loc,
                        "confidence": _confidence(fields, category or "", filename, False),
                        "kind": "text",
                        "structured": True,
                    }
                )
        elif buffer:
            text = "\n".join(buffer).strip()
            if len(text) > 40:
                category, _ = classify(text, filename)
                if category:
                    fields = _normalise_fields({}, category, text)
                    fields["summary"] = clean(text)[:400]
                    if fields.get("title"):
                        records.append(
                            {
                                "category": category,
                                "fields": fields,
                                "source_file": filename,
                                "locator": page_label or locator_prefix,
                                "confidence": round(min(0.8, 0.52 + 0.02 * len(fields)), 2),
                                "kind": "text",
                                "structured": False,
                            }
                        )
        current = {}
        buffer = []

    for line in lines:
        text = clean(line)
        if not text:
            flush()
            continue
        m = LABEL_RE.match(text)
        field = map_header(m.group(1)) if m else None
        if field and m:
            value = m.group(2).strip()
            if field in current:
                flush()
            current[field] = value
            extra.append(text)
        else:
            if current and len(current) >= 2:
                buffer.append(text)
            else:
                buffer.append(text)
    flush()
    return records


def _extract_docx(path: Path, filename: str):
    doc = Document(str(path))
    records = []
    group = []

    def merge_group(items):
        merged = []
        for rec in items:
            if merged:
                prev = merged[-1]
                if prev["category"] == rec["category"] and set(prev["fields"]).isdisjoint(rec["fields"]):
                    prev["fields"].update(rec["fields"])
                    prev["confidence"] = max(prev["confidence"], rec["confidence"])
                    continue
            merged.append(rec)
        return merged

    for idx, block in enumerate(_docx_blocks(doc)):
        if isinstance(block, Table):
            if group:
                records.extend(merge_group(group))
                group = []
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            records.extend(_table_records(rows, filename, f"table {idx + 1}"))
            continue

        text = block.text.strip()
        if not text:
            # Blank paragraph = record boundary.
            if group:
                records.extend(merge_group(group))
                group = []
            continue
        style = (block.style.name or "") if block.style is not None else ""
        if style.startswith("Heading") or style in ("Title", "Subtitle"):
            if group:
                records.extend(merge_group(group))
                group = []
            continue
        group.extend(_records_from_lines([text], filename, f"para {idx + 1}"))

    if group:
        records.extend(merge_group(group))
    return records


def _extract_xlsx(path: Path, filename: str):
    from openpyxl import load_workbook

    records = []
    wb = load_workbook(str(path), data_only=True)
    for sheet in wb.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([clean(c) for c in row])
        records.extend(_table_records(rows, filename, f"{sheet.title}"))
    return records


def _extract_csv(path: Path, filename: str):
    with open(path, newline="", encoding="utf-8", errors="ignore") as fh:
        rows = [row for row in csv.reader(fh)]
    return _table_records(rows, filename, "csv")


def _extract_pdf(path: Path, filename: str):
    reader = PdfReader(str(path))
    records = []
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        lines = text.splitlines()
        records.extend(
            _records_from_lines(lines, filename, f"page {page_no}", page_label=f"page {page_no}")
        )
    return records


def _extract_image(path: Path, filename: str):
    category, _ = classify(filename.replace("_", " "), filename)
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return [
        {
            "category": category,
            "fields": {"title": stem[:120], "caption": ""},
            "source_file": filename,
            "locator": "image",
            "confidence": 0.72,
            "kind": "image",
            "image_path": str(path),
            "structured": False,
        }
    ]


def extract_file(path: Path, filename: str, media_dir: Path):
    """Return raw records for one uploaded file. Never raises on bad input."""
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return _extract_image(path, filename)
    if ext == ".docx":
        return _extract_docx(path, filename)
    if ext in (".xlsx", ".xlsm"):
        return _extract_xlsx(path, filename)
    if ext == ".csv":
        return _extract_csv(path, filename)
    if ext == ".pdf":
        return _extract_pdf(path, filename)
    if ext in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        return _records_from_lines(text.splitlines(), filename, "text")
    return []


def copy_evidence(path: Path, media_dir: Path, filename: str) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    shutil.copyfile(path, target)
    return str(target)


def dedupe_key(category: str, fields: dict) -> str:
    parts = [fields.get("title", ""), fields.get("faculty_name", ""), fields.get("student_name", "")]
    return " ".join(p for p in parts if p)


def looks_similar(a: dict, b: dict) -> float:
    """Similarity of two records for duplicate detection.

    Sharing a person is not evidence of a duplicate: the same faculty member
    writes many papers.  The activity title has to match as well, so the score
    is title-dominant and identity only breaks ties.
    """
    if a.get("category") != b.get("category"):
        return 0.0
    title = similarity(a["fields"].get("title", ""), b["fields"].get("title", ""))
    if title < 0.55:
        return title * 0.5
    identity = 0.0
    for key in ("faculty_name", "student_name", "resource_person"):
        if a["fields"].get(key) and b["fields"].get(key):
            identity = max(identity, similarity(a["fields"][key], b["fields"][key]))
    if not identity:
        return title
    return round(0.7 * title + 0.3 * identity, 3)
