from fastapi import APIRouter

from app.database.connection import jobs_collection
from app.schemas.job import JobCreate


router = APIRouter()

@router.post("/jobs")
def create_job(job : JobCreate):
    job_data = job.model_dump()
    
    result = jobs_collection.insert_one(job_data)
    return{
        "message" : "job saved successfully",
        "job_id" : str(result.inserted_id)
        
    }

@router.get("/jobs")
def get_job():
    jobs = list(jobs_collection.find())
    for job in jobs:
        job["_id"] = str(job["_id"])
    return jobs