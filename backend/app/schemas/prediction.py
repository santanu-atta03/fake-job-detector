from typing import List, Optional
from pydantic import BaseModel, Field

class JobPostingRequest(BaseModel):
    title: str = ""
    company_profile: str = ""
    description: str = ""
    requirements: str = ""
    benefits: str = ""
    salary_range: str = ""
    has_company_logo: int = Field(
        default=0,
        ge=0,
        le=1
    )
    has_questions: int = Field(
        default=0,
        ge=0,
        le=1
    )
    location: str = ""
    employment_type: str = ""
    required_experience: str = ""
    required_education: str = ""

class ExplanationReason(BaseModel):
    feature: str
    reason: str
    impact: str
    importance: float
    value: float

class RiskFinding(BaseModel):
    severity: str
    category: str
    title: str
    description: str
    evidence: Optional[str] = None
    weight: Optional[int] = 0

class DomainDetail(BaseModel):
    domain: str
    raw_url: str
    registration_date: Optional[str] = None
    registration_age_days: Optional[int] = None
    is_newly_registered: bool = False
    is_typosquatted: bool = False
    matched_brand: Optional[str] = None
    is_suspicious_tld: bool = False
    risk_score: int = 0
    flags: List[str] = []

class DomainReputationSummary(BaseModel):
    total_domains_found: int = 0
    domains: List[DomainDetail] = []
    has_domain_risk: bool = False
    typosquatting_count: int = 0
    newly_registered_count: int = 0
    suspicious_tld_count: int = 0

class PredictionResponse(BaseModel):
    prediction: str
    fraud_probability: float
    legitimate_probability: float
    risk_score: int
    risk_level: str
    riskLevel: str
    classification: str
    confidence: float
    threshold: float
    reasons: List[str]
    findings: List[RiskFinding] = []
    shap_details: List[ExplanationReason] = []
    domain_reputation: Optional[DomainReputationSummary] = None