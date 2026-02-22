# 🛡️ Smart Risk Analyzer — Pro Version

> **AI-powered Chrome Extension that analyzes Terms & Conditions and Privacy Policies for hidden privacy risks in real-time.**

Smart Risk Analyzer uses a fine-tuned **Legal-BERT** transformer model trained on the **CUAD (Contract Understanding Atticus Dataset)** to classify risky clauses in legal text. It features sliding-window inference for long documents, generative AI summarization via **Flan-T5**, OCR support for scanned PDFs, and a polished Chrome Extension frontend.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Real-time Page Scan** | One-click analysis of any webpage's Terms & Conditions directly from the browser |
| 📄 **PDF Upload & OCR** | Upload policy PDFs — with automatic OCR fallback for scanned/image-based documents |
| ✏️ **Manual Text Input** | Paste any legal text for instant risk assessment |
| 🤖 **Legal-BERT Classifier** | Domain-specific transformer model fine-tuned on real legal contracts (CUAD dataset) |
| 🪟 **Sliding Window Inference** | Handles long documents by chunking text with overlapping windows (stride 256, window 510 tokens) |
| 📝 **AI Summarization** | Generative summary of detected risks using Google's Flan-T5 |
| 📊 **Risk Scoring** | Normalized 0–100 risk score with LOW / MEDIUM / HIGH classification |
| 🏷️ **Category Breakdown** | Risks categorized into: Data Retention, Data Sharing, User Rights, Legal & Liability, Forced Arbitration, Third-Party Tracking, Biometric Data, IP & Location |
| 📈 **Readability Analysis** | Automated readability grade-level scoring via `textstat` |
| 🕓 **Scan History** | SQLite-backed history of past scans with domain tracking |
| ⚡ **Response Caching** | TTL-based in-memory cache (24h, 100 entries) for repeated URL scans |
| 🧪 **ONNX Export** | Export trained model to ONNX (with Int8 quantization) for potential client-side browser inference |

---

## 🏗️ Architecture

```
SmartRiskAnalyzer/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # API endpoints (/analyze, /upload, /history)
│   ├── risk_engine.py          # Core ML engine (Legal-BERT + Flan-T5 + OCR)
│   ├── train_model.py          # Model training script (Legal-BERT fine-tuning)
│   ├── ingest_cuad.py          # CUAD dataset downloader & preprocessor
│   ├── build_dataset.py        # Regex-based weak supervision dataset builder
│   ├── export_onnx.py          # ONNX model export + quantization
│   ├── manual_test.py          # Manual testing utility
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment config template
│   ├── models/                 # Trained model artifacts (git-ignored)
│   └── dataset.csv             # Training dataset (git-ignored)
│
├── extension/                  # Chrome Extension (Manifest V3)
│   ├── manifest.json           # Extension config & permissions
│   ├── popup.html              # Extension popup UI
│   ├── popup.js                # UI logic, API calls, result rendering
│   ├── content.js              # Content script for page text extraction
│   ├── style.css               # Extension styling
│   └── icons/                  # Extension icons
│
├── .gitignore
└── README.md
```

---

## 🧠 ML Pipeline

### Data Pipeline

1. **Strong Supervision — CUAD Ingestion** (`ingest_cuad.py`)
   - Downloads the [CUAD dataset](https://huggingface.co/datasets/cuad) from Hugging Face (SQuAD-format real contract clauses)
   - Maps 18+ CUAD legal categories → 8 Smart Risk Analyzer risk categories
   - Extracts and cleans clause-level annotations
   - Merges with existing regex-generated samples for hybrid coverage

2. **Weak Supervision — Regex Builder** (`build_dataset.py`)
   - Processes raw `.txt` files of Terms & Conditions
   - Splits text into sentence-level clauses
   - Auto-labels clauses using curated regex patterns for each risk category
   - Generates `dataset.csv` for training

### Model Training (`train_model.py`)

- **Base Model**: [`nlpaueb/legal-bert-base-uncased`](https://huggingface.co/nlpaueb/legal-bert-base-uncased) — a BERT model pre-trained on legal corpora
- **Fine-tuning**: 3 epochs, batch size 8, AdamW optimizer with warmup + weight decay
- **Evaluation**: Epoch-level validation with best-model checkpoint selection
- **Output**: Saved to `models/risk_bert/` (tokenizer + model weights)

### Inference Engine (`risk_engine.py`)

- **Clause Splitting**: Regex-based sentence segmentation
- **Sliding Window**: For clauses exceeding 512 tokens — stride of 256, window of 510 tokens, max-risk aggregation
- **Classification**: Softmax probabilities → risk label + confidence score
- **Risk Scoring**: 20 points per risky clause (confidence > 60%), normalized to 0–100
- **Summarization**: Flan-T5 generates a plain-English summary of detected risks
- **Readability**: `textstat` computes reading grade level

### ONNX Export (`export_onnx.py`)

- Exports the trained Legal-BERT to ONNX format with dynamic axes
- Applies Int8 dynamic quantization for optimized file size
- Enables potential future client-side inference in the Chrome Extension via ONNX Runtime Web

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — confirms API is online |
| `POST` | `/analyze` | Analyze text for privacy risks (accepts `text` and optional `url`) |
| `POST` | `/upload` | Upload a PDF or text file for analysis |
| `GET` | `/history` | Retrieve last 10 scan results |

### Sample Request

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "We reserve the right to share your data with third-party advertisers.", "url": "https://example.com"}'
```

### Sample Response

```json
{
  "total_risk_score": 40,
  "risk_level": "MEDIUM",
  "summary": [
    "Reading Grade Level: 12.3",
    "AI Summary: This policy allows sharing of personal data with advertisers."
  ],
  "risky_clauses": [
    {
      "text": "We reserve the right to share your data with third-party advertisers.",
      "risk_score": 87,
      "issues": ["Data Sharing (87%)"]
    }
  ],
  "category_details": {
    "Data Sharing": 20
  }
}
```

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.9+
- Google Chrome (for the extension)
- (Optional) Tesseract OCR — for scanned PDF support

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### 2. Build Dataset & Train Model

```bash
# Step 1: Download CUAD dataset and create strongly-supervised training data
python ingest_cuad.py

# Step 2 (Optional): Add regex-based weakly-supervised samples
python build_dataset.py

# Step 3: Fine-tune Legal-BERT on the merged dataset
python train_model.py
```

> ⏱️ **Note**: Training Legal-BERT on CPU may take 30–60 minutes. The script auto-downsamples to 2000 samples for faster CPU training.

### 3. Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**.

### 4. Export to ONNX (Optional)

```bash
python export_onnx.py
```

Creates `models/risk_bert.onnx` and a quantized `models/risk_bert_quantized.onnx`.

### 5. Chrome Extension Setup

1. Open Chrome → navigate to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The **Smart Risk Analyzer** icon will appear in your toolbar

---

## 🎮 Usage

1. **Ensure the backend server is running** (`uvicorn main:app --reload`)
2. Navigate to any website with Terms & Conditions
3. Click the **Smart Risk Analyzer** extension icon
4. Choose your input method:
   - **Scan Page** — auto-extracts text from the current page
   - **Paste Text** — manually paste legal text
   - **Upload PDF** — upload a policy document
5. View the analysis results: risk score, risk level, AI summary, risky clauses, and category breakdown
6. Check **History** tab for past scan results

---

## 🔄 Recent Changes (Pro Version Upgrade)

- **Replaced Scikit-Learn model with Legal-BERT** — migrated from a simple logistic regression classifier to a domain-specific transformer (`nlpaueb/legal-bert-base-uncased`) for significantly improved clause understanding
- **CUAD Dataset Integration** — added `ingest_cuad.py` to download and preprocess the Contract Understanding Atticus Dataset for strong supervision, replacing sole reliance on regex-based weak labels
- **Sliding Window Inference** — implemented overlapping-window chunking (stride 256, window 510) in `risk_engine.py` to handle clauses exceeding BERT's 512-token limit
- **AI Summarization with Flan-T5** — integrated Google's `flan-t5-small` to generate plain-English summaries of detected privacy risks
- **ONNX Export Pipeline** — added `export_onnx.py` with dynamic-axis export and Int8 quantization, enabling future client-side inference in the Chrome Extension
- **Hybrid Dataset Strategy** — merged CUAD-sourced strong labels with regex-based weak labels for broader category coverage (e.g., Tracking/Cookies not present in CUAD)
- **Response Caching** — added TTL-based in-memory cache (24h, 100 entries) to avoid redundant analysis of the same URL
- **OCR Fallback for PDFs** — added `pytesseract` + `Pillow` for optical character recognition on scanned/image-based PDF pages

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI + Uvicorn |
| **ML Classifier** | Legal-BERT (`nlpaueb/legal-bert-base-uncased`) via Hugging Face Transformers |
| **Summarizer** | Flan-T5 (`google/flan-t5-small`) |
| **Training Dataset** | CUAD (Hugging Face) + Regex weak supervision |
| **Model Export** | ONNX + ONNX Runtime Quantization |
| **Database** | SQLite via SQLAlchemy |
| **PDF Processing** | pdfplumber + pytesseract (OCR) |
| **Caching** | cachetools (TTLCache) |
| **Readability** | textstat |
| **Extension** | Chrome Manifest V3 (HTML/CSS/JS) |

---

## 📝 License

This project is for educational and research purposes.
