import pandas as pd
from datasets import load_dataset
import re
import os

# Map CUAD categories to Smart Risk Analyzer categories
CUAD_MAPPING = {
    "Termination For Convenience": "User Rights",
    "Irrevocable or Perpetual License": "Data Retention",
    "Liquidated Damages": "Legal & Liability",
    "Warranty Duration": "Legal & Liability",
    "Insurance": "Legal & Liability",
    "Covenant Not To Sue": "Legal & Liability",
    "Waiver Of Jury Trial": "Forced Arbitration",
    "Governing Law": "Legal & Liability",
    "Most Favored Nation": "Data Sharing",
    "Non-Compete": "User Rights",
    "Exclusivity": "User Rights",
    "No-Solicit Of Employees": "User Rights",
    "No-Solicit Of Customers": "User Rights",
    "Intellectual Property": "User Rights",
    "Confidentiality clause": "Data Sharing",
    "License Grant": "Data Sharing",
    "Post-Termination Services": "Data Retention",
    "Audit Rights": "Legal & Liability",
    "Cap On Liability": "Legal & Liability",
    "Indemnification": "Legal & Liability",
}

def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def ingest_cuad():
    print("Downloading CUAD dataset from Hugging Face...")
    # CUAD on HF is 'cuad'
    dataset = load_dataset("cuad", split="train") 
    
    print(f"Loaded {len(dataset)} contracts. Extracting clauses...")
    
    rows = []
    
    for i, item in enumerate(dataset):
        if i == 0:
            print("Sample item keys:", item.keys())
            print("Sample question:", item.get('question', 'N/A'))
            print("Sample answers:", item.get('answers', 'N/A'))
            
        context = item['context'] # The full contract text
        
        # SQuAD format: answers are list of dicts with 'text' and 'answer_start'
        # But for 'cuad' HF dataset, the structure is slightly different usually.
        # Let's check typical squad structure:
        # answers: {'text': ['clause...'], 'answer_start': [123]}
        
        # CUAD structure: each item is a contract-question pair or contract with all Qs?
        # Actually in HF 'cuad', each row is often a separate question-answer pair for a context.
        # But let's see. If it's SQuAD style, it's one row per question.
        
        question = item.get('question', '')
        answers = item.get('answers', {})
        answer_texts = answers.get('text', [])
        
        if not answer_texts:
            continue
            
        # Map Category
        mapped_label = None
        for key, val in CUAD_MAPPING.items():
            if key.lower() in question.lower():
                mapped_label = val
                break
        
        if mapped_label:
            for text in answer_texts:
                clean_clause = clean_text(text)
                if len(clean_clause) > 20:
                    rows.append({"text": clean_clause, "category": mapped_label})
    
    # Add some 'Safe' samples from the context that were NOT labeled? 
    # For now, let's just use the risky ones.
    
    df = pd.DataFrame(rows)
    print(f"Extracted {len(df)} risky clauses from CUAD.")
    print(df['category'].value_counts())
    
    # Merge with existing regex dataset if desired, OR overwrite. 
    # Strategy: Overwrite to leverage "Strong Supervision" exclusively? 
    # Or Hybrid? Let's Hybridize for now to keep coverage of "Tracking/Cookies" which CUAD might lack.
    
    if os.path.exists("dataset.csv"):
        print("Merging with existing regex dataset...")
        old_df = pd.read_csv("dataset.csv")
        combined_df = pd.concat([old_df, df], ignore_index=True)
        # Drop duplicates
        combined_df = combined_df.drop_duplicates(subset=["text"])
    else:
        combined_df = df
        
    combined_df.to_csv("dataset.csv", index=False)
    print(f"Saved merged dataset with {len(combined_df)} samples to dataset.csv")

if __name__ == "__main__":
    ingest_cuad()
