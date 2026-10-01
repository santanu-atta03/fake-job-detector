import json
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

async def scrape_glassdoor(url: str) -> dict:
    """Scrape job details from Glassdoor link."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = None
    company = None
    location = None
    description = None
    salary = None

    # Check JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict) and data.get("@type") in ("JobPosting", "Posting"):
                title = title or data.get("title")
                description = description or data.get("description")
                if isinstance(data.get("hiringOrganization"), dict):
                    company = company or data["hiringOrganization"].get("name")
                if isinstance(data.get("jobLocation"), dict):
                    loc_addr = data["jobLocation"].get("address")
                    if isinstance(loc_addr, dict):
                        location = location or f"{loc_addr.get('addressLocality', '')}, {loc_addr.get('addressRegion', '')}".strip(", ")
                    elif isinstance(loc_addr, str):
                        location = location or loc_addr
        except Exception:
            pass

    # Glassdoor HTML Selectors
    if not title:
        title_el = (
            soup.select_one("[data-test='jobTitle']")
            or soup.select_one(".JobDetails_jobTitle__g5_34")
            or soup.select_one("h1")
        )
        if title_el:
            title = title_el.get_text(strip=True)

    if not company:
        comp_el = (
            soup.select_one("[data-test='employerName']")
            or soup.select_one(".EmployerProfile_employerName__d222P")
        )
        if comp_el:
            company = comp_el.get_text(strip=True)

    if not location:
        loc_el = (
            soup.select_one("[data-test='location']")
            or soup.select_one(".JobDetails_location__mS15n")
        )
        if loc_el:
            location = loc_el.get_text(strip=True)

    if not description:
        desc_el = (
            soup.select_one("[data-test='jobDescription']")
            or soup.select_one(".JobDetails_jobDescription__25NnH")
            or soup.select_one(".desc")
        )
        if desc_el:
            description = desc_el.get_text(separator="\n", strip=True)

    # Meta tag fallback
    if not title:
        og_t = soup.find("meta", property="og:title")
        if og_t and og_t.get("content"):
            title = og_t["content"]

    if not description:
        og_d = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_d and og_d.get("content"):
            description = og_d["content"]

    if description and ("<p>" in description or "<br>" in description or "<div>" in description):
        description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

    return {
        "title": title or "",
        "company": company or "",
        "company_profile": company or "",
        "location": location or "",
        "description": description or "",
        "requirements": "",
        "benefits": "",
        "employment_type": "",
        "salary": salary or "",
        "salary_range": salary or "",
        "required_experience": "",
        "required_education": "",
        "has_company_logo": 1 if company else 0,
        "has_questions": 0,
        "skills": []
    }
