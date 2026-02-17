# Smart Risk Analyzer

Smart Risk Analyzer is an AI-powered tool designed to analyze Terms & Conditions and Privacy Policies for potential privacy risks. It consists of a Python FastAPI backend and a Chrome Extension frontend.

## Features

- **Real-time Analysis**: Analyze text directly from the browser extension.
- **PDF Upload**: Upload policy documents for risk assessment.
- **Risk Scoring**: Get a calculated risk score and level (Low, Medium, High).
- **History Tracking**: View past scan results.
- **Privacy Focused**: Runs locally with a SQLite database.

## Project Structure

- `backend/`: FastAPI application, ML model, and database.
- `extension/`: Chrome extension source code.

## Setup Instructions

### 1. Backend Setup

The backend powers the risk analysis engine.

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Build the dataset and train the NEW Transformer model:
   ```bash
   python build_dataset.py
   python train_model.py
   ```
   *Note: Training DistilBERT on CPU may take 10-30 minutes.*

### 4. Update .gitignore
Ensure the following lines are in your `.gitignore` to avoid committing large model files:
```
backend/dataset.csv
backend/risk_history.db
backend/models/
backend/results/
backend/logs/
```

### 5. Run the Server
```bash
uvicorn main:app --reload
```
   The API will be available at `http://localhost:8000`.

### 2. Extension Setup

The extension allows you to interact with the analyzer from your browser.

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** in the top right corner.
3. Click **Load unpacked**.
4. Select the `extension` folder from this project.
5. The "Smart Risk Analyzer" icon should appear in your toolbar.

## Usage

1. Ensure the backend server is running.
2. Navigate to a website with Terms & Conditions you want to analyze.
3. Click the extension icon.
4. The extension will extract text from the page (or you can paste text/upload PDF) and display the risk analysis.
