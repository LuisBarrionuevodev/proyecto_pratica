# app/main.py
import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from app.database import db
from app.routes import usuario as usuario_bp
from app.routes import actuacion as actuacion_bp
from app.routes.catalogos import catalogos
migrate = Migrate()


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:1234@localhost/mi_db",
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
        os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() == "true"
    )
    CORS(
    app,
    resources={r"/*": {"origins": "http://localhost:5173"}},
    )
    db.init_app(app)
    migrate.init_app(app, db)
    app.url_map.strict_slashes = False
    app.register_blueprint(catalogos, url_prefix="/catalogos")
    app.register_blueprint(usuario_bp, url_prefix="/usuarios")
    app.register_blueprint(actuacion_bp, url_prefix="/actuaciones")
    return app
