# Smart Risk Analyzer — Detailed Project Report

**Date**: February 17, 2026
**Version**: Pro (v1.0)
**Repository**: [RTRAOPP on GitHub](https://github.com/Faraz1608/RTRAOPP)

---

## 1. Introduction

### 1.1 Problem Statement

Terms & Conditions and Privacy Policies are notoriously long, complex, and written in dense legal language. Studies show that the average user spends less than a minute reviewing these documents before clicking "I Agree." Hidden within them are clauses that authorize excessive data collection, force users into binding arbitration, waive the right to class-action lawsuits, permit indefinite data retention, and more.

There is a clear need for an automated, intelligent tool that can parse these legal documents, identify risky clauses, and present the findings in a clear, actionable summary — without requiring users to have legal expertise.

### 1.2 Proposed Solution

**Smart Risk Analyzer** is an AI-powered Chrome Extension + FastAPI backend system that:

1. Extracts Terms & Conditions text from any webpage (or accepts pasted text / uploaded PDFs)
2. Classifies individual clauses using a fine-tuned Legal-BERT transformer model
3. Scores overall risk on a 0–100 scale (LOW / MEDIUM / HIGH)
4. Generates a plain-English AI summary of privacy risks using Flan-T5
5. Highlights risky text directly on the original webpage
6. Maintains a persistent history of scans in a local SQLite database

### 1.3 Key Technologies

| Technology | Purpose |
|---|---|
| Python 3.9+ | Backend language |
| FastAPI + Uvicorn | REST API framework and ASGI server |
| Hugging Face Transformers | Model loading, training, and inference |
| Legal-BERT (`nlpaueb/legal-bert-base-uncased`) | Domain-specific clause classification |
| Flan-T5 (`google/flan-t5-small`) | Generative AI summarization |
| CUAD Dataset | Strong supervision training data (real legal contracts) |
| PyTorch | Deep learning framework |
| SQLite + SQLAlchemy | Persistent scan history database |
| pdfplumber + pytesseract | PDF text extraction and OCR |
| Chrome Extension (Manifest V3) | Browser frontend |
| ONNX Runtime | Model export for potential client-side inference |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CHROME EXTENSION (Frontend)                 │
│                                                                 │
│  ┌────────────┐    ┌────────────┐    ┌──────────────────────┐   │
│  │ popup.html │    │  popup.js  │    │     content.js       │   │
│  │  (UI/Tabs) │◄──►│  (Logic)   │    │  (Page Extraction +  │   │
│  │            │    │            │    │   Risk Highlighting)  │   │
│  └────────────┘    └─────┬──────┘    └──────────────────────┘   │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │  HTTP (localhost:8000)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (Server)                    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  main.py — API Layer                                      │  │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │ /analyze │  │  /upload  │  │ /history │  │  Cache   │ │  │
│  │  └────┬─────┘  └─────┬─────┘  └────┬─────┘  │ (TTL)   │ │  │
│  │       │              │              │        └──────────┘ │  │
│  └───────┼──────────────┼──────────────┼─────────────────────┘  │
│          │              │              │                         │
│  ┌───────▼──────────────▼──────┐  ┌────▼─────────────────────┐  │
│  │  risk_engine.py             │  │  SQLite Database          │  │
│  │  ┌───────────────────────┐  │  │  (risk_history.db)        │  │
│  │  │ Legal-BERT Classifier │  │  └──────────────────────────┘  │
│  │  │ (Clause → Category)   │  │                                │
│  │  ├───────────────────────┤  │                                │
│  │  │ Flan-T5 Summarizer    │  │                                │
│  │  │ (Risks → Summary)     │  │                                │
│  │  ├───────────────────────┤  │                                │
│  │  │ textstat (Readability)│  │                                │
│  │  ├───────────────────────┤  │                                │
│  │  │ pdfplumber + OCR      │  │                                │
│  │  │ (PDF/Image → Text)    │  │                                │
│  │  └───────────────────────┘  │                                │
│  └─────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  TRAINING PIPELINE (Offline)                    │
│                                                                 │
│  ingest_cuad.py → build_dataset.py → train_model.py            │
│  (CUAD Download)   (Regex Labels)     (Legal-BERT Fine-tuning)  │
│                         ↓                                       │
│                    dataset.csv → models/risk_bert/              │
│                                                                 │
│  export_onnx.py → models/risk_bert.onnx (Optional)             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Descriptions

| Component | File(s) | Role |
|---|---|---|
| **API Server** | `main.py` | Exposes REST endpoints, manages CORS, caching, and database |
| **Risk Engine** | `risk_engine.py` | Core ML inference: clause splitting, classification, summarization, readability |
| **CUAD Ingester** | `ingest_cuad.py` | Downloads and maps CUAD dataset for strong supervision |
| **Dataset Builder** | `build_dataset.py` | Regex-based weak labeling of raw text files |
| **Model Trainer** | `train_model.py` | Fine-tunes Legal-BERT on the merged dataset |
| **ONNX Exporter** | `export_onnx.py` | Exports model to ONNX format with Int8 quantization |
| **Content Script** | `content.js` | Extracts text from webpages and highlights risky clauses |
| **Popup UI** | `popup.html`, `popup.js`, `style.css` | Chrome Extension user interface (tabs, results, history) |

---

## 3. How It Works — End-to-End Flow

### 3.1 User Initiates a Scan

The user clicks the **"SCAN PAGE"** button in the Chrome Extension popup. The extension then:

1. **Identifies the active tab** using `chrome.tabs.query()`
2. **Sends a message** to the content script (`content.js`) via `chrome.tabs.sendMessage()`
3. The content script receives the `getText` action

### 3.2 Text Extraction (content.js)

The content script extracts the page's visible text using a smart cleaning approach:

```
Page DOM → Clone body → Remove noise elements → Extract innerText → Normalize whitespace
```

**Noise elements removed**: `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<nav>`, `<footer>`, `<header>`, `<aside>`

The cleaned text is sent back to `popup.js` via the message response.

### 3.3 API Request (popup.js → main.py)

The popup sends a `POST` request to `http://localhost:8000/analyze` with:

```json
{
  "text": "<extracted text>",
  "url": "<current page URL>"
}
```

### 3.4 Caching Check (main.py)

Before running analysis, the server checks its in-memory TTL cache:
- **Cache hit**: Returns stored results immediately (avoids re-analysis for 24 hours)
- **Cache miss**: Proceeds to full analysis

### 3.5 Risk Analysis Pipeline (risk_engine.py)

This is the core of the system. The `analyze_text()` method runs the following pipeline:

#### Step 1: Readability Analysis
Uses the `textstat` library to compute a reading grade level score. Example: *"Reading Grade Level: 14.2"* means the text requires a college-level education to understand.

#### Step 2: Clause Splitting
Splits the input text into individual sentences/clauses using regex:
```python
clauses = re.split(r'(?<=[.!?])\s+', text)
```
Only clauses with more than 20 characters are kept to filter out noise.

#### Step 3: Legal-BERT Classification (Per Clause)

For each clause, the system runs inference through Legal-BERT:

1. **Tokenize** the clause using the Legal-BERT tokenizer
2. **Check token length**:
   - If ≤ 512 tokens → Run inference directly
   - If > 512 tokens → Use **Sliding Window** approach (see Section 4.2)
3. **Get prediction**: Softmax over logits → predicted category + confidence score
4. **Filter**: Only clauses with confidence > 60% and a non-"Safe" label are flagged as risky
5. **Score**: Each risky clause contributes 20 points to the total risk score

**Risk Categories**:

| Category | Description |
|---|---|
| Data Retention | Indefinite storage, no deletion policy |
| Data Sharing | Selling data, third-party transfers |
| User Rights | Cannot delete account, waived feedback rights |
| Legal & Liability | Indemnification, no warranty, liability caps |
| Forced Arbitration | Binding arbitration, class-action waivers |
| Third-Party Tracking | Cookies, tracking pixels, web beacons |
| Biometric Data | Fingerprints, facial recognition, voice prints |
| IP & Location | GPS data, geolocation, device identifiers |
| Safe | Privacy-protective clauses (GDPR compliance, encryption) |

#### Step 4: AI Summary Generation (Flan-T5)

If risky clauses are found, the system:

1. Concatenates the risky clause texts into a single blob (max 1000 characters)
2. Constructs a prompt: `"summarize privacy risks: <risky_text>"`
3. Feeds the prompt to the local **Flan-T5** model (`google/flan-t5-small`)
4. The model generates a max-60-token plain-English summary
5. Example output: *"This policy allows sharing of personal data with advertisers and retains data indefinitely."*

**Important**: This runs entirely locally — no external API calls. The model weights (~300 MB) are downloaded once from Hugging Face and cached.

#### Step 5: Risk Scoring

The total risk score is computed as:
```
total_score = (number of risky clauses) × 20 points each
normalized_score = min(total_score, 100)
```

Classification:
| Score Range | Level |
|---|---|
| 0–29 | LOW |
| 30–69 | MEDIUM |
| 70–100 | HIGH |

### 3.6 Database Storage (main.py)

After analysis, the result is saved to SQLite:
```
domain | risk_score | risk_level | timestamp
```

### 3.7 Response Delivery (main.py → popup.js)

The API returns a JSON response:

```json
{
  "total_risk_score": 60,
  "risk_level": "MEDIUM",
  "summary": [
    "Reading Grade Level: 13.5",
    "AI Summary: Data is shared with third parties and retained indefinitely."
  ],
  "risky_clauses": [
    {
      "text": "We may share your data with third-party advertisers.",
      "risk_score": 87,
      "issues": ["Data Sharing (87%)"]
    }
  ],
  "category_details": {
    "Data Sharing": 20,
    "Data Retention": 20,
    "Forced Arbitration": 20
  }
}
```

### 3.8 Results Rendering (popup.js)

The popup displays:
- **Risk Level Badge**: Color-coded (green/yellow/red)
- **Risk Score Progress Bar**: Visual bar from 0–100%
- **Summary Section**: Readability score + AI-generated summary
- **Category Breakdown**: Per-category progress bars with color coding
- **Top 5 Risky Clauses**: Sorted by confidence, with truncated preview + issues

### 3.9 On-Page Highlighting (content.js)

After results are received, `popup.js` sends a `highlightRisks` message to the content script with the risky clauses. The content script:

1. Walks the entire DOM tree using `TreeWalker` to find text nodes
2. For each risky clause, searches for a matching text node using:
   - **Exact match** on the first 60 characters
   - **Fuzzy match** (first 20 + last 20 chars) as fallback
3. Wraps matched text nodes in a `<span>` with:
   - Yellow background + orange border for risk score ≤ 50
   - Red background + red border for risk score > 50
   - Hover tooltip showing the detected risk category

---

## 4. Machine Learning — Deep Dive

### 4.1 Training Data Pipeline

The system uses a **hybrid supervision** strategy combining two data sources:

#### Source 1: CUAD Dataset (Strong Supervision)

- **Dataset**: [Contract Understanding Atticus Dataset](https://huggingface.co/datasets/cuad)
- **Format**: SQuAD-style (context paragraph + question + answer spans)
- **Size**: ~13,000+ annotated contract clauses
- **Processing** (`ingest_cuad.py`):
  1. Downloads the full CUAD dataset from Hugging Face
  2. For each question-answer pair, maps the CUAD category to one of 8 risk categories
  3. Extracts the answer text as the clause, cleans whitespace
  4. Filters out clauses shorter than 20 characters
  5. Merges with any existing `dataset.csv`

**Category Mapping** (18 CUAD categories → 8 risk categories):

| CUAD Category | → Mapped Category |
|---|---|
| Termination For Convenience, Non-Compete, Exclusivity, Intellectual Property | User Rights |
| Irrevocable or Perpetual License, Post-Termination Services | Data Retention |
| Liquidated Damages, Warranty Duration, Insurance, Governing Law, Cap On Liability, Indemnification, Audit Rights | Legal & Liability |
| Waiver Of Jury Trial | Forced Arbitration |
| Most Favored Nation, Confidentiality clause, License Grant | Data Sharing |

#### Source 2: Regex-Based Weak Supervision

- **Source Files**: Raw `.txt` files of Terms & Conditions (from `d:/ML/text/`)
- **Processing** (`build_dataset.py`):
  1. Reads all `.txt` files
  2. Splits into sentence-level clauses using regex
  3. Auto-labels each clause by matching against curated keyword patterns
  4. Provides coverage for categories CUAD lacks (e.g., "Third-Party Tracking", "Biometric Data", "IP & Location")

**Regex Pattern Examples**:

| Category | Patterns |
|---|---|
| Data Retention | `retain.*indefinitely`, `store.*forever`, `no.*deletion.*policy` |
| Data Sharing | `sell.*data`, `share.*partners`, `third.*party.*marketing` |
| Forced Arbitration | `arbitration`, `class.*action.*waiver`, `waive.*right.*trial` |
| Safe | `protect.*privacy`, `encrypted`, `adhere.*gdpr` |

### 4.2 Model Architecture

#### Legal-BERT Classifier

- **Base**: `nlpaueb/legal-bert-base-uncased` — BERT pre-trained on 12 GB of English legal text (court cases, contracts, legislation)
- **Architecture**: BERT-base (12 layers, 768 hidden dim, 12 attention heads, ~110M parameters) + linear classification head
- **Input**: Tokenized clause (max 512 tokens)
- **Output**: Softmax probabilities over 9 categories (8 risk + 1 safe)

#### Sliding Window for Long Documents

When a clause exceeds 512 tokens:

```
Clause tokens: [t₁, t₂, t₃, ... t₁₅₀₀]

Window 1: [t₁    ... t₅₁₀]     → Predict → (label_1, score_1)
Window 2: [t₂₅₆  ... t₇₆₆]     → Predict → (label_2, score_2)
Window 3: [t₅₁₂  ... t₁₀₂₂]    → Predict → (label_3, score_3)
Window 4: [t₇₆₈  ... t₁₂₇₈]    → Predict → (label_4, score_4)
...

Final prediction = Window with HIGHEST confidence score
```

- **Window size**: 510 tokens (leaving room for `[CLS]` and `[SEP]`)
- **Stride**: 256 tokens (50% overlap)
- **Aggregation**: Max-risk — takes the window with the highest confidence

#### Flan-T5 Summarizer

- **Model**: `google/flan-t5-small` (77M parameters)
- **Type**: Encoder-decoder (sequence-to-sequence)
- **Task**: Conditional text generation
- **Prompt template**: `"summarize privacy risks: <risky clauses text>"`
- **Max output**: 60 tokens
- **Inference mode**: Greedy decoding (`model.generate()`)

### 4.3 Training Configuration

| Parameter | Value |
|---|---|
| Base Model | `nlpaueb/legal-bert-base-uncased` |
| Epochs | 3 |
| Batch Size | 8 (train & eval) |
| Max Sequence Length | 128 tokens |
| Optimizer | AdamW |
| Warmup Steps | 100 |
| Weight Decay | 0.01 |
| Evaluation Strategy | Per epoch |
| Save Strategy | Per epoch |
| Best Model Selection | Yes (`load_best_model_at_end=True`) |
| Downsampling | Max 2000 samples (for CPU training) |
| Train/Val Split | 80/20 |

### 4.4 ONNX Export

The trained model can be exported to ONNX format for deployment:

1. **Export**: `torch.onnx.export()` with dynamic axes for batch size and sequence length
2. **Quantization**: Int8 dynamic quantization via `onnxruntime.quantization`
3. **Output files**:
   - `models/risk_bert.onnx` — full precision
   - `models/risk_bert_quantized.onnx` — Int8 quantized (~4× smaller)

This enables potential future **client-side inference** in the Chrome Extension using ONNX Runtime Web (no backend needed).

---

## 5. API Reference

### 5.1 Endpoints

#### `GET /`
Health check endpoint.

**Response**:
```json
{
  "status": "online",
  "message": "Risk Analyzer API is running with DistilBERT & OCR"
}
```

#### `POST /analyze`
Analyzes text for privacy risks.

**Request Body**:
| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | Legal text to analyze (max 100,000 chars) |
| `url` | string | No | Source URL (used for caching and history) |

**Response**: See Section 3.7 for full response format.

#### `POST /upload`
Upload a file for analysis.

**Request**: Multipart form data with `file` field. Accepts `.pdf` and `.txt` files.

**Processing**:
- **PDF**: Extracts text using `pdfplumber`. Falls back to OCR (`pytesseract`) for pages with no extractable text.
- **TXT**: Reads directly as UTF-8.

#### `GET /history`
Retrieves the 10 most recent scan results.

**Response**: Array of scan objects:
```json
[
  {
    "id": 1,
    "domain": "example.com",
    "risk_score": 60.0,
    "risk_level": "MEDIUM",
    "timestamp": "2026-02-17T10:00:00"
  }
]
```

### 5.2 Caching

- **Implementation**: In-memory TTL cache (`cachetools.TTLCache`)
- **Max entries**: 100
- **TTL**: 24 hours (86,400 seconds)
- **Cache key**: Request URL
- **Behavior**: Only URLs are cached (manual text/paste inputs are not)

### 5.3 CORS

CORS is enabled for all origins (`*`), all methods, and all headers — designed for local development where the Chrome Extension calls `localhost:8000`.

---

## 6. Chrome Extension — Deep Dive

### 6.1 Manifest Configuration

- **Manifest Version**: 3 (latest Chrome standard)
- **Permissions**: `activeTab`, `scripting`
- **Host Permissions**: `http://localhost:8000/*`
- **Content Scripts**: Injected on all URLs (`<all_urls>`)
- **Content Security Policy**: Allows `wasm-unsafe-eval` (for potential ONNX Runtime Web)

### 6.2 User Interface (popup.html)

The popup has a **3-tab layout**:

| Tab | Description |
|---|---|
| **Page Scan** | One-click scan of the current webpage |
| **Upload/Paste** | Manual text area + PDF file upload |
| **History** | List of past scan results with domain, score, and date |

**Result Display Sections**:
1. **Score Card**: Risk level badge + animated progress bar
2. **Summary**: Readability score + AI-generated summary
3. **Category Breakdown**: Per-category progress bars with color coding
4. **Top Risks**: Up to 5 risky clauses sorted by confidence

### 6.3 Content Script Features (content.js)

1. **Smart Text Extraction**: Clones page DOM, removes non-content elements, extracts normalized text
2. **Risk Highlighting**: After analysis, highlights risky text directly on the webpage with:
   - Color-coded backgrounds (yellow for moderate, red for high risk)
   - Colored underlines
   - Tooltip on hover showing the risk category and score

---

## 7. Database Design

### 7.1 Schema

**Table**: `scans`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `domain` | STRING (indexed) | Extracted domain from URL |
| `risk_score` | FLOAT | Normalized risk score (0–100) |
| `risk_level` | STRING | LOW, MEDIUM, or HIGH |
| `timestamp` | DATETIME | UTC timestamp of scan |

### 7.2 Implementation

- **ORM**: SQLAlchemy with declarative base
- **Database**: SQLite (`risk_history.db`) — file-based, zero-config
- **Connection**: Thread-safe with `check_same_thread=False`
- **Session Management**: Per-request sessions via FastAPI dependency injection (`Depends(get_db)`)

---

## 8. Dependencies

```
fastapi          - Web framework
uvicorn          - ASGI server
pydantic         - Data validation
scikit-learn     - ML utilities
pandas           - Data manipulation
numpy            - Numerical computing
nltk             - Natural language toolkit
beautifulsoup4   - HTML parsing
requests         - HTTP client
textstat         - Readability analysis
pdfplumber       - PDF text extraction
sqlalchemy       - ORM / database
python-multipart - File upload support
torch            - PyTorch deep learning
transformers     - Hugging Face model hub
pytesseract      - OCR engine
Pillow           - Image processing
cachetools       - In-memory caching
accelerate       - Hugging Face training acceleration
datasets         - Hugging Face dataset loading
```

---

## 9. Recent Changes — Pro Version Upgrade

The project was significantly upgraded from its initial version. The key changes are:

| Change | Before | After |
|---|---|---|
| **ML Model** | Scikit-Learn logistic regression | Legal-BERT transformer (`nlpaueb/legal-bert-base-uncased`) |
| **Training Data** | Regex-generated weak labels only | Hybrid: CUAD strong supervision + regex weak labels |
| **Long Document Handling** | Simple truncation | Sliding window inference (stride 256, window 510) |
| **Summarization** | None | Generative AI via Flan-T5 |
| **Model Export** | Not available | ONNX with Int8 quantization |
| **Caching** | Not available | TTL-based in-memory cache (24h, 100 entries) |
| **PDF Support** | Basic text extraction | pdfplumber + OCR fallback (pytesseract) |

---

## 10. How to Run

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Build training data (first time)
python ingest_cuad.py          # Download CUAD dataset
python build_dataset.py        # Add regex-labeled data (optional)

# 3. Train the model (first time)
python train_model.py          # ~30-60 min on CPU

# 4. Start the server
uvicorn main:app --reload      # API at http://localhost:8000

# 5. Load Chrome Extension
# Chrome → chrome://extensions/ → Developer Mode → Load Unpacked → select extension/
```

---

## 11. Future Scope

- **Client-side ONNX inference** — run the model entirely in the browser, eliminating the Python backend requirement
- **Multi-language support** — analyze policies in languages other than English
- **Spacy-based clause splitting** — more accurate segmentation using NLP tools
- **Fine-tuned summarizer** — train Flan-T5 specifically on legal risk summaries
- **Comparative analysis** — compare multiple companies' privacy policies side-by-side
- **Browser notification alerts** — warn users automatically when visiting high-risk sites
