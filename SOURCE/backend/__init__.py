"""
Backend package initialization.

This module exposes the application factory so that scripts and other
services can import `create_app` without causing circular imports.
"""

from .app import create_app

__all__ = ["create_app"]

