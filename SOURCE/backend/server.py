"""
Entry-point to run the Flask development server.
"""

from __future__ import annotations

from .app import create_app
from .config import get_settings


def main() -> None:
    app = create_app()
    settings = get_settings()
    app.run(debug=settings.debug)


if __name__ == "__main__":
    main()

