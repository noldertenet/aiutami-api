from datetime import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, nullable=False, index=True)

    credits = Column(Integer, default=1)
    strikes = Column(Integer, default=0)
    is_blocked = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    channel = Column(String, default="mvp")  # in futuro: whatsapp
    media_url = Column(String, nullable=True)

    ocr_text = Column(Text, nullable=True)
    categoria = Column(String, nullable=True)
    rischio = Column(String, nullable=True)
    response_whatsapp = Column(Text, nullable=True)

    status = Column(String, default="draft")  # draft|sent|closed
    cost_credits = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    delta = Column(Integer, nullable=False)  # +1, -1, +10...
    reason = Column(String, nullable=False)  # welcome|analysis|manual_topup|partner_code
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
