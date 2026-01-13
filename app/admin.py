import os
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .credits import get_or_create_user

ADMIN_KEY = os.getenv("AIUTAMI_ADMIN_KEY", "")

def require_admin(x_aiutami_admin: str | None):
    if not ADMIN_KEY:
        raise HTTPException(status_code=500, detail="Admin key non configurata")
    if not x_aiutami_admin or x_aiutami_admin != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def topup_credits(db: Session, phone: str, amount: int):
    user = get_or_create_user(db, phone)
    user.credits += amount
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
