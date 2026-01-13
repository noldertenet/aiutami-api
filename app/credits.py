import os
from sqlalchemy.orm import Session

from .models import User, CreditLedger


STARTING_CREDITS = int(os.getenv("AIUTAMI_STARTING_CREDITS", "1"))
COST_CREDITS = int(os.getenv("AIUTAMI_CREDIT_COST", "1"))


def get_or_create_user(db: Session, phone: str) -> User:
    """
    Crea utente al primo contatto e assegna crediti iniziali (welcome).
    """
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


def ensure_can_spend(user: User, cost: int = COST_CREDITS) -> None:
    """
    Controlla blocchi/crediti prima di elaborare una richiesta.
    """
    if user.is_blocked:
        raise PermissionError("blocked")
    if user.credits < cost:
        raise ValueError("no_credits")


def spend(db: Session, user: User, cost: int, request_id: int) -> None:
    """
    Scala crediti e registra ledger per audit.
    """
    user.credits -= cost
    db.add(user)
    db.add(CreditLedger(user_id=user.id, delta=-cost, reason="analysis", request_id=request_id))
    db.commit()
