"""EduTemplateFitAI – FastAPI backend.

Pipeline: upload template -> analyse quality -> confirm mapping -> ingest
heterogeneous evidence -> extract to structured records -> validate
(duplicates / conflicts / gaps) -> human approval -> template-preserving export.
"""

import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import store
from .demo import create_demo_project
from .ingest import ALLOWED_EXTENSIONS, ingest_file
from .pipeline import analyze_project, summarize
from .schema import CATEGORIES, FIELD_LABELS, category_label
from .template_engine import (
    analyze_template,
    generation_metrics,
    recalculate_quality,
    render_docx,
    render_pdf,
)
from .util import slugify
from .validation import record_summary, status_for


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load_all()
    yield


app = FastAPI(title="EduTemplateFitAI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    department: str = ""
    academic_year: str = ""
    institution: str = ""


class SectionMapping(BaseModel):
    id: str
    category: Optional[str] = None


class SectionsUpdate(BaseModel):
    sections: list[SectionMapping]


class RecordPatch(BaseModel):
    fields: Optional[dict] = None
    approved: Optional[bool] = None
    category: Optional[str] = None


class GenerateRequest(BaseModel):
    include_audit: bool = True
    placeholders: dict = Field(default_factory=dict)


class DuplicateAction(BaseModel):
    action: str  # "keep_both" | "discard"


class ConflictChoice(BaseModel):
    record_id: str


def _project_or_404(project_id: str) -> dict:
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def _refresh_summary(project: dict):
    project["summary"] = summarize(project)


def _recompute_missing(project: dict):
    from .validation import detect_missing

    sections = ((project.get("template") or {}).get("analysis") or {}).get("sections", [])
    project["validation"]["missing"] = detect_missing(project["records"], sections)
    stats = project["validation"].get("stats", {})
    stats["missing_fields"] = len([m for m in project["validation"]["missing"] if m["type"] == "field"])
    stats["missing_sections"] = len([m for m in project["validation"]["missing"] if m["type"] == "section"])
    project["validation"]["stats"] = stats


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "EduTemplateFitAI", "projects": len(store.list_projects())}


@app.get("/api/schema")
def schema():
    return {
        "categories": [
            {
                "key": cat,
                "label": spec["label"],
                "fields": [{"key": f, "label": label, "required": req} for f, label, req in spec["fields"]],
            }
            for cat, spec in CATEGORIES.items()
        ],
        "field_labels": FIELD_LABELS,
    }


@app.get("/api/projects")
def list_projects():
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "meta": p["meta"],
            "stage": p.get("stage"),
            "created_at": p.get("created_at"),
            "records": len([r for r in p.get("records", []) if not r.get("duplicate_of")]),
            "sources": len(p.get("sources", [])),
            "has_output": bool(p.get("generated")),
        }
        for p in store.list_projects()
    ]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate):
    project = store.create(payload.name.strip(), payload.department, payload.academic_year, payload.institution)
    return store.public(project)


@app.post("/api/demo", status_code=201)
def demo():
    project = create_demo_project()
    return store.public(project)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return store.public(_project_or_404(project_id))


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    _project_or_404(project_id)
    store.delete(project_id)
    return {"deleted": project_id}


@app.post("/api/projects/{project_id}/template")
async def upload_template(project_id: str, file: UploadFile = File(...)):
    project = _project_or_404(project_id)
    filename = Path(file.filename or "template.docx").name
    if Path(filename).suffix.lower() != ".docx":
        raise HTTPException(400, "Phase 1 supports DOCX templates only.")

    directory = store.project_dir(project_id) / "template"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{uuid.uuid4().hex[:6]}_{filename}"
    with target.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    try:
        analysis = analyze_template(target)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not parse template: {exc}") from exc

    project["template"] = {
        "filename": filename,
        "path": str(target),
        "analysis": analysis,
        "confirmed": False,
    }
    project["stage"] = "template"
    store.save(project)
    return store.public(project)


@app.patch("/api/projects/{project_id}/template/sections")
def update_sections(project_id: str, payload: SectionsUpdate):
    project = _project_or_404(project_id)
    if not project.get("template"):
        raise HTTPException(400, "Upload a template first.")
    analysis = project["template"]["analysis"]
    mappings = {item.id: item.category for item in payload.sections}
    for section in analysis["sections"]:
        if section["id"] not in mappings:
            continue
        category = mappings[section["id"]]
        if category and category not in CATEGORIES:
            raise HTTPException(400, f"Unknown category '{category}'")
        section["category"] = category
        section["category_label"] = category_label(category) if category else "Unmapped"
        section["confidence"] = 1.0 if category else 0.0

    recalculate_quality(analysis)
    project["template"]["confirmed"] = False
    analyze_project(project)
    project["stage"] = "template"
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/template/confirm")
def confirm_template(project_id: str):
    project = _project_or_404(project_id)
    if not project.get("template"):
        raise HTTPException(400, "Upload a template first.")
    project["template"]["confirmed"] = True
    project["stage"] = "review" if project.get("records") else "sources"
    _refresh_summary(project)
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/sources")
async def upload_sources(project_id: str, files: list[UploadFile] = File(...)):
    project = _project_or_404(project_id)
    if not project.get("template"):
        raise HTTPException(400, "Upload and confirm a template first.")

    accepted = 0
    errors = []
    tmp_dir = Path(store.project_dir(project_id)) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        filename = Path(upload.filename or "upload").name
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{filename}: unsupported file type {ext or '(none)'}")
            continue
        temp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
        with temp_path.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        source = ingest_file(project, temp_path, filename)
        temp_path.unlink(missing_ok=True)
        accepted += 1
        if source["status"] == "error":
            errors.append(f"{filename}: {source['error']}")

    analyze_project(project)
    if project["template"].get("confirmed"):
        project["stage"] = "review"
    store.save(project)
    return {"project": store.public(project), "accepted": accepted, "errors": errors}


@app.delete("/api/projects/{project_id}/sources/{source_id}")
def delete_source(project_id: str, source_id: str):
    project = _project_or_404(project_id)
    source = next((s for s in project.get("sources", []) if s["id"] == source_id), None)
    if not source:
        raise HTTPException(404, "Source not found")
    project["sources"] = [s for s in project["sources"] if s["id"] != source_id]
    Path(source.get("path", "")).unlink(missing_ok=True)
    analyze_project(project)
    if project.get("template", {}).get("confirmed"):
        project["stage"] = "review"
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/analyze")
def reanalyze(project_id: str):
    project = _project_or_404(project_id)
    analyze_project(project)
    store.save(project)
    return store.public(project)


@app.patch("/api/projects/{project_id}/records/{record_id}")
def patch_record(project_id: str, record_id: str, payload: RecordPatch):
    project = _project_or_404(project_id)
    record = next((r for r in project["records"] if r["id"] == record_id), None)
    if not record:
        raise HTTPException(404, "Record not found")

    if payload.fields:
        for key, value in payload.fields.items():
            if key in FIELD_LABELS:
                record["fields"][key] = str(value).strip()
        record["edited"] = True
        record["confidence"] = max(float(record["confidence"]), 0.95)
        if record["status"] not in ("duplicate", "conflict"):
            record["status"] = "verified"
            record["approved"] = True

    if payload.category:
        if payload.category not in CATEGORIES:
            raise HTTPException(400, f"Unknown category '{payload.category}'")
        record["category"] = payload.category
        record["category_label"] = category_label(payload.category)
        sections = project["template"]["analysis"]["sections"] if project.get("template") else []
        section = next((s for s in sections if s.get("category") == payload.category), None)
        record["section_id"] = section["id"] if section else None
        if record["status"] not in ("duplicate", "conflict"):
            record["status"] = status_for(record["confidence"], payload.category)
            record["approved"] = record["status"] == "auto"

    if payload.approved is not None:
        record["approved"] = payload.approved
        if payload.approved and record["status"] in ("review", "manual", "unverified"):
            record["status"] = "verified"

    record["display"] = record_summary(record)
    _recompute_missing(project)
    _refresh_summary(project)
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/records/approve-safe")
def approve_safe(project_id: str):
    project = _project_or_404(project_id)
    count = 0
    for record in project["records"]:
        if record.get("duplicate_of") or record.get("conflict"):
            continue
        if record.get("approved"):
            continue
        if record["status"] in ("auto", "verified", "review"):
            record["approved"] = True
            if record["status"] == "review":
                record["status"] = "verified"
            count += 1
    _refresh_summary(project)
    store.save(project)
    return {"approved": count, "project": store.public(project)}


@app.post("/api/projects/{project_id}/duplicates/{duplicate_id}")
def resolve_duplicate(project_id: str, duplicate_id: str, payload: DuplicateAction):
    project = _project_or_404(project_id)
    duplicate = next((d for d in project["validation"]["duplicates"] if d["id"] == duplicate_id), None)
    if not duplicate:
        raise HTTPException(404, "Duplicate group not found")
    first_id, second_id = duplicate["record_ids"]
    second = next((r for r in project["records"] if r["id"] == second_id), None)
    if payload.action == "keep_both":
        if second:
            second["duplicate_of"] = None
            second["status"] = "review"
            second["approved"] = False
        project["validation"]["duplicates"] = [
            d for d in project["validation"]["duplicates"] if d["id"] != duplicate_id
        ]
    elif payload.action == "discard":
        if second:
            second["duplicate_of"] = first_id
            second["approved"] = False
            second["status"] = "duplicate"
    else:
        raise HTTPException(400, "action must be 'keep_both' or 'discard'")

    _refresh_summary(project)
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/conflicts/{conflict_id}")
def resolve_conflict(project_id: str, conflict_id: str, payload: ConflictChoice):
    project = _project_or_404(project_id)
    conflict = next((c for c in project["validation"]["conflicts"] if c["id"] == conflict_id), None)
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    if payload.record_id not in conflict["record_ids"]:
        raise HTTPException(400, "Chosen record is not part of this conflict")
    chosen = next(
        (v for v in conflict["values"] if v["record_id"] == payload.record_id), None
    )
    if not chosen:
        raise HTTPException(400, "Invalid value choice")

    value = chosen["value"]
    for record_id in conflict["record_ids"]:
        record = next((r for r in project["records"] if r["id"] == record_id), None)
        if record:
            record["fields"][conflict["field"]] = value
            record["conflict"] = False
            record["status"] = "review"
            record["approved"] = False
            record["display"] = record_summary(record)

    project["validation"]["conflicts"] = [
        c for c in project["validation"]["conflicts"] if c["id"] != conflict_id
    ]
    _recompute_missing(project)
    _refresh_summary(project)
    store.save(project)
    return store.public(project)


@app.post("/api/projects/{project_id}/generate")
def generate(project_id: str, payload: GenerateRequest):
    project = _project_or_404(project_id)
    if not project.get("template"):
        raise HTTPException(400, "No template uploaded.")
    if not project["template"].get("confirmed"):
        raise HTTPException(400, "Confirm the template mapping before generating.")
    approved = [r for r in project["records"] if r.get("approved") and not r.get("duplicate_of")]
    if not approved:
        raise HTTPException(400, "No approved records. Review and approve at least one record.")

    meta = project["meta"]
    values = {
        "DEPARTMENT_NAME": meta.get("department", ""),
        "DEPARTMENT": meta.get("department", ""),
        "ACADEMIC_YEAR": meta.get("academic_year", ""),
        "YEAR": meta.get("academic_year", ""),
        "PROJECT_NAME": project["name"],
        "REPORT_TITLE": project["name"],
        "INSTITUTION_NAME": meta.get("institution", ""),
        "INSTITUTION": meta.get("institution", ""),
        "FACULTY_NAME": "Faculty Coordinator",
    }
    for key, value in payload.placeholders.items():
        values[str(key).strip().upper()] = str(value)

    sections = project["template"]["analysis"]["sections"]
    out_dir = store.project_dir(project_id) / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    year = meta.get("academic_year", "")
    stem = project["name"] if year and year in project["name"] else f"{project['name']} {year}"
    base = slugify(stem) or "generated-report"
    docx_path = out_dir / f"{base}.docx"
    pdf_path = out_dir / f"{base}.pdf"

    try:
        result = render_docx(
            Path(project["template"]["path"]),
            docx_path,
            sections,
            project["records"],
            values,
            include_audit=payload.include_audit,
        )
        render_pdf(project, sections, project["records"], pdf_path)
    except Exception as exc:
        raise HTTPException(500, f"Generation failed: {exc}") from exc

    metrics = generation_metrics(sections, project["records"], project["template"]["analysis"], result)
    project["generated"] = {
        "docx": {
            "filename": docx_path.name,
            "url": f"/api/projects/{project_id}/download/docx",
            "size": docx_path.stat().st_size,
        },
        "pdf": {
            "filename": pdf_path.name,
            "url": f"/api/projects/{project_id}/download/pdf",
            "size": pdf_path.stat().st_size,
        },
        "metrics": metrics,
        "include_audit": payload.include_audit,
        "generated_at": store.now(),
    }
    project["stage"] = "generated"
    store.save(project)
    return store.public(project)


@app.get("/api/projects/{project_id}/download/{kind}")
def download(project_id: str, kind: str):
    project = _project_or_404(project_id)
    generated = project.get("generated")
    if not generated:
        raise HTTPException(404, "No generated document yet.")
    if kind not in ("docx", "pdf"):
        raise HTTPException(400, "kind must be 'docx' or 'pdf'")
    info = generated.get(kind)
    path = store.project_dir(project_id) / "generated" / info["filename"]
    if not path.exists():
        raise HTTPException(404, "Generated file missing on disk.")
    media = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if kind == "docx"
        else "application/pdf"
    )
    return FileResponse(path, filename=info["filename"], media_type=media)


@app.get("/api/projects/{project_id}/evidence/{name}")
def evidence(project_id: str, name: str):
    _project_or_404(project_id)
    path = store.project_dir(project_id) / "media" / Path(name).name
    if not path.exists():
        raise HTTPException(404, "Evidence file not found")
    return FileResponse(path)
