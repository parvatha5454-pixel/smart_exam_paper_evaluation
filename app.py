"""
app.py
------
Application entry point for the AI-Powered Offline Exam Answer
Analysis System.

Run with:
    python app.py
"""

from flask import Flask
from config import Config
from routes.auth_routes import auth_bp
from routes.answer_key_routes import answer_key_bp
from routes.scanning_routes import scanning_bp
from routes.evaluation_routes import evaluation_bp
from routes.report_routes import report_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints (modules)
    app.register_blueprint(auth_bp)
    app.register_blueprint(answer_key_bp)
    app.register_blueprint(scanning_bp)
    app.register_blueprint(evaluation_bp)
    app.register_blueprint(report_bp)

    return app


app = create_app()

if __name__ == "__main__":
    # debug=True is fine for local development; set to False for production.
    app.run(host="127.0.0.1", port=5000, debug=True)
