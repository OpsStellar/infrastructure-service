"""
Database configuration for Infrastructure Service.
Uses shared PostgreSQL database - all schemas managed in db-service/alembic/versions/.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import os

from config import settings

# Use shared PostgreSQL database (synchronous for consistency with other services)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://opsstellar_user:opsstellar_password@postgres:5432/opsstellar"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """
    Validate database connection.
    Note: Tables are managed by db-service migrations (see 017_infrastructure_management.sql), not created here.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Database connection successful - using shared PostgreSQL")
        print("   Schema managed by db-service/alembic/versions/017_infrastructure_management.sql")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


def get_db():
    """
    Dependency for database sessions.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on import
try:
    init_db()
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")
