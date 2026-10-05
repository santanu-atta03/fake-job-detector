import json
import re
import httpx
from bs4 import BeautifulSoup
from app.utils.url_parser import fetch_html, scrape_generic_url

async def scrape_indeed(url: str) -> dict:
    """Scrape job details from Indeed link."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    html_content = ""
    try:
        html_content = await fetch_html(url)
    except Exception:
        return await scrape_generic_url(url)

    soup = BeautifulSoup(html_content, "html.parser")

    title = None
    company = None
    location = None
    description = None
    salary = None

    # Try JSON-LD script tag
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

    # Indeed HTML Selectors
    if not title:
        title_el = (
            soup.select_one("h1.jobsearch-JobInfoHeader-title")
            or soup.select_one("[data-testid='jobsearch-JobInfoHeader-title']")
            or soup.select_one("h1")
        )
        if title_el:
            title = title_el.get_text(strip=True)

    if not company:
        comp_el = (
            soup.select_one("[data-testid='inlineHeader-companyName']")
            or soup.select_one(".jobsearch-InlineCompanyRating div")
            or soup.select_one("meta[property='og:site_name']")
        )
        if comp_el:
            company = comp_el.get("content") if comp_el.name == "meta" else comp_el.get_text(strip=True)

    if not location:
        loc_el = (
            soup.select_one("[data-testid='inlineHeader-companyLocation']")
            or soup.select_one(".jobsearch-JobInfoHeader-subtitle div")
        )
        if loc_el:
            location = loc_el.get_text(strip=True)

    if not description:
        desc_el = (
            soup.select_one("#jobDescriptionText")
            or soup.select_one(".jobsearch-jobDescriptionText")
        )
        if desc_el:
            description = desc_el.get_text(separator="\n", strip=True)

    if not salary:
        sal_el = soup.select_one("#salaryInfoAndJobType") or soup.select_one("[data-testid='attribute_snippet']")
        if sal_el:
            salary = sal_el.get_text(strip=True)

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
        "employment_type": "",
        "salary": salary or "",
        "salary_range": salary or "",
        "required_experience": "",
        "required_education": "",
        "has_company_logo": 1 if company else 0,
        "has_questions": 0,
        "skills": []
    }

