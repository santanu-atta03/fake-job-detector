import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ml.domain_reputation import (
    extract_urls_and_domains,
    check_typosquatting,
    query_domain_rdap_age,
    analyze_job_domains
)
from app.ml.model_service import predict_job


def test_url_and_domain_extraction():
    sample_text = (
        "Check our site at https://careers.google.com/jobs or http://micros0ft-careers.xyz/apply. "
        "Email recruiter@amazon-jobs-hr.top for info."
    )
    extracted = extract_urls_and_domains(sample_text)
    domains = [e["domain"] for e in extracted]

    assert "google.com" in domains or "careers.google.com" in domains
    assert "micros0ft-careers.xyz" in domains
    assert "amazon-jobs-hr.top" in domains
    print("[PASSED] test_url_and_domain_extraction")


def test_typosquatting_detection():
    # Test Levenshtein / visual substitution
    r1 = check_typosquatting("micros0ft", "micros0ft.com")
    assert r1["is_typosquatted"] is True
    assert r1["matched_brand"] == "microsoft.com"

    # Test brand keyword squatting
    r2 = check_typosquatting("google-careers-portal", "google-careers-portal.xyz")
    assert r2["is_typosquatted"] is True
    assert r2["matched_brand"] == "google.com"

    # Test legitimate brand match
    r3 = check_typosquatting("google", "google.com")
    assert r3["is_typosquatted"] is False
    print("[PASSED] test_typosquatting_detection")


def test_rdap_domain_age():
    # Test known legitimate old domain
    res = query_domain_rdap_age("google.com")
    assert res["status"] in ["verified", "unverified"]
    if res["status"] == "verified":
        assert res["age_days"] > 365
        assert res["registration_date"] is not None
    print("[PASSED] test_rdap_domain_age")


def test_full_prediction_integration():
    job_posting = {
        "title": "Urgent Remote Data Analyst",
        "company_profile": "Global hiring partner at http://micros0ft-careers.xyz",
        "description": "Earn $5000/week! Apply now at http://amazon-jobs-portal.top or email HR at recruit@g00gle.com.",
        "requirements": "No experience needed.",
        "benefits": "High pay",
        "has_company_logo": 0
    }

    result = predict_job(job_posting)
    assert "domain_reputation" in result
    dom_rep = result["domain_reputation"]
    assert dom_rep["total_domains_found"] >= 2
    assert dom_rep["has_domain_risk"] is True
    assert dom_rep["typosquatting_count"] >= 1
    assert dom_rep["suspicious_tld_count"] >= 1

    # Check reasons
    assert any("Domain Warning" in reason or "domain" in reason.lower() for reason in result["reasons"])
    print("[PASSED] test_full_prediction_integration")


if __name__ == "__main__":
    print("Running URL & Domain Reputation Checks Unit Tests...")
    test_url_and_domain_extraction()
    test_typosquatting_detection()
    test_rdap_domain_age()
    test_full_prediction_integration()
    print("All Domain Reputation tests passed successfully!")
