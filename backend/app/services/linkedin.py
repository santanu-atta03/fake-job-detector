import json
import re
import httpx
from bs4 import BeautifulSoup
from app.utils.url_parser import fetch_html, scrape_generic_url

HEADERS_LINKEDIN = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

async def scrape_linkedin(url: str) -> dict:
    """Scrape public LinkedIn job posting details."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    html_content = ""
    
    # Try fetching via LinkedIn public guest API if job ID is in URL
    job_id_match = re.search(r'(?:/jobs/view/|currentJobId=)(\d+)', url)
    if job_id_match:
        job_id = job_id_match.group(1)
        guest_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(guest_url, headers=HEADERS_LINKEDIN)
                if resp.status_code == 200 and resp.text:
                    html_content = resp.text
        except Exception:
            pass

    if not html_content:
        try:
            html_content = await fetch_html(url)
        except Exception:
            return await scrape_generic_url(url)

    soup = BeautifulSoup(html_content, "html.parser")

    title = None
    company = None
    location = None
    description = None
    employment_type = None
    salary = None

    # Check JSON-LD structured data first
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict) and data.get("@type") in ("JobPosting", "Posting"):
                title = title or data.get("title")
                description = description or data.get("description")
                employment_type = employment_type or data.get("employmentType")

                if isinstance(data.get("hiringOrganization"), dict):
                    company = company or data["hiringOrganization"].get("name")

                if isinstance(data.get("jobLocation"), dict):
                    loc_addr = data["jobLocation"].get("address")
                    if isinstance(loc_addr, dict):
                        location = location or f"{loc_addr.get('addressLocality', '')}, {loc_addr.get('addressRegion', '')}".strip(", ")
                    elif isinstance(loc_addr, str):
                        location = location or loc_addr

                if isinstance(data.get("baseSalary"), dict):
                    val = data["baseSalary"].get("value", {})
                    if isinstance(val, dict):
                        salary = salary or f"{val.get('minValue', '')} - {val.get('maxValue', '')} {val.get('unitText', '')}".strip()
        except Exception:
            pass

    # HTML selector fallback for LinkedIn public job cards
    if not title:
        title_el = (
            soup.select_one("h1.top-card-layout__title")
            or soup.select_one("h2.top-card-layout__title")
            or soup.select_one("h1.topcard__title")
            or soup.select_one("h1")
        )
        if title_el:
            title = title_el.get_text(strip=True)

    if not company:
        company_el = (
            soup.select_one(".topcard__org-name-link")
            or soup.select_one(".top-card-layout__first-sub-headline a")
            or soup.select_one(".topcard__flavor a")
        )
        if company_el:
            company = company_el.get_text(strip=True)

    if not location:
        loc_el = (
            soup.select_one(".topcard__flavor--bullet")
            or soup.select_one(".top-card-layout__first-sub-headline span:nth-of-type(2)")
        )
        if loc_el:
            location = loc_el.get_text(strip=True)

    if not description:
        desc_el = (
            soup.select_one(".show-more-less-html__markup")
            or soup.select_one(".description__text")
            or soup.select_one("#job-details")
        )
        if desc_el:
            description = desc_el.get_text(separator="\n", strip=True)

    # Clean description HTML tags if JSON-LD gave raw HTML
    if description and ("<p>" in description or "<br>" in description or "<div>" in description):
        description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

    # Has company logo signal check
    logo_el = soup.select_one("img.artdeco-entity-image") or soup.select_one("img.company-logo")
    has_logo = 1 if logo_el or company else 0

    # Fallback to generic url if main fields are missing
    if not title and not description:
        generic_data = await scrape_generic_url(url)
        title = title or generic_data.get("title")
        company = company or generic_data.get("company")
        description = description or generic_data.get("description")
        location = location or generic_data.get("location")

    return {
        "title": title or "",
        "company": company or "",
        "company_profile": company or "",
        "location": location or "",
        "description": description or "",
        "requirements": "",
        "benefits": "",
        "employment_type": employment_type or "",
        "salary": salary or "",
        "salary_range": salary or "",
        "required_experience": "",
        "required_education": "",
        "has_company_logo": has_logo,
        "has_questions": 0,
        "skills": []
    }