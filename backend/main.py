from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from risk_engine import RiskEngine

app = FastAPI(title="Smart Risk Analyzer API")

# Allow CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RiskEngine()

class AnalyzeRequest(BaseModel):
    text: str
    url: str | None = None

@app.get("/")
def read_root():
    return {"status": "online", "message": "Risk Analyzer API is running"}

@app.post("/analyze")
def analyze_policy(request: AnalyzeRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    # Cap text length to prevent overload in this demo
    processed_text = request.text[:100000] 
    
    results = engine.analyze_text(processed_text)
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
