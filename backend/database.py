from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# PostgreSQL connection
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username="postgres",
    password="Mahek@16",
    host="localhost",
    port=5432,
    database="smart_campus_db"
)


# Database engine
engine = create_engine(
    DATABASE_URL,
    echo=True
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# Base class for database models
class Base(DeclarativeBase):
    pass


# FastAPI database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()