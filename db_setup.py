import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ---------- Configuration ----------
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "agent_db")

TARGET_DB_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SQLITE_URL = "sqlite:///agent_db.sqlite"

# ---------- ORM Base ----------
Base = declarative_base()

# ---------- Models ----------

class Opportunity(Base):
    __tablename__ = 'opportunities'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)          # internship, research_project, scholarship, certification_webinar, postdoc_visiting
    title = Column(String, nullable=False)
    description = Column(Text)
    source = Column(String)                        # website or API name
    location = Column(String)
    eligibility = Column(Text)
    deadline = Column(String)                      # kept as string for fuzzy dates
    url = Column(String, nullable=False)
    tags = Column(Text)                            # comma-separated or JSON

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    profile = Column(Text)
    interests = Column(Text)                       # comma-separated or JSON
    skills = Column(Text)

class OpportunityCluster(Base):
    __tablename__ = 'opportunity_clusters'
    cluster_id = Column(Integer, primary_key=True)
    cluster_name = Column(String, nullable=False)
    members = Column(Text)                         # JSON list of opportunity IDs

class Recommendation(Base):
    __tablename__ = 'recommendations'
    recommendation_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    score = Column(Float)

class Notification(Base):
    __tablename__ = 'notifications'
    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    status = Column(String)                        # unread / read
    timestamp = Column(TIMESTAMP(timezone=True))

class Swipe(Base):
    __tablename__ = 'swipes'
    swipe_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    action = Column(String, nullable=False)        # liked / rejected
    timestamp = Column(TIMESTAMP(timezone=True))

# ---------- Engine bootstrap ----------

def _try_create_pg_database():
    """Attempt to create the PostgreSQL database if it does not exist."""
    try:
        import pg8000.native
        conn = pg8000.native.Connection(
            user=DB_USER, password=DB_PASS,
            host=DB_HOST, port=int(DB_PORT), database="postgres"
        )
        exists = conn.run(
            f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'"
        )
        if not exists:
            conn.run("COMMIT")
            conn.run(f"CREATE DATABASE {DB_NAME}")
            print(f"[db_setup] Database '{DB_NAME}' created.")
        else:
            print(f"[db_setup] Database '{DB_NAME}' already exists.")
        conn.close()
        return True
    except Exception as e:
        print(f"[db_setup] PostgreSQL unavailable ({e}). Will use SQLite.")
        return False


def _build_engine():
    """Return a working SQLAlchemy engine (PostgreSQL preferred, SQLite fallback)."""
    pg_ok = _try_create_pg_database()
    if pg_ok:
        try:
            eng = create_engine(TARGET_DB_URL)
            # quick connectivity test
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
            print(f"[db_setup] Connected to PostgreSQL ({DB_NAME}).")
            return eng
        except Exception as e:
            print(f"[db_setup] PostgreSQL connect failed ({e}). Falling back to SQLite.")
    eng = create_engine(SQLITE_URL)
    print(f"[db_setup] Using SQLite at agent_db.sqlite")
    return eng


from sqlalchemy import text          # needed for connectivity test

engine = _build_engine()
Session = sessionmaker(bind=engine)


def init_db():
    """Create all tables in the active engine."""
    Base.metadata.create_all(engine)
    print("[db_setup] All tables created / verified.")


if __name__ == "__main__":
    init_db()
