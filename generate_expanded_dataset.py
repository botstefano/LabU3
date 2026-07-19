import pandas as pd
import numpy as np
from typing import List, Tuple

def load_existing_data(filepath: str) -> pd.DataFrame:
    """Load existing dataset"""
    return pd.read_csv(filepath)

def analyze_distribution(df: pd.DataFrame) -> dict:
    """Analyze distribution of features"""
    analysis = {}
    for col in df.columns:
        if col != 'label':
            analysis[col] = {
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'std': df[col].std(),
                'median': df[col].median()
            }
    return analysis

def generate_synthetic_samples(analysis: dict, n_samples: int) -> List[dict]:
    """Generate synthetic samples based on distribution analysis"""
    synthetic = []
    
    for _ in range(n_samples):
        # Generate features with realistic variation
        pct_facturas_vencidas = np.random.uniform(0.02, 0.75)
        pct_pagos_tardios = np.random.uniform(0.01, pct_facturas_vencidas * 0.9)
        
        # Correlated features
        if pct_facturas_vencidas > 0.35:
            dias_mora = np.random.uniform(15, 60)
            monto = np.random.uniform(500, 1200)
            cantidad = np.random.randint(2, 5)
            antiguedad = np.random.randint(15, 60)
            label = 1
        elif pct_facturas_vencidas > 0.20:
            dias_mora = np.random.uniform(8, 25)
            monto = np.random.uniform(800, 1500)
            cantidad = np.random.randint(3, 6)
            antiguedad = np.random.randint(30, 100)
            # Mixed label based on other factors
            if pct_pagos_tardios > 0.25 or dias_mora > 18:
                label = 1
            else:
                label = np.random.choice([0, 1], p=[0.7, 0.3])
        else:
            dias_mora = np.random.uniform(1, 12)
            monto = np.random.uniform(1200, 3000)
            cantidad = np.random.randint(5, 20)
            antiguedad = np.random.randint(80, 600)
            label = 0
        
        # Add some randomness to make it more realistic
        pct_facturas_vencidas = min(0.95, max(0.01, pct_facturas_vencidas + np.random.normal(0, 0.05)))
        pct_pagos_tardios = min(0.90, max(0.01, pct_pagos_tardios + np.random.normal(0, 0.03)))
        dias_mora = max(1, int(dias_mora + np.random.normal(0, 3)))
        monto = max(400, int(monto + np.random.normal(0, 200)))
        cantidad = max(2, min(30, int(cantidad + np.random.normal(0, 2))))
        antiguedad = max(15, min(800, int(antiguedad + np.random.normal(0, 50))))
        
        synthetic.append({
            'pct_facturas_vencidas': round(pct_facturas_vencidas, 2),
            'pct_pagos_tardios': round(pct_pagos_tardios, 2),
            'dias_mora_promedio': dias_mora,
            'monto_promedio_factura': monto,
            'cantidad_facturas': cantidad,
            'antiguedad_dias': antiguedad,
            'label': label
        })
    
    return synthetic

def expand_dataset(original_df: pd.DataFrame, synthetic_samples: List[dict]) -> pd.DataFrame:
    """Combine original and synthetic data"""
    synthetic_df = pd.DataFrame(synthetic_samples)
    combined = pd.concat([original_df, synthetic_df], ignore_index=True)
    
    # Shuffle the combined dataset
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    
    return combined

def main():
    # Load existing data
    print("Loading existing dataset...")
    original_df = load_existing_data('training_dataset_realistic.csv')
    print(f"Original dataset size: {len(original_df)} samples")
    
    # Analyze distribution
    print("Analyzing feature distributions...")
    analysis = analyze_distribution(original_df)
    
    # Generate synthetic samples
    target_size = 700
    n_synthetic = target_size - len(original_df)
    print(f"Generating {n_synthetic} synthetic samples...")
    
    synthetic_samples = generate_synthetic_samples(analysis, n_synthetic)
    
    # Combine datasets
    print("Combining datasets...")
    expanded_df = expand_dataset(original_df, synthetic_samples)
    
    # Save expanded dataset
    output_file = 'training_dataset_realistic.csv'
    expanded_df.to_csv(output_file, index=False)
    print(f"Expanded dataset saved to {output_file}")
    print(f"Final dataset size: {len(expanded_df)} samples")
    
    # Print class distribution
    print("\nClass distribution:")
    print(expanded_df['label'].value_counts())
    print(f"Class balance: {expanded_df['label'].mean():.2%} high risk")

if __name__ == "__main__":
    main()
