"""
Initialize the SQLite database for the notes application.

Usage:
    python scripts/init_db.py
"""

from pathlib import Path

from backend.app import create_app
from backend.database import engine
from backend.models import Base


def main() -> None:
    app = create_app()
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        db_path = Path(engine.url.database or "notes.db")
        print(f"Database initialized at {db_path.resolve()}")


if __name__ == "__main__":
    main()

