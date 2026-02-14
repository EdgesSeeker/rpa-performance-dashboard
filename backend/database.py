"""
SQLite database setup and SQLAlchemy models for RPA performance data.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import Column, Integer, String, DateTime, Float, Date, UniqueConstraint
from sqlalchemy.sql import func

# Project root: parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "rpa_performance.db"

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    """UiPath job record."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_key = Column(String(100), unique=True, nullable=False, index=True)
    robot_name = Column(String(255), nullable=True)
    machine_name = Column(String(255), nullable=True)
    process_name = Column(String(255), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    state = Column(String(50), nullable=True)  # Successful, Faulted, Stopped
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_job_start_time", "start_time"),
        Index("idx_job_robot", "robot_name"),
        Index("idx_job_process", "process_name"),
    )


class DailyUtilization(Base):
    """Daily utilization per robot (24/7 basis)."""
    __tablename__ = "daily_utilization"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    robot_name = Column(String(255), nullable=False)
    total_runtime_hours = Column(Float, default=0.0)
    idle_hours = Column(Float, default=0.0)
    utilization_percent = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("date", "robot_name", name="uq_daily_util_robot"),
    )


def get_db() -> Session:
    """Yield a DB session; close after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_tables() -> None:
    """Create all tables and indexes if they do not exist."""
    Base.metadata.create_all(bind=engine)
