import os
import json

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openai import OpenAI

from .models import Base, Request
from .credits import get_or_create_user, ensure_can_spend, spend, COST_CREDITS
from .ocr import ocr_image_bytes
from .aiutami_prompt import SYSTEM_PROMPT
from .pdf_utils import extract_text_from_pdf_bytes, render_pdf_pages_to_images


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
    return {"service": "AIutaMI API", "health": "/health", "analyze": "/analyze"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
async def analyze(
    phone: str = Form(..., description="Numero utente es. +39333..."),
    image: UploadFile = File(...),
):
    allowed = ("image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf")
    if image.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Formato non supportato. Invia una foto oppure un PDF."
        )

    file_bytes = await image.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File troppo grande (max 15MB).")

    db = SessionLocal()
    try:
        user = get_or_create_user(db, phone)

        try:
            ensure_can_spend(user, COST_CREDITS)
        except PermissionError:
            return {"ok": False, "message": BLOCKED_MSG, "credits": user.credits}
        except ValueError:
            return {"ok": False, "message": CREDITS_FINISHED_MSG, "credits": user.credits}

        ocr_text = ""

        if image.content_type == "application/pdf":
            # 1) prova estrazione testo vero
            ocr_text = extract_text_from_pdf_bytes(file_bytes, max_pages=3)

            # 2) se è scansione, renderizza pagine e OCR
            if len(ocr_text) < 30:
                pages = render_pdf_pages_to_images(file_bytes, max_pages=2, dpi=220)
                texts = []
                for p in pages:
                    t = ocr_image_bytes(p)
                    if t and len(t) > 10:
                        texts.append(t)
                ocr_text = "\n\n".join(texts).strip()
        else:
            # immagine classica
            ocr_text = ocr_image_bytes(file_bytes)

        # Se testo troppo povero: non consumiamo credito
        if len(ocr_text) < 30:
            return {
                "ok": False,
                "message": (
                    "Non riesco a leggere bene il testo.\n"
                    "Se hai il PDF originale, invialo come documento (è meglio della foto).\n"
                    "Altrimenti rifai la foto più ravvicinata, dritta e con più luce (prima pagina completa)."
                ),
                "credits": user.credits,
                "ocr_text": ocr_text,
            }

        req = Request(
            user_id=user.id,
            ocr_text=ocr_text,
            status="draft",
            cost_credits=COST_CREDITS
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Testo estratto:\n\n{ocr_text}\n\nRispondi nel JSON richiesto."},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        data = json.loads(resp.choices[0].message.content)

        req.categoria = data.get("categoria")
        req.rischio = data.get("rischio")
        req.response_whatsapp = data.get("risposta_whatsapp")
        db.add(req)
        db.commit()

        spend(db, user, COST_CREDITS, req.id)

        return {"ok": True, "credits": user.credits, "ocr_text": ocr_text, "result": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()import os
import json

from .pdf_utils import extract_text_from_pdf_bytes, render_pdf_pages_to_images
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openai import OpenAI

from .models import Base, Request
from .credits import get_or_create_user, ensure_can_spend, spend, COST_CREDITS
from .ocr import ocr_image_bytes
from .aiutami_prompt import SYSTEM_PROMPT
from .pdf_utils import extract_text_from_pdf_bytes, render_pdf_pages_to_images

DB_URL = os.getenv("AIUTAMI_DB_URL", "sqlite:///./aiutami.db")

# SQLite needs check_same_thread=False
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


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
async def analyze(
    phone: str = Form(..., description="Numero utente es. +39333..."),
    image: UploadFile = File(...),
):
    # File guard
    if image.allowed = ("image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf")
if image.content_type not in allowed:
    raise HTTPException(
        status_code=400,
        detail="Formato non supportato. Invia una foto oppure un PDF."
    )content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(status_code=400, detail="Formato non supportato. Invia una foto JPG/PNG.")

    img_bytes = await image.read()
    if len(img_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Immagine troppo grande (max 10MB).")

    db = SessionLocal()
    try:
        # user + crediti
        user = get_or_create_user(db, phone)

        try:
            ensure_can_spend(user, COST_CREDITS)
        except PermissionError:
            return {"ok": False, "message": BLOCKED_MSG, "credits": user.credits}
        except ValueError:
            return {"ok": False, "message": CREDITS_FINISHED_MSG, "credits": user.credits}

        # OCR
        ocr_text = # Estrazione testo: PDF-first, poi OCR
ocr_text = ""

if image.content_type == "application/pdf":
    # 1) prova estrazione testo vero
    ocr_text = extract_text_from_pdf_bytes(img_bytes, max_pages=3)

    # 2) se è scansione, converti pagine in immagini e OCR
    if len(ocr_text) < 30:
        pages = render_pdf_pages_to_images(img_bytes, max_pages=2, dpi=220)
        texts = []
        for p in pages:
            t = ocr_image_bytes(p)
            if t and len(t) > 10:
                texts.append(t)
        ocr_text = "\n\n".join(texts).strip()
else:
    # immagine classica
    ocr_text = ocr_image_bytes(img_bytes)ocr_image_bytes(img_bytes)

        # Se OCR troppo povero: non consumiamo credito
        if len(ocr_text) < 30:
            return {
                "ok": False,
                "message": "Non riesco a leggere bene il testo dalla foto. Prova a rifarla più ravvicinata e con più luce (prima pagina completa).",
                "credits": user.credits,
                "ocr_text": ocr_text,
            }

        # Salva request draft
        req = Request(
            user_id=user.id,
            ocr_text=ocr_text,
            status="draft",
            cost_credits=COST_CREDITS
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        # OpenAI: chiediamo JSON puro
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Testo estratto (OCR):\n\n{ocr_text}\n\nRispondi nel JSON richiesto."},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        data = json.loads(resp.choices[0].message.content)

        # salva risposta
        req.categoria = data.get("categoria")
        req.rischio = data.get("rischio")
        req.response_whatsapp = data.get("risposta_whatsapp")
        db.add(req)
        db.commit()

        # scala credito solo dopo risposta valida
        spend(db, user, COST_CREDITS, req.id)

        return {
            "ok": True,
            "credits": user.credits,
            "ocr_text": ocr_text,
            "result": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
