import json
import re
from urllib.parse import urlparse, unquote
import httpx
from bs4 import BeautifulSoup

HEADERS_CHROME = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1"
}

HEADERS_BOT = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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

def infer_data_from_url(url: str) -> dict:
    """Infer job title and company from URL path when scraping is blocked."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parse_domain(url)
    path = unquote(parsed.path).strip("/")

    title = ""
    company = ""

    # Check for LinkedIn pattern e.g. /jobs/view/senior-python-developer-at-acme-corp-12345
    match_linkedin = re.search(r'jobs/view/([a-zA-Z0-9-]+?)-(?:at-)?([a-zA-Z0-9-]+?)-?\d*$', path, re.IGNORECASE)
    if match_linkedin:
        slug_title = match_linkedin.group(1).replace("-", " ").title()
        slug_company = match_linkedin.group(2).replace("-", " ").title()
        if slug_title:
            title = slug_title
        if slug_company and slug_company.lower() not in ("view", "jobs"):
            company = slug_company

    if not title and path:
        parts = [p for p in path.split("/") if p]
        if parts:
            last_part = parts[-1]
            last_part = re.sub(r'\d+$', '', last_part).strip("-")
            if last_part and len(last_part) > 3 and not last_part.isdigit():
                title = last_part.replace("-", " ").replace("_", " ").title()

    if not company and domain:
        domain_name = domain.split(".")[0]
        if domain_name not in ("linkedin", "indeed", "glassdoor", "monster", "ziprecruiter", "careers"):
            company = domain_name.title()

    return {
        "title": title,
        "company": company,
        "company_profile": company,
        "location": "",
        "description": "",
        "requirements": "",
        "benefits": "",
        "employment_type": "",
        "salary": "",
        "salary_range": "",
        "required_experience": "",
        "required_education": "",
        "has_company_logo": 1 if company else 0,
        "has_questions": 0,
        "skills": []
    }

async def fetch_html(url: str) -> str:
    """Fetch HTML content using realistic browser headers with Googlebot fallback."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=HEADERS_CHROME)
            resp.raise_for_status()
            return resp.text
        except Exception:
            # Fallback to Googlebot user agent if standard request is blocked
            resp = await client.get(url, headers=HEADERS_BOT)
            resp.raise_for_status()
            return resp.text

async def scrape_generic_url(url: str) -> dict:
    """Fallback scraper using OpenGraph metadata, JSON-LD, and basic HTML elements."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    html_content = ""
    try:
        html_content = await fetch_html(url)
    except Exception:
        # Return URL inferred data if HTTP request fails completely
        return infer_data_from_url(url)

    soup = BeautifulSoup(html_content, "html.parser")

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

    # OpenGraph & meta tags fallback
    if not title:
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"]
        else:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

    if not description:
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"name": "twitter:description"})
        if og_desc and og_desc.get("content"):
            description = og_desc["content"]

    if not company:
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            company = og_site["content"]

    # HTML body elements fallback if description is empty
    if not description:
        desc_el = (
            soup.select_one("#job-details")
            or soup.select_one(".job-description")
            or soup.select_one(".description")
            or soup.select_one("article")
        )
        if desc_el:
            description = desc_el.get_text(separator="\n", strip=True)

    # Clean HTML tags from description if present
    if description and ("<p>" in description or "<br>" in description or "<div>" in description):
        description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

    # Fallback to URL inference if title or company is missing
    inferred = infer_data_from_url(url)
    if not title:
        title = inferred.get("title", "")
    if not company:
        company = inferred.get("company", "")

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

