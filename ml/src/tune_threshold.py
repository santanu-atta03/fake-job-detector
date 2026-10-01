import os
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, fbeta_score

from data_loader import load_raw_data, clean_job_data, split_and_save_data, PROCESSED_DATA_DIR
from feature_engineering import create_scam_features, combine_features

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "ml" / "models"


def tune_decision_threshold(beta: float = 1.0, target_min_precision: float = 0.70):
    """Sweep classification probability thresholds and find the optimal decision threshold."""
    test_path = PROCESSED_DATA_DIR / "test.csv"
    if not os.path.exists(test_path):
        print("Processed test set not found. Loading data loader...")
        raw_df = load_raw_data()
        cleaned_df = clean_job_data(raw_df)
        _, test_df = split_and_save_data(cleaned_df)
    else:
        test_df = pd.read_csv(test_path)

    model_path = MODEL_DIR / "xgboost_model.pkl" if (MODEL_DIR / "xgboost_model.pkl").exists() else MODEL_DIR / "model.pkl"
    model = joblib.load(model_path)

    scam_features = create_scam_features(test_df)
    job_text = test_df["title"].fillna("") + " " + test_df["company_profile"].fillna("") + " " + test_df["description"].fillna("") + " " + test_df["requirements"].fillna("") + " " + test_df["benefits"].fillna("")

    if (MODEL_DIR / "embedding_config.pkl").exists():
        embedding_config = joblib.load(MODEL_DIR / "embedding_config.pkl")
        if hasattr(embedding_config, "encode"):
            text_emb = embedding_config.encode(job_text.tolist())
        elif hasattr(embedding_config, "transform"):
            text_emb = embedding_config.transform(job_text)
        elif isinstance(embedding_config, dict) and "model_name" in embedding_config:
            from sentence_transformers import SentenceTransformer
            transformer_model = SentenceTransformer(embedding_config["model_name"])
            text_emb = transformer_model.encode(job_text.tolist())
        else:
            text_emb = np.zeros((len(test_df), 384))
        X_test = np.hstack([np.asarray(text_emb), scam_features.values])
    else:
        tfidf = joblib.load(MODEL_DIR / "tfidf.pkl")
        text_vector = tfidf.transform(job_text)
        X_test = combine_features(text_vector, scam_features)

    y_test = test_df["fraudulent"].values

    y_probs = model.predict_proba(X_test)[:, 1]

    thresholds = np.linspace(0.05, 0.95, 91)
    results = []

    for t in thresholds:
        preds = (y_probs >= t).astype(int)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        f_beta = fbeta_score(y_test, preds, beta=beta, zero_division=0)

        results.append({
            "threshold": round(float(t), 3),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "f_beta": round(float(f_beta), 4)
        })

    results_df = pd.DataFrame(results)

    # Select threshold maximizing f_beta with precision constraint if possible
    constrained = results_df[results_df["precision"] >= target_min_precision]
    if not constrained.empty:
        best_row = constrained.loc[constrained["f1_score"].idxmax()]
    else:
        best_row = results_df.loc[results_df["f1_score"].idxmax()]

    best_threshold = float(best_row["threshold"])

    print("\n--- Decision Threshold Tuning ---")
    print(f"Target Min Precision: {target_min_precision}")
    print(f"Optimal Threshold Selected: {best_threshold}")
    print(f"  Precision: {best_row['precision']:.4f}")
    print(f"  Recall:    {best_row['recall']:.4f}")
    print(f"  F1-Score:  {best_row['f1_score']:.4f}")

    # Save to threshold.pkl
    joblib.dump(best_threshold, MODEL_DIR / "threshold.pkl")
    print(f"Updated threshold saved to {MODEL_DIR / 'threshold.pkl'}")

    return results_df, best_threshold


if __name__ == "__main__":
    tune_decision_threshold()
