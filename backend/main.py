from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import pdfplumber
import io
from cachetools import TTLCache 

from risk_engine import RiskEngine

app = FastAPI(title="Smart Risk Analyzer API")

# 1. Database Setup (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./risk_history.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    risk_score = Column(Float)
    risk_level = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

risk_engine = RiskEngine()

# 2. Caching Layer (Max 100 items, TTL 24 hours)
cache = TTLCache(maxsize=100, ttl=86400)

class AnalyzeRequest(BaseModel):
    text: str
    url: str | None = None

@app.get("/")
def read_root():
    return {"status": "online", "message": "Risk Analyzer API is running with DistilBERT & OCR"}

@app.post("/analyze")
def analyze_policy(request: AnalyzeRequest, db: Session = Depends(get_db)):
    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    # Check Cache
    if request.url and request.url in cache:
        print(f"Dataset Cache Hit for {request.url}")
        return cache[request.url]

    # Analyze
    # Limit text length to avoid memory explosion (Transformers handle usually 512 tokens, but we use chunks)
    processed_text = request.text[:100000] 
    results = risk_engine.analyze_text(processed_text)
    
    # Save to History
    domain = "Unknown"
    if request.url:
        try:
             domain = request.url.split("//")[-1].split("/")[0]
             # Update Cache
             cache[request.url] = results
        except:
             pass

    scan = ScanResult(
        domain=domain,
        risk_score=results["total_risk_score"],
        risk_level=results["risk_level"]
    )
    db.add(scan)
    db.commit()
    
    return results

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    scans = db.query(ScanResult).order_by(ScanResult.timestamp.desc()).limit(10).all()
    return scans

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return risk_engine.analyze_file(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File Processing Error: {str(e)}")
