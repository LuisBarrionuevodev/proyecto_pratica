# app/main.py
import os
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import inspect

from app.database import db
from app.domains.actuaciones.routes import actuacion as actuacion_bp
from app.domains.grid.routes import grid as grid_bp
from app.domains.relevamientos.routes import relevamiento as relevamiento_bp
from app.domains.geolocalizacion.normalizacion_calles.routes import geolocalizacion_calles as geoloc_calles_bp
from app.domains.geolocalizacion.geocoding.routes import geolocalizacion_geocode as geoloc_geocode_bp
from app.domains.geolocalizacion.geocode.routes import geolocalizacion_map as geoloc_map_bp
from app.domains.usuarios.routes import usuarios_api as usuarios_api_bp
from app.domains.mapa_detalle.routes import mapa_detalle_api as mapa_detalle_api_bp
from app.domains.denuncias.routes import denuncias_api as denuncias_api_bp
from app.domains.usuarios.security.jwt import init_jwt
from app.domains.usuarios.services.users_service import ensure_dev_admin_seed

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
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-change-this-secret")
    app.config["SMTP_HOST"] = os.getenv("SMTP_HOST")
    app.config["SMTP_PORT"] = os.getenv("SMTP_PORT", "587")
    app.config["SMTP_USER"] = os.getenv("SMTP_USER")
    app.config["SMTP_PASS"] = os.getenv("SMTP_PASS")
    app.config["SMTP_FROM"] = os.getenv("SMTP_FROM")
    app.config["PASSWORD_RESET_PEPPER"] = os.getenv("PASSWORD_RESET_PEPPER")

    # ✅ override ANTES de init_app
    if config_override:
        app.config.update(config_override)

    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

    db.init_app(app)
    migrate.init_app(app, db)
    init_jwt(app)

    app.url_map.strict_slashes = False
  
    app.register_blueprint(actuacion_bp, url_prefix="/actuaciones")
    app.register_blueprint(relevamiento_bp, url_prefix="/relevamientos")
    
    app.register_blueprint(grid_bp)
    app.register_blueprint(geoloc_calles_bp)
    app.register_blueprint(geoloc_geocode_bp)
    app.register_blueprint(geoloc_map_bp)
    app.register_blueprint(mapa_detalle_api_bp)
    app.register_blueprint(usuarios_api_bp)
    app.register_blueprint(denuncias_api_bp)

    # Seed opcional de admin solo en desarrollo.
    if os.getenv("FLASK_ENV", "development").lower() == "development":
        with app.app_context():
            try:
                if inspect(db.engine).has_table("users"):
                    ensure_dev_admin_seed()
            except Exception:
                app.logger.exception("No se pudo crear/verificar seed admin de desarrollo")
    print(app.url_map)

    return app
