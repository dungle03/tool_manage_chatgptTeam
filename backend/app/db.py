from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

DATABASE_URL = "sqlite:///./workspace_manager.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)
