
import requests
import re
from html import unescape

boards = ["composio", "ema", "sycamore", "sardine", "secfix"]

keywords = [
    "intern",
    "new grad",
    "fresh grad",
    "graduate",
    "ai resident",
    "product engineer",
    "infrastructure engineer",
    "core ai engineer",
    "software engineer - backend"
]

for board in boards:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])

        for job in jobs:
            title = job.get("title", "")
            location = job.get("location", "")

            if any(word in title.lower() for word in keywords):
                description = (
                    job.get("descriptionPlain")
                    or job.get("descriptionHtml")
                    or job.get("description")
                    or ""
                )

                description = unescape(
                    re.sub(r"<[^>]+>", " ", description)
                )
                description = " ".join(description.split())

                print("\n" + "=" * 65)
                print("COMPANY:", board)
                print("ROLE:", title)
                print("LOCATION:", location)
                print("EMPLOYMENT:", job.get("employmentType"))
                print("PUBLISHED:", job.get("publishedAt"))
                print("APPLICATION:", job.get("applyUrl") or job.get("jobUrl"))
                print("DESCRIPTION:", description[:1800])

    except Exception as error:
        print(board, "ERROR:", error)
