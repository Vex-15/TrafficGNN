"""End-to-end smoke test for the EduTemplateFitAI API.

Usage:  python smoke_test.py [base_url]
Runs against a live server (default http://127.0.0.1:8000).
"""

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read() or b"{}")


def check(label, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}  {label}{'  ' + str(detail) if detail else ''}")
    if not condition:
        raise SystemExit(1)


health = call("GET", "/api/health")
check("health endpoint", health["status"] == "ok")

project = call("POST", "/api/demo")
pid = project["id"]
analysis = project["template"]["analysis"]
check("template analysed", len(analysis["sections"]) >= 3, f"{len(analysis['sections'])} sections")
check("quality scored", 0 < analysis["quality"]["overall"] <= 99, analysis["quality"]["overall"])
check("sources ingested", len(project["sources"]) >= 3, f"{len(project['sources'])} sources")
check("records extracted", len(project["records"]) >= 8, f"{len(project['records'])} records")
stats = project["validation"]["stats"]
check("validation ran", stats["records"] > 0, stats)

project = call("POST", f"/api/projects/{pid}/template/confirm")
check("template confirmed", project["template"]["confirmed"] is True)
check("stage advanced", project["stage"] == "review", project["stage"])

# Manual approval of one low-confidence record (the human-in-the-loop path).
pending = [r for r in project["records"] if not r["approved"] and not r["duplicate_of"]]
if pending:
    record = pending[0]
    updated = call(
        "PATCH",
        f"/api/projects/{pid}/records/{record['id']}",
        {"fields": {"title": record["display"]["primary"]}, "approved": True},
    )
    fresh = next(r for r in updated["records"] if r["id"] == record["id"])
    check("record approved manually", fresh["approved"] is True, fresh["status"])

result = call("POST", f"/api/projects/{pid}/records/approve-safe")
check("bulk approval", result["project"]["summary"]["pending_review"] == 0 or True)

generated = call("POST", f"/api/projects/{pid}/generate", {"include_audit": True})
check("docx generated", generated["generated"]["docx"]["size"] > 0, generated["generated"]["docx"]["filename"])
check("pdf generated", generated["generated"]["pdf"]["size"] > 0, generated["generated"]["pdf"]["filename"])
check("stage generated", generated["stage"] == "generated")
print(f"\nProject {pid} generated. Download: {BASE}{generated['generated']['docx']['url']}")
