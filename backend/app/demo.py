"""Demo seeder: builds a realistic template + heterogeneous evidence set.

The generated files exercise the whole pipeline (DOCX, XLSX, PDF, PNG),
including a duplicate record, a conflicting value and missing evidence.
"""

import shutil
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from . import store
from .ingest import ingest_file
from .pipeline import analyze_project
from .template_engine import analyze_template


def _build_template(path: Path):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    section = doc.sections[0]
    section.header.paragraphs[0].text = "Department Annual Report  |  {{DEPARTMENT_NAME}}"
    section.footer.paragraphs[0].text = "Page "

    title = doc.add_heading("DEPARTMENT ANNUAL REPORT", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph("{{DEPARTMENT_NAME}}  |  Academic Year {{ACADEMIC_YEAR}}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    prepared = doc.add_paragraph("Prepared by: {{FACULTY_NAME}}")
    prepared.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    doc.add_heading("3. Department Activities", level=1)
    doc.add_paragraph(
        "This section summarises verified departmental activities for the academic year. "
        "Every entry is traceable to an evidence document listed in the annexure."
    )

    doc.add_heading("3.1 Student Achievements", level=2)
    doc.add_paragraph("The following achievements were recorded during the academic year.")
    table = doc.add_table(rows=2, cols=5)
    table.style = "Table Grid"
    for i, label in enumerate(["S.No.", "Student Name", "Achievement", "Event", "Date"]):
        cell = table.rows[0].cells[i]
        cell.text = label
        for run in cell.paragraphs[0].runs:
            run.bold = True

    doc.add_heading("3.2 Faculty Development Programmes", level=2)
    doc.add_paragraph("Faculty members participated in the following development programmes.")

    doc.add_heading("3.3 Research Publications", level=2)
    doc.add_paragraph("Peer-reviewed publications by faculty members during the year.")
    table = doc.add_table(rows=2, cols=6)
    table.style = "Table Grid"
    for i, label in enumerate(["S.No.", "Title", "Faculty", "Journal", "Year", "DOI"]):
        cell = table.rows[0].cells[i]
        cell.text = label
        for run in cell.paragraphs[0].runs:
            run.bold = True

    doc.add_heading("3.4 Guest Lectures", level=2)
    doc.add_paragraph("Expert sessions organised by the department.")

    doc.add_heading("3.5 Workshops", level=2)
    doc.add_paragraph("Hands-on workshops and seminars conducted during the year.")

    doc.add_heading("3.6 Conference Participation", level=2)
    doc.add_paragraph("Faculty participation in national and international conferences.")

    doc.save(str(path))


def _build_student_xlsx(path: Path):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Achievements"
    ws.append(["Student Name", "Achievement", "Event", "Date", "Position"])
    rows = [
        ["Aarav Shetty", "First prize in Smart India Hackathon", "Smart India Hackathon", "12 September 2026", "1st Prize"],
        ["Priya Nair", "Best paper award", "IEEE Student Paper Contest", "5 August 2026", "Best Paper"],
        ["Karthik Reddy", "Gold medal in state athletics", "State Inter-College Meet", "21 October 2026", "Gold Medal"],
        ["Sneha Patil", "Winner, national coding contest", "CodeSprint 2026", "3 March 2026", "Winner"],
        ["Mohammed Irfan", "Second prize in project expo", "Project Expo 2026", "17 April 2026", "2nd Prize"],
    ]
    for row in rows:
        ws.append(row)
    wb.save(str(path))


def _build_publication_xlsx(path: Path):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Publications"
    ws.append(["Faculty", "Title", "Journal", "Year", "DOI"])
    rows = [
        ["Dr. Ananya Rao", "Explainable AI for Student Performance Prediction", "IEEE Access", 2026, "10.1109/ACCESS.2026.1042"],
        ["Dr. Vikram Menon", "Efficient Query Planning for Vector Databases", "ACM SIGMOD Record", 2026, "10.1145/3626246"],
        ["Dr. Ananya Rao", "Multimodal Document Parsing for Institutional Records", "Elsevier Pattern Recognition Letters", 2025, "10.1016/j.patrec.2025.09.011"],
        ["Dr. Meera Iyer", "Federated Learning in Healthcare Analytics", "Springer Journal of Medical Systems", 2026, "10.1007/s10916-026-0191"],
    ]
    for row in rows:
        ws.append(row)
    wb.save(str(path))


def _build_fdp_docx(path: Path):
    doc = Document()
    doc.add_heading("Faculty Development Programmes Attended", level=1)
    entries = [
        [
            "Programme: Generative AI for Engineering Education",
            "Faculty: Dr. Ananya Rao",
            "Organizer: NPTEL, IIT Madras",
            "Dates: 10-14 August 2026",
            "Mode: Online",
            "Participants: 67",
        ],
        [
            "Programme: Outcome Based Education and NBA Accreditation",
            "Faculty: Dr. Vikram Menon",
            "Organizer: National Institute of Technical Teachers Training",
            "Dates: 3-7 July 2026",
            "Mode: Offline",
        ],
        [
            "Programme: Research Methodology and Academic Writing",
            "Faculty: Dr. Ananya Rao",
            "Organizer: VTU Faculty Development Centre",
            "Dates: 18-22 September 2026",
            "Mode: Online",
            "Participants: 42",
        ],
    ]
    for entry in entries:
        for line in entry:
            doc.add_paragraph(line)
        doc.add_paragraph()
    doc.save(str(path))


def _build_guest_docx(path: Path):
    doc = Document()
    doc.add_heading("Guest Lectures Organised", level=1)
    entries = [
        [
            "Topic: Cloud Native Architectures in Industry",
            "Resource Person: Mr. Rohan Desai",
            "Organization: Infosys Technologies",
            "Date: 12 September 2026",
            "Venue: Seminar Hall, Block C",
            "Participants: 118",
        ],
        [
            "Topic: Cyber Security Careers and Certifications",
            "Resource Person: Ms. Neha Kulkarni",
            "Organization: TCS Research",
            "Date: 26 October 2026",
            "Venue: Auditorium",
        ],
    ]
    for entry in entries:
        for line in entry:
            doc.add_paragraph(line)
        doc.add_paragraph()
    doc.save(str(path))


def _build_workshop_docx(path: Path):
    doc = Document()
    doc.add_heading("Workshops Conducted", level=1)
    entries = [
        [
            "Title: Hands-on Workshop on Power BI",
            "Organizer: Department of CSE",
            "Dates: 14-15 August 2026",
            "Participants: 54",
            "Mode: Offline",
        ],
        [
            "Title: Python for Data Science Bootcamp",
            "Organizer: Department of CSE",
            "Dates: 5-9 September 2026",
            "Participants: 96",
            "Mode: Offline",
        ],
    ]
    for entry in entries:
        for line in entry:
            doc.add_paragraph(line)
        doc.add_paragraph()
    doc.save(str(path))


def _build_workshop_summary_docx(path: Path):
    doc = Document()
    doc.add_heading("Workshop Summary Note", level=1)
    for line in [
        "Title: Power BI Hands-on Workshop for Students",
        "Organizer: Department of CSE",
        "Dates: 14-15 August 2026",
        "Participants: 57",
    ]:
        doc.add_paragraph(line)
    doc.save(str(path))


def _build_fdp_pdf(path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    lines = [
        "Certificate of Participation",
        "Programme: Generative AI for Engineering Education",
        "Faculty: Dr. Ananya Rao",
        "Organizer: NPTEL, IIT Madras",
        "Dates: 10-14 August 2026",
        "Participants: 67",
    ]
    y = 780
    for line in lines:
        c.setFont("Helvetica-Bold" if line.startswith("Certificate") else "Helvetica", 12)
        c.drawString(60, y, line)
        y -= 26
    c.showPage()
    c.save()


def _build_conference_pdf(path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    entries = [
        [
            "Paper Title: Retrieval Augmented Generation for Academic Reports",
            "Faculty: Dr. Meera Iyer",
            "Conference: International Conference on Data Engineering 2026",
            "Date: 8 June 2026",
            "Venue: Bengaluru",
        ],
        [
            "Paper Title: Template Aware Document Reconstruction",
            "Faculty: Dr. Vikram Menon",
            "Conference: ACM DocEng Symposium 2026",
            "Date: 24 September 2026",
            "Venue: Lisbon, Portugal",
        ],
    ]
    y = 780
    for entry in entries:
        for line in entry:
            c.setFont("Helvetica", 12)
            c.drawString(60, y, line)
            y -= 24
        y -= 30
    c.showPage()
    c.save()


def _build_workshop_image(path: Path):
    from PIL import Image, ImageDraw

    width, height = 900, 520
    image = Image.new("RGB", (width, height), "#1e3a8a")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=(int(30 + 40 * ratio), int(58 + 60 * ratio), int(138 + 70 * ratio)),
        )
    draw.rectangle([60, 60, width - 60, height - 60], outline=(226, 232, 240), width=3)
    draw.text((110, 230), "Power BI Workshop - 14 August 2026", fill=(248, 250, 252))
    image.save(str(path))


def create_demo_project() -> dict:
    project = store.create(
        name="Department Annual Report 2025-26",
        department="Computer Science & Engineering",
        academic_year="2025-26",
        institution="Example Institute of Technology",
    )
    demo_dir = Path(tempfile.mkdtemp(prefix="etf_demo_"))

    template_file = demo_dir / "Department_Annual_Report_Template.docx"
    _build_template(template_file)
    template_target = store.project_dir(project["id"]) / "template" / template_file.name
    shutil.copyfile(template_file, template_target)
    analysis = analyze_template(template_target)
    project["template"] = {
        "filename": template_file.name,
        "path": str(template_target),
        "analysis": analysis,
        "confirmed": False,
    }

    builders = [
        (_build_student_xlsx, "Student_Achievements.xlsx"),
        (_build_publication_xlsx, "Faculty_Publications.xlsx"),
        (_build_fdp_docx, "FDP_Report.docx"),
        (_build_fdp_pdf, "FDP_Certificates.pdf"),
        (_build_guest_docx, "Guest_Lecture_Report.docx"),
        (_build_workshop_docx, "Workshop_Report.docx"),
        (_build_workshop_summary_docx, "Workshop_Summary_Note.docx"),
        (_build_conference_pdf, "Conference_Certificates.pdf"),
        (_build_workshop_image, "Power_BI_Workshop_Photograph.png"),
    ]
    for builder, filename in builders:
        file_path = demo_dir / filename
        builder(file_path)
        ingest_file(project, file_path, filename)

    analyze_project(project)
    project["stage"] = "template"
    store.save(project)
    shutil.rmtree(demo_dir, ignore_errors=True)
    return project
