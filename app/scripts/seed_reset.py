"""python -m app.scripts.seed_reset — wipe all data and reseed from scratch.
Used by the demo panel's "Reset demo data" button (later task) and by
developers who want a clean deterministic state."""
from app.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403
from app.scripts.seed import seed


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
