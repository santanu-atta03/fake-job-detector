import pytest
from unittest.mock import patch, MagicMock

# Patch MongoDB connection before importing app.main
with patch("app.database.connection.test_connection"), patch("app.database.connection.jobs_collection"):
    from app.main import app
    from fastapi.testclient import TestClient

client = TestClient(app)


def test_user_reported_scam_posting():
    """Test the exact user prompt scenario:
    - 'No interview required'
    - 'Selected candidates must pay a $499 registration and training fee'
    - 'Urgently hiring'
    - 'No experience required'
    - '$150,000–$250,000 salary'
    - Structured '2+ years experience'
    Must produce VERY HIGH RISK with critical upfront payment finding.
    """
    job_data = {
        "title": "Data Entry Specialist",
        "company_profile": "Acme Global Solutions",
        "description": "Urgently hiring! No interview required. Selected candidates must pay a $499 registration and training fee before starting work. No experience required.",
        "requirements": "Must have computer access.",
        "benefits": "Flexible hours",
        "salary_range": "$150,000 - $250,000",
        "required_experience": "2+ years experience",
        "has_company_logo": 1,
        "has_questions": 0
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "fraudulent"
    assert data["risk_score"] >= 75
    assert data["risk_level"] == "Very High"
    assert data["riskLevel"] == "VERY_HIGH"
    assert data["classification"] == "SUSPICIOUS"

    # Verify findings contain upfront payment & no interview
    findings = data["findings"]
    assert len(findings) >= 2
    critical_findings = [f for f in findings if f["severity"] == "CRITICAL"]
    assert len(critical_findings) > 0
    assert any(f["category"] == "UPFRONT_PAYMENT" for f in critical_findings)
    assert any(f["category"] == "HIRING_PROCESS" for f in findings)
    assert any(f["category"] == "CONTRADICTION" for f in findings)


def test_corporate_software_engineer():
    """Test legitimate corporate software engineering job."""
    job_data = {
        "title": "Software Engineer",
        "company_profile": "TechCorp Inc. is a leading cloud infrastructure company.",
        "description": "We are seeking a Software Engineer to join our core backend team. You will build high performance microservices in Python and Go.",
        "requirements": "3+ years of experience with Python, Docker, and Kubernetes. BS in Computer Science.",
        "benefits": "Competitive salary, 401k matching, comprehensive health insurance.",
        "salary_range": "$120,000 - $150,000",
        "required_experience": "3+ years",
        "required_education": "Bachelor's Degree",
        "has_company_logo": 1,
        "has_questions": 1
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "legitimate"
    assert data["risk_score"] < 20
    assert data["risk_level"] == "Low"
    assert data["riskLevel"] == "LOW"
    assert data["classification"] == "LEGITIMATE"


def test_normal_remote_job():
    """Test legitimate remote job with salary range. Should NOT be marked fraudulent simply because it is remote."""
    job_data = {
        "title": "Remote Frontend Developer",
        "company_profile": "Innovate Digital Studios",
        "description": "Fully remote role. Build responsive web interfaces using React and TypeScript for global clients.",
        "requirements": "2+ years React experience, CSS, HTML5. Strong communication.",
        "benefits": "Remote stipend, flexible hours",
        "salary_range": "$80,000 - $110,000",
        "required_experience": "2+ years",
        "has_company_logo": 0,
        "has_questions": 0
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "legitimate"
    assert data["risk_score"] < 20
    assert data["classification"] == "LEGITIMATE"


def test_fake_check_reimbursement():
    """Test fake check / equipment purchase scam."""
    job_data = {
        "title": "Virtual Assistant",
        "company_profile": "Global Logistics LLC",
        "description": "We will issue a check deposit of $3,000 for you to purchase home office equipment from our approved vendor. Wire back the remaining funds.",
        "requirements": "Basic computer skills.",
        "salary_range": "$50,000",
        "has_company_logo": 0
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "fraudulent"
    assert data["risk_score"] >= 75
    assert any(f["category"] == "CHECK_SCAM" for f in data["findings"])


def test_telegram_only_recruiter():
    """Test recruiter requiring exclusive Telegram communication."""
    job_data = {
        "title": "Customer Service Representative",
        "company_profile": "Apex Media",
        "description": "Great remote job opportunity. Contact us via Telegram @ApexRecruiter to start your interview today.",
        "requirements": "High school diploma",
        "salary_range": "$30/hr"
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "fraudulent"
    assert any(f["category"] == "COMMUNICATION" for f in data["findings"])


def test_gmail_recruiter_impersonating_major_brand():
    """Test recruiter using Gmail email to impersonate Microsoft."""
    job_data = {
        "title": "Cloud Architect - Microsoft Project",
        "company_profile": "Microsoft Cloud Services",
        "description": "Join our Microsoft Cloud team! Please email your resume directly to microsoft.jobs.recruiting@gmail.com to apply.",
        "requirements": "Azure experience"
    }

    response = client.post("/api/v1/predict", json=job_data)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction"] == "fraudulent"
    assert any(f["category"] == "IMPERSONATION" for f in data["findings"])
