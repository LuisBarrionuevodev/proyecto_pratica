# app/main.py
import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate

from app.database import db
from app.routes import usuario as usuario_bp

migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "mysql+pymysql://root:1234@localhost/mi_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
        os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower == "true"
    )

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(usuario_bp, url_prefix="/usuarios")

    return app
