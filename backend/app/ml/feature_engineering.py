import re
import numpy as np
import pandas as pd

from .domain_reputation import analyze_job_domains


URGENCY_WORDS = [
    "urgent",
    "urgently",
    "immediately",
    "immediate",
    "hurry",
    "asap",
    "now",
    "today",
    "quickly",
    "limited",
    "apply now",
    "act now",
    "start immediately"
]


MONEY_WORDS = [
    "earn",
    "income",
    "cash",
    "money",
    "profit",
    "commission",
    "payment",
    "bonus",
    "salary",
    "financial",
    "revenue"
]


SCAM_WORDS = [
    "no experience",
    "easy money",
    "quick money",
    "make money",
    "work from home",
    "get rich",
    "guaranteed income",
    "guaranteed job",
    "financial freedom",
    "instant income",
    "risk free",
    "investment opportunity",
    "wire transfer",
    "bank account",
    "western union",
    "cash deposit",
    "processing fee",
    "registration fee",
    "training fee",
    "send money"
]


SUSPICIOUS_PHRASES = [
    "no experience required",
    "make money fast",
    "easy money",
    "get rich",
    "guaranteed income",
    "guaranteed job",
    "work from home",
    "earn money",
    "financial freedom",
    "instant income",
    "quick cash",
    "limited positions",
    "apply immediately",
    "start immediately",
    "send your bank",
    "send money",
    "processing fee",
    "registration fee",
    "training fee",
    "western union"
]


FREE_EMAIL_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "protonmail.com",
    "mail.com"
]


def count_keywords(text, keywords):

    text = str(text).lower()

    return sum(
        text.count(keyword.lower())
        for keyword in keywords
    )


def extract_emails(text):

    return re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        str(text)
    )


def extract_email_domains(text):

    emails = extract_emails(text)

    return [
        email.split("@")[-1].lower()
        for email in emails
    ]


def count_free_emails(text):

    domains = extract_email_domains(text)

    return sum(
        domain in FREE_EMAIL_DOMAINS
        for domain in domains
    )


def suspicious_phrase_count(text):

    text = str(text).lower()

    return sum(
        phrase in text
        for phrase in SUSPICIOUS_PHRASES
    )


def create_scam_features(df):

    result = pd.DataFrame(index=df.index)

    text = (
        df["title"].fillna("").astype(str) + " " +
        df["company_profile"].fillna("").astype(str) + " " +
        df["description"].fillna("").astype(str) + " " +
        df["requirements"].fillna("").astype(str) + " " +
        df["benefits"].fillna("").astype(str)
    )

    text_lower = text.str.lower()

    result["text_length"] = text.str.len()

    result["word_count"] = (
        text.str.split().str.len()
    )

    result["sentence_count"] = (
        text.str.count(r"[.!?]")
    )

    result["exclamation_count"] = (
        text.str.count("!")
    )

    result["question_count"] = (
        text.str.count(r"\?")
    )

    result["special_char_count"] = (
        text.str.count(r"[^a-zA-Z0-9\s]")
    )

    result["uppercase_count"] = (
        text.str.count(r"[A-Z]")
    )

    result["uppercase_ratio"] = (
        result["uppercase_count"] /
        result["text_length"].replace(0, 1)
    )

    result["url_count"] = (
        text.str.count(r"https?://|www\.")
    )

    result["email_count"] = (
        text.str.count(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        )
    )

    result["urgency_word_count"] = text.apply(
        lambda x: count_keywords(
            x,
            URGENCY_WORDS
        )
    )

    result["money_word_count"] = text.apply(
        lambda x: count_keywords(
            x,
            MONEY_WORDS
        )
    )

    result["scam_keyword_count"] = text.apply(
        lambda x: count_keywords(
            x,
            SCAM_WORDS
        )
    )

    result["suspicious_phrase_count"] = (
        text.apply(
            suspicious_phrase_count
        )
    )

    result["work_from_home_count"] = (
        text_lower.str.count("work from home")
        +
        text_lower.str.count("remote")
    )

    if "salary_range" in df.columns:

        salary_text = (
            df["salary_range"]
            .fillna("")
            .astype(str)
        )

    else:

        salary_text = pd.Series(
            "",
            index=df.index
        )

    salary_numbers = salary_text.str.findall(
        r"\d+(?:\.\d+)?"
    )

    result["salary_number_count"] = (
        salary_numbers.str.len()
    )

    result["salary_min"] = salary_numbers.apply(
        lambda x:
        float(x[0])
        if len(x) >= 1
        else 0
    )

    result["salary_max"] = salary_numbers.apply(
        lambda x:
        float(x[1])
        if len(x) >= 2
        else (
            float(x[0])
            if len(x) == 1
            else 0
        )
    )

    result["salary_range_width"] = (
        result["salary_max"] -
        result["salary_min"]
    )

    result["has_company_profile"] = (
        df["company_profile"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.len() > 0
    ).astype(int)

    result["has_company_logo"] = (
        df["has_company_logo"]
        .fillna(0)
        .astype(int)
        if "has_company_logo" in df.columns
        else 0
    )

    result["has_questions"] = (
        df["has_questions"]
        .fillna(0)
        .astype(int)
        if "has_questions" in df.columns
        else 0
    )

    result["has_location"] = (
        df["location"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.len() > 0
    ).astype(int)

    result["has_employment_type"] = (
        df["employment_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.len() > 0
    ).astype(int)

    result["has_experience"] = (
        df["required_experience"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.len() > 0
    ).astype(int)

    result["has_education"] = (
        df["required_education"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.len() > 0
    ).astype(int)

    result["free_email_count"] = (
        text.apply(
            count_free_emails
        )
    )

    result["excessive_exclamation"] = (
        result["exclamation_count"] >= 3
    ).astype(int)

    result["excessive_caps"] = (
        result["uppercase_ratio"] > 0.20
    ).astype(int)

    result["missing_company_info"] = (
        (
            result["has_company_profile"] == 0
        )
        &
        (
            result["has_company_logo"] == 0
        )
    ).astype(int)

    result = result.replace(
        [np.inf, -np.inf],
        0
    )

    result = result.fillna(0)

    return result
