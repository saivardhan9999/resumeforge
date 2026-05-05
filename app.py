from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for


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
    return {
        "id": uuid.uuid4().hex,
        "name": form.get("name", "Your Name").strip(),
        "role": role,
        "template": template,
        "score": score,
        "summary": f"{role} with practical experience in {', '.join(skills[:4])}, focused on clear outcomes and recruiter-friendly impact.",
        "skills": skills[:8],
        "bullets": bullets,
        "saved": True,
    }


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


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5186)
