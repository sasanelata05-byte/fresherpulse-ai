
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sqlite3

# ==========================================
# FRESHERPULSE AI - MAIN BACKEND
# ==========================================

app = FastAPI(
    title="FresherPulse AI",
    description="India Fresher Job and Internship Aggregator",
    version="2.0.0"
)

DB_PATH = Path(__file__).resolve().parent / "jobs.db"


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# DATABASE
# ==========================================

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            city TEXT,
            job_type TEXT,
            category TEXT,
            description TEXT,
            salary TEXT,
            apply_url TEXT NOT NULL,
            posted_date TEXT,
            content_hash TEXT UNIQUE,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_role
        ON jobs(role)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_city
        ON jobs(city)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_category
        ON jobs(category)
    """)

    connection.commit()
    connection.close()


# ==========================================
# JOB CATEGORIZATION
# ==========================================

CATEGORY_KEYWORDS = {
    "AI & Machine Learning": [
        "machine learning", "artificial intelligence",
        "deep learning", "generative ai", "genai",
        "ai engineer", "ml engineer", "llm",
        "nlp", "computer vision"
    ],

    "Data Science": [
        "data scientist", "data science",
        "data analyst", "data engineer",
        "data analytics", "business analyst"
    ],

    "Frontend Development": [
        "frontend", "front-end",
        "react developer", "angular developer",
        "vue developer", "ui developer",
        "web developer"
    ],

    "Backend Development": [
        "backend", "back-end",
        "backend engineer", "api developer",
        "django", "fastapi", "server-side"
    ],

    "DevOps & Cloud": [
        "devops", "cloud engineer",
        "cloud computing", "aws",
        "azure", "kubernetes", "docker",
        "site reliability", "sre"
    ],

    "Cybersecurity": [
        "cybersecurity", "cyber security",
        "security engineer", "information security",
        "penetration testing", "application security"
    ],

    "Product & Operations": [
        "product manager", "product operations",
        "product ops", "operations intern",
        "business operations"
    ],

    "Software Development": [
        "software engineer", "software developer",
        "full stack", "fullstack",
        "application developer", "programmer",
        "java developer", "python developer",
        "c++ developer", "product engineer",
        "engineering intern"
    ]
}


def categorize_job(role, description=""):
    role_text = (role or "").lower()
    description_text = (description or "").lower()

    # First check the role title.
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in role_text for keyword in keywords):
            return category

    # Then check the description.
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in description_text for keyword in keywords):
            return category

    return "Other"


def categorize_uncategorized_jobs(connection):
    rows = connection.execute("""
        SELECT id, role, description
        FROM jobs
        WHERE category IS NULL
        OR TRIM(category) = ''
    """).fetchall()

    for row in rows:
        category = categorize_job(
            row["role"],
            row["description"]
        )

        connection.execute("""
            UPDATE jobs
            SET category = ?
            WHERE id = ?
        """, (category, row["id"]))

    connection.commit()
    return len(rows)


# Initialize database when application starts.
initialize_database()


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():
    return {
        "project": "FresherPulse AI",
        "status": "running",
        "version": "2.0.0"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/api/health")
def health():
    try:
        connection = get_db()
        connection.execute("SELECT 1")
        connection.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ==========================================
# CATEGORIZE ALL JOBS
# ==========================================

@app.get("/api/categorize")
def categorize_all_jobs():
    connection = get_db()

    try:
        updated = categorize_uncategorized_jobs(connection)

        rows = connection.execute("""
            SELECT category, COUNT(*) AS total
            FROM jobs
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

        return {
            "message": "Categorization completed",
            "newly_categorized": updated,
            "categories": [dict(row) for row in rows]
        }

    finally:
        connection.close()


# ==========================================
# GET JOBS WITH SEARCH AND FILTERS
# ==========================================

@app.get("/api/jobs")
def get_jobs(
    search: str = Query(default=""),
    city: str = Query(default=""),
    category: str = Query(default=""),
    job_type: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    connection = get_db()

    try:
        categorize_uncategorized_jobs(connection)

        sql = """
            SELECT *
            FROM jobs
            WHERE 1=1
        """

        params = []

        if search:
            sql += """
                AND (
                    role LIKE ?
                    OR company LIKE ?
                    OR category LIKE ?
                    OR description LIKE ?
                )
            """
            keyword = f"%{search}%"
            params.extend([
                keyword, keyword, keyword, keyword
            ])

        if city:
            sql += " AND city LIKE ?"
            params.append(f"%{city}%")

        if category:
            sql += " AND category LIKE ?"
            params.append(f"%{category}%")

        if job_type:
            sql += " AND job_type LIKE ?"
            params.append(f"%{job_type}%")

        count_sql = sql.replace(
            "SELECT *",
            "SELECT COUNT(*)",
            1
        )

        total = connection.execute(
            count_sql, params
        ).fetchone()[0]

        sql += """
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        rows = connection.execute(
            sql, params
        ).fetchall()

        return {
            "total": total,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "jobs": [dict(row) for row in rows]
        }

    finally:
        connection.close()


# ==========================================
# MAIN STATISTICS
# ==========================================

@app.get("/api/stats")
def get_stats():
    connection = get_db()

    try:
        categorize_uncategorized_jobs(connection)

        total = connection.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        verified = connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE verified = 1"
        ).fetchone()[0]

        cities = connection.execute("""
            SELECT COUNT(DISTINCT city)
            FROM jobs
            WHERE city IS NOT NULL
            AND TRIM(city) != ''
        """).fetchone()[0]

        companies = connection.execute(
            "SELECT COUNT(DISTINCT company) FROM jobs"
        ).fetchone()[0]

        internships = connection.execute("""
            SELECT COUNT(*)
            FROM jobs
            WHERE job_type LIKE '%intern%'
        """).fetchone()[0]

        return {
            "total_jobs": total,
            "verified_jobs": verified,
            "cities": cities,
            "companies": companies,
            "internships": internships
        }

    finally:
        connection.close()


# ==========================================
# CATEGORY STATISTICS
# ==========================================

@app.get("/api/categories")
def get_categories():
    connection = get_db()

    try:
        categorize_uncategorized_jobs(connection)

        rows = connection.execute("""
            SELECT category, COUNT(*) AS total
            FROM jobs
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

        return {
            "total_categories": len(rows),
            "categories": [dict(row) for row in rows]
        }

    finally:
        connection.close()


# ==========================================
# CITY STATISTICS
# ==========================================

@app.get("/api/cities")
def get_cities():
    connection = get_db()

    try:
        rows = connection.execute("""
            SELECT city, COUNT(*) AS total
            FROM jobs
            WHERE city IS NOT NULL
            AND TRIM(city) != ''
            GROUP BY city
            ORDER BY total DESC
        """).fetchall()

        return {
            "cities": [dict(row) for row in rows]
        }

    finally:
        connection.close()


# ==========================================
# VERIFIED JOBS
# ==========================================

@app.get("/api/verified-jobs")
def get_verified_jobs(
    limit: int = Query(default=50, ge=1, le=200)
):
    connection = get_db()

    try:
        rows = connection.execute("""
            SELECT *
            FROM jobs
            WHERE verified = 1
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return {
            "count": len(rows),
            "jobs": [dict(row) for row in rows]
        }

    finally:
        connection.close()


# ==========================================
# PROJECT INFORMATION
# ==========================================

@app.get("/api/about")
def about():
    return {
        "project": "FresherPulse AI",
        "purpose": "India fresher jobs and internships",
        "sources": ["Greenhouse", "Ashby", "Lever"],
        "features": [
            "Job collection",
            "Automatic categorization",
            "Search and filtering",
            "City statistics",
            "Company statistics",
            "Verified job filtering"
        ],
        "categorization_method": "Keyword-based classification"
    }
