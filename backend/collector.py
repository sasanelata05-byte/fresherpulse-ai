
import hashlib
import html
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "jobs.db"

# -----------------------------------------------
# JOB BOARD SOURCES
# -----------------------------------------------

GREENHOUSE_BOARDS = [
    "stripe", "cloudflare", "datadog", "gitlab", "twilio",
    "brex", "figma", "coinbase", "airbnb", "instacart",
    "reddit", "asana", "duolingo"
]

LEVER_SITES = [
    "browserstack", "razorpay", "postman"
]

ASHBY_BOARDS = [
    "composio", "josys", "secfix", "evaratus", "ema",
    "sycamore", "sardine", "weave", "emergence",
    "libra", "almabase",
    "openai", "notion", "linear", "ramp", "retool",
    "posthog", "vanta", "airbyte", "webflow", "supabase"
]

# -----------------------------------------------
# FILTER KEYWORDS
# -----------------------------------------------

INDIA_TERMS = re.compile(
    r"\b(india|bengaluru|bangalore|pune|mumbai|"
    r"navi mumbai|thane|pimpri|hyderabad|chennai|"
    r"delhi|gurugram|gurgaon|noida|kolkata|"
    r"ahmedabad|jaipur|kochi|coimbatore|mysore|mysuru|"
    r"indore|bhopal|chandigarh|mohali|lucknow|"
    r"nagpur|surat|vadodara|bhubaneswar|"
    r"visakhapatnam|vizag|thiruvananthapuram|"
    r"trivandrum|mangalore|mangaluru|patna|ranchi)\b",
    re.I
)

SENIOR_TERMS = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|"
    r"head of|chief|vice president|vp|architect)\b",
    re.I
)

TITLE_TERMS = re.compile(
    r"\b(fresher|freshers|intern|internship|graduate|"
    r"new grad|junior|trainee|apprentice|"
    r"entry[- ]level|campus|early career|"
    r"university graduate|graduate engineer trainee|"
    r"engineering trainee|management trainee|"
    r"graduate program|graduate programme)\b",
    re.I
)

DESCRIPTION_TERMS = re.compile(
    r"(0\s*(?:-|–|—|to)\s*2\s*(?:years?|yrs?)|"
    r"0\s*(?:-|–|—|to)\s*1\s*(?:years?|yrs?)|"
    r"1\s*(?:-|–|—|to)\s*2\s*(?:years?|yrs?)|"
    r"up to 2 years|"
    r"no experience required|"
    r"no prior experience|"
    r"entry[- ]level position|"
    r"recent graduate|new graduate|"
    r"early career|graduate program|graduate programme|"
    r"campus hiring|fresh graduate|"
    r"graduates with no experience|"
    r"less than 2 years of experience)",
    re.I
)

# Collection statistics for this run.
FILTER_COUNTS = {
    "checked": 0,
    "accepted": 0,
    "rejected_location": 0,
    "rejected_senior": 0,
    "rejected_experience": 0,
    "duplicates": 0
}


# -----------------------------------------------
# FETCH AND CLEAN HELPERS
# -----------------------------------------------

def fetch_json(url):
    request = Request(
        url,
        headers={
            "User-Agent": "FresherPulseAI/2.0 (public job board collector)",
            "Accept": "application/json"
        }
    )

    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_date(value):
    if not value:
        return ""

    try:
        if isinstance(value, (int, float)):
            if value > 100000000000:
                value = value / 1000

            return datetime.fromtimestamp(
                value, timezone.utc
            ).strftime("%Y-%m-%d")

        return str(value)[:10]

    except (ValueError, TypeError, OSError):
        return str(value)[:30]


# -----------------------------------------------
# JOB CLASSIFICATION
# -----------------------------------------------

def categorize(title, description):
    title_text = title.lower()
    text = (title + " " + description).lower()

    if re.search(
        r"machine learning|artificial intelligence|"
        r"\bai engineer\b|\bai scientist\b|"
        r"\bllm engineer\b|data scientist",
        title_text
    ):
        return "AI / ML"

    if re.search(
        r"data analyst|analytics engineer|"
        r"business intelligence|data analytics|"
        r"business analyst",
        title_text
    ):
        return "Data Analytics"

    if re.search(
        r"frontend|front-end|ui developer|"
        r"web designer|ux designer|ui/ux",
        title_text
    ):
        return "Design & Frontend"

    if re.search(
        r"product ops|operations analyst|"
        r"product operations|business operations",
        title_text
    ):
        return "Product & Operations"

    if re.search(
        r"customer support|customer success|"
        r"technical support",
        title_text
    ):
        return "Customer Support"

    # GTM engineering roles can be technical.
    if re.search(r"\bgtm engineer\b|\bgtm engineering\b", title_text):
        if re.search(
            r"\b(python|java|sql|api|apis|software|"
            r"engineering|developer|programming|"
            r"data pipeline|automation)\b",
            text
        ):
            return "Software Development"

        return "Product & Operations"

    if re.search(
        r"software engineer|software developer|"
        r"backend|back-end|full stack|fullstack|"
        r"developer|engineering|programmer",
        title_text
    ):
        return "Software Development"

    # Description-based classification is a fallback.
    if re.search(
        r"machine learning|artificial intelligence|"
        r"\bllm\b|deep learning",
        text
    ):
        return "AI / ML"

    return "Other"


def get_job_type(title, employment_type=""):
    value = (title + " " + str(employment_type)).lower()

    if re.search(r"intern|internship|apprentice", value):
        return "Internship"

    if "contract" in value:
        return "Contract"

    if "part-time" in value or "part time" in value:
        return "Part-time"

    return "Full-time"


# -----------------------------------------------
# FRESHER RELEVANCE FILTER
# -----------------------------------------------

def relevance_reason(title, location, description):
    """
    Returns:
    accepted
    location
    senior
    experience
    """

    title = title or ""
    location = location or ""
    description = description or ""

    # The job must have an India-based location.
    if not INDIA_TERMS.search(location):
        return "location"

    # Exclude senior and leadership roles.
    if SENIOR_TERMS.search(title):
        return "senior"

    # Require early-career evidence in title or description.
    title_match = bool(TITLE_TERMS.search(title))
    description_match = bool(
        DESCRIPTION_TERMS.search(description)
    )

    if not title_match and not description_match:
        return "experience"

    return "accepted"


def is_relevant(title, location, description):
    return (
        relevance_reason(title, location, description)
        == "accepted"
    )


# -----------------------------------------------
# DEDUPLICATION
# -----------------------------------------------

def make_hash(company, title, url):
    raw = f"{company}|{title}|{url}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# -----------------------------------------------
# SAVE JOB
# -----------------------------------------------

def save_job(
    conn,
    source,
    source_id,
    company,
    title,
    location,
    description,
    url,
    posted_date,
    employment_type=""
):
    FILTER_COUNTS["checked"] += 1

    if not url or not title or not company:
        FILTER_COUNTS["rejected_experience"] += 1
        return False

    reason = relevance_reason(title, location, description)

    if reason != "accepted":
        FILTER_COUNTS[f"rejected_{reason}"] += 1
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
        get_job_type(title, employment_type),
        categorize(title, description),
        description[:5000],
        "Not disclosed",
        url,
        normalize_date(posted_date),
        digest,
        0
    ))

    if cursor.rowcount == 1:
        FILTER_COUNTS["accepted"] += 1
        return True

    FILTER_COUNTS["duplicates"] += 1
    return False


# -----------------------------------------------
# CLEAN OLD UNSUITABLE JOBS
# -----------------------------------------------

def clean_existing_jobs(conn):
    rows = conn.execute("""
        SELECT id, role, city, description
        FROM jobs
        WHERE verified = 0
    """).fetchall()

    removed = 0

    for job_id, title, location, description in rows:
        if not is_relevant(title, location, description or ""):
            conn.execute(
                "DELETE FROM jobs WHERE id = ?",
                (job_id,)
            )
            removed += 1

    conn.commit()

    print(f"Removed unsuitable unverified listings: {removed}")


# -----------------------------------------------
# GREENHOUSE COLLECTOR
# -----------------------------------------------

def collect_greenhouse(conn):
    added = 0

    for board in GREENHOUSE_BOARDS:
        url = (
            "https://boards-api.greenhouse.io/v1/boards/"
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
                ) or board.replace("-", " ").title()

                if save_job(
                    conn,
                    "Greenhouse",
                    job.get("id"),
                    company,
                    title,
                    location,
                    description,
                    job.get("absolute_url"),
                    job.get("first_published") or job.get("updated_at")
                ):
                    added += 1

            conn.commit()

        except (
            HTTPError, URLError, TimeoutError,
            ValueError, KeyError, TypeError
        ) as error:
            print(f"[Greenhouse] {board}: skipped ({error})")

        time.sleep(0.5)

    return added


# -----------------------------------------------
# LEVER COLLECTOR
# -----------------------------------------------

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

                location = clean_text(
                    categories.get("allLocations")
                    or categories.get("location")
                )

                description = clean_text(
                    job.get("descriptionPlain")
                )

                company = site.replace("-", " ").title()

                if save_job(
                    conn,
                    "Lever",
                    job.get("id"),
                    company,
                    title,
                    location,
                    description,
                    job.get("applyUrl") or job.get("hostedUrl"),
                    job.get("createdAt"),
                    categories.get("commitment", "")
                ):
                    added += 1

            conn.commit()

        except (
            HTTPError, URLError, TimeoutError,
            ValueError, KeyError, TypeError
        ) as error:
            print(f"[Lever] {site}: skipped ({error})")

        time.sleep(0.5)

    return added


# -----------------------------------------------
# ASHBY COLLECTOR
# -----------------------------------------------

def collect_ashby(conn):
    added = 0

    for board in ASHBY_BOARDS:
        url = (
            "https://api.ashbyhq.com/posting-api/"
            f"job-board/{board}?includeCompensation=true"
        )

        try:
            data = fetch_json(url)
            jobs = data.get("jobs", [])

            print(f"[Ashby] {board}: received {len(jobs)} posts")

            for job in jobs:
                if not job.get("isListed", True):
                    continue

                title = clean_text(job.get("title"))

                address = job.get("address") or {}
                postal = address.get("postalAddress") or {}

                location_parts = [
                    job.get("location"),
                    postal.get("addressLocality"),
                    postal.get("addressRegion"),
                    postal.get("addressCountry")
                ]

                location = clean_text(
                    ", ".join(
                        str(part)
                        for part in location_parts
                        if part
                    )
                )

                description = clean_text(
                    job.get("descriptionPlain")
                    or job.get("descriptionHtml")
                    or job.get("description")
                    or ""
                )

                company = board.replace("-", " ").title()

                apply_url = (
                    job.get("applyUrl")
                    or job.get("jobUrl")
                )

                employment_type = job.get("employmentType", "")

                if save_job(
                    conn,
                    "Ashby",
                    job.get("id"),
                    company,
                    title,
                    location,
                    description,
                    apply_url,
                    job.get("publishedAt", ""),
                    employment_type
                ):
                    added += 1

            conn.commit()

        except (
            HTTPError, URLError, TimeoutError,
            ValueError, KeyError, TypeError
        ) as error:
            print(f"[Ashby] {board}: skipped ({error})")

        time.sleep(0.5)

    return added


# -----------------------------------------------
# COLLECTION DIAGNOSTICS
# -----------------------------------------------

def print_filter_statistics():
    print("\n========== FILTER STATISTICS ==========")

    print("Posts checked:", FILTER_COUNTS["checked"])
    print("New jobs accepted:", FILTER_COUNTS["accepted"])
    print("Rejected - location:", FILTER_COUNTS["rejected_location"])
    print("Rejected - seniority:", FILTER_COUNTS["rejected_senior"])
    print("Rejected - experience:", FILTER_COUNTS["rejected_experience"])
    print("Duplicates skipped:", FILTER_COUNTS["duplicates"])


def diagnose_collection():
    if not DB_PATH.exists():
        print("Database not found:", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        total = cursor.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        print("\n========== DATABASE DIAGNOSTIC ==========")
        print("Total saved jobs:", total)

        print("\nJobs by source:")
        for row in cursor.execute(
            "SELECT source, COUNT(*) FROM jobs GROUP BY source"
        ):
            print(row)

        print("\nJobs by category:")
        for row in cursor.execute(
            "SELECT category, COUNT(*) FROM jobs GROUP BY category"
        ):
            print(row)

        print("\nJobs by city:")
        for row in cursor.execute(
            "SELECT city, COUNT(*) FROM jobs GROUP BY city"
        ):
            print(row)

        print("\nSaved job titles:")
        for row in cursor.execute(
            "SELECT company, role, city, job_type FROM jobs"
        ):
            print(row)

    finally:
        conn.close()


# -----------------------------------------------
# MAIN
# -----------------------------------------------

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

        print("\nFresherPulse AI - Job Collector")
        print("--------------------------------")
        print(f"Database: {DB_PATH}")

        clean_existing_jobs(conn)

        before = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        print(f"Existing suitable jobs: {before}")
        print("\nStarting collection...\n")

        greenhouse_added = collect_greenhouse(conn)
        lever_added = collect_lever(conn)
        ashby_added = collect_ashby(conn)

        conn.commit()

        after = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        print("\nCollection finished.")
        print("--------------------------------")
        print(f"New Greenhouse jobs: {greenhouse_added}")
        print(f"New Lever jobs: {lever_added}")
        print(f"New Ashby jobs: {ashby_added}")
        print(f"Total new jobs: {after - before}")
        print(f"Total suitable jobs: {after}")

        print("\nCategory breakdown:")

        rows = conn.execute("""
            SELECT category, COUNT(*)
            FROM jobs
            GROUP BY category
            ORDER BY COUNT(*) DESC
        """).fetchall()

        for category, count in rows:
            print(f"{category}: {count}")

    except sqlite3.Error as error:
        print(f"Database error: {error}")

    finally:
        conn.close()

    print_filter_statistics()
    diagnose_collection()


if __name__ == "__main__":
    main()
