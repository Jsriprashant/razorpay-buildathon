"""python -m app.scripts.init_db — create every table (create_all is fine
per Section 2 of the spec; no migration framework needed for this build)."""
from app.database import Base, engine
from app.models import *  # noqa: F401,F403  (ensures every model is registered)
from app.services.settings_service import ensure_defaults
from app.database import SessionLocal


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_defaults(db)
    finally:
        db.close()
    print("Database initialized.")


if __name__ == "__main__":
    main()
