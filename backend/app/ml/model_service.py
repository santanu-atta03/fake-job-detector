import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from scipy.sparse import hstack, csr_matrix

from .feature_engineering import create_scam_features
from .domain_reputation import analyze_job_domains
from .explanation import (
    get_risk_level,
    format_reason
)



# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_VARIANT = os.getenv("MODEL_VARIANT", "tfidf").strip().lower()

if MODEL_VARIANT not in {"tfidf", "embedding"}:
    raise ValueError(
        "MODEL_VARIANT must be either 'tfidf' or 'embedding'"
    )

if MODEL_VARIANT == "embedding":
    ACTIVE_MODEL_DIR = MODEL_DIR / "embedding_model"
else:
    ACTIVE_MODEL_DIR = MODEL_DIR


def load_joblib_artifact(path, map_torch_to_cpu=False):
    if not map_torch_to_cpu:
        return joblib.load(path)

    import torch

    if torch.cuda.is_available():
        obj = joblib.load(path)
    else:
        orig_load = torch.load

        def cpu_load(*args, **kwargs):
            kwargs["map_location"] = torch.device("cpu")
            return orig_load(*args, **kwargs)

        try:
            torch.load = cpu_load
            obj = joblib.load(path)
        finally:
            torch.load = orig_load

    # Compatibility fix for SentenceTransformer objects pickled across different version boundaries
    if hasattr(obj, "modules"):
        for m in obj.modules():
            if not hasattr(m, "module_input_name"):
                setattr(m, "module_input_name", "sentence_embedding")
            if not hasattr(m, "module_output_name"):
                setattr(m, "module_output_name", "sentence_embedding")

    return obj


# ============================================================
# LOAD MODEL ARTIFACTS
# ============================================================

print(f"Loading Fake Job Detector from {ACTIVE_MODEL_DIR}...")

map_torch_to_cpu = MODEL_VARIANT == "embedding"
model_filename = "xgboost_model.pkl" if map_torch_to_cpu else "model.pkl"
model = load_joblib_artifact(
    ACTIVE_MODEL_DIR / model_filename,
    map_torch_to_cpu=map_torch_to_cpu,
)

embedding_config_path = ACTIVE_MODEL_DIR / "embedding_config.pkl"
tfidf_path = ACTIVE_MODEL_DIR / "tfidf.pkl"

if embedding_config_path.exists():
    tfidf = None
    embedding_config = load_joblib_artifact(
        embedding_config_path,
        map_torch_to_cpu=map_torch_to_cpu,
    )
elif tfidf_path.exists():
    tfidf = load_joblib_artifact(
        tfidf_path,
        map_torch_to_cpu=map_torch_to_cpu,
    )
    embedding_config = None
else:
    tfidf = None
    embedding_config = None

threshold = load_joblib_artifact(
    ACTIVE_MODEL_DIR / "threshold.pkl",
    map_torch_to_cpu=map_torch_to_cpu,
)

feature_names = load_joblib_artifact(
    ACTIVE_MODEL_DIR / "feature_names.pkl",
    map_torch_to_cpu=map_torch_to_cpu,
)

scam_feature_names = load_joblib_artifact(
    ACTIVE_MODEL_DIR / "scam_feature_names.pkl",
    map_torch_to_cpu=map_torch_to_cpu,
)

feature_descriptions = load_joblib_artifact(
    ACTIVE_MODEL_DIR / "feature_descriptions.pkl",
    map_torch_to_cpu=map_torch_to_cpu,
)

config = load_joblib_artifact(
    ACTIVE_MODEL_DIR / "config.pkl",
    map_torch_to_cpu=map_torch_to_cpu,
)


# ============================================================
# SHAP EXPLAINER
# ============================================================

print("Creating SHAP explainer...")


explainer = shap.TreeExplainer(
    model
)


print("Model loaded successfully.")


# ============================================================
# HUMAN-READABLE FEATURE NAMES
# ============================================================

FEATURE_DESCRIPTIONS = {

    "urgency_word_count":
        "Excessive urgency language",

    "money_word_count":
        "Strong money-related language",

    "scam_keyword_count":
        "Suspicious or scam-related keywords",

    "suspicious_phrase_count":
        "Suspicious phrases commonly associated with job scams",

    "free_email_count":
        "Free email provider detected",

    "email_count":
        "Email contact information detected",

    "url_count":
        "External URL detected",

    "missing_company_info":
        "Company information appears to be missing",

    "has_company_profile":
        "Company profile information is available",

    "has_company_logo":
        "Company logo information is available",

    "excessive_exclamation":
        "Excessive use of exclamation marks",

    "excessive_caps":
        "Unusually high capitalization",

    "work_from_home_count":
        "Work-from-home or remote language detected",

    "salary_min":
        "Salary information detected",

    "salary_max":
        "Salary information detected",

    "salary_range_width":
        "Large salary range detected",

    "text_length":
        "Length of job posting",

    "word_count":
        "Number of words in job posting",

    "sentence_count":
        "Number of sentences",

    "question_count":
        "Number of question marks",

    "special_char_count":
        "Number of special characters",

    "uppercase_count":
        "Number of uppercase characters",

    "uppercase_ratio":
        "Ratio of uppercase characters",

    "salary_number_count":
        "Number of salary values",

    "has_questions":
        "Screening questions are provided",

    "has_location":
        "Job location is provided",

    "has_employment_type":
        "Employment type is provided",

    "has_experience":
        "Experience requirement is provided",

    "has_education":
        "Education requirement is provided",

    "has_suspicious_domain":
        "Suspicious domain or link detected in posting",

    "typosquatting_domain_count":
        "Typosquatted domain / brand impersonation attempt detected",

    "newly_registered_domain_count":
        "Newly registered domain detected",

    "suspicious_tld_count":
        "High-risk top-level domain (TLD) detected"
}


def humanize_feature(feature):

    if feature in FEATURE_DESCRIPTIONS:

        return FEATURE_DESCRIPTIONS[
            feature
        ]

    return (
        feature
        .replace("_", " ")
        .title()
    )


# ============================================================
# PREPARE JOB DATA
# ============================================================

def prepare_job_data(job_data):

    df = pd.DataFrame(
        [job_data]
    )


    # --------------------------------------------------------
    # Text fields
    # --------------------------------------------------------

    text_columns = [
        "title",
        "company_profile",
        "description",
        "requirements",
        "benefits"
    ]


    for column in text_columns:

        if column not in df.columns:

            df[column] = ""


        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
        )


    # --------------------------------------------------------
    # Optional fields
    # --------------------------------------------------------

    defaults = {

        "salary_range": "",

        "has_company_logo": 0,

        "has_questions": 0,

        "location": "",

        "employment_type": "",

        "required_experience": "",

        "required_education": ""
    }


    for column, default in defaults.items():

        if column not in df.columns:

            df[column] = default


    return df


# ============================================================
# BUILD MODEL INPUT
# ============================================================

def build_model_input(df):

    # --------------------------------------------------------
    # Combine text
    # --------------------------------------------------------

    df["job_text"] = (
        df["title"] + " " +
        df["company_profile"] + " " +
        df["description"] + " " +
        df["requirements"] + " " +
        df["benefits"]
    )

    scam_features = create_scam_features(df)

    if embedding_config is not None:
        if hasattr(embedding_config, "encode"):
            text_emb = embedding_config.encode(df["job_text"].tolist())
        elif hasattr(embedding_config, "transform"):
            text_emb = embedding_config.transform(df["job_text"])
        elif isinstance(embedding_config, dict) and "model_name" in embedding_config:
            try:
                from sentence_transformers import SentenceTransformer
                transformer_model = SentenceTransformer(embedding_config["model_name"])
                text_emb = transformer_model.encode(df["job_text"].tolist())
            except Exception:
                text_emb = np.zeros((len(df), 384))
        elif isinstance(embedding_config, np.ndarray):
            text_emb = embedding_config
        else:
            text_emb = np.zeros((len(df), 384))

        text_emb = np.asarray(text_emb)
        if text_emb.ndim == 1:
            text_emb = text_emb.reshape(1, -1)

        combined_vector = np.hstack([text_emb, scam_features.values])
        return combined_vector, scam_features

    elif tfidf is not None:
        text_vector = tfidf.transform(df["job_text"])
        scam_vector = csr_matrix(scam_features.values)
        combined_vector = hstack([text_vector, scam_vector]).tocsr()
        return combined_vector, scam_features

    else:
        scam_vector = csr_matrix(scam_features.values)
        return scam_vector, scam_features


# ============================================================
# EXTRACT SHAP REASONS
# ============================================================

def get_shap_reasons(
    combined_vector,
    top_n=5
):

    # --------------------------------------------------------
    # Calculate SHAP
    # --------------------------------------------------------

    shap_values = explainer.shap_values(
        combined_vector
    )

    shap_values = (
        shap_values
        .reshape(-1)
    )

    # --------------------------------------------------------
    # Get actual feature values
    # --------------------------------------------------------

    if hasattr(combined_vector, "toarray"):
        feature_values = combined_vector.toarray().reshape(-1)
    else:
        feature_values = np.asarray(combined_vector).reshape(-1)


    # --------------------------------------------------------
    # Create dataframe
    # --------------------------------------------------------

    explanation = pd.DataFrame({

        "feature":
            feature_names,

        "shap_value":
            shap_values,

        "feature_value":
            feature_values
    })


    # --------------------------------------------------------
    # Only consider features that
    # actually affected this prediction
    # --------------------------------------------------------

    explanation = explanation[
        explanation["feature_value"] != 0
    ]


    # --------------------------------------------------------
    # Sort by absolute SHAP value
    # --------------------------------------------------------

    explanation["abs_shap"] = (
        explanation["shap_value"]
        .abs()
    )


    explanation = (
        explanation
        .sort_values(
            "abs_shap",
            ascending=False
        )
    )


    # --------------------------------------------------------
    # Create human-readable reasons
    # --------------------------------------------------------

    reasons = []


    for _, row in explanation.iterrows():

        feature = row["feature"]

        shap_value = row["shap_value"]

        feature_value = row[
            "feature_value"
        ]


        # Ignore extremely small contributions

        if abs(shap_value) < 0.01:

            continue


        reasons.append({

            "feature":
                feature,

            "reason":
                humanize_feature(
                    feature
                ),

            "impact":
                (
                    "increases fraud risk"
                    if shap_value > 0
                    else "decreases fraud risk"
                ),

            "importance":
                round(
                    float(abs(shap_value)),
                    4
                ),

            "value":
                float(feature_value)
        })


        if len(reasons) >= top_n:

            break


    return reasons


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_job(job_data):

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    df = prepare_job_data(
        job_data
    )


    # --------------------------------------------------------
    # Build features
    # --------------------------------------------------------

    combined_vector, scam_features = (
        build_model_input(df)
    )


    # --------------------------------------------------------
    # Model probability
    # --------------------------------------------------------

    fraud_probability = (
        model
        .predict_proba(
            combined_vector
        )[0, 1]
    )


    domain_reputation = analyze_job_domains(job_data)

    # Adjust fraud probability if domain risk anomalies (typosquatting, newly registered, high-risk TLD) are present
    if domain_reputation.get("typosquatting_count", 0) > 0:
        fraud_probability = max(fraud_probability, 0.88)
    elif domain_reputation.get("newly_registered_count", 0) > 0 or domain_reputation.get("suspicious_tld_count", 0) > 0:
        fraud_probability = max(fraud_probability, 0.65)

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    prediction = (

        "fraudulent"

        if fraud_probability >= threshold

        else "legitimate"
    )

    # --------------------------------------------------------
    # SHAP explanation & Human reasons
    # --------------------------------------------------------

    reasons = get_shap_reasons(
        combined_vector,
        top_n=5
    )

    risk_level = get_risk_level(
        fraud_probability
    )
    human_reasons = [

        format_reason(reason)

        for reason in reasons

        if reason["impact"] == "increases fraud risk"
    ]
    
    # Add high-level domain risk findings to human reasons
    if domain_reputation.get("has_domain_risk"):
        for dom in domain_reputation.get("domains", []):
            for flag in dom.get("flags", []):
                domain_msg = f"Domain Warning ({dom['domain']}): {flag}"
                if domain_msg not in human_reasons:
                    human_reasons.append(domain_msg)


    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "prediction":
            prediction,
        "fraud_probability":
            round(
                float(fraud_probability * 100),
                2
            ),

        "legitimate_probability":
            round(
                float(
                    (1 - fraud_probability) * 100
                ),
                2
            ),

        "risk_level":
            risk_level,

        "threshold":
            round(
                float(threshold * 100),
                2
            ),

        "reasons":
            human_reasons,

        "shap_details":
            reasons,

        "domain_reputation":
            domain_reputation
    }
