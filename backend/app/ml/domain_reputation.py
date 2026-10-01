import re
import json
import socket
from datetime import datetime, timezone
import urllib.request
import urllib.error
from functools import lru_cache

# ============================================================
# CONSTANTS & CONFIGURATIONS
# ============================================================

# Common high-risk or suspicious TLDs frequently used in phishing/scams
SUSPICIOUS_TLDS = {
    "xyz", "top", "tk", "ml", "ga", "cf", "gq", "work", "click", "site",
    "online", "zip", "mov", "vip", "monster", "club", "buzz", "cc", "fit",
    "rest", "cam", "cx", "top", "space", "bid", "pw", "stream", "download"
}

# Free email domains that are common for personal emails
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com",
    "yandex.com", "zoho.com", "gmx.com", "live.com"
}

# Key global brands frequently targeted by job scam typosquatting
TARGET_BRANDS = {
    "google": "google.com",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "apple": "apple.com",
    "meta": "meta.com",
    "facebook": "facebook.com",
    "netflix": "netflix.com",
    "linkedin": "linkedin.com",
    "indeed": "indeed.com",
    "glassdoor": "glassdoor.com",
    "ibm": "ibm.com",
    "oracle": "oracle.com",
    "salesforce": "salesforce.com",
    "cisco": "cisco.com",
    "adobe": "adobe.com",
    "intel": "intel.com",
    "workday": "workday.com",
    "paypal": "paypal.com",
    "stripe": "stripe.com",
    "uber": "uber.com",
    "airbnb": "airbnb.com",
    "deloitte": "deloitte.com",
    "accenture": "accenture.com",
    "tcs": "tcs.com",
    "infosys": "infosys.com",
    "wipro": "wipro.com",
    "cognizant": "cognizant.com"
}

# Keywords indicative of fake HR / hiring portals
TYPOSQUATTING_KEYWORDS = [
    "careers", "jobs", "hr", "recruitment", "recruit", "hiring",
    "verify", "portal", "support", "interview", "onboarding", "workforce"
]


# ============================================================
# ALGORITHMIC UTILITIES
# ============================================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_homoglyphs(text: str) -> str:
    """Normalize common visual character substitutions (leetspeak/homoglyphs)."""
    substitutions = {
        '0': 'o',
        '1': 'l',
        '3': 'e',
        '4': 'a',
        '5': 's',
        '8': 'b',
        '@': 'a',
        '$': 's',
        'vv': 'w',
        'rn': 'm'
    }
    res = text.lower()
    for sub, repl in substitutions.items():
        res = res.replace(sub, repl)
    return res


def extract_registered_domain(domain_str: str) -> tuple[str, str, str]:
    """
    Extract (fully_qualified_domain, second_level_domain, top_level_domain).
    Example: 'sub.micros0ft-careers.com' -> ('sub.micros0ft-careers.com', 'micros0ft-careers', 'com')
    """
    clean_domain = domain_str.lower().strip()
    clean_domain = re.sub(r"^https?://", "", clean_domain)
    clean_domain = re.sub(r"^www\.", "", clean_domain)
    clean_domain = clean_domain.split("/")[0].split(":")[0]

    parts = clean_domain.split(".")
    if len(parts) < 2:
        return clean_domain, clean_domain, ""

    # Simple TLD and SLD extraction (handling double-tlds like co.uk)
    double_tlds = {"co.uk", "com.au", "co.in", "net.au", "org.uk", "gov.uk"}
    if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in double_tlds:
        tld = f"{parts[-2]}.{parts[-1]}"
        sld = parts[-3]
        registered_domain = f"{sld}.{tld}"
    else:
        tld = parts[-1]
        sld = parts[-2]
        registered_domain = f"{sld}.{tld}"

    return clean_domain, sld, tld


def extract_urls_and_domains(text: str) -> list[dict]:
    """Extract all URLs and email domain addresses from text."""
    if not text:
        return []

    text_str = str(text)

    # URL regex matching http, https, www, or clear standard URLs
    url_pattern = r"(?:https?://|www\.)[A-Za-z0-9.\-_]+(?::\d+)?(?:/[^\s<>\"]*)?"
    email_pattern = r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"

    raw_urls = re.findall(url_pattern, text_str, flags=re.IGNORECASE)
    email_matches = re.finditer(email_pattern, text_str, flags=re.IGNORECASE)

    results = []
    seen_domains = set()

    for url in raw_urls:
        clean_url = url.rstrip(".,;!?)")
        fqdn, sld, tld = extract_registered_domain(clean_url)
        registered_domain = f"{sld}.{tld}" if tld else fqdn

        if registered_domain and registered_domain not in seen_domains:
            seen_domains.add(registered_domain)
            results.append({
                "type": "url",
                "raw": clean_url,
                "domain": registered_domain,
                "sld": sld,
                "tld": tld
            })

    for match in email_matches:
        email_domain = match.group(1).lower()
        fqdn, sld, tld = extract_registered_domain(email_domain)
        registered_domain = f"{sld}.{tld}" if tld else fqdn

        if registered_domain and registered_domain not in seen_domains:
            # Skip free email providers from standalone domain threat analysis
            if registered_domain in FREE_EMAIL_DOMAINS:
                continue

            seen_domains.add(registered_domain)
            results.append({
                "type": "email_domain",
                "raw": match.group(0),
                "domain": registered_domain,
                "sld": sld,
                "tld": tld
            })

    return results


# ============================================================
# TYPOSQUATTING & BRAND IMPERSONATION CHECKER
# ============================================================

def check_typosquatting(sld: str, registered_domain: str) -> dict:
    """
    Check if second-level domain (SLD) or registered domain exhibits typosquatting,
    visual homoglyphs, or brand impersonation.
    """
    clean_sld = sld.lower()
    norm_sld = normalize_homoglyphs(clean_sld)

    for brand, official_domain in TARGET_BRANDS.items():
        official_sld = brand.lower()

        # If it's the exact legitimate official domain, skip
        if registered_domain.lower() == official_domain.lower():
            continue

        # 1. Direct Levenshtein Edit Distance Check (distance 1 or 2)
        dist = levenshtein_distance(clean_sld, official_sld)
        if 1 <= dist <= 2 and abs(len(clean_sld) - len(official_sld)) <= 2 and len(clean_sld) >= 4:
            return {
                "is_typosquatted": True,
                "matched_brand": official_domain,
                "reason": f"Typosquatting attempt detected targeting '{official_domain}' (edit distance: {dist})"
            }

        # 2. Homoglyph / Visual Substitution Match
        norm_dist = levenshtein_distance(norm_sld, official_sld)
        if norm_dist == 0 and clean_sld != official_sld:
            return {
                "is_typosquatted": True,
                "matched_brand": official_domain,
                "reason": f"Visual homoglyph/character substitution detected targeting '{official_domain}'"
            }

        # 3. Brand Keyword-Squatting (e.g. google-careers.com or amazon-jobs-hr.net)
        if official_sld in clean_sld:
            for kw in TYPOSQUATTING_KEYWORDS:
                if kw in clean_sld:
                    return {
                        "is_typosquatted": True,
                        "matched_brand": official_domain,
                        "reason": f"Brand impersonation attempt using brand name '{official_domain}' with key phrase '{kw}'"
                    }

    return {
        "is_typosquatted": False,
        "matched_brand": None,
        "reason": None
    }


# ============================================================
# RDAP REGISTRATION AGE CHECKER
# ============================================================

@lru_cache(maxsize=256)
def query_domain_rdap_age(domain: str) -> dict:
    """
    Fetch domain registration creation date via ICANN RDAP protocol.
    Returns domain registration age in days and creation date.
    """
    if not domain or "." not in domain:
        return {"registration_date": None, "age_days": None, "status": "invalid_domain"}

    # RDAP endpoint standard lookup
    rdap_url = f"https://rdap.org/domain/{domain}"

    try:
        req = urllib.request.Request(
            rdap_url,
            headers={"User-Agent": "FakeJobDetector-ReputationCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                events = payload.get("events", [])

                registration_date_str = None
                for event in events:
                    if event.get("eventAction") in ["registration", "created"]:
                        registration_date_str = event.get("eventDate")
                        break

                if registration_date_str:
                    # Parse ISO 8601 timestamp
                    clean_date_str = registration_date_str.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_date_str)
                    now = datetime.now(timezone.utc)

                    age_days = (now - dt).days
                    return {
                        "registration_date": dt.strftime("%Y-%m-%d"),
                        "age_days": max(0, age_days),
                        "status": "verified"
                    }

    except Exception:
        pass

    return {
        "registration_date": None,
        "age_days": None,
        "status": "unverified"
    }


# ============================================================
# MASTER DOMAIN REPUTATION EVALUATOR
# ============================================================

def analyze_job_domains(job_data: dict) -> dict:
    """
    Extract and evaluate all domain names and URLs in job posting fields.
    Returns detailed reputation analysis for each domain and overall risk metadata.
    """
    full_text = " ".join([
        str(job_data.get("title", "")),
        str(job_data.get("company_profile", "")),
        str(job_data.get("description", "")),
        str(job_data.get("requirements", "")),
        str(job_data.get("benefits", ""))
    ])

    extracted = extract_urls_and_domains(full_text)

    analyzed_domains = []
    has_typosquatting = False
    has_newly_registered = False
    has_suspicious_tld = False

    typosquatting_count = 0
    newly_registered_count = 0
    suspicious_tld_count = 0

    for item in extracted:
        domain = item["domain"]
        sld = item["sld"]
        tld = item["tld"]

        # Check typosquatting
        typo_res = check_typosquatting(sld, domain)
        if typo_res["is_typosquatted"]:
            has_typosquatting = True
            typosquatting_count += 1

        # Check TLD risk
        is_suspicious_tld_flag = tld.lower() in SUSPICIOUS_TLDS
        if is_suspicious_tld_flag:
            has_suspicious_tld = True
            suspicious_tld_count += 1

        # Check Domain Age via RDAP
        rdap_res = query_domain_rdap_age(domain)
        age_days = rdap_res["age_days"]
        is_new_flag = age_days is not None and age_days < 90
        if is_new_flag:
            has_newly_registered = True
            newly_registered_count += 1

        # Compile flags & risk score
        flags = []
        risk_score = 0

        if typo_res["is_typosquatted"]:
            flags.append(typo_res["reason"])
            risk_score += 45

        if is_suspicious_tld_flag:
            flags.append(f"Domain uses high-risk TLD (.{tld})")
            risk_score += 30

        if is_new_flag:
            if age_days < 30:
                flags.append(f"Domain registered extremely recently ({age_days} days ago)")
                risk_score += 40
            else:
                flags.append(f"Domain registered recently ({age_days} days ago)")
                risk_score += 25

        risk_score = min(100, risk_score)

        analyzed_domains.append({
            "domain": domain,
            "raw_url": item["raw"],
            "registration_date": rdap_res["registration_date"],
            "registration_age_days": age_days,
            "is_newly_registered": is_new_flag,
            "is_typosquatted": typo_res["is_typosquatted"],
            "matched_brand": typo_res["matched_brand"],
            "is_suspicious_tld": is_suspicious_tld_flag,
            "risk_score": risk_score,
            "flags": flags
        })

    has_domain_risk = has_typosquatting or has_newly_registered or has_suspicious_tld

    return {
        "total_domains_found": len(analyzed_domains),
        "domains": analyzed_domains,
        "has_domain_risk": has_domain_risk,
        "typosquatting_count": typosquatting_count,
        "newly_registered_count": newly_registered_count,
        "suspicious_tld_count": suspicious_tld_count
    }
