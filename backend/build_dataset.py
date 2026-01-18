import os
import re
import pandas as pd

# Define the keywords for auto-labeling
RISK_KEYWORDS = {
    "Data Retention": [
        "retain.*indefinitely", "store.*forever", "data.*preservation", 
        "keep.*information.*unlimited", "no.*deletion.*policy"
    ],
    "Data Sharing": [
        "sell.*data", "share.*partners", "third.*party.*marketing", 
        "disclose.*advertisers", "transfer.*information.*affiliates", 
        "exchange.*personal.*data"
    ],
    "User Rights": [
        "no.*right.*delete", "cannot.*remove.*account", "waive.*class.*action", 
        "arbitration.*only", "feedback.*property"
    ],
    "Legal & Liability": [
        "indemnify", "hold.*harmless", "no.*warranty", "liability.*limitation",
        "jurisdiction.*courts"
    ],
    "Safe": [
        "protect.*privacy", "encrypted", "not.*share.*personal", 
        "delete.*upon.*request", "adhere.*gdpr", "safe.*harbor"
    ]
}

def split_into_clauses(text):
    """Splits text into sentences/clauses."""
    # Simple split by punctuation
    clauses = re.split(r'(?<=[.!?])\s+', text)
    return [c.strip() for c in clauses if len(c) > 20] # Filter very short strings

def label_clause(clause):
    """Assigns a label based on regex keywords."""
    clause_lower = clause.lower()
    for category, patterns in RISK_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, clause_lower):
                return category
    return None # No label found

def build_dataset(data_dir):
    """Reads files, extracts clauses, labels them, and saves to CSV."""
    all_clauses = []
    all_labels = []
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
    print(f"Found {len(files)} files in {data_dir}. Processing...")
    
    for filename in files:
        path = os.path.join(data_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                clauses = split_into_clauses(text)
                
                for clause in clauses:
                    label = label_clause(clause)
                    if label:
                        all_clauses.append(clause)
                        all_labels.append(label)
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    # Create DataFrame
    df = pd.DataFrame({"text": all_clauses, "category": all_labels})
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["text"])
    
    print(f"\nGenerated dataset with {len(df)} labeled clauses.")
    print(df['category'].value_counts())
    
    # Save
    output_path = "dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    build_dataset("d:/ML/text")
