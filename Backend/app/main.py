# app/main.py
import os
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS

from app.database import db
from app.domains.actuaciones.routes import actuacion as actuacion_bp
from app.domains.grid.routes import grid as grid_bp

migrate = Migrate()


def create_app(config_override: dict | None = None):
    load_dotenv()

    app = Flask(__name__)

    # defaults
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:1234@localhost/mi_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
        os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() == "true"
    )

    # ✅ override ANTES de init_app
    if config_override:
        app.config.update(config_override)

    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

    db.init_app(app)
    migrate.init_app(app, db)

    app.url_map.strict_slashes = False
  
    app.register_blueprint(actuacion_bp, url_prefix="/actuaciones")
    
    app.register_blueprint(grid_bp)
    print(app.url_map)

    return app
