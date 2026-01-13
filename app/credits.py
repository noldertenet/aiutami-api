import os
import re
from sqlalchemy.orm import Session

from .models import User, CreditLedger

# -------------------------------
# Config
# -------------------------------

STARTING_CREDITS = int(os.getenv("AIUTAMI_STARTING_CREDITS", "1"))
COST_CREDITS = int(os.getenv("AIUTAMI_CREDIT_COST", "1"))

# -------------------------------
# Utils
# -------------------------------

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    p = phone.strip()
    # tieni solo + e cifre
    p = re.sub(r"[^\d+]", "", p)

    # se non inizia con +, assumiamo Italia
    if not p.startswith("+"):
        p = "+39" + p

    # evita duplicazioni tipo +3939...
    if p.startswith("+3939"):
        p = "+39" + p[4:]

    return p

# -------------------------------
# Users & Credits
# -------------------------------

def get_or_create_user(db: Session, phone: str) -> User:
    """
    Crea utente al primo contatto e assegna crediti iniziali (welcome).
    """
    phone = normalize_phone(phone)

    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user

    user = User(phone=phone, credits=STARTING_CREDITS)
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(CreditLedger(user_id=user.id, delta=STARTING_CREDITS, reason="welcome"))
    db.commit()

    return user


def ensure_can_spend(user: User, cost: int) -> bool:
    return user.credits >= cost


def spend(db: Session, user: User, cost: int):
    user.credits -= cost
    db.add(user)
    db.add(CreditLedger(user_id=user.id, delta=-cost, reason="usage"))
    db.commit()
