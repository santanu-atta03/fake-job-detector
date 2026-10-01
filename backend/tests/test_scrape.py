import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Patch MongoDB connection before importing app.main
with patch("app.database.connection.test_connection"), patch("app.database.connection.jobs_collection"):
    from app.main import app
    from fastapi.testclient import TestClient

client = TestClient(app)

def test_scrape_empty_url():
    response = client.post("/api/v1/scrape", json={"url": ""})
    assert response.status_code == 400

@patch("app.api.routes.scrape.scrape_job", new_callable=AsyncMock)
def test_scrape_success(mock_scrape):
    mock_scrape.return_value = {
        "title": "Software Engineer",
        "company": "Acme Corp",
        "company_profile": "Acme Corp",
        "location": "New York, NY",
        "description": "Great python position.",
        "requirements": "Python, FastAPI",
        "benefits": "Health, 401k",
        "employment_type": "Full-time",
        "salary": "$120,000 - $150,000",
        "salary_range": "$120,000 - $150,000",
        "required_experience": "3+ years",
        "required_education": "Bachelor's",
        "has_company_logo": 1,
        "has_questions": 0,
        "skills": ["Python", "FastAPI"]
    }

    response = client.post("/api/v1/scrape", json={"url": "https://www.linkedin.com/jobs/view/123456789"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Software Engineer"
    assert data["data"]["company"] == "Acme Corp"
