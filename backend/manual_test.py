from risk_engine import RiskEngine

engine = RiskEngine()

sample_text = """
We collect your personal information including location and contact details.
We may share your data with third party advertisers for marketing purposes.
We retain your data indefinitely.
You have no right to delete your data.
Any dispute will be resolved by arbitration and you waive your right to a class action.
"""

print("Analyzing sample text...")
results = engine.analyze_text(sample_text)

print(f"Risk Level: {results['risk_level']}")
print(f"Total Score: {results['total_risk_score']}")
print("Risky Clauses:")
for c in results['risky_clauses']:
    print(f"- {c['risk_score']}: {c['text']} -> {c['issues']}")

print("\nAI Summary:")
for s in results['summary']:
    print(f"- {s}")
