import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openai import OpenAI
from pydantic import BaseModel

from .models import Base, Request
from .credits import get_or_create_user, ensure_can_spend, spend, COST_CREDITS, normalize_phone
from .ocr import ocr_image_bytes
from .aiutami_prompt import SYSTEM_PROMPT
from .pdf_utils import extract_text_from_pdf_bytes, render_pdf_pages_to_images
from .admin import require_admin, topup_credits


DB_URL = os.getenv("AIUTAMI_DB_URL", "sqlite:///./aiutami.db")

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIutaMI API MVP")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CREDITS_FINISHED_MSG = (
    "Hai terminato i crediti disponibili per le analisi.\n"
    "Se vuoi continuare, scrivi “RICARICA” e ti spieghiamo come ottenere nuovi crediti."
)

BLOCKED_MSG = (
    "AIutaMI è un servizio dedicato esclusivamente ad assistenza su bollette, truffe e burocrazia.\n"
    "Non posso gestire questa richiesta."
)


@app.get("/")
def root():
    return {"service": "AIutaMI API", "status": "running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/credits")
def credits(phone: str):
    db = SessionLocal()
    try:
        phone_n = normalize_phone(phone)
        user = get_or_create_user(db, phone_n)
        return {"ok": True, "phone": user.phone, "credits": user.credits}
    finally:
        db.close()


@app.post("/analyze")
async def analyze(
    phone: str = Form(...),
    image: UploadFile = File(...),
):
    db = SessionLocal()
    try:
        phone_n = normalize_phone(phone)
        user = get_or_create_user(db, phone_n)

        if not ensure_can_spend(user, COST_CREDITS):
            return {"ok": False, "message": CREDITS_FINISHED_MSG, "credits": user.credits}

        raw = await image.read()
        ctype = (image.content_type or "").lower()
        filename = (image.filename or "").lower()

        extracted_text = ""
        ocr_text = ""
        text_for_ai = ""

        is_pdf = ("pdf" in ctype) or filename.endswith(".pdf")

        if is_pdf:
            extracted_text = (extract_text_from_pdf_bytes(raw) or "").strip()

            if not extracted_text:
                # OCR fallback: render first 2 pages to images and OCR them
                pages = render_pdf_pages_to_images(raw, max_pages=2, dpi=200)
                if not pages:
                    return {
                        "ok": False,
                        "message": "Non riesco a leggere il PDF. Prova a caricarlo di nuovo oppure invia una foto più nitida.",
                        "credits": user.credits
                    }

                ocr_chunks = []
                for img_bytes in pages:
                    t = (ocr_image_bytes(img_bytes) or "").strip()
                    if t:
                        ocr_chunks.append(t)
                ocr_text = "\n\n".join(ocr_chunks).strip()

            text_for_ai = extracted_text if extracted_text else ocr_text

            if not text_for_ai:
                return {
                    "ok": False,
                    "message": "Non riesco a leggere bene il testo dal PDF. Prova a inviarlo più nitido o in un formato diverso.",
                    "credits": user.credits,
                    "extracted_text": extracted_text,
                    "ocr_text": ocr_text
                }

        else:
            ocr_text = (ocr_image_bytes(raw) or "").strip()
            if not ocr_text:
                return {
                    "ok": False,
                    "message": "Non riesco a leggere bene il testo dalla foto. Prova a rifarla più ravvicinata e con più luce.",
                    "credits": user.credits,
                    "ocr_text": ocr_text
                }
            text_for_ai = ocr_text

        # OpenAI analysis
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text_for_ai}
            ],
            temperature=0.2
        )
        ai_response = completion.choices[0].message.content

        # Spend credits
        spend(db, user, COST_CREDITS)

        # Log request
        req = Request(
            phone=user.phone,
            raw_text=text_for_ai,
            response=ai_response
        )
        db.add(req)
        db.commit()

        return {
            "ok": True,
            "result": ai_response,
            "credits": user.credits,
            "source": "pdf-text" if extracted_text else ("pdf-ocr" if is_pdf else "image-ocr")
        }

    finally:
        db.close()


class TopupBody(BaseModel):
    phone: str
    amount: int


@app.post("/admin/topup")
def admin_topup(
    payload: TopupBody,
    x_aiutami_admin: str | None = Header(default=None),
):
    require_admin(x_aiutami_admin)

    phone_n = normalize_phone(payload.phone)
    amount = int(payload.amount)

    if not phone_n or amount <= 0:
        raise HTTPException(status_code=400, detail="Parametri non validi")

    db = SessionLocal()
    try:
        user = topup_credits(db, phone_n, amount)
        return {"ok": True, "phone": user.phone, "credits": user.credits}
    finally:
        db.close()
