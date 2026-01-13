import re

class RiskEngine:
    def __init__(self):
        self.risk_patterns = {
            "Data Collection": {
                "keywords": ["collect", "gather", "process", "obtain", "monitor", "track", "record"],
                "high_risk": ["precise location", "biometric", "social security", "financial info", "credit card", "health data"],
                "base_score": 10
            },
            "Data Sharing": {
                "keywords": ["share", "disclose", "transfer", "exchange", "provide access"],
                "high_risk": ["sell", "advertisers", "third parties", "marketing partners", "brokers", "freely"],
                "base_score": 15
            },
            "Data Retention": {
                "keywords": ["retain", "store", "keep", "archive", "preserve"],
                "high_risk": ["indefinitely", "forever", "perpetuity", "as long as we want", "no time limit"],
                "base_score": 10
            },
            "User Rights": {
                "keywords": ["right", "access", "correct", "delete", "withdraw", "opt-out"],
                "high_risk": ["no right", "cannot delete", "waive", "unable to remove"],
                "base_score": 5 # Actually reduces risk usually, but lack of it is bad. Handled in logic.
            },
            "Legal & Liability": {
                "keywords": ["liable", "liability", "warranty", "indemnify", "dispute"],
                "high_risk": ["arbitration", "class action waiver", "not liable", "as is", "no warranty"],
                "base_score": 20
            }
        }

    def analyze_text(self, text: str):
        # normalize text
        text = text.lower()
        
        # Simple clause segmentation (by newline or period)
        # In a real scenario, use NLTK sentence tokenizer.
        clauses = [c.strip() for c in re.split(r'\.\s+|\n+', text) if len(c.strip()) > 20]
        
        analysis_results = {
            "total_risk_score": 0,
            "risk_level": "Low",
            "summary": [],
            "risky_clauses": []
        }

        category_scores = {
            "Data Collection": 0,
            "Data Sharing": 0,
            "Data Retention": 0,
            "User Rights": 0,
            "Legal & Liability": 0
        }

        total_score = 0
        
        for clause in clauses:
            clause_risk = 0
            category_matches = []
            
            for category, data in self.risk_patterns.items():
                if any(k in clause for k in data["keywords"]):
                    # Check for high risk keywords
                    for hr in data["high_risk"]:
                        if hr in clause:
                            score_inc = 20
                            clause_risk += score_inc
                            category_scores[category] += score_inc
                            category_matches.append(f"High Risk {category}: {hr}")
                            
                    # Penalize "selling" data heavily
                    if "sell" in clause and "data" in clause:
                        score_inc = 50
                        clause_risk += score_inc
                        category_scores[category] += score_inc
                        category_matches.append("CRITICAL: Selling Data")
                    
                    # Base score just for mentioning the topic (if not already high risk)
                    if clause_risk == 0:
                         # Slight risk just for having these clauses without specific protections? 
                         # For now, let's only score specific keywords or just add base_score if matches logic
                         pass

            if clause_risk > 0:
                total_score += clause_risk
                analysis_results["risky_clauses"].append({
                    "text": clause,
                    "risk_score": clause_risk,
                    "issues": category_matches
                })

        # Normalize score
        normalized_score = min(100, total_score)
        
        # Normalize category scores for display (cap at 100 relative)
        final_category_breakdown = {}
        for cat, score in category_scores.items():
            final_category_breakdown[cat] = min(100, score)

        if normalized_score >= 70:
            analysis_results["risk_level"] = "HIGH"
            analysis_results["summary"].append("⚠️ This policy contains high-risk clauses (e.g., selling data, arbitration).")
        elif normalized_score >= 30:
            analysis_results["risk_level"] = "MEDIUM"
            analysis_results["summary"].append("⚠️ Some potential concerns detected (data sharing, retention).")
        else:
            analysis_results["risk_level"] = "LOW"
            analysis_results["summary"].append("✅ Appears mostly standard/safe.")

        analysis_results["total_risk_score"] = normalized_score
        analysis_results["category_details"] = final_category_breakdown
        
        # Sort risky clauses by score
        analysis_results["risky_clauses"].sort(key=lambda x: x["risk_score"], reverse=True)
        # Keep top 5
        analysis_results["risky_clauses"] = analysis_results["risky_clauses"][:5]

        return analysis_results
