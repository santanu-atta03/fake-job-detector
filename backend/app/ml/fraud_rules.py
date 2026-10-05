import re
from typing import Dict, List, Tuple, Any, Optional

# Known major brands for impersonation detection
MAJOR_BRANDS = {
    "microsoft": ["microsoft.com", "msft.com"],
    "google": ["google.com", "alphabet.com"],
    "apple": ["apple.com"],
    "amazon": ["amazon.com", "aws.com"],
    "meta": ["meta.com", "facebook.com"],
    "netflix": ["netflix.com"],
    "ibm": ["ibm.com"],
    "tesla": ["tesla.com"],
    "oracle": ["oracle.com"],
    "salesforce": ["salesforce.com"],
    "adobe": ["adobe.com"],
    "intel": ["intel.com"],
    "nvidia": ["nvidia.com"],
    "cisco": ["cisco.com"],
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com", "gmx.com"
}


def extract_evidence(text: str, pattern: str) -> Optional[str]:
    """Extract match snippet from text for evidence reporting."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        start = max(0, match.start() - 15)
        end = min(len(text), match.end() + 15)
        snippet = text[start:end].strip()
        # Clean up snippet
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return match.group(0)
    return None


def evaluate_job_rules(job_data: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Evaluates job data against weighted fraud rules, contradiction checks,
    payment extraction, and domain verification.
    
    Returns:
        total_risk_score: int (weighted sum of risk signals)
        findings: List of finding dicts
    """
    findings = []
    total_risk = 0

    title = str(job_data.get("title", "") or "")
    company = str(job_data.get("company_profile", "") or job_data.get("company", "") or "")
    desc = str(job_data.get("description", "") or "")
    reqs = str(job_data.get("requirements", "") or "")
    benefits = str(job_data.get("benefits", "") or "")
    salary_range = str(job_data.get("salary_range", "") or job_data.get("salary", "") or "")
    exp_req = str(job_data.get("required_experience", "") or "")
    edu_req = str(job_data.get("required_education", "") or "")

    full_text = f"{title} {company} {desc} {reqs} {benefits}".strip()
    full_text_lower = full_text.lower()

    # -------------------------------------------------------------------------
    # 1. HIGH SEVERITY SIGNALS (+25 to +45)
    # -------------------------------------------------------------------------

    # Signal 1A: Upfront Payment Request (+45)
    payment_patterns = [
        r'(?:pay|purchase|send|deposit|transfer|remit|reimburse)\s+(?:a\s+)?(?:\$\d+|\d+\s*dollars?|fee|cost|registration|training|equipment|kit|software|laptop)',
        r'(?:registration|training|application|processing|onboarding|equipment|background check|uniform)\s+fee',
        r'fee\s+of\s+\$\d+',
        r'\$\d+\s*(?:registration|training|application|processing|onboarding|equipment)\s+fee',
        r'purchase\s+(?:equipment|tools|materials|software)\s+from\s+our\s+vendor',
        r'pay\s+before\s+receiving',
        r'send\s+money\s+to\s+secure',
        r'candidate\s+must\s+pay'
    ]
    
    for pattern in payment_patterns:
        match_str = extract_evidence(full_text, pattern)
        if match_str:
            total_risk += 45
            findings.append({
                "severity": "CRITICAL",
                "category": "UPFRONT_PAYMENT",
                "title": "Upfront Payment or Fee Requested",
                "description": f"The posting requires job applicants to pay an upfront fee or purchase equipment prior to employment ({match_str}). Legitimate employers do not charge applicants fees.",
                "evidence": match_str,
                "weight": 45
            })
            break

    # Signal 1B: Fake Check / Overpayment Scheme (+45)
    check_patterns = [
        r'fake\s+check',
        r'check\s+deposit',
        r'send\s+(?:you\s+)?a\s+check\s+to\s+buy',
        r'cash\s+(?:the\s+)?check',
        r'wire\s+back\s+the\s+remaining',
        r'overpayment',
        r'deposit\s+check'
    ]
    for pattern in check_patterns:
        match_str = extract_evidence(full_text, pattern)
        if match_str:
            total_risk += 45
            findings.append({
                "severity": "CRITICAL",
                "category": "CHECK_SCAM",
                "title": "Check Deposit / Wire Scheme Detected",
                "description": "The posting mentions sending checks or depositing funds for purchasing equipment or wiring money back, a hallmark of fake check scams.",
                "evidence": match_str,
                "weight": 45
            })
            break

    # Signal 1C: Guaranteed Hiring / No Interview (+25)
    no_interview_patterns = [
        r'no\s+interview\s+required',
        r'no\s+interview\s+needed',
        r'instant\s+(?:job\s+)?offer',
        r'guaranteed\s+(?:job|employment|position)\s+without',
        r'hired\s+immediately\s+without\s+interview',
        r'no\s+formal\s+interview'
    ]
    for pattern in no_interview_patterns:
        match_str = extract_evidence(full_text, pattern)
        if match_str:
            total_risk += 25
            findings.append({
                "severity": "HIGH",
                "category": "HIRING_PROCESS",
                "title": "No Interview Required",
                "description": "The posting guarantees employment or an offer without a normal hiring process or interview.",
                "evidence": match_str,
                "weight": 25
            })
            break

    # Signal 1D: Request for Sensitive Information (+30)
    sensitive_patterns = [
        r'send\s+(?:your\s+)?(?:ssn|social\s+security|bank\s+account|credit\s+card|passport|routing\s+number)',
        r'financial\s+information\s+before',
        r'bank\s+details\s+required\s+prior'
    ]
    for pattern in sensitive_patterns:
        match_str = extract_evidence(full_text, pattern)
        if match_str:
            total_risk += 30
            findings.append({
                "severity": "HIGH",
                "category": "SENSITIVE_DATA",
                "title": "Request for Sensitive Financial Information",
                "description": "The posting requests sensitive financial or personal identification details before formal hiring.",
                "evidence": match_str,
                "weight": 30
            })
            break

    # Signal 1E: Recruiter Impersonation & Free Email Domain (+20 to +30)
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', full_text)
    full_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text)
    
    if full_emails:
        for full_email in full_emails:
            domain_part = full_email.split("@")[-1].lower()
            if domain_part in FREE_EMAIL_DOMAINS:
                # Check if text claims a major brand name
                impersonated_brand = None
                for brand in MAJOR_BRANDS:
                    if brand in full_text_lower and brand not in domain_part:
                        impersonated_brand = brand.title()
                        break
                
                if impersonated_brand:
                    total_risk += 30
                    findings.append({
                        "severity": "HIGH",
                        "category": "IMPERSONATION",
                        "title": f"Potential {impersonated_brand} Impersonation",
                        "description": f"The posting claims to represent {impersonated_brand}, but the recruiter uses a free email domain ({full_email}).",
                        "evidence": full_email,
                        "weight": 30
                    })
                else:
                    total_risk += 20
                    findings.append({
                        "severity": "HIGH",
                        "category": "RECRUITER_EMAIL",
                        "title": "Free Recruiter Email Domain",
                        "description": f"The recruitment contact uses a public free email address ({full_email}) rather than an official corporate domain.",
                        "evidence": full_email,
                        "weight": 20
                    })
                break

    # Signal 1F: Off-Platform Messaging Only (Telegram / WhatsApp) (+20)
    chat_patterns = [
        r'contact\s+(?:us\s+)?(?:via|on|through)\s+(?:telegram|whatsapp|signal)',
        r'interview\s+will\s+be\s+conducted\s+(?:on|via)\s+(?:telegram|whatsapp)',
        r'(?:telegram|whatsapp)\s+only',
        r'msg\s+us\s+on\s+telegram'
    ]
    for pattern in chat_patterns:
        match_str = extract_evidence(full_text, pattern)
        if match_str:
            total_risk += 20
            findings.append({
                "severity": "HIGH",
                "category": "COMMUNICATION",
                "title": "Exclusive Use of Messaging Apps",
                "description": "The employer requests interview or contact exclusively through messaging channels like Telegram or WhatsApp.",
                "evidence": match_str,
                "weight": 20
            })
            break

    # -------------------------------------------------------------------------
    # 2. MEDIUM SEVERITY SIGNALS (+10 to +15)
    # -------------------------------------------------------------------------

    # Signal 2A: Contradictions Detection (+10 each)
    has_no_exp_in_text = bool(re.search(r'no\s+(?:prior\s+)?experience\s+(?:required|needed)', full_text_lower))
    
    # Contradiction: Structured Experience vs Description
    if exp_req and has_no_exp_in_text:
        # Check if structured exp has numbers > 0
        exp_digits = re.findall(r'\d+', exp_req)
        if exp_digits and any(int(d) > 0 for d in exp_digits):
            total_risk += 10
            findings.append({
                "severity": "MEDIUM",
                "category": "CONTRADICTION",
                "title": "Inconsistent Experience Requirements",
                "description": f"Job requirements are inconsistent: the structured listing requires {exp_req} of experience, while the description states that no experience is required.",
                "evidence": f"Structured: '{exp_req}' | Text: 'No experience required'",
                "weight": 10
            })

    # Contradiction: Senior Role Title vs No Experience Required
    senior_titles = ["senior", "sr", "lead", "principal", "director", "vp", "manager", "head"]
    is_senior_role = any(st in title.lower() for st in senior_titles)
    if is_senior_role and has_no_exp_in_text:
        total_risk += 15
        findings.append({
            "severity": "MEDIUM",
            "category": "CONTRADICTION",
            "title": "Senior Title with No Experience Required",
            "description": f"The job title indicates a senior role ('{title}'), but the description states no experience is needed.",
            "evidence": f"Title: '{title}' | Requirement: 'No experience required'",
            "weight": 15
        })

    # Signal 2B: Unrealistic Compensation (+15)
    salary_nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', salary_range.replace(',', ''))]
    max_salary = max(salary_nums) if salary_nums else 0
    if max_salary > 1000 and max_salary < 10000:  # Hourly converted or monthly
        max_salary = max_salary * 12
        
    if (max_salary >= 150000 and has_no_exp_in_text) or max_salary >= 300000:
        total_risk += 15
        findings.append({
            "severity": "MEDIUM",
            "category": "COMPENSATION",
            "title": "Unusually High Compensation",
            "description": f"The specified salary range ({salary_range}) is disproportionately high for a role with minimal or no stated qualifications.",
            "evidence": salary_range,
            "weight": 15
        })

    # Signal 2C: High Urgency / Pressure Language (+10)
    urgency_match = extract_evidence(full_text, r'urgently\s+hiring|hire\s+immediately|apply\s+today\s+only|start\s+immediately|limited\s+positions')
    if urgency_match:
        total_risk += 10
        findings.append({
            "severity": "MEDIUM",
            "category": "URGENCY",
            "title": "High Urgency & Pressure Language",
            "description": "The posting uses urgent hiring language to pressure candidates into rapid action.",
            "evidence": urgency_match,
            "weight": 10
        })

    # Signal 2D: Vague Company Information (+10)
    if not company or len(company.strip()) < 10:
        total_risk += 10
        findings.append({
            "severity": "MEDIUM",
            "category": "COMPANY_INFO",
            "title": "Vague Company Information",
            "description": "The posting provides minimal or vague information about the hiring company.",
            "evidence": company if company else "Missing company profile",
            "weight": 10
        })

    # -------------------------------------------------------------------------
    # 3. LOW SEVERITY SIGNALS (+1 to +3)
    # -------------------------------------------------------------------------
    if len(salary_nums) >= 2 and (max(salary_nums) - min(salary_nums)) > 80000:
        total_risk += 3
        findings.append({
            "severity": "LOW",
            "category": "SALARY_RANGE",
            "title": "Broad Salary Range",
            "description": "The listing features an unusually wide compensation range.",
            "evidence": salary_range,
            "weight": 3
        })

    has_logo = int(job_data.get("has_company_logo", 0) or 0)
    if has_logo == 0 and total_risk > 0:
        total_risk += 1
        findings.append({
            "severity": "LOW",
            "category": "MISSING_LOGO",
            "title": "Missing Company Logo",
            "description": "The job posting does not include an official company logo.",
            "evidence": "No company logo provided",
            "weight": 1
        })

    has_questions = int(job_data.get("has_questions", 0) or 0)
    if has_questions == 0 and total_risk > 0:
        total_risk += 1
        findings.append({
            "severity": "LOW",
            "category": "MISSING_QUESTIONS",
            "title": "No Screening Questions",
            "description": "The listing does not include applicant screening questions.",
            "evidence": "No screening questions",
            "weight": 1
        })

    return total_risk, findings
