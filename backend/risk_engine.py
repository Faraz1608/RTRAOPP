import re
import pickle
import os
import textstat

class RiskEngine:
    def __init__(self):
        # Load ML Model if available
        self.model = None
        model_path = "models/risk_classifier.pkl"
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                print("✅ ML Model loaded successfully (Real-World Data).")
            except Exception as e:
                print(f"⚠️ Failed to load ML Model: {e}")
        
        # Fallback Keywords (Heuristics)
        self.risk_patterns = {
            "Data Collection": {
                "keywords": ["collect", "gather", "process", "obtain", "monitor", "track", "record"],
                "high_risk": ["precise location", "biometric", "social security", "financial info", "credit card", "health data"],
            },
            "Data Sharing": {
                "keywords": ["share", "disclose", "transfer", "exchange", "provide access"],
                "high_risk": ["sell", "advertisers", "third parties", "marketing partners", "brokers", "freely"],
            },
            "Data Retention": {
                "keywords": ["retain", "store", "keep", "archive", "preserve"],
                "high_risk": ["indefinitely", "forever", "perpetuity", "as long as we want", "no time limit"],
            },
            "User Rights": {
                "keywords": ["right", "access", "correct", "delete", "withdraw", "opt-out"],
                "high_risk": ["no right", "cannot delete", "waive", "unable to remove"],
            },
            "Legal & Liability": {
                "keywords": ["liable", "liability", "warranty", "indemnify", "dispute"],
                "high_risk": ["arbitration", "class action waiver", "not liable", "as is", "no warranty"],
            }
        }

    def analyze_text(self, text: str):
        # 1. Readability Analysis (Flesch-Kincaid)
        grade_level = textstat.text_standard(text, float_output=True)
        readability_msg = f"Reading Grade Level: {grade_level:.1f}"
        if grade_level > 12:
            readability_msg += " (PhD/Lawyer complexity)"
        else:
             readability_msg += " (Accessible)"

        # 2. Preprocess
        # Simple clause segmentation
        clauses = [c.strip() for c in re.split(r'\.\s+|\n+', text) if len(c.strip()) > 20]
        
        analysis_results = {
            "total_risk_score": 0,
            "risk_level": "Low",
            "summary": [readability_msg],
            "risky_clauses": [],
            "category_details": {
                "Data Collection": 0, "Data Sharing": 0, "Data Retention": 0, 
                "User Rights": 0, "Legal & Liability": 0
            }
        }

        total_score = 0
        
        # 3. Analyze Clauses
        for clause in clauses:
            clause_risk = 0
            category = "Unknown"
            category_matches = []

            # A) ML Prediction (primary)
            if self.model:
                try:
                    prediction = self.model.predict([clause])[0]
                    if prediction != "Safe":
                        category = prediction
                        clause_risk += 15 # Base risk for flagged category
                        analysis_results["category_details"][category] = analysis_results["category_details"].get(category, 0) + 15
                except:
                    pass

            # B) Heuristic Refinement (for specific keywords / high risk)
            # We still check heuristics to catch "selling data" which ML might miss if trained on small data
            for cat, data in self.risk_patterns.items():
                if any(k in clause.lower() for k in data["high_risk"]):
                    clause_risk += 20
                    category = cat # Override if high risk keyphrase found
                    analysis_results["category_details"][cat] = analysis_results["category_details"].get(cat, 0) + 20
                    category_matches.append(f"High Risk: {cat}")
                
                if "sell" in clause.lower() and "data" in clause.lower():
                    clause_risk += 40
                    category_matches.append("CRITICAL: Selling Data")
                    analysis_results["category_details"]["Data Sharing"] = analysis_results["category_details"].get("Data Sharing", 0) + 40

            if clause_risk > 0:
                total_score += clause_risk
                analysis_results["risky_clauses"].append({
                    "text": clause,
                    "risk_score": clause_risk,
                    "issues": category_matches or [f"ML Detected: {category}"]
                })

        # Normalize score
        normalized_score = min(100, total_score)
        
        # Normalize category scores
        for cat in analysis_results["category_details"]:
             analysis_results["category_details"][cat] = min(100, analysis_results["category_details"][cat])

        if normalized_score >= 70:
            analysis_results["risk_level"] = "HIGH"
        elif normalized_score >= 30:
            analysis_results["risk_level"] = "MEDIUM"
        else:
            analysis_results["risk_level"] = "LOW"

        # Add generic summaries if needed
        if normalized_score > 50:
             analysis_results["summary"].append("⚠️ Significant privacy risks detected.")

        analysis_results["total_risk_score"] = normalized_score
        
        # Sort risky clauses by score
        analysis_results["risky_clauses"].sort(key=lambda x: x["risk_score"], reverse=True)
        # Keep top 5
        analysis_results["risky_clauses"] = analysis_results["risky_clauses"][:5]

        return analysis_results
