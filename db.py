import os

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./camp_alerts.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class Subscriber(Base):
    __tablename__ = "subscribers"
    phone_number = Column(String, primary_key=True)

class Admin(Base):
    __tablename__ = "admins"
    phone_number = Column(String, primary_key=True)
    state = Column(String, default="idle")  # idle, awaiting_alert

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_admins_from_env():
    raw_admins = os.getenv("ADMIN_NUMBERS", "")
    admin_numbers = [num.strip() for num in raw_admins.split(",") if num.strip()]

    db = SessionLocal()
    for number in admin_numbers:
        exists = db.query(Admin).filter_by(phone_number=number).first()
        if not exists:
            db.add(Admin(phone_number=number, state="idle"))
    db.commit()
    db.close()