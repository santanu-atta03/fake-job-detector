import os
import json
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

from data_loader import load_raw_data, clean_job_data, split_and_save_data, PROCESSED_DATA_DIR
from feature_engineering import create_scam_features, combine_features

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "ml" / "models"
ACTIVE_MODEL_DIR = MODEL_DIR / "embedding_model" if (MODEL_DIR / "embedding_model").is_dir() else MODEL_DIR


def load_joblib_artifact(path):
    """Load a joblib pickle artifact safely, mapping PyTorch CUDA tensors to CPU if CUDA is unavailable."""
    obj = None
    try:
        import torch
        if not torch.cuda.is_available():
            orig_load = torch.load
            def cpu_load(*args, **kwargs):
                kwargs["map_location"] = torch.device("cpu")
                return orig_load(*args, **kwargs)
            try:
                torch.load = cpu_load
                obj = joblib.load(path)
            finally:
                torch.load = orig_load
        else:
            obj = joblib.load(path)
    except Exception:
        obj = joblib.load(path)

    if hasattr(obj, "modules"):
        for m in obj.modules():
            if not hasattr(m, "module_input_name"):
                setattr(m, "module_input_name", "sentence_embedding")
            if not hasattr(m, "module_output_name"):
                setattr(m, "module_output_name", "sentence_embedding")

    return obj


def evaluate_model():
    """Evaluate trained model performance on test set and generate report."""
    test_path = PROCESSED_DATA_DIR / "test.csv"
    if not os.path.exists(test_path):
        print("Processed test set not found. Loading data loader...")
        raw_df = load_raw_data()
        cleaned_df = clean_job_data(raw_df)
        _, test_df = split_and_save_data(cleaned_df)
    else:
        test_df = pd.read_csv(test_path)

    print(f"Loaded test dataset shape: {test_df.shape}")

    # Load artifacts
    model_path = ACTIVE_MODEL_DIR / "xgboost_model.pkl" if (ACTIVE_MODEL_DIR / "xgboost_model.pkl").exists() else ACTIVE_MODEL_DIR / "model.pkl"
    model = load_joblib_artifact(model_path)
    threshold = load_joblib_artifact(ACTIVE_MODEL_DIR / "threshold.pkl")

    scam_features = create_scam_features(test_df)
    job_text = test_df["title"].fillna("") + " " + test_df["company_profile"].fillna("") + " " + test_df["description"].fillna("") + " " + test_df["requirements"].fillna("") + " " + test_df["benefits"].fillna("")

    if (ACTIVE_MODEL_DIR / "embedding_config.pkl").exists():
        embedding_config = load_joblib_artifact(ACTIVE_MODEL_DIR / "embedding_config.pkl")
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
        tfidf = load_joblib_artifact(ACTIVE_MODEL_DIR / "tfidf.pkl")
        text_vector = tfidf.transform(job_text)
        X_test = combine_features(text_vector, scam_features)

    y_test = test_df["fraudulent"].values

    # Predictions
    y_probs = model.predict_proba(X_test)[:, 1]
    y_preds = (y_probs >= threshold).astype(int)

    # Metrics calculation
    roc_auc = float(roc_auc_score(y_test, y_probs))
    pr_auc = float(average_precision_score(y_test, y_probs))
    prec = float(precision_score(y_test, y_preds, zero_division=0))
    rec = float(recall_score(y_test, y_preds, zero_division=0))
    f1 = float(f1_score(y_test, y_preds, zero_division=0))

    cm = confusion_matrix(y_test, y_preds)
    tn, fp, fn, tp = cm.ravel()

    report_str = classification_report(y_test, y_preds, target_names=["Legitimate", "Fraudulent"])

    metrics = {
        "test_samples": int(len(y_test)),
        "test_fraud_count": int(sum(y_test)),
        "decision_threshold": float(threshold),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }

    print("\n==============================================")
    print("           MODEL EVALUATION REPORT            ")
    print("==============================================")
    print(f"Test Samples: {metrics['test_samples']} (Fraudulent: {metrics['test_fraud_count']})")
    print(f"Decision Threshold: {metrics['decision_threshold']}")
    print(f"ROC-AUC Score:      {metrics['roc_auc']}")
    print(f"PR-AUC Score:       {metrics['pr_auc']}")
    print(f"Precision:          {metrics['precision']}")
    print(f"Recall:             {metrics['recall']}")
    print(f"F1-Score:           {metrics['f1_score']}")
    print("\nConfusion Matrix:")
    print(f"  TN: {tn:<6} FP: {fp}")
    print(f"  FN: {fn:<6} TP: {tp}")
    print("\nClassification Report:")
    print(report_str)

    report_path = MODEL_DIR / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=4)

    print(f"Evaluation report saved to {report_path}")
    return metrics


if __name__ == "__main__":
    evaluate_model()
