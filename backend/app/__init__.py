from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    if test_config:
        app.config.update(test_config)
    secret = app.config.get("SECRET_KEY") or ""
    if len(secret) < 32 or secret.startswith("replace_with"):
        raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("Set DATABASE_URL before starting Smart Park.")
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
         allow_headers=["Authorization", "Content-Type"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parents[1] / "migrations"))

    from app.routes.admin_routes import admin_bp
    from app.routes.parking_routes import parking_bp
    from app.cli import register_commands
    app.register_blueprint(admin_bp)
    app.register_blueprint(parking_bp)
    register_commands(app)

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled API error")
        return jsonify(error="An internal error occurred"), 500

    return app
