import re
import os
import io
import torch
import textstat
import pdfplumber
import pytesseract
from PIL import Image
from transformers import AutoTokenizer, AutoModelForSequenceClassification, T5Tokenizer, T5ForConditionalGeneration

class RiskEngine:
    def __init__(self, model_path="models/risk_bert"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"RiskEngine running on: {self.device}")

        # 1. Load Classifier (Legal-BERT)
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        
        if os.path.exists(self.model_path):
            try:
                print(f"Loading model from {self.model_path}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path).to(self.device)
                self.model.eval()
                print("[SUCCESS] Risk Classifier Loaded.")
            except Exception as e:
                print(f"[ERROR] Failed to load Risk Model: {e}")
        else:
            print(f"[ERROR] Model not found at {self.model_path}. Run train_model.py first.")

        # 2. Load Summarizer (Flan-T5)
        print("Loading Summarizer (Flan-T5)...")
        try:
            self.sum_tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-small")
            self.sum_model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-small").to(self.device)
            print("[SUCCESS] Summarizer Loaded.")
        except Exception as e:
            print(f"[ERROR] Failed to load Summarizer: {e}")
            self.sum_model = None

    def analyze_text(self, text: str):
        # 1. Readability
        grade_level = textstat.text_standard(text, float_output=True)
        readability_msg = f"Reading Grade Level: {grade_level:.1f}"

        # 2. Preprocess / Clause Split
        # Improved splitting using simple heuristic (can upgrade to Spacy later)
        clauses = [c.strip() for c in re.split(r'(?<=[.!?])\s+', text) if len(c.strip()) > 20]
        
        analysis_results = {
            "total_risk_score": 0,
            "risk_level": "Low",
            "summary": [readability_msg],
            "risky_clauses": [],
            "category_details": {}
        }

        total_score = 0
        risky_text_blob = "" 

        # 3. Inference
        # 3. Inference
        if self.model and self.tokenizer:
            for i, clause in enumerate(clauses):
                # Sliding Window for Long Clauses
                # If clause is long, split into chunks of 512 tokens with overlap
                # But simple approach: just truncate to 512 (Legal-BERT limit) is usually enough for a single "clause".
                # A "clause" > 512 tokens (approx 300-400 words) is rare unless split logic failed.
                # Let's implement robust chunking for safety.
                
                inputs = self.tokenizer(clause, return_tensors="pt", truncation=False, verbose=False)
                input_ids = inputs['input_ids'][0]
                
                # If short enough, run once
                if len(input_ids) <= 512:
                    chunk_input_ids = input_ids.unsqueeze(0).to(self.device)
                    attention_mask = inputs['attention_mask'].to(self.device)
                    
                    with torch.no_grad():
                        output = self.model(chunk_input_ids, attention_mask=attention_mask)
                        probs = torch.nn.functional.softmax(output.logits, dim=-1)
                        top_score, top_label_id = torch.max(probs, dim=-1)
                        
                    final_score = top_score.item()
                    final_label_id = top_label_id.item()
                else:
                    # Sliding Window Logic
                    stride = 256
                    window_size = 510 # Leave room for [CLS] [SEP]
                    chunks = []
                    
                    for k in range(0, len(input_ids), stride):
                        chunk = input_ids[k:k+window_size]
                        if len(chunk) < 10: break # Skip tiny residues
                        # Pad or handle? Auto-handling via tokenizer batching is easier but here we have IDs.
                        # Actually, let's just re-tokenize chunks to be safe with special tokens.
                        chunks.append(self.tokenizer.decode(chunk, skip_special_tokens=True))
                        
                    # Predict on chunks and take MAX risk
                    max_risk_score = -1
                    best_label_id = 0 # Default/Safe
                    
                    for chunk_text in chunks:
                         chunk_inputs = self.tokenizer(chunk_text, return_tensors="pt", truncation=True, max_length=512, padding=True).to(self.device)
                         with torch.no_grad():
                             out = self.model(**chunk_inputs)
                             p = torch.nn.functional.softmax(out.logits, dim=-1)
                             s, l = torch.max(p, dim=-1)
                             
                             # Prioritize Risk Labels (assuming Safe is ID with lowest priority or just check score)
                             # We need the ID map to know which is "Safe". Usually we want the *highest probability of a non-safe class*.
                             # But here we just take max probability.
                             if s.item() > max_risk_score:
                                 max_risk_score = s.item()
                                 best_label_id = l.item()
                                 
                    final_score = max_risk_score
                    final_label_id = best_label_id

                # Common Logic
                id2label = self.model.config.id2label
                label = id2label[final_label_id]
                
                if label != "Safe":
                    if final_score > 0.6:
                         risk_pts = 20
                         total_score += risk_pts
                         analysis_results["category_details"][label] = analysis_results["category_details"].get(label, 0) + risk_pts
                         
                         analysis_results["risky_clauses"].append({
                             "text": clause,
                             "risk_score": int(final_score * 100),
                             "issues": [f"{label} ({int(final_score*100)}%)"]
                         })
                         risky_text_blob += clause + " "

        # 4. Generative Summary
        if self.sum_model and risky_text_blob:
            summary_prompt = "summarize privacy risks: " + risky_text_blob[:1000] # Limit context
            input_ids = self.sum_tokenizer(summary_prompt, return_tensors="pt").input_ids.to(self.device)
            
            with torch.no_grad():
                outputs = self.sum_model.generate(input_ids, max_length=60)
                gen_summary = self.sum_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            analysis_results["summary"].append(f"AI Summary: {gen_summary}")

        # Post-process scores
        normalized_score = min(100, total_score)
        if normalized_score >= 70:
            analysis_results["risk_level"] = "HIGH"
        elif normalized_score >= 30:
            analysis_results["risk_level"] = "MEDIUM"
        else:
            analysis_results["risk_level"] = "LOW"
            
        analysis_results["total_risk_score"] = normalized_score
        analysis_results["risky_clauses"] = sorted(analysis_results["risky_clauses"], key=lambda x: x["risk_score"], reverse=True)[:5]

        return analysis_results

    def analyze_file(self, file_content: bytes, filename: str):
        text = ""
        if filename.endswith(".pdf"):
            try:
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text
                        else:
                            # OCR Fallback
                            print("No text found, running OCR...")
                            im = page.to_image(resolution=300).original
                            text += pytesseract.image_to_string(im)
            except Exception as e:
                return {"error": f"PDF Error: {str(e)}"}
        else:
            text = file_content.decode("utf-8", errors="ignore")
            
        return self.analyze_text(text[:100000])
