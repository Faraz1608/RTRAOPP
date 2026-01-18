import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# 1. Load Data
DATA_FILE = "dataset.csv"

if not os.path.exists(DATA_FILE):
    print(f"Error: {DATA_FILE} not found. Run 'python build_dataset.py' first.")
    exit(1)

print(f"Loading data from {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)

# Drop NaN values
df = df.dropna()

print(f"Loaded {len(df)} samples.")
print("Category distribution:\n", df['category'].value_counts())

# Ensure we have enough data
if len(df) < 10:
    print("Not enough data to train. Please add more rules or files in build_dataset.py")
    exit(1)

# 2. Split Data
X_train, X_test, y_train, y_test = train_test_split(
    df['text'], df['category'], test_size=0.2, random_state=42, stratify=df['category']
)

# 3. Create Pipeline
# TF-IDF -> LinearSVC is fast and effective for short text classification
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(stop_words='english', max_features=5000, ngram_range=(1,2))),
    ('clf', LinearSVC(class_weight='balanced', random_state=42))
])

# 4. Train
print("\nTraining model on real data...")
pipeline.fit(X_train, y_train)

# 5. Evaluate
print("\nEvaluation:")
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred))

# 6. Save Model
os.makedirs("models", exist_ok=True)
MODEL_PATH = "models/risk_classifier.pkl"
with open(MODEL_PATH, "wb") as f:
    pickle.dump(pipeline, f)

print(f"Saving model to {MODEL_PATH}...")
print("Done! The model is now powered by real-world data.")
