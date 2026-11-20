
import hashlib
import html
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DB_PATH = Path(__file__).resolve().parent / "jobs.db"

GREENHOUSE_BOARDS = [
    "stripe", "cloudflare", "datadog", "gitlab", "twilio",
    "brex", "figma", "coinbase", "airbnb", "instacart",
    "reddit", "asana", "duolingo"
]

LEVER_SITES = [
    "browserstack", "razorpay", "postman"
]

# Location must be in the actual location field.
INDIA_TERMS = re.compile(
    r"\b(india|bengaluru|bangalore|pune|mumbai|hyderabad|"
    r"chennai|delhi|gurugram|gurgaon|noida|kolkata|"
    r"ahmedabad|jaipur|kochi)\b",
    re.I
)

# Reject clearly experienced roles.
SENIOR_TERMS = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|"
    r"head of|chief|vice president|vp|architect)\b",
    re.I
)

# Clear entry-level indicators in job titles.
TITLE_TERMS = re.compile(
    r"\b(fresher|freshers|intern|internship|graduate|"
    r"new grad|junior|trainee|apprentice|"
    r"entry[- ]level|campus|early career)\b",
    re.I
)

# Explicit early-career indicators in descriptions.
DESCRIPTION_TERMS = re.compile(
    r"(0\s*(?:-|–|to)\s*2\s*years?|"
    r"0\s*(?:-|–|to)\s*1\s*years?|"
    r"no experience required|"
    r"entry[- ]level position|"
    r"recent graduate|"
    r"new graduate|"
    r"early career|"
    r"graduate program|"
    r"campus hiring|"
    r"fresh graduate)",
    re.I
)

def fetch_json(url):
    request = Request(
        url,
        headers={
            "User-Agent": "FresherPulseAI/1.0 (public career-board collector)"
        }
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def categorize(title, description):
    text = (title + " " + description).lower()

    if re.search(r"machine learning|artificial intelligence|\bai\b|\bllm\b|data scientist", text):
        return "AI / ML"

    if any(x in text for x in [
        "data analyst", "analytics",
        "business intelligence", "sql analyst"
    ]):
        return "Data Analytics"

    if any(x in text for x in [
        "frontend", "front-end", "ui developer",
        "web designer", "ux", "ui/ux"
    ]):
        return "Design & Frontend"

    return "Software Development"


def get_job_type(title):
    if re.search(r"intern|apprentice", title, re.I):
        return "Internship"
    return "Full-time"


def make_hash(company, title, url):
    raw = f"{company}|{title}|{url}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_relevant(title, location, description):
    # Never infer job location from the description.
    if not INDIA_TERMS.search(location or ""):
        return False

    # Exclude experienced positions.
    if SENIOR_TERMS.search(title):
        return False

    # Require a clear entry-level signal in the title
    # or explicit early-career evidence in the description.
    title_match = bool(TITLE_TERMS.search(title))
    description_match = bool(DESCRIPTION_TERMS.search(description))

    return title_match or description_match


def save_job(
    conn, source, source_id, company, title,
    location, description, url, posted_date
):
    if not url or not title or not company:
        return False

    if not is_relevant(title, location, description):
        return False

    digest = make_hash(company, title, url)

    cursor = conn.execute("""
        INSERT OR IGNORE INTO jobs
        (
            source, source_id, company, role, city,
            job_type, category, description, salary,
            apply_url, posted_date, content_hash, verified
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source,
        str(source_id or ""),
        company,
        title,
        location,
        get_job_type(title),
        categorize(title, description),
        description[:5000],
        "Not disclosed",
        url,
        str(posted_date or ""),
        digest,
        0
    ))

    return cursor.rowcount == 1


def clean_existing_jobs(conn):
    rows = conn.execute("""
        SELECT id, role, city, description
        FROM jobs
        WHERE verified = 0
    """).fetchall()

    removed = 0

    for job_id, title, location, description in rows:
        if not is_relevant(title, location, description or ""):
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            removed += 1

    conn.commit()
    print(f"Removed unsuitable unverified listings: {removed}")


def collect_greenhouse(conn):
    added = 0

    for board in GREENHOUSE_BOARDS:
        url = (
            f"https://boards-api.greenhouse.io/v1/boards/"
            f"{board}/jobs?content=true"
        )

        try:
            data = fetch_json(url)
            jobs = data.get("jobs", [])
            print(f"[Greenhouse] {board}: received {len(jobs)} posts")

            for job in jobs:
                title = clean_text(job.get("title"))
                location = clean_text(
                    (job.get("location") or {}).get("name")
                )
                description = clean_text(job.get("content"))
                company = clean_text(
                    job.get("company_name")
                ) or board.title()

                if save_job(
                    conn, "Greenhouse", job.get("id"),
                    company, title, location, description,
                    job.get("absolute_url"), job.get("updated_at")
                ):
                    added += 1

            conn.commit()

        except (HTTPError, URLError, TimeoutError,
                ValueError, KeyError, TypeError) as error:
            print(f"[Greenhouse] {board}: skipped ({error})")

        time.sleep(0.5)

    return added


def collect_lever(conn):
    added = 0

    for site in LEVER_SITES:
        url = f"https://api.lever.co/v0/postings/{site}?mode=json"

        try:
            data = fetch_json(url)
            print(f"[Lever] {site}: received {len(data)} posts")

            for job in data:
                categories = job.get("categories") or {}

                title = clean_text(job.get("text"))
                location = clean_text(categories.get("location"))
                description = clean_text(
                    job.get("descriptionPlain")
                )
                company = site.replace("-", " ").title()

                if save_job(
                    conn, "Lever", job.get("id"),
                    company, title, location, description,
                    job.get("hostedUrl"), job.get("createdAt")
                ):
                    added += 1

            conn.commit()

        except (HTTPError, URLError, TimeoutError,
                ValueError, KeyError, TypeError) as error:
            print(f"[Lever] {site}: skipped ({error})")

        time.sleep(0.5)

    return added


def main():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        table = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='jobs'
        """).fetchone()

        if not table:
            print("ERROR: jobs table does not exist.")
            return

        print("FresherPulse AI - Quality Checked Collection")
        print("--------------------------------------------")

        clean_existing_jobs(conn)

        before = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        print(f"Existing suitable jobs: {before}")
        print("\nStarting collection...\n")

        greenhouse_added = collect_greenhouse(conn)
        lever_added = collect_lever(conn)

        after = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        print("\nCollection finished.")
        print(f"New Greenhouse jobs: {greenhouse_added}")
        print(f"New Lever jobs: {lever_added}")
        print(f"Total new jobs: {after - before}")
        print(f"Suitable jobs in database: {after}")

    except sqlite3.Error as error:
        print(f"Database error: {error}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
