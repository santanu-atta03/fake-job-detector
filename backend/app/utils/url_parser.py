import json
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def parse_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

async def scrape_generic_url(url: str) -> dict:
    """Fallback scraper using OpenGraph metadata, JSON-LD, and basic HTML elements."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = None
    company = None
    description = None
    location = None
    salary = None

    # Check JSON-LD structured data
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
                if isinstance(data.get("baseSalary"), dict):
                    val = data["baseSalary"].get("value", {})
                    if isinstance(val, dict):
                        salary = salary or f"{val.get('minValue', '')} - {val.get('maxValue', '')} {val.get('unitText', '')}".strip()
        except Exception:
            pass

    # OpenGraph meta tags fallback
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
        else:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

    if not description:
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            description = og_desc["content"]

    if not company:
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            company = og_site["content"]

    # Clean HTML tags from description if present
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
