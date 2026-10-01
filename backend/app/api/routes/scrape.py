from fastapi import APIRouter, HTTPException
from app.schemas.job import ScrapeRequest, ScrapeResponse
from app.services.scraper import scrape_job

router = APIRouter(tags=["Scraper"])

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    if not request.url or not request.url.strip():
        raise HTTPException(
            status_code=400,
            detail="URL is required"
        )
    
    try:
        job = await scrape_job(str(request.url).strip())
        return {
            "success": True,
            "data": job
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape the job: {str(e)}"
        )
