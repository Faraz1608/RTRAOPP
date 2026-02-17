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
        "no.*right.*delete", "cannot.*remove.*account", "waive", 
        "feedback.*property", "unable.*to.*opt-out"
    ],
    "Legal & Liability": [
        "indemnify", "hold.*harmless", "no.*warranty", "liability.*limitation",
        "jurisdiction.*courts"
    ],
    "Forced Arbitration": [
        "arbitration", "class.*action.*waiver", "resolve.*disputes.*arbitration",
        "waive.*right.*trial", "binding.*arbitration"
    ],
    "Third-Party Tracking": [
        "third-party.*cookies", "tracking.*pixels", "web.*beacons",
        "advertising.*id", "cross-site.*tracking"
    ],
    "Biometric Data": [
        "biometric", "facial.*recognition", "fingerprint", "voice.*print",
        "dna", "retina.*scan"
    ],
    "IP & Location": [
        "ip.*address", "geolocation", "precise.*location", "gps.*data",
        "device.*identifier"
    ],
    "Safe": [
        "protect.*privacy", "encrypted", "not.*share.*personal", 
        "delete.*upon.*request", "adhere.*gdpr", "safe.*harbor"
    ]
}

def split_into_clauses(text):
    """Splits text into sentences/clauses."""
    # Simple split by punctuation
    # Improved regex to handle common abbreviations slightly better
    clauses = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    return [c.strip() for c in clauses if len(c.strip()) > 20] # Filter very short strings

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
    
    if not os.path.exists(data_dir):
        print(f"Directory {data_dir} does not exist. Creating simple text file for testing.")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "sample.txt"), "w") as f:
            f.write("We sell your data to third parties. We retain data indefinitely. You cannot sue us, only arbitration.")
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
    print(f"Found {len(files)} files in {data_dir}. Processing...")
    
    if len(files) == 0:
        print("No .txt files found to build dataset.")
        return

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
    # Updated path to where text files might reside, or keep default
    build_dataset("d:/ML/text")
