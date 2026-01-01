import joblib
import numpy as np
import warnings

warnings.filterwarnings('ignore')

def inspect_model():
    print("=" * 50)
    print("MODEL INSPECTION REPORT")
    print("=" * 50)
    
    try:
        print("\n[1/5] Loading artifacts...")
        model = joblib.load('artifacts/artifact_model.pkl')
        columns = joblib.load('artifacts/artifact_columns.pkl')
        encoder = joblib.load('artifacts/artifact_encoder.pkl')
        cat_cols = joblib.load('artifacts/artifact_cat_cols.pkl')
        card_stats = joblib.load('artifacts/artifact_card1_stats.pkl')
        
        print(f"   [OK] Model loaded: {model.__class__.__name__}")
        print(f"   [OK] Columns loaded: {len(columns)} features")
        print(f"   [OK] Encoder loaded: {encoder.__class__.__name__}")
        print(f"   [OK] Categorical columns: {len(cat_cols)}")
        print(f"   [OK] Card stats loaded: {len(card_stats)} entries")
        
        print("\n" + "=" * 50)
        print("MODEL DETAILS")
        print("=" * 50)
        
        print(f"\nType: {model.__class__.__name__}")
        print(f"Module: {model.__class__.__module__}")
        
        if hasattr(model, 'n_features_in_'):
            print(f"Input Features: {model.n_features_in_}")
        
        if hasattr(model, 'n_classes_'):
            print(f"Output Classes: {model.n_classes_}")
        
        if hasattr(model, 'classes_'):
            print(f"Classes: {model.classes_}")
        
        print(f"\nHyperparameters:")
        for key, value in model.get_params().items():
            if not key.startswith('_'):
                print(f"  - {key}: {value}")
        
        print("\n" + "=" * 50)
        print("ENCODER DETAILS")
        print("=" * 50)
        
        print(f"\nType: {encoder.__class__.__name__}")
        print(f"Module: {encoder.__class__.__module__}")
        
        if hasattr(encoder, 'n_features_in_'):
            print(f"Input Features: {encoder.n_features_in_}")
        
        if hasattr(encoder, 'categories_'):
            print(f"Categories per feature:")
            for i, cats in enumerate(encoder.categories_):
                print(f"  - Feature {i}: {len(cats)} categories")
        
        if hasattr(encoder, 'handle_unknown'):
            print(f"Handle Unknown: {encoder.handle_unknown}")
        
        if hasattr(encoder, 'dtype'):
            print(f"Output Dtype: {encoder.dtype}")
        
        print("\n" + "=" * 50)
        print("FEATURE INFORMATION")
        print("=" * 50)
        
        print(f"\nTotal Features: {len(columns)}")
        print(f"Categorical Features: {len(cat_cols)}")
        print(f"Numerical Features: {len(columns) - len(cat_cols)}")
        
        print(f"\nCategorical Columns:")
        for i, col in enumerate(cat_cols):
            print(f"  {i+1}. {col}")
        
        print("\n" + "=" * 50)
        print("CARD STATS INFORMATION")
        print("=" * 50)
        
        sample_card_id = list(card_stats.keys())[0]
        print(f"\nSample Card ID: {sample_card_id}")
        print(f"Metrics available: {list(card_stats[sample_card_id].keys())}")
        print(f"Total unique cards: {len(card_stats)}")
        
        print("\n" + "=" * 50)
        print("ONNX COMPATIBILITY CHECK")
        print("=" * 50)
        
        model_supported = False
        encoder_supported = False
        
        try:
            import skl2onnx
            from skl2onnx import convert_sklearn
            
            print(f"\nsklearn-onnx version: {skl2onnx.__version__}")
            
            supported_ops = skl2onnx.supported_converters()
            
            model_type = model.__class__.__name__
            encoder_type = encoder.__class__.__name__

            # Check with "Sklearn" prefix
            model_converter_name = f"Sklearn{model_type}"
            encoder_converter_name = f"Sklearn{encoder_type}"

            model_supported = model_converter_name in supported_ops
            encoder_supported = encoder_converter_name in supported_ops
            
            print(f"\nModel ({model_type}): {'[OK] Supported' if model_supported else '[X] NOT Supported'}")
            print(f"  Converter: {model_converter_name}")
            print(f"Encoder ({encoder_type}): {'[OK] Supported' if encoder_supported else '[X] NOT Supported'}")
            print(f"  Converter: {encoder_converter_name}")
            
            print("\n" + "=" * 50)
            print("RECOMMENDATION")
            print("=" * 50)
            
            if model_supported and encoder_supported:
                print("\n[OK] Model and Encoder are ONNX-compatible!")
                print("\nRecommended Conversion Strategy:")
                print("  1. Create sklearn Pipeline: Encoder + Model")
                print("  2. Convert pipeline to ONNX")
                print("  3. Keep feature engineering in Python:")
                print("     - uid1 creation (string concatenation)")
                print("     - card stats lookup (dictionary)")
                print("     - Ratio calculations")
                print("\nOutput Files:")
                print("  - ai_model/pipeline.onnx (encoder + model)")
                print("  - ai_model/metadata.json (feature info)")

            else:
                print("\n[X] Some components are not ONNX-compatible")
                if not model_supported:
                    print(f"  - Model ({model_type}) - Converter {model_converter_name} not found")
                if not encoder_supported:
                    print(f"  - Encoder ({encoder_type}) - Converter {encoder_converter_name} not found")
        
        except ImportError:
            print("\n[!] sklearn-onnx not installed")
            print("   Install with: pip install skl2onnx")
        
        print("\n" + "=" * 50)
        print("END OF REPORT")
        print("=" * 50)
        
        return {
            'model_type': model.__class__.__name__,
            'encoder_type': encoder.__class__.__name__,
            'n_features': len(columns),
            'n_categorical': len(cat_cols),
            'model_supported': model_supported,
            'encoder_supported': encoder_supported
        }
        
    except FileNotFoundError as e:
        print(f"\n[X] Error: File not found - {e}")
        return None
    except Exception as e:
        print(f"\n[X] Error during inspection: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    inspect_model()
