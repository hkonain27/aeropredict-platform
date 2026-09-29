"""WSGI entry point: gunicorn backend.wsgi:app."""
from backend.app import app

__all__ = ['app']
