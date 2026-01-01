import pandas as pd
import numpy as np
import joblib
import os
from typing import Optional, Union


def load_test_data(transaction_path, identity_path):
    """
    Load and merge test data following training script approach.

    Args:
        transaction_path: Path to test_transaction.csv
        identity_path: Path to test_identity.csv

    Returns:
        Merged DataFrame ready for inference
    """
    print("Loading test data...")
    test_trans = pd.read_csv(transaction_path)
    test_id = pd.read_csv(identity_path)

    # Fix column names (replace hyphens with underscores)
    test_trans.columns = test_trans.columns.str.replace('-', '_')
    test_id.columns = test_id.columns.str.replace('-', '_')

    # Merge on TransactionID (left join = keep all transactions)
    print("Merging transaction and identity data...")
    test_merged = test_trans.merge(test_id, on='TransactionID', how='left')

    print(f"Test shape after merge: {test_merged.shape}")
    return test_merged


class FraudDetector:
    def __init__(
        self,
        artifact_path: str = './',
        hf_repo_id: Optional[str] = None,
        force_hf_download: bool = False
    ):
        """
        Initialize the FraudDetector with model artifacts.

        Args:
            artifact_path: Local path to the artifacts directory (ending with / or os.sep)
            hf_repo_id: HuggingFace repository ID for remote model loading.
                       If provided, models will be downloaded from HuggingFace.
            force_hf_download: If True, always re-download from HuggingForce.
        """
        self.artifact_path = artifact_path
        self.hf_repo_id = hf_repo_id

        # Try HuggingFace if repo_id is provided
        if hf_repo_id:
            self._load_from_huggingface(force_hf_download)
        else:
            # Load from local artifacts
            self._load_local_artifacts()

    def _load_local_artifacts(self):
        """Load artifacts from local filesystem."""
        # Ensure path ends with separator
        path = self.artifact_path
        if not path.endswith(os.sep):
            path = path + os.sep

        # Load the Artifact Bundle
        self.model = joblib.load(f'{path}artifact_model.pkl')
        self.encoder = joblib.load(f'{path}artifact_encoder.pkl')
        self.card_stats = joblib.load(f'{path}artifact_card1_stats.pkl')
        self.cat_cols = joblib.load(f'{path}artifact_cat_cols.pkl')
        self.final_columns = joblib.load(f'{path}artifact_columns.pkl')

    def _load_from_huggingface(self, force_download: bool = False):
        """Load artifacts from HuggingFace Hub."""
        try:
            from huggingface_utils import get_huggingface_downloader

            downloader = get_huggingface_downloader(
                repo_id=self.hf_repo_id,
                force_download=force_download
            )

            # Download all artifacts to local cache
            artifacts = downloader.download_all_artifacts()

            # Load the artifacts
            self.model = joblib.load(artifacts['artifact_model.pkl'])
            self.encoder = joblib.load(artifacts['artifact_encoder.pkl'])
            self.card_stats = joblib.load(artifacts['artifact_card1_stats.pkl'])
            self.cat_cols = joblib.load(artifacts['artifact_cat_cols.pkl'])
            self.final_columns = joblib.load(artifacts['artifact_columns.pkl'])

            print(f"Successfully loaded artifacts from HuggingFace: {self.hf_repo_id}")

        except ImportError:
            print("Warning: huggingface_utils not available, falling back to local artifacts")
            self._load_local_artifacts()
        except Exception as e:
            print(f"Warning: Failed to load from HuggingFace ({e}), falling back to local artifacts")
            self._load_local_artifacts()
        
    def preprocess(self, input_data):
        """
        Accepts a dictionary (single row) or DataFrame.
        Returns a formatted DataFrame ready for the model.
        """
        # 1. Convert dict to DataFrame if needed
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        else:
            df = input_data.copy()
            
        # 2. Engineer Interaction: uid1
        # Handle cases where addr1 might be missing
        c1 = df['card1'].fillna('MISSING').astype(str)
        a1 = df['addr1'].fillna('MISSING').astype(str)
        df['uid1'] = c1 + '_' + a1
        
        # 3. Feature Engineering via Lookup Table
        # We DO NOT groupby here. We look up the historical stats.
        
        # Helper to safely get stats
        def get_stat(card_id, metric):
            if card_id in self.card_stats:
                return self.card_stats[card_id].get(metric, np.nan)
            return np.nan # Unknown card? Return NaN
            
        # Apply Lookup
        df['card1_mean'] = df['card1'].apply(lambda x: get_stat(x, 'mean'))
        df['card1_std'] = df['card1'].apply(lambda x: get_stat(x, 'std'))
        
        # Calculate Ratios
        df['TransactionAmt_to_mean_card1'] = df['TransactionAmt'] / df['card1_mean']
        df['TransactionAmt_to_std_card1'] = df['TransactionAmt'] / df['card1_std']
        
        # Clean Infinity/NaN -> -999
        cols = ['TransactionAmt_to_mean_card1', 'TransactionAmt_to_std_card1']
        df[cols] = df[cols].replace([np.inf, -np.inf], -999).fillna(-999)
        
        # 4. Categorical Encoding
        # Must match training string format
        df[self.cat_cols] = df[self.cat_cols].fillna('MISSING').astype(str)

        # Transform (OrdinalEncoder handles unknown categories automatically now!)
        df[self.cat_cols] = self.encoder.transform(df[self.cat_cols])

        # Handle remaining string columns (id columns, DeviceType, DeviceInfo)
        # Convert them to numeric using factorize for compatibility
        for col in df.select_dtypes(include=['object']).columns:
            if col in self.final_columns:
                df[col] = pd.factorize(df[col].fillna('MISSING').astype(str))[0]

        # 5. Final Alignment
        # Ensure we have exactly the columns the model expects, in order
        # Fill any missing columns with -999 (e.g. if input JSON missed a field)
        for col in self.final_columns:
            if col not in df.columns:
                df[col] = -999
        
        # Select and Reorder
        return df[self.final_columns].fillna(-999)

    def _get_risk_level(self, prob):
        """Helper to get risk level from probability."""
        if prob > 0.8:
            return "CRITICAL"
        elif prob > 0.5:
            return "HIGH"
        else:
            return "LOW"

    def predict(self, input_data):
        # 1. Preprocess
        processed_df = self.preprocess(input_data)

        # 2. Predict Probability
        prob = self.model.predict_proba(processed_df)[:, 1][0]

        # 3. Post-Process (User Interpretation)
        risk_level = self._get_risk_level(prob)

        return {
            "fraud_probability": float(round(prob, 4)),
            "risk_level": risk_level,
            "status": "DENY" if prob > 0.5 else "APPROVE"
        }

    def predict_batch(self, df):
        """
        Run prediction on a DataFrame (batch mode).

        Args:
            df: DataFrame with raw transaction data

        Returns:
            DataFrame with original TransactionID and predictions
        """
        print(f"Preprocessing {len(df)} transactions...")

        # 1. Preprocess all rows at once
        processed_df = self.preprocess(df)

        print(f"Running inference...")
        # 2. Predict probabilities for all rows
        probs = self.model.predict_proba(processed_df)[:, 1]

        # 3. Create results DataFrame
        results = pd.DataFrame({
            'TransactionID': df['TransactionID'],
            'fraud_probability': probs,
            'risk_level': pd.Series(probs).apply(self._get_risk_level),
            'status': pd.Series(probs).apply(lambda p: 'DENY' if p > 0.5 else 'APPROVE')
        })

        return results

def main():
    """
    Main inference pipeline: Load data -> Preprocess -> Predict -> Save results.
    """
    # 1. Initialize detector with cross-platform path
    artifact_path = os.path.join('.', 'artifacts')
    detector = FraudDetector(artifact_path=artifact_path + os.sep)
    print("FraudDetector initialized successfully.")

    # 2. Load and merge test data with cross-platform paths
    base_path = os.path.join('.', 'content', 'ieee-fraud-detection')
    test_merged = load_test_data(
        os.path.join(base_path, 'test_transaction.csv'),
        os.path.join(base_path, 'test_identity.csv')
    )

    # 3. Run batch inference
    print("\n" + "=" * 60)
    print("RUNNING INFERENCE ON TEST DATA")
    print("=" * 60)

    results = detector.predict_batch(test_merged)

    # 4. Display summary statistics
    print("\n" + "=" * 60)
    print("PREDICTION SUMMARY")
    print("=" * 60)
    print(f"Total predictions: {len(results)}")
    print(f"\nRisk level distribution:")
    print(results['risk_level'].value_counts())
    print(f"\nFraud probability statistics:")
    print(results['fraud_probability'].describe())
    print(f"\nStatus distribution:")
    print(results['status'].value_counts())

    # 5. Save results
    output_file = 'test_predictions.csv'
    results.to_csv(output_file, index=False)
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}")

    # 6. Show sample predictions
    print("\nSample predictions (first 10):")
    print(results.head(10).to_string(index=False))


if __name__ == '__main__':
    main()