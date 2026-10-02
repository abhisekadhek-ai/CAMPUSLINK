import json
from urllib.request import Request, urlopen
from urllib.parse import quote


JOB_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_external_jobs(query: str = "", limit: int = 20):
    """
    Fetch publicly available jobs from an external job feed.
    This function does not modify the CampusLink database.
    """
    search_query = query.strip().lower()

    request = Request(
        JOB_API_URL,
        headers={"User-Agent": "CampusLink-Student-Portal/1.0"},
    )

    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

        jobs = []

        for item in payload.get("data", []):
            title = item.get("title", "")
            company = item.get("company_name", "")
            location = item.get("location", "")
            tags = item.get("tags", [])

            searchable_text = (
                f"{title} {company} {location} {' '.join(tags)}"
            ).lower()

            if search_query and search_query not in searchable_text:
                continue

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": item.get("url", ""),
                "tags": tags,
                "remote": item.get("remote", False),
                "created_at": item.get("created_at"),
                "source": "Arbeitnow",
            })

            if len(jobs) >= max(1, min(limit, 50)):
                break

        return jobs

    except Exception as exc:
        raise RuntimeError(
            f"External job service unavailable: {exc}"
        ) from exc