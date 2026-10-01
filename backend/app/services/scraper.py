from app.utils.url_parser import parse_domain, scrape_generic_url
from app.services.linkedin import scrape_linkedin
from app.services.indeed import scrape_indeed
from app.services.glassdoor import scrape_glassdoor

async def scrape_job(url: str) -> dict:
    """Scrape job posting data by routing to platform specific scraper or fallback."""
    domain = parse_domain(url)

    try:
        if "linkedin.com" in domain:
            data = await scrape_linkedin(url)
        elif "indeed.com" in domain:
            data = await scrape_indeed(url)
        elif "glassdoor.com" in domain:
            data = await scrape_glassdoor(url)
        else:
            data = await scrape_generic_url(url)

        # Fallback to generic url scraper if platform-specific scraper couldn't find a title or description
        if not data.get("title") and not data.get("description"):
            generic_data = await scrape_generic_url(url)
            for key, value in generic_data.items():
                if value and not data.get(key):
                    data[key] = value

        return data
    except Exception as e:
        # If platform scraping fails (e.g. anti-bot blocking), attempt generic fallback
        try:
            return await scrape_generic_url(url)
        except Exception:
            raise ValueError(f"Could not scrape job details from URL: {str(e)}")