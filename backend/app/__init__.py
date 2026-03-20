# app/__init__.py — Flask application factory
# Creates and configures the Flask app instance

from flask import Flask
from flask_cors import CORS
from .config import Config
from .utils.db import init_db


def create_app(config_class=Config):
    """
    Application factory pattern — creates a configured Flask app.
    This pattern makes testing and multiple environments easy.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for the frontend S3 origin
    CORS(app, resources={
        r"/api/*": {
            "origins": [app.config["FRONTEND_URL"], "http://localhost:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize database connection pool
    init_db(app)

    # Register all route blueprints
    from .routes.auth     import auth_bp
    from .routes.company  import company_bp
    from .routes.jobs     import jobs_bp
    from .routes.bookings import bookings_bp
    from .routes.interview import interview_bp

    app.register_blueprint(auth_bp,      url_prefix="/api/auth")
    app.register_blueprint(company_bp,   url_prefix="/api/company")
    app.register_blueprint(jobs_bp,      url_prefix="/api/jobs")
    app.register_blueprint(bookings_bp,  url_prefix="/api/bookings")
    app.register_blueprint(interview_bp, url_prefix="/api/interview")

    # Health check endpoint for ALB / ECS
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app