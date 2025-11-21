import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from database import create_document
from schemas import Lead
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

class LeadRequest(Lead):
    pass

@app.post("/api/lead")
def create_lead(lead: LeadRequest) -> Dict[str, Any]:
    """Create a lead: save to DB and send to Telegram."""
    # 1) Save to database
    try:
        doc_id = create_document("lead", lead)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    # 2) Send to Telegram bot if env vars exist
    sent_to_telegram = False
    telegram_error = None
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            text = (
                "🚗 Новая заявка на пригон авто\n\n"
                f"Имя: {lead.name}\n"
                f"Телефон/Telegram: {lead.phone}\n"
                f"Модель: {lead.car_model or '-'}\n"
                f"Бюджет: {lead.budget or '-'}\n"
                f"Email: {lead.email or '-'}\n"
                f"Комментарий: {lead.message or '-'}\n"
            )
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            sent_to_telegram = True
        except Exception as e:
            telegram_error = str(e)

    return {
        "ok": True,
        "id": doc_id,
        "sent_to_telegram": sent_to_telegram,
        "telegram_error": telegram_error,
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
