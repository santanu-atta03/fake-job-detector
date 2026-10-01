from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class ScrapeRequest(BaseModel):
    url: str

class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    salary: Optional[str] = None

class JobData(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    company_profile: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None
    salary_range: Optional[str] = None
    required_experience: Optional[str] = None
    required_education: Optional[str] = None
    has_company_logo: Optional[int] = 0
    has_questions: Optional[int] = 0
    skills: List[str] = []

class ScrapeResponse(BaseModel):
    success: bool
    data: JobData