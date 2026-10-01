def get_risk_level(fraud_probability : float) -> str:
    percentage = fraud_probability * 100
    if percentage < 30:
        return "Low"
    elif percentage < 60:
        return "Medium"
    elif percentage < 80:
        return "High"
    else:
        return "Very High"

def format_reason(reason : dict) -> str:
    feature = reason["feature"]
    impact = reason["impact"]
    value = reason["value"]
    
    if feature == "urgency_word_count":
        return (
            f"The posting uses excessive urgency "
            f"language ({int(value)} detected)."
        )
    if feature == "scam_keyword_count":
        return (
            f"Several suspicious or scam-related "
            f"keywords were detected ({int(value)} found)."
        )
    if feature == "suspicious_phrase_count":
        return (
            f"Suspicious phrases commonly associated "
            f"with job scams were detected ({int(value)} found)."
        )
    if feature == "missing_company_info":
        return (
            "Important company information appears "
            "to be missing."
        )

    if feature == "free_email_count":
        return (
            f"The posting contains a free email provider "
            f"such as Gmail or Yahoo ({int(value)} detected)."
        )

    if feature == "excessive_exclamation":
        return (
            "The posting uses an unusually high number "
            "of exclamation marks."
        )

    if feature == "excessive_caps":
        return (
            "The posting contains unusually high "
            "capitalization."
        )

    if feature == "work_from_home_count":
        return (
            "The posting contains strong work-from-home "
            "or remote-work language."
        )

    if feature == "url_count":
        return (
            f"The posting contains external links "
            f"({int(value)} detected)."
        )

    if feature == "email_count":
        return (
            f"Contact email addresses were detected "
            f"({int(value)} found)."
        )

    if feature == "salary_range_width":
        return (
            "The salary range is unusually broad."
        )


    if impact == "increases fraud risk":
        return (
            f"{reason['reason']} may increase "
            "the likelihood of fraud."
        )

    else:
        return (
            f"{reason['reason']} appears to reduce "
            "the likelihood of fraud."
        )
