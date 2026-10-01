import os
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = BASE_DIR / "ml" / "data" / "raw" / "fake_job_postings.csv"
PROCESSED_DATA_DIR = BASE_DIR / "ml" / "data" / "processed"


def load_raw_data(filepath=RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw fake job postings dataset."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Raw data file not found at: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"Successfully loaded raw dataset. Shape: {df.shape}")
    return df


def clean_job_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean missing values and standardize text columns in the DataFrame."""
    df = df.copy()
    
    text_columns = [
        "title",
        "company_profile",
        "description",
        "requirements",
        "benefits"
    ]
    
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        else:
            df[col] = ""
            
    # Binary / Flag columns
    defaults = {
        "salary_range": "",
        "has_company_logo": 0,
        "has_questions": 0,
        "location": "",
        "employment_type": "",
        "required_experience": "",
        "required_education": "",
        "fraudulent": 0
    }
    
    for col, default in defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)
        else:
            df[col] = default

    # Combined text representation
    df["job_text"] = (
        df["title"] + " " +
        df["company_profile"] + " " +
        df["description"] + " " +
        df["requirements"] + " " +
        df["benefits"]
    )

    return df


def split_and_save_data(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
    """Perform stratified train/test split and save datasets to processed folder."""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df["fraudulent"]
    )
    
    train_path = PROCESSED_DATA_DIR / "train.csv"
    test_path = PROCESSED_DATA_DIR / "test.csv"
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"Train split saved to {train_path} (Shape: {train_df.shape}, Fraud: {train_df['fraudulent'].sum()})")
    print(f"Test split saved to {test_path} (Shape: {test_df.shape}, Fraud: {test_df['fraudulent'].sum()})")
    
    return train_df, test_df


def prepare_dataset():
    """Main execution function to load, clean, split, and save data."""
    df = load_raw_data()
    cleaned_df = clean_job_data(df)
    train_df, test_df = split_and_save_data(cleaned_df)
    return train_df, test_df


if __name__ == "__main__":
    prepare_dataset()
