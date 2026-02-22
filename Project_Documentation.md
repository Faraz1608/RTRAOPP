# Smart Risk Analyzer — Project Documentation

**Version:** 1.0 (Pro)
**Date:** February 22, 2026
**Author:** Faraz

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Module Descriptions](#6-module-descriptions)
   - 6.1 [Backend — FastAPI Server](#61-backend--fastapi-server)
   - 6.2 [ML Inference Engine](#62-ml-inference-engine)
   - 6.3 [Data Pipeline & Training](#63-data-pipeline--training)
   - 6.4 [Chrome Extension Frontend](#64-chrome-extension-frontend)
7. [Data Flow](#7-data-flow)
8. [API Specification](#8-api-specification)
9. [Machine Learning Pipeline](#9-machine-learning-pipeline)
   - 9.1 [Dataset Construction](#91-dataset-construction)
   - 9.2 [Model Architecture](#92-model-architecture)
   - 9.3 [Training Configuration](#93-training-configuration)
   - 9.4 [Inference Strategy](#94-inference-strategy)
   - 9.5 [Risk Scoring Algorithm](#95-risk-scoring-algorithm)
10. [Chrome Extension Design](#10-chrome-extension-design)
11. [Database Design](#11-database-design)
12. [Caching Strategy](#12-caching-strategy)
13. [Setup & Installation](#13-setup--installation)
14. [Future Enhancements](#14-future-enhancements)
15. [Conclusion](#15-conclusion)

---

## 1. Introduction

**Smart Risk Analyzer** is an AI-powered Chrome Extension that analyzes Terms & Conditions and Privacy Policies for hidden privacy risks in real-time. The system uses a fine-tuned **Legal-BERT** transformer model trained on the **CUAD (Contract Understanding Atticus Dataset)** to classify risky clauses in legal text, combined with a **Flan-T5** generative model for producing human-readable risk summaries.

The tool empowers end users — who typically skip reading lengthy legal documents — to instantly understand the privacy implications of the agreements they accept online.

---

## 2. Problem Statement

Terms & Conditions and Privacy Policies are designed to be legally comprehensive but are often intentionally complex, making them inaccessible to average users. Studies show that over **90% of users accept these agreements without reading them**, exposing themselves to:

- Unconsented data sharing with third-party advertisers
- Indefinite data retention policies
- Forced arbitration clauses waiving legal rights
- Biometric data collection without explicit opt-in
- Cross-site tracking and behavioral profiling

There is a critical need for an **automated, AI-driven tool** that can quickly analyze these documents and highlight specific risks in an understandable format.

---

## 3. Objectives

1. **Classify risky clauses** in legal text using a domain-specific NLP model
2. **Provide real-time analysis** of any webpage's Terms & Conditions via a browser extension
3. **Support multiple input methods**: page scanning, PDF upload (with OCR), and manual text paste
4. **Generate human-readable summaries** of detected risks using generative AI
5. **Categorize risks** into actionable categories (Data Sharing, Forced Arbitration, etc.)
6. **Maintain scan history** for user reference and trend tracking
7. **Highlight risky text** directly on the webpage for visual context

---

## 4. System Architecture

The system follows a **client-server architecture** with two main components:

```
┌──────────────────────────────────────────────────┐
│                 CHROME EXTENSION                  │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ popup.js │  │content.js│  │ background.js  │ │
│  │  (UI &   │  │ (Page    │  │ (Service       │ │
│  │  Logic)  │  │  Scraper │  │  Worker -      │ │
│  │          │  │  & Risk  │  │  ONNX Stub)    │ │
│  │          │  │  Highlighte│ │               │ │
│  └────┬─────┘  └──────────┘  └────────────────┘ │
│       │                                          │
└───────┼──────────────────────────────────────────┘
        │  HTTP (localhost:8000)
        ▼
┌──────────────────────────────────────────────────┐
│               BACKEND (FastAPI)                   │
│  ┌──────────┐  ┌──────────────────┐  ┌────────┐ │
│  │ main.py  │  │  risk_engine.py  │  │ SQLite │ │
│  │ (API     │──│  (Legal-BERT +   │  │  DB    │ │
│  │  Routes) │  │   Flan-T5 +      │  └────────┘ │
│  │          │  │   OCR)           │              │
│  └──────────┘  └──────────────────┘              │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         TRAINING PIPELINE                    │ │
│  │  ingest_cuad.py → build_dataset.py →        │ │
│  │  train_model.py → export_onnx.py            │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## 5. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | FastAPI + Uvicorn | RESTful API server |
| **ML Classifier** | Legal-BERT (`nlpaueb/legal-bert-base-uncased`) | Risky clause classification |
| **Summarizer** | Flan-T5 (`google/flan-t5-small`) | Generative risk summarization |
| **Training Dataset** | CUAD (HuggingFace) + Regex weak supervision | Hybrid labeled data |
| **Model Export** | ONNX + Int8 Quantization | Optimized inference / client-side |
| **Database** | SQLite via SQLAlchemy | Scan history persistence |
| **PDF Processing** | pdfplumber | Text extraction from PDFs |
| **OCR** | pytesseract + Pillow | Scanned/image PDF fallback |
| **Caching** | cachetools (TTLCache) | Response caching (24h, 100 entries) |
| **Readability** | textstat | Reading grade-level analysis |
| **Extension** | Chrome Manifest V3 (HTML/CSS/JS) | Browser UI and page interaction |

---

## 6. Module Descriptions

### 6.1 Backend — FastAPI Server

**File:** `backend/main.py`

The API server is the central hub connecting the Chrome Extension frontend to the ML inference engine. It provides three REST endpoints for text analysis, file upload, and history retrieval.

**Key responsibilities:**
- Request validation and text truncation (100K character limit)
- URL-based response caching to avoid redundant analysis
- Scan result persistence to SQLite database
- Domain extraction from URLs for history tracking
- CORS configuration for cross-origin extension requests

### 6.2 ML Inference Engine

**File:** `backend/risk_engine.py`

The `RiskEngine` class encapsulates all machine learning logic:

- **Classifier**: Legal-BERT fine-tuned for multi-class clause classification across 9 categories (8 risk + 1 safe)
- **Summarizer**: Flan-T5 generates concise, plain-English summaries of detected risks
- **Readability Analyzer**: Uses `textstat` to compute the reading grade level of the input document
- **Clause Splitter**: Regex-based sentence segmentation for granular analysis
- **Sliding Window**: Handles clauses exceeding BERT's 512-token limit using overlapping chunks
- **File Processor**: Extracts text from PDFs (with OCR fallback) and plain text files

### 6.3 Data Pipeline & Training

The training pipeline consists of three stages:

| Stage | File | Method | Purpose |
|-------|------|--------|---------|
| **1. Strong Supervision** | `ingest_cuad.py` | CUAD dataset from HuggingFace | Real legal contract annotations |
| **2. Weak Supervision** | `build_dataset.py` | Regex pattern matching | Auto-label raw T&C files |
| **3. Fine-Tuning** | `train_model.py` | Legal-BERT training | Domain-adapted classifier |

An optional fourth stage (`export_onnx.py`) converts the model to ONNX format with Int8 quantization for optimized deployment.

### 6.4 Chrome Extension Frontend

The extension provides a polished, dark-themed popup interface with three tabs:

| Tab | Functionality |
|-----|--------------|
| **Page Scan** | One-click extraction and analysis of current webpage content |
| **Upload/Paste** | Manual text input or PDF file upload for analysis |
| **History** | View last 10 scans with domain, risk level, and score |

Additional features include in-page risk highlighting with color-coded backgrounds and tooltip annotations.

---

## 7. Data Flow

### Page Scan Flow

1. User clicks **SCAN PAGE** in the extension popup
2. `popup.js` sends a `getText` message to `content.js`
3. `content.js` clones the page DOM, strips noise elements (scripts, nav, footer, etc.), and returns the cleaned text
4. `popup.js` sends a `POST /analyze` request to the backend with the extracted text and current URL
5. `main.py` checks the TTL cache for a cached result by URL
6. If not cached, `risk_engine.py` processes the text through the full pipeline:
   - Readability scoring → Clause splitting → BERT inference → Risk scoring → Flan-T5 summarization
7. Results are cached by URL and saved to SQLite
8. Response is returned to `popup.js`, which renders the results UI
9. `popup.js` sends a `highlightRisks` message to `content.js` with the identified risky clauses
10. `content.js` walks the DOM tree and highlights matching text nodes

### File Upload Flow

1. User selects a PDF/TXT file in the Upload/Paste tab
2. `popup.js` creates a `FormData` and sends `POST /upload` to the backend
3. `main.py` reads the file content and delegates to `risk_engine.analyze_file()`
4. For PDFs: `pdfplumber` extracts text page by page; pages without text trigger OCR fallback via `pytesseract`
5. For TXT: UTF-8 decoding
6. Text is truncated to 100K characters and sent through `analyze_text()`
7. Results are returned and rendered in the popup

---

## 8. API Specification

### `GET /`

**Purpose:** Health check

**Response:**
```json
{
  "status": "online",
  "message": "Risk Analyzer API is running with DistilBERT & OCR"
}
```

### `POST /analyze`

**Purpose:** Analyze text for privacy risks

**Request Body:**
```json
{
  "text": "We reserve the right to share your data with third-party advertisers.",
  "url": "https://example.com"  // optional
}
```

**Response:**
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

### `POST /upload`

**Purpose:** Upload a PDF or text file for analysis

**Request:** `multipart/form-data` with a `file` field

**Response:** Same structure as `/analyze`

### `GET /history`

**Purpose:** Retrieve the last 10 scan results

**Response:**
```json
[
  {
    "id": 1,
    "domain": "example.com",
    "risk_score": 60.0,
    "risk_level": "MEDIUM",
    "timestamp": "2026-02-22T12:00:00"
  }
]
```

---

## 9. Machine Learning Pipeline

### 9.1 Dataset Construction

The training dataset is built using a **hybrid approach** combining two sources:

**Strong Supervision — CUAD Ingestion (`ingest_cuad.py`):**
- Downloads the CUAD dataset (510 real commercial contracts) from HuggingFace
- Contains SQuAD-format clause-level annotations for 41 legal categories
- Maps 18+ CUAD categories to the app's 8 risk categories using a predefined mapping table
- Extracts clean answer spans filtered by minimum length (> 20 characters)

**Weak Supervision — Regex Builder (`build_dataset.py`):**
- Processes raw Terms & Conditions `.txt` files
- Splits text into sentence-level clauses using regex
- Auto-labels clauses using curated regex patterns per risk category
- Covers categories not well-represented in CUAD (e.g., Third-Party Tracking, Biometric Data)
- Also generates "Safe" samples using positive privacy patterns

The two sources are merged and deduplicated to produce `dataset.csv`.

### 9.2 Model Architecture

**Base Model:** `nlpaueb/legal-bert-base-uncased`
- A BERT-base model (12 layers, 768 hidden, 110M parameters) pre-trained on a large corpus of legal documents
- Provides superior understanding of legal terminology compared to general-purpose BERT

**Classification Head:**
- Standard `AutoModelForSequenceClassification` from HuggingFace Transformers
- 9 output classes: Data Retention, Data Sharing, User Rights, Legal & Liability, Forced Arbitration, Third-Party Tracking, Biometric Data, IP & Location, Safe

### 9.3 Training Configuration

| Parameter | Value |
|-----------|-------|
| Base model | `nlpaueb/legal-bert-base-uncased` |
| Number of epochs | 3 |
| Batch size (train & eval) | 8 |
| Max sequence length | 128 tokens |
| Optimizer | AdamW |
| Warmup steps | 100 |
| Weight decay | 0.01 |
| Evaluation strategy | Per epoch |
| Model selection | Best model (lowest eval loss) |
| Sample limit | 2,000 (auto-downsampled for CPU) |
| Train/test split | 80/20 |

### 9.4 Inference Strategy

**Standard Inference (< 512 tokens):**
1. Tokenize the clause (no truncation)
2. Single forward pass through Legal-BERT
3. Apply softmax to get probability distribution over 9 classes
4. Select the class with highest probability

**Sliding Window Inference (≥ 512 tokens):**
1. Tokenize without truncation to get full token sequence
2. Create overlapping chunks: window size = 510 tokens, stride = 256 tokens
3. Decode each chunk back to text and re-tokenize (ensures proper special tokens)
4. Run inference on each chunk independently
5. **Max-risk aggregation**: select the prediction with the highest confidence score across all chunks

### 9.5 Risk Scoring Algorithm

```
For each clause:
  IF predicted_label ≠ "Safe" AND confidence > 40%:
    total_score += 20 points
    Add to risky_clauses list
    Accumulate in category_details

Final score = min(total_score, 100)

Risk Level:
  ≥ 70  → HIGH
  ≥ 30  → MEDIUM
  < 30  → LOW
```

**Design rationale:**
- 20-point increment means 5+ risky clauses = 100% risk score
- 40% confidence threshold balances recall vs. false positives
- Score capped at 100 for normalized presentation
- Clauses sorted by confidence (descending) in output

---

## 10. Chrome Extension Design

### Manifest Configuration

- **Manifest Version:** 3 (latest Chrome standard)
- **Permissions:** `activeTab` (access current tab), `scripting` (inject content scripts)
- **Host Permissions:** `http://localhost:8000/*` (API access)
- **Content Security Policy:** Allows `wasm-unsafe-eval` for future ONNX Runtime Web integration

### UI Components

| Component | Description |
|-----------|-------------|
| **Score Card** | Central risk level display (LOW/MEDIUM/HIGH) with animated color-coded progress bar |
| **Summary Section** | Reading grade level + AI-generated risk summary |
| **Category Breakdown** | Per-category risk scores with mini progress bars |
| **Risky Clauses List** | Individual clause cards with risk score, category label, and truncated text (150 chars) |
| **History List** | Domain, risk level (color-coded), score, and date for past scans |
| **Error View** | Connection error message with retry button |

### Visual Design

The extension uses a modern **dark theme** with a carefully curated color palette:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Navy | `#0f172a` |
| Card Surface | Slate | `#1e293b` |
| Primary Text | Off-White | `#f8fafc` |
| Secondary Text | Muted Blue-Gray | `#94a3b8` |
| Accent / Links | Blue | `#3b82f6` |
| Low Risk | Green | `#22c55e` |
| Medium Risk | Yellow | `#ffc107` |
| High Risk | Red | `#ef4444` / `#dc3545` |

### In-Page Highlighting

When risks are detected during a page scan, `content.js` highlights the matching text directly on the webpage:

| Risk Score | Background | Border |
|-----------|-----------|--------|
| ≤ 50% | Warning Yellow (`#fffbeb`) | `#f59e0b` |
| > 50% | Danger Red (`#fef2f2`) | `#ef4444` |

Highlighted elements display risk details on hover via the `title` tooltip attribute.

---

## 11. Database Design

**Engine:** SQLite (file: `risk_history.db`)
**ORM:** SQLAlchemy

### `scans` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto-increment | Unique scan ID |
| `domain` | String | Indexed | Extracted domain from URL |
| `risk_score` | Float | — | Normalized risk score (0–100) |
| `risk_level` | String | — | LOW, MEDIUM, or HIGH |
| `timestamp` | DateTime | Default: `utcnow()` | Scan timestamp |

---

## 12. Caching Strategy

The system implements a **TTL-based in-memory cache** using `cachetools.TTLCache`:

| Parameter | Value |
|-----------|-------|
| Maximum entries | 100 |
| Time-to-live | 86,400 seconds (24 hours) |
| Cache key | Full URL string |
| Cache value | Complete analysis result dict |

**Cache behavior:**
- Cache is checked before ML inference on `/analyze` endpoint
- Only URL-based requests are cached (manual text paste is not cacheable)
- Cache entries are automatically evicted after 24 hours
- When capacity is reached, least-recently-used entries are evicted first

---

## 13. Setup & Installation

### Prerequisites

- Python 3.9 or higher
- Google Chrome browser
- (Optional) Tesseract OCR installed and on system PATH for scanned PDF support

### Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Build Training Dataset

```bash
# Download CUAD dataset (strong supervision)
python ingest_cuad.py

# (Optional) Add regex-labeled samples (weak supervision)
python build_dataset.py
```

### Step 3: Train the Model

```bash
python train_model.py
```

> **Note:** Training on CPU takes approximately 30–60 minutes. The script auto-downsamples to 2,000 samples for CPU efficiency.

### Step 4: Start the API Server

```bash
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`.

### Step 5: (Optional) Export to ONNX

```bash
python export_onnx.py
```

Produces `models/risk_bert.onnx` and `models/risk_bert_quantized.onnx`.

### Step 6: Install Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The **Smart Risk Analyzer** icon will appear in the toolbar

---

## 14. Future Enhancements

| Enhancement | Description |
|-------------|-------------|
| **Client-side ONNX Inference** | Use the exported ONNX model with ONNX Runtime Web to run inference directly in the browser, eliminating the need for a backend server |
| **Multi-language Support** | Extend the model to analyze legal documents in languages beyond English |
| **Spacy-based Clause Splitting** | Replace regex-based sentence segmentation with a proper NLP library for better accuracy |
| **Comparative Analysis** | Compare privacy policies across similar services |
| **Risk Trend Tracking** | Visualize how a website's privacy risk changes over time using scan history |
| **User Configurable Thresholds** | Allow users to adjust confidence thresholds and risk category weights |

---

## 15. Conclusion

Smart Risk Analyzer demonstrates a practical application of modern NLP techniques — specifically domain-adapted transformer models — to solve a real-world consumer protection problem. By combining strong supervision from curated legal datasets (CUAD) with weak supervision from regex-based labeling, the system achieves broad category coverage while maintaining classification quality. The Chrome Extension interface makes the tool accessible to non-technical users, enabling them to make informed decisions about the privacy agreements they accept online.

---

*Document generated on February 22, 2026*
