import re
import os
import io
import torch
import textstat
import pdfplumber
import pytesseract
from PIL import Image
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification, T5Tokenizer, T5ForConditionalGeneration

class RiskEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"RiskEngine running on: {self.device}")

        # 1. Load Classifier (DistilBERT)
        self.model_path = "models/risk_bert"
        self.tokenizer = None
        self.model = None
        
        if os.path.exists(self.model_path):
            try:
                print("Loading fine-tuned DistilBERT model...")
                self.tokenizer = DistilBertTokenizerFast.from_pretrained(self.model_path)
                self.model = DistilBertForSequenceClassification.from_pretrained(self.model_path).to(self.device)
                self.model.eval()
                print("✅ Risk Classifier Loaded.")
            except Exception as e:
                print(f"⚠️ Failed to load Risk Model: {e}")
        else:
            print(f"⚠️ Model not found at {self.model_path}. Run train_model.py first.")

        # 2. Load Summarizer (Flan-T5)
        print("Loading Summarizer (Flan-T5)...")
        try:
            self.sum_tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-small")
            self.sum_model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-small").to(self.device)
            print("✅ Summarizer Loaded.")
        except Exception as e:
            print(f"⚠️ Failed to load Summarizer: {e}")
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
        if self.model and self.tokenizer:
            # Batch prediction could be faster, but let's do simple loop for now or small batches
            inputs = self.tokenizer(clauses, padding=True, truncation=True, max_length=128, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predictions = torch.argmax(probabilities, dim=-1)

            # Map IDs to labels (Need to fetch label map from model config)
            id2label = self.model.config.id2label

            for i, clause in enumerate(clauses):
                pred_id = predictions[i].item()
                label = id2label[pred_id]
                score = probabilities[i][pred_id].item()

                if label != "Safe": # Assuming 'Safe' is a label
                    # Heuristic: Only flag if confidence > 0.6 to reduce false positives
                    if score > 0.6: 
                        risk_pts = 20
                        total_score += risk_pts
                        analysis_results["category_details"][label] = analysis_results["category_details"].get(label, 0) + risk_pts
                        
                        analysis_results["risky_clauses"].append({
                            "text": clause,
                            "risk_score": int(score * 100),
                            "issues": [f"{label} ({int(score*100)}%)"]
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
