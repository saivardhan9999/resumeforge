from __future__ import annotations

import hashlib
import io
import json
import textwrap
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_file, session, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "resumeforge.json"

app = Flask(__name__)
app.secret_key = "resumeforge-demo-secret"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


TEMPLATES = {
    "Executive": {"accent": "#c49024", "tone": "Confident, boardroom-ready, achievement-heavy"},
    "Creative": {"accent": "#d6a23a", "tone": "Expressive, portfolio-friendly, personality-led"},
    "Technical": {"accent": "#9b6a17", "tone": "Precise, system-focused, metrics-first"},
    "Student": {"accent": "#f1bf54", "tone": "Clean, internship-focused, project-forward"},
}

SEED_RESUMES = [
    {
        "id": "demo1",
        "name": "Aarav Mehta",
        "role": "Frontend Developer",
        "template": "Technical",
        "score": 91,
        "summary": "Frontend developer building fast React interfaces, design systems, and accessible dashboards.",
        "contact": {"phone": "9963756412", "email": "aarav@example.com", "github": "github.com/aarav", "linkedin": "linkedin.com/in/aarav"},
        "education": ["SRM Institute of Science and Technology | B.Tech - Computer Science and Engineering | 2023-2027 | CGPA-9.2"],
        "experience": ["Frontend Intern | Built reusable UI components and improved Lighthouse performance across product pages."],
        "projects": ["Portfolio Dashboard | Built a responsive React dashboard with reusable charts, filters, and API-driven views."],
        "certifications": ["Responsive Web Design - freeCodeCamp", "JavaScript Algorithms - freeCodeCamp"],
        "skills": ["React", "TypeScript", "Tailwind", "REST APIs", "Testing"],
        "bullets": [
            "Built reusable UI components that reduced feature delivery time by 28%.",
            "Improved Lighthouse performance from 71 to 94 across core product pages.",
            "Collaborated with designers to ship responsive flows for 20k+ monthly users.",
        ],
        "saved": True,
    },
    {
        "id": "demo2",
        "name": "Maya Iyer",
        "role": "Marketing Analyst",
        "template": "Executive",
        "score": 86,
        "summary": "Data-driven marketing analyst turning campaign signals into growth experiments.",
        "contact": {"phone": "9000000000", "email": "maya@example.com", "github": "github.com/maya", "linkedin": "linkedin.com/in/maya"},
        "education": ["Andhra University | BBA - Marketing Analytics | 2021-2024 | CGPA-8.8"],
        "experience": ["Marketing Analyst Intern | Built campaign dashboards and identified funnel drop-offs that improved conversion."],
        "projects": ["Campaign ROI Tracker | Developed a spreadsheet dashboard for paid, organic, and lifecycle channels."],
        "certifications": ["Google Analytics Certification", "Excel for Business Analytics"],
        "skills": ["SQL", "Excel", "Campaign Strategy", "GA4", "Storytelling"],
        "bullets": [
            "Identified funnel drop-offs that lifted trial conversion by 13%.",
            "Built weekly dashboards for paid, organic, and lifecycle channels.",
            "Presented campaign insights to leadership with clear next-step recommendations.",
        ],
        "saved": False,
    },
]


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def default_store() -> dict:
    return {"users": {}, "resumes": {}}


def load_store() -> dict:
    if not DATA_FILE.exists():
        return default_store()
    store = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    store.setdefault("users", {})
    store.setdefault("resumes", {})
    return store


def save_store(store: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return load_store()["users"].get(user_id)


def user_resumes(user_id: str) -> list[dict]:
    store = load_store()
    if user_id not in store["resumes"]:
        store["resumes"][user_id] = json.loads(json.dumps(SEED_RESUMES))
        save_store(store)
    return store["resumes"][user_id]


def save_user_resumes(user_id: str, resumes: list[dict]) -> None:
    store = load_store()
    store["resumes"][user_id] = resumes
    save_store(store)


def split_values(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def split_lines(value: str) -> list[str]:
    value = value.replace("\\n", "\n")
    return [item.strip(" -\t") for item in value.splitlines() if item.strip(" -\t")]


def build_resume(form) -> dict:
    role = form.get("role", "Software Developer").strip()
    experience = form.get("experience", "Built projects, improved workflows, collaborated with teams").strip()
    skills = split_values(form.get("skills", "Python, HTML, CSS, Flask"))
    template = form.get("template", "Technical")
    keywords = split_values(form.get("keywords", role))
    score = min(99, 72 + len(skills) * 3 + min(12, len(keywords) * 2))
    action = "delivered" if template != "Student" else "created"
    bullets = [
        f"{action.title()} {role.lower()} work using {', '.join(skills[:3])} with measurable project outcomes.",
        f"Translated {', '.join(keywords[:3]) or 'business goals'} into resume-ready achievements and clean portfolio proof.",
        f"Strengthened communication, ownership, and execution across {experience[:58].lower()}.",
    ]
    education = split_lines(form.get("education", "")) or [
        "SRM Institute of Science and Technology | B.Tech - Computer Science and Engineering | 2023-2027 | CGPA-9.2"
    ]
    projects = split_lines(form.get("projects", "")) or [
        f"{role} Portfolio Project | Built a polished application using {', '.join(skills[:4])} with responsive design and practical workflows."
    ]
    certifications = split_lines(form.get("certifications", "")) or [
        "Python Programming Certification", "Web Development Fundamentals"
    ]
    return {
        "id": uuid.uuid4().hex,
        "name": form.get("name", "Your Name").strip(),
        "role": role,
        "template": template,
        "score": score,
        "summary": f"{role} with practical experience in {', '.join(skills[:4])}, focused on clear outcomes and recruiter-friendly impact.",
        "contact": {
            "phone": form.get("phone", "9963756412").strip(),
            "email": form.get("email", "you@example.com").strip(),
            "github": form.get("github", "github.com/username").strip(),
            "linkedin": form.get("linkedin", "linkedin.com/in/username").strip(),
        },
        "education": education,
        "experience": [experience, *bullets[:2]],
        "projects": projects,
        "certifications": certifications,
        "skills": skills[:8],
        "bullets": bullets,
        "saved": True,
    }


def fit_text(canvas, text: str, x: float, y: float, max_width: float, font_name: str, font_size: int, min_size: int = 7) -> int:
    size = font_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 1
    canvas.setFont(font_name, size)
    canvas.drawString(x, y, text)
    return size


def draw_wrapped(canvas, text: str, x: float, y: float, width: float, font_name: str = "Times-Roman", font_size: int = 10, leading: int = 13, bullet: bool = False) -> float:
    prefix = "- " if bullet else ""
    lines = textwrap.wrap(prefix + text, width=max(45, int(width / (font_size * 0.48))))
    canvas.setFont(font_name, font_size)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def draw_section(canvas, title: str, x: float, y: float) -> float:
    canvas.setFont("Times-Bold", 13)
    canvas.drawString(x, y, title.upper())
    return y - 18


def resume_pdf_bytes(resume: dict) -> bytes:
    buffer = io.BytesIO()
    canvas = __import__("reportlab.pdfgen.canvas", fromlist=["Canvas"]).Canvas(buffer, pagesize=letter)
    width, height = letter
    left = 0.63 * inch
    right = width - 0.63 * inch
    y = height - 0.68 * inch

    def new_page_if_needed(current_y: float, needed: float = 70) -> float:
        if current_y > needed:
            return current_y
        canvas.showPage()
        return height - 0.62 * inch

    name = resume.get("name", "Your Name").upper()
    fit_text(canvas, name, left, y, right - left, "Times-Bold", 23, 13)
    y -= 18
    contact = resume.get("contact", {})
    contact_line = " | ".join(
        item for item in [contact.get("phone"), contact.get("email"), contact.get("github"), contact.get("linkedin")] if item
    )
    fit_text(canvas, contact_line, left, y, right - left, "Times-Roman", 8, 6)
    y -= 17
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1.3)
    canvas.line(left, y, right, y)
    y -= 18

    y = draw_section(canvas, "Education", left, y)
    for item in resume.get("education", []):
        parts = [part.strip() for part in item.split("|")]
        school = parts[0] if parts else item
        degree = parts[1] if len(parts) > 1 else ""
        date = parts[2] if len(parts) > 2 else ""
        score = parts[3] if len(parts) > 3 else ""
        canvas.setFont("Times-Roman", 11)
        canvas.drawString(left, y, school)
        if date:
            canvas.drawRightString(right - 28, y, date)
        y -= 14
        if degree:
            canvas.drawString(left, y, degree)
        if score:
            canvas.drawRightString(right - 28, y, score)
        y -= 20

    y = new_page_if_needed(y)
    y = draw_section(canvas, "Technical Skills", left, y)
    skill_groups = [
        ("Core Skills", ", ".join(resume.get("skills", [])[:5])),
        ("Tools & Technologies", ", ".join(resume.get("skills", [])[5:]) or "Git, VS Code, APIs, Responsive Design"),
    ]
    for label, value in skill_groups:
        canvas.setFont("Times-Bold", 10.5)
        canvas.drawString(left + 18, y, f"-  {label}:")
        canvas.setFont("Times-Roman", 10.5)
        canvas.drawString(left + 130, y, value)
        y -= 14
    y -= 8

    y = new_page_if_needed(y)
    y = draw_section(canvas, "Work Experience", left, y)
    experience = resume.get("experience", [])
    heading = experience[0] if experience else resume.get("role", "Professional Experience")
    heading_parts = [part.strip() for part in heading.split("|")]
    canvas.setFont("Times-Bold", 10.5)
    canvas.drawString(left, y, " | ".join(heading_parts[:-1]) if len(heading_parts) > 1 else heading_parts[0])
    if len(heading_parts) > 1:
        canvas.drawRightString(right - 28, y, heading_parts[-1])
    y -= 14
    for item in experience[1:] or resume.get("bullets", []):
        y = draw_wrapped(canvas, item, left + 34, y, right - left - 48, bullet=True)
    y -= 8

    y = new_page_if_needed(y)
    y = draw_section(canvas, "Projects", left, y)
    for project in resume.get("projects", []):
        y = new_page_if_needed(y)
        title, _, detail = project.partition("|")
        canvas.setFont("Times-Bold", 10.5)
        canvas.drawString(left, y, title.strip())
        y -= 14
        if detail:
            y = draw_wrapped(canvas, detail.strip(), left + 34, y, right - left - 48, bullet=True)
        y -= 6

    y = new_page_if_needed(y)
    y = draw_section(canvas, "Certifications", left, y)
    for cert in resume.get("certifications", []):
        y = draw_wrapped(canvas, cert, left + 18, y, right - left - 28, bullet=True)

    canvas.save()
    buffer.seek(0)
    return buffer.read()


@app.route("/", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    mode = request.form.get("mode") or request.args.get("mode", "login")
    message = ""
    if request.method == "POST":
        store = load_store()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        if not email or not password:
            message = "Email and password are required."
        elif mode == "register":
            if not name:
                message = "Name is required."
            elif any(user["email"] == email for user in store["users"].values()):
                message = "That account already exists."
            else:
                user_id = uuid.uuid4().hex
                store["users"][user_id] = {"id": user_id, "name": name, "email": email, "password_hash": password_hash(password)}
                store["resumes"][user_id] = json.loads(json.dumps(SEED_RESUMES))
                save_store(store)
                session["user_id"] = user_id
                return redirect(url_for("dashboard"))
        else:
            user = next((candidate for candidate in store["users"].values() if candidate["email"] == email), None)
            if not user or user["password_hash"] != password_hash(password):
                message = "Account not found. Create one first."
            else:
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
    return render_template("login.html", mode=mode, message=message)


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    resumes = user_resumes(user["id"])
    active_id = request.args.get("resume")
    active = next((resume for resume in resumes if resume["id"] == active_id), resumes[0] if resumes else None)
    saved_count = sum(1 for resume in resumes if resume.get("saved"))
    avg_score = round(sum(resume["score"] for resume in resumes) / max(1, len(resumes)))
    return render_template("dashboard.html", user=user, resumes=resumes, active=active, templates=TEMPLATES, saved_count=saved_count, avg_score=avg_score)


@app.route("/resume/generate", methods=["POST"])
def generate_resume():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    resumes = user_resumes(user["id"])
    resume = build_resume(request.form)
    resumes.insert(0, resume)
    save_user_resumes(user["id"], resumes)
    return redirect(url_for("dashboard", resume=resume["id"]) + "#generator")


@app.route("/resume/<resume_id>/<action>", methods=["POST"])
def resume_action(resume_id: str, action: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    resumes = user_resumes(user["id"])
    for resume in resumes:
        if resume["id"] != resume_id:
            continue
        if action == "save":
            resume["saved"] = not resume.get("saved", False)
        elif action == "boost":
            resume["score"] = min(100, resume["score"] + 4)
        elif action == "delete":
            resumes = [item for item in resumes if item["id"] != resume_id]
        break
    save_user_resumes(user["id"], resumes)
    return redirect(url_for("dashboard"))


@app.route("/resume/<resume_id>/download")
def download_resume(resume_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    resume = next((item for item in user_resumes(user["id"]) if item["id"] == resume_id), None)
    if not resume:
        return redirect(url_for("dashboard"))
    filename = f"{resume.get('name', 'resume').lower().replace(' ', '_')}_resume.pdf"
    return send_file(
        io.BytesIO(resume_pdf_bytes(resume)),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5186)
