
import requests

boards = [
    "composio",
    "josys",
    "secfix",
    "ema",
    "sycamore",
    "sardine",
    "weave",
    "emergence",
    "almabase"
]

for board in boards:
    try:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        jobs = response.json().get("jobs", [])

        print(f"\n========== {board.upper()} ({len(jobs)} jobs) ==========")

        for job in jobs:
            title = job.get("title", "Unknown")
            location = job.get("location", "Unknown")
            print(f"{title} | {location}")

    except Exception as error:
        print(f"\n{board}: ERROR - {error}")
