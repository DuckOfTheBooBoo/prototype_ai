# ONNX Model Conversion

This directory contains the converted ONNX model from the original scikit-learn RandomForestClassifier.

## Files

- `model.onnx` - Converted RandomForestClassifier model in ONNX format
- `metadata.json` - Model metadata including feature names and configuration

## Model Information

- **Type**: RandomForestClassifier
- **Features**: 373 input features
- **Classes**: 2 (binary classification: 0 = legitimate, 1 = fraud)
- **ONNX Opset**: 18
- **Conversion Date**: 2025-12-27

## Usage

### Quick Start

```python
import onnxruntime as ort

# Load ONNX model
session = ort.InferenceSession(
    'ai_model/model.onnx',
    providers=['CPUExecutionProvider']
)

# Get input/output names
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[1].name  # Probabilities output

# Prepare input data (float32, shape: [1, 373])
input_data = your_preprocessed_data.astype(np.float32)

# Run inference
result = session.run([output_name], {input_name: input_data})
fraud_probability = result[0][0, 1]
```

### Using the Helper Script

See `test_onnx_inference.py` for a complete example including preprocessing:

```python
from test_onnx_inference import predict_onnx

# Sample input
sample_input = {
    'TransactionAmt': 100.0,
    'ProductCD': 'W',
    'card1': 12345,
    # ... other features
}

# Run prediction
result = predict_onnx(sample_input)
print(result)
# Output: {
#   "fraud_probability": 0.2904,
#   "risk_level": "LOW",
#   "status": "APPROVE"
# }
```

## Preprocessing Requirements

The ONNX model expects preprocessed data (373 float32 features). Before inference, you must:

1. **Feature Engineering**:
   - Create `uid1` = `card1` + '_' + `addr1`
   - Lookup `card1_mean` and `card1_std` from `artifact_card1_stats.pkl`
   - Calculate ratios:
     - `TransactionAmt_to_mean_card1` = `TransactionAmt` / `card1_mean`
     - `TransactionAmt_to_std_card1` = `TransactionAmt` / `card1_std`

2. **Categorical Encoding**:
   - Encode 23 categorical features using `OrdinalEncoder` from `artifact_encoder.pkl`
   - Fill missing values with 'MISSING'

3. **Feature Alignment**:
   - Ensure all 373 features are present
   - Fill missing features with -999
   - Order features according to `metadata.json`

See `test_onnx_inference.py::preprocess_input()` for complete preprocessing logic.

## Conversion Script

To convert the model again or convert other models:

```bash
python convert_pkl_to_onnx.py \
  --model artifacts/artifact_model.pkl \
  --columns artifacts/artifact_columns.pkl \
  --output ai_model/
```

### Options

- `--model`: Path to model .pkl file (default: `artifacts/artifact_model.pkl`)
- `--columns`: Path to feature columns .pkl file (default: `artifacts/artifact_columns.pkl`)
- `--output`: Output directory (default: `ai_model/`)
- `--opset`: Target ONNX opset version (default: 18)
- `--no-validate`: Skip prediction validation

## Validation

The conversion was validated with test data:

- Sklearn probability: 0.258556
- ONNX probability: 0.258556
- Difference: 0.000000

Predictions match exactly with the original model.

## Performance

- ONNX Model Size: ~213 MB
- Inference time: Typically < 10ms per prediction on CPU
- Providers: CPUExecutionProvider (can use GPU with CUDAExecutionProvider)

## Notes

- Preprocessing (feature engineering, encoding) is done in Python before ONNX inference
- The model outputs raw probabilities (no zipmap)
- For production use, consider:
  - GPU acceleration with CUDAExecutionProvider
  - Model quantization for faster inference
  - Batch processing for multiple predictions
