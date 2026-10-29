"""Canonical institutional schema for EduTemplateFitAI.

Every extracted record is normalised into this schema before it is allowed
anywhere near the template.  This is the "structured data layer" the proposal
insists on: documents -> extraction -> JSON -> validation -> approval -> render.
"""

CATEGORIES = {
    "student_achievement": {
        "label": "Student Achievement",
        "keywords": [
            "student achievement", "achievement", "award", "prize", "winner",
            "rank", "topper", "merit", "sports", "competition", "medal",
        ],
        "fields": [
            ("title", "Achievement", True),
            ("student_name", "Student Name", True),
            ("event", "Event", False),
            ("date", "Date", False),
            ("position", "Position / Award", False),
        ],
        "identity": ["student_name", "title"],
        "critical": ["date", "position"],
    },
    "faculty_fdp": {
        "label": "Faculty Development Programme",
        "keywords": [
            "fdp", "faculty development", "refresher course", "orientation",
            "training programme", "training program", "short term course",
        ],
        "fields": [
            ("title", "Programme", True),
            ("faculty_name", "Faculty", False),
            ("organizer", "Organizer", False),
            ("start_date", "Start Date", False),
            ("end_date", "End Date", False),
            ("mode", "Mode", False),
            ("participants", "Participants", False),
        ],
        "identity": ["faculty_name", "title"],
        "critical": ["start_date", "participants"],
    },
    "guest_lecture": {
        "label": "Guest Lecture",
        "keywords": [
            "guest lecture", "guest talk", "expert talk", "invited talk",
            "guest session", "resource person", "lecture",
        ],
        "fields": [
            ("title", "Topic", True),
            ("resource_person", "Resource Person", True),
            ("organization", "Organization", False),
            ("date", "Date", False),
            ("venue", "Venue", False),
            ("participants", "Participants", False),
        ],
        "identity": ["resource_person", "title"],
        "critical": ["date", "participants"],
    },
    "workshop": {
        "label": "Workshop / Seminar",
        "keywords": [
            "workshop", "seminar", "webinar", "hands-on", "hands on",
            "bootcamp", "training session",
        ],
        "fields": [
            ("title", "Title", True),
            ("organizer", "Organizer", False),
            ("start_date", "Start Date", False),
            ("end_date", "End Date", False),
            ("participants", "Participants", False),
            ("mode", "Mode", False),
        ],
        "identity": ["title"],
        "critical": ["start_date", "participants"],
    },
    "research_publication": {
        "label": "Research Publication",
        "keywords": [
            "publication", "journal", "scopus", "web of science", "sci",
            "research paper", "paper published", "doi", "patent",
        ],
        "fields": [
            ("title", "Title", True),
            ("faculty_name", "Faculty", False),
            ("journal", "Journal / Publisher", True),
            ("year", "Year", False),
            ("doi", "DOI", False),
        ],
        "identity": ["title", "faculty_name"],
        "critical": ["year"],
    },
    "conference": {
        "label": "Conference Participation",
        "keywords": [
            "conference", "symposium", "proceedings", "paper presentation",
            "convention",
        ],
        "fields": [
            ("title", "Paper Title", True),
            ("faculty_name", "Faculty", False),
            ("conference", "Conference", False),
            ("date", "Date", False),
            ("venue", "Venue", False),
        ],
        "identity": ["faculty_name", "title"],
        "critical": ["date"],
    },
}

FIELD_LABELS = {
    "title": "Title",
    "student_name": "Student Name",
    "faculty_name": "Faculty",
    "resource_person": "Resource Person",
    "achievement": "Achievement",
    "event": "Event",
    "date": "Date",
    "position": "Position / Award",
    "organizer": "Organizer",
    "organization": "Organization",
    "start_date": "Start Date",
    "end_date": "End Date",
    "mode": "Mode",
    "participants": "Participants",
    "venue": "Venue",
    "journal": "Journal / Publisher",
    "year": "Year",
    "doi": "DOI",
    "conference": "Conference",
    "caption": "Caption",
}

# Header / label synonyms used when parsing tabular rows and "Label: value" text.
FIELD_SYNONYMS = {
    "title": [
        "title", "title of paper", "paper title", "paper", "programme",
        "program", "name of programme", "name of program", "fdp title",
        "event", "topic", "activity", "achievement", "name of the event",
    ],
    "student_name": ["student", "student name", "name of student", "name of the student"],
    "faculty_name": ["faculty", "faculty name", "name of faculty", "author", "authors", "presenter"],
    "resource_person": ["resource person", "speaker", "guest", "guest name", "name of resource person", "resource person name"],
    "event": ["event", "occasion", "competition"],
    "date": ["date", "dates", "held on", "conducted on", "day"],
    "position": ["position", "award", "prize", "rank", "result"],
    "organizer": ["organizer", "organiser", "organised by", "organized by", "conducted by", "host"],
    "organization": ["organization", "organisation", "institution", "company", "affiliation", "from"],
    "start_date": ["start date", "from", "from date", "start"],
    "end_date": ["end date", "to", "to date", "end"],
    "mode": ["mode", "mode of conduct", "online/offline"],
    "participants": ["participants", "no of participants", "no. of participants", "number of participants", "beneficiaries", "attendees", "students attended"],
    "venue": ["venue", "place", "location", "held at"],
    "journal": ["journal", "journal name", "publisher", "publication"],
    "year": ["year", "publication year", "published year"],
    "doi": ["doi", "doi link"],
    "conference": ["conference", "conference name", "symposium"],
    "caption": ["caption", "description"],
}

REQUIRED_FIELDS = {
    cat: [f for f, _label, req in spec["fields"] if req]
    for cat, spec in CATEGORIES.items()
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def category_label(cat: str) -> str:
    return CATEGORIES.get(cat, {}).get("label", "Unclassified")
