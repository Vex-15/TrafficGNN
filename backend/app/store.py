"""Tiny JSON-backed project store (in-memory cache + disk persistence).

This is intentionally simple for a prototype: one process, one JSON file per
project.  Swapping in PostgreSQL later only requires replacing this module.
"""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"

_PROJECTS: dict = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def save(project: dict):
    directory = project_dir(project["id"])
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(project, indent=2, ensure_ascii=False)
    (directory / "project.json").write_text(payload, encoding="utf-8")
    _PROJECTS[project["id"]] = project


def load_all():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in PROJECTS_DIR.glob("*/project.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
            _PROJECTS[project["id"]] = project
        except (json.JSONDecodeError, OSError):
            continue


def get(project_id: str):
    return _PROJECTS.get(project_id)


def list_projects():
    return sorted(_PROJECTS.values(), key=lambda p: p.get("created_at", ""), reverse=True)


def create(name: str, department: str, academic_year: str, institution: str = ""):
    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    directory = project_dir(project_id)
    for sub in ("template", "sources", "media", "generated"):
        (directory / sub).mkdir(parents=True, exist_ok=True)
    project = {
        "id": project_id,
        "name": name or "Untitled reporting project",
        "meta": {
            "department": department,
            "academic_year": academic_year,
            "institution": institution,
        },
        "stage": "template",
        "created_at": now(),
        "template": None,
        "sources": [],
        "records": [],
        "validation": {"duplicates": [], "conflicts": [], "missing": [], "stats": {}},
        "summary": {},
        "generated": None,
    }
    save(project)
    return project


def delete(project_id: str):
    _PROJECTS.pop(project_id, None)
    shutil.rmtree(project_dir(project_id), ignore_errors=True)


def public(project: dict) -> dict:
    """Trim internal absolute paths before sending a project to the browser."""
    clone = json.loads(json.dumps(project))
    if clone.get("template"):
        clone["template"].pop("path", None)
    for source in clone.get("sources", []):
        source.pop("path", None)
    return clone
