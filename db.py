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

def init_db():
    Base.metadata.create_all(bind=engine)
