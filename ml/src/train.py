import os
import time
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import roc_auc_score, f1_score

from data_loader import load_raw_data, clean_job_data, split_and_save_data, PROCESSED_DATA_DIR
from feature_engineering import create_scam_features, build_tfidf_vectorizer, combine_features

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "ml" / "models"

FEATURE_DESCRIPTIONS = {
    "urgency_word_count": "Excessive urgency language",
    "money_word_count": "Strong money-related language",
    "scam_keyword_count": "Suspicious or scam-related keywords",
    "suspicious_phrase_count": "Suspicious phrases commonly associated with job scams",
    "free_email_count": "Free email provider detected",
    "email_count": "Email contact information detected",
    "url_count": "External URL detected",
    "missing_company_info": "Company information appears to be missing",
    "has_company_profile": "Company profile information is available",
    "has_company_logo": "Company logo information is available",
    "excessive_exclamation": "Excessive use of exclamation marks",
    "excessive_caps": "Unusually high capitalization",
    "work_from_home_count": "Work-from-home or remote language detected",
    "salary_min": "Salary minimum detected",
    "salary_max": "Salary maximum detected",
    "salary_range_width": "Large salary range detected",
    "text_length": "Length of job posting",
    "word_count": "Number of words in job posting",
    "sentence_count": "Number of sentences",
    "question_count": "Number of question marks",
    "special_char_count": "Number of special characters",
    "uppercase_count": "Number of uppercase characters",
    "uppercase_ratio": "Ratio of uppercase characters",
    "salary_number_count": "Number of salary values",
    "has_questions": "Screening questions are provided",
    "has_location": "Job location is provided",
    "has_employment_type": "Employment type is provided",
    "has_experience": "Experience requirement is provided",
    "has_education": "Education requirement is provided"
}


def get_candidate_models():
    """Return dictionary of candidate machine learning models for comparison."""
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=150,
            max_depth=20,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=150,
            max_depth=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
    }

    # Attempt optional imports for XGBoost and LightGBM
    try:
        from xgboost import XGBClassifier
        models["XGBoost"] = XGBClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=15,
            random_state=42,
            eval_metric="logloss",
            n_jobs=-1
        )
    except ImportError:
        print("[Notice] XGBoost not installed. Using Scikit-Learn ensemble models.")

    try:
        from lightgbm import LGBMClassifier
        models["LightGBM"] = LGBMClassifier(
            n_estimators=150,
            learning_rate=0.1,
            scale_pos_weight=15,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    except ImportError:
        print("[Notice] LightGBM not installed. Using Scikit-Learn ensemble models.")

    return models


def train_and_select_best_model():
    """Train candidate models, evaluate cross-validation ROC-AUC, select best model, and export artifacts."""
    train_path = PROCESSED_DATA_DIR / "train.csv"
    if not os.path.exists(train_path):
        print("Processed train dataset not found. Running data loader...")
        raw_df = load_raw_data()
        cleaned_df = clean_job_data(raw_df)
        train_df, test_df = split_and_save_data(cleaned_df)
    else:
        train_df = pd.read_csv(train_path)

    print(f"Loaded training data: {train_df.shape}")

    # Build features
    scam_features = create_scam_features(train_df)
    scam_feature_names = list(scam_features.columns)

    tfidf_vectorizer = build_tfidf_vectorizer(train_df["job_text"], max_features=10000)
    text_vector = tfidf_vectorizer.transform(train_df["job_text"])
    tfidf_feature_names = [f"tfidf_{name}" for name in tfidf_vectorizer.get_feature_names_out()]

    X_train = combine_features(text_vector, scam_features)
    y_train = train_df["fraudulent"].values

    feature_names = tfidf_feature_names + scam_feature_names

    print(f"Combined Feature Matrix Shape: {X_train.shape}")

    # Candidate evaluation
    candidates = get_candidate_models()
    best_score = -1.0
    best_model_name = None
    best_model_obj = None

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print("\n--- Model Cross-Validation ---")
    for name, model in candidates.items():
        start_time = time.time()
        cv_scores = cross_val_score(model, X_train, y_train, cv=skf, scoring="roc_auc", n_jobs=-1)
        mean_score = np.mean(cv_scores)
        std_score = np.std(cv_scores)
        elapsed = time.time() - start_time
        print(f"Model: {name:<16} | 5-Fold ROC-AUC: {mean_score:.4f} (+/- {std_score:.4f}) | Time: {elapsed:.2f}s")

        if mean_score > best_score:
            best_score = mean_score
            best_model_name = name
            best_model_obj = model

    print(f"\n>>> Best Performing Model Selected: {best_model_name} (ROC-AUC: {best_score:.4f})")

    # Fit best model on full training set
    print(f"Fitting {best_model_name} on complete training dataset...")
    best_model_obj.fit(X_train, y_train)

    # Prepare export directory
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Default threshold
    default_threshold = 0.35

    config = {
        "best_model_name": best_model_name,
        "cv_roc_auc": float(best_score),
        "num_train_samples": int(X_train.shape[0]),
        "num_features": int(X_train.shape[1]),
        "default_threshold": default_threshold,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    joblib.dump(best_model_obj, MODEL_DIR / "model.pkl")
    joblib.dump(tfidf_vectorizer, MODEL_DIR / "tfidf.pkl")
    joblib.dump(default_threshold, MODEL_DIR / "threshold.pkl")
    joblib.dump(feature_names, MODEL_DIR / "feature_names.pkl")
    joblib.dump(scam_feature_names, MODEL_DIR / "scam_feature_names.pkl")
    joblib.dump(FEATURE_DESCRIPTIONS, MODEL_DIR / "feature_descriptions.pkl")
    joblib.dump(config, MODEL_DIR / "config.pkl")

    print(f"Successfully saved all model artifacts to {MODEL_DIR}")
    return best_model_name, best_score


if __name__ == "__main__":
    train_and_select_best_model()
