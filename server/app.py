"""
Shopo Robo — Flask Application Server
=======================================
Main entry point for the Shopo Robo web application.
Serves the auth frontend and proxies to the main app after login.

Usage:
    python server/app.py
    
    Or with environment overrides:
    SHOPO_OTP_MODE=production SHOPO_PORT=8000 python server/app.py
"""

import os
import sys

# Ensure server/ is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, redirect, request, jsonify

from config import config
from database import init_db
from auth_routes import auth_bp, user_bp
from inventory_routes import inventory_bp
from sales_routes import sales_bp
from ai_routes import ai_bp
from news_routes import news_bp
from bi_routes import bi_bp
from group_b_routes import group_b_bp
from group_c_routes import group_c_bp
from group_d_routes import group_d_bp


def create_app() -> Flask:
    """Flask application factory."""
    # Determine project root (parent of server/)
    server_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(server_dir)

    app = Flask(
        __name__,
        static_folder=None,  # We'll serve statics manually
    )
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max payload limit
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if not config.DEBUG:
        app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SHOPO_COOKIE_SECURE", "True").lower() == "true"

    # Security Response Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # ── Health Check Endpoints ──
    @app.route("/healthz")
    @app.route("/api/health")
    def health_check():
        """Readiness and liveness probe for production hosting environments."""
        from datetime import datetime, timezone
        from database import get_connection

        db_ok = False
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            conn.close()
            db_ok = True
        except Exception:
            db_ok = False

        ai_status = "active (gemini)" if config.GEMINI_API_KEY else "active (smart_local)"
        status_code = 200 if db_ok else 503
        return jsonify({
            "status": "healthy" if db_ok else "unhealthy",
            "app": "Shopo Robo",
            "version": "1.0.0",
            "database": "connected" if db_ok else "disconnected",
            "ai_engine": ai_status,
            "subscription_enabled": config.SUBSCRIPTION_ENABLED,
            "environment": config.ENV,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), status_code

    # ── Register API Blueprints ──
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(bi_bp)
    app.register_blueprint(group_b_bp)
    app.register_blueprint(group_c_bp)
    app.register_blueprint(group_d_bp)

    # ── Initialise Database ──
    with app.app_context():
        init_db()

    # ────────────────────────────────────────────────────
    # Static File Serving
    # ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Redirect root to auth page."""
        return redirect("/auth/")

    # Serve auth frontend
    @app.route("/auth/")
    @app.route("/auth/<path:filename>")
    def serve_auth(filename="index.html"):
        auth_dir = os.path.join(project_root, "auth")
        return send_from_directory(auth_dir, filename)

    # Serve main Shopo Robo dashboard
    @app.route("/app")
    @app.route("/app/")
    def serve_main_app():
        dashboard_dir = os.path.join(project_root, "dashboard")
        return send_from_directory(dashboard_dir, "index.html")

    @app.route("/app/<path:filename>")
    def serve_app_assets(filename):
        dashboard_dir = os.path.join(project_root, "dashboard")
        if os.path.exists(os.path.join(dashboard_dir, filename)):
            return send_from_directory(dashboard_dir, filename)
        return send_from_directory(project_root, filename)

    # Preserve original reference cockpit at /jarvis/
    @app.route("/jarvis")
    @app.route("/jarvis/")
    def serve_jarvis_cockpit():
        return send_from_directory(project_root, "index.html")

    # Serve CSS directory
    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(os.path.join(project_root, "css"), filename)

    # Serve JS directory
    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(os.path.join(project_root, "js"), filename)

    # Serve icons
    @app.route("/icons/<path:filename>")
    def serve_icons(filename):
        return send_from_directory(os.path.join(project_root, "icons"), filename)

    # Serve manifest and service worker
    @app.route("/manifest.json")
    def serve_manifest():
        return send_from_directory(project_root, "manifest.json")

    @app.route("/favicon.ico")
    def serve_favicon():
        return send_from_directory(project_root, "favicon.ico", mimetype="image/x-icon")

    @app.route("/sw.js")
    def serve_sw():
        return send_from_directory(project_root, "sw.js")

    # ────────────────────────────────────────────────────
    # Error Handlers
    # ────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Endpoint not found."}), 404
        return redirect("/auth/")

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Something went wrong. Please try again."}), 500

    return app


# Module-level application instance for WSGI servers (Gunicorn, Waitress, etc.)
app = create_app()


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  [SHOPO ROBO] Auth Server")
    print("=" * 60)
    print(f"  URL        : http://{config.HOST}:{config.PORT}")
    print(f"  Auth Page  : http://{config.HOST}:{config.PORT}/auth/")
    print(f"  Main App   : http://{config.HOST}:{config.PORT}/app/")
    print(f"  OTP Mode   : {config.OTP_MODE.upper()}")
    if config.OTP_MODE == "mock":
        print("  Mock OTP   : Active (Simulated verification for development)")
        print("  [!] DEVELOPMENT MODE -- No real SMS will be sent")
    print(f"  Subscription: {'ENABLED' if config.SUBSCRIPTION_ENABLED else 'DISABLED (Free)'}")
    print(f"  Database   : {config.DATABASE_PATH}")
    print("=" * 60 + "\n")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False,
    )
