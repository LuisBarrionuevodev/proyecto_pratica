# app/main.py
import json
import os
from dotenv import load_dotenv
import click
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import inspect

from app.database import db
from app.security.deployment_config import (
    apply_cors,
    deployment_is_strict,
    enforce_strict_runtime_config,
    parse_cors_origins,
)
from app.security.phase1_jwt_guard import register_phase1_jwt_guard
from app.security.dev_post_root_logger import register_dev_post_root_logger
from app.security.rate_limiter import init_rate_limiter
from app.domains.actuaciones.routes import actuacion as actuacion_bp
from app.domains.grid.routes import grid as grid_bp
from app.domains.relevamientos.routes import relevamiento as relevamiento_bp
from app.domains.geolocalizacion.normalizacion_calles.routes import geolocalizacion_calles as geoloc_calles_bp
from app.domains.geolocalizacion.geocoding.routes import geolocalizacion_geocode as geoloc_geocode_bp
from app.domains.geolocalizacion.geocode.routes import geolocalizacion_map as geoloc_map_bp
from app.domains.usuarios.routes import usuarios_api as usuarios_api_bp
from app.domains.mapa_detalle.routes import mapa_detalle_api as mapa_detalle_api_bp
from app.domains.denuncias.routes import denuncias_api as denuncias_api_bp
from app.domains.establecimientos.routes.establecimientos_operativos import (
    establecimientos_operativos_bp,
)
from app.domains.rutas_trabajo.routes import rutas_trabajo as rutas_trabajo_bp
from app.domains.indicadores.routes import indicadores_api as indicadores_api_bp
from app.domains.catalogos.routes import catalogos as catalogos_bp
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

    # EpiCollect5 (API de export; opcional hasta usar import-from-api)
    app.config["EPICOLLECT_BASE_URL"] = os.getenv("EPICOLLECT_BASE_URL") or "https://five.epicollect.net"
    app.config["EPICOLLECT_PROJECT_SLUG"] = os.getenv("EPICOLLECT_PROJECT_SLUG")
    app.config["EPICOLLECT_FORM_REF"] = os.getenv("EPICOLLECT_FORM_REF")
    app.config["EPICOLLECT_CLIENT_ID"] = os.getenv("EPICOLLECT_CLIENT_ID")
    app.config["EPICOLLECT_CLIENT_SECRET"] = os.getenv("EPICOLLECT_CLIENT_SECRET")
    app.config["EPICOLLECT_TIMEOUT_SECONDS"] = os.getenv("EPICOLLECT_TIMEOUT_SECONDS")

    # ✅ override ANTES de init_app
    if config_override:
        app.config.update(config_override)

    enforce_strict_runtime_config(app)
    _cors_origins = parse_cors_origins(strict=deployment_is_strict())
    apply_cors(app, _cors_origins)

    db.init_app(app)
    migrate.init_app(app, db)
    init_jwt(app)
    init_rate_limiter(app)
    register_phase1_jwt_guard(app)
    register_dev_post_root_logger(app)

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
    app.register_blueprint(establecimientos_operativos_bp, url_prefix="/establecimientos-operativos")
    app.register_blueprint(rutas_trabajo_bp, url_prefix="/rutas-trabajo")
    app.register_blueprint(indicadores_api_bp, url_prefix="/api/indicadores")
    app.register_blueprint(catalogos_bp, url_prefix="/catalogos")

    # Seed opcional de admin solo en desarrollo.
    if os.getenv("FLASK_ENV", "development").lower() == "development":
        with app.app_context():
            try:
                if inspect(db.engine).has_table("users"):
                    ensure_dev_admin_seed()
            except Exception:
                app.logger.exception("No se pudo crear/verificar seed admin de desarrollo")

    @app.cli.command("sync-notificaciones-vencidas")
    def sync_notificaciones_vencidas_cli() -> None:
        """
        Materializa iniciadores REINSPECCION_NOTIFICACION por notificaciones vencidas (Fase C).

        Camino canónico para cron / Task Scheduler: equivalente al módulo
        `app.domains.actuaciones.pipelines.sync_notificaciones_vencidas`.
        """
        from app.domains.actuaciones.pipelines.sync_notificaciones_vencidas import (
            run_sync_notificaciones_vencidas,
        )

        try:
            metrics = run_sync_notificaciones_vencidas()
        except Exception:
            app.logger.exception("sync-notificaciones-vencidas CLI falló")
            raise click.Abort()
        click.echo(json.dumps(metrics, ensure_ascii=True))

    @app.cli.command("epicollect-import-from-api")
    @click.argument("actuacion_id", type=int)
    @click.argument("ec5_uuid")
    def epicollect_import_from_api_cli(actuacion_id: int, ec5_uuid: str) -> None:
        """
        Descarga un entry desde la API EpiCollect y ejecuta el import sobre ACTUACION_ID.

        Requiere EPICOLLECT_PROJECT_SLUG (y credenciales OAuth si el proyecto es privado).
        """
        from flask import current_app

        from app.domains.actuaciones.services.epicollect_import_service import (
            EpicollectImportConflictError,
        )
        from app.domains.actuaciones.services.epicollect_remote_import_service import (
            fetch_and_import_epicollect_entry,
        )
        from app.integrations.epicollect.errors import (
            EpicollectAuthError,
            EpicollectClientError,
            EpicollectConfigError,
            EpicollectEntryNotFoundError,
            EpicollectHttpError,
            EpicollectNetworkError,
        )

        with app.app_context():
            try:
                act, media_n = fetch_and_import_epicollect_entry(
                    actuacion_id,
                    ec5_uuid,
                    app_config=dict(current_app.config),
                )
            except EpicollectConfigError as e:
                click.echo(f"Config: {e}", err=True)
                raise click.Abort()
            except EpicollectEntryNotFoundError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except EpicollectAuthError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except EpicollectHttpError as e:
                click.echo(f"HTTP {e.status_code}: {e}", err=True)
                raise click.Abort()
            except EpicollectNetworkError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except EpicollectImportConflictError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except EpicollectClientError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except ValueError as e:
                click.echo(str(e), err=True)
                raise click.Abort()
            except Exception:
                app.logger.exception("epicollect-import-from-api CLI falló")
                raise click.Abort()
        click.echo(
            json.dumps(
                {"actuacion_id": act.id, "ec5_uuid": act.ec5_uuid, "media_count": media_n},
                ensure_ascii=True,
            )
        )

    @app.cli.command("audit-inspectores-actuaciones")
    @click.option(
        "--max-ids",
        type=int,
        default=200,
        show_default=True,
        help="Máximo de ids listados en actuacion_ids_mas_de_3.",
    )
    def audit_inspectores_actuaciones_cli(max_ids: int) -> None:
        """
        Inventario: cuántas actuaciones tienen más de 3 inspectores activos (tabla puente).

        Cuenta solo filas con deleted_at IS NULL. Salida JSON para scripts y revisiones previas
        a migrar el contrato de grilla (inspector1/2/3).
        """
        from app.domains.actuaciones.audit.inspectores_actuaciones_audit import (
            audit_actuaciones_inspectores_summary,
        )

        with app.app_context():
            try:
                report = audit_actuaciones_inspectores_summary(max_detail_ids=max_ids)
            except Exception:
                app.logger.exception("audit-inspectores-actuaciones falló")
                raise click.Abort()
        click.echo(json.dumps(report, ensure_ascii=True, indent=2))

    return app
