"""
Shopo Robo — Production WSGI Entry Point
=========================================
Standard WSGI application entry point for production deployments.
Compatible with Gunicorn, Waitress, uWSGI, and containerized runtimes.

Usage:
    # Linux / Production:
    gunicorn wsgi:app

    # Windows / Local Production Verification:
    waitress-serve --port=5000 wsgi:app
"""

import os
import sys

# Ensure server/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))

from app import app, create_app

if __name__ == "__main__":
    from config import config
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
