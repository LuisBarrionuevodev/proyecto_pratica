import logging
from logging.config import fileConfig
import os

from flask import current_app

# Import models if available so metadata is populated for autogenerate.
# For explicit (manual) migrations, metadata is not strictly required.
try:
    import app.models  # noqa: F401
except Exception:  # pragma: no cover
    app = None

from alembic import context
from sqlalchemy import create_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def _get_db_url_fallback() -> str:
    """Obtener URL de DB cuando no existe un contexto Flask activo.

    Prioridad:
    1) env var `SQLALCHEMY_DATABASE_URI`
    2) `sqlalchemy.url` desde `migrations/alembic.ini`
    """
    return os.getenv("SQLALCHEMY_DATABASE_URI") or config.get_main_option(
        "sqlalchemy.url"
    )


def _has_flask_app_context() -> bool:
    """Detecta si `current_app` es accesible (hay app context)."""
    try:
        _ = current_app.name  # noqa: F841
        return True
    except Exception:
        return False


def get_engine():
    """Devuelve un Engine, con o sin Flask app context."""
    if _has_flask_app_context():
        try:
            # this works with Flask-SQLAlchemy<3 and Alchemical
            return current_app.extensions["migrate"].db.get_engine()
        except (TypeError, AttributeError):
            # this works with Flask-SQLAlchemy>=3
            return current_app.extensions["migrate"].db.engine

    return create_engine(_get_db_url_fallback())


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
if _has_flask_app_context():
    target_db = current_app.extensions["migrate"].db
else:
    from app.database import db as target_db  # type: ignore

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    if _has_flask_app_context():
        conf_args = current_app.extensions["migrate"].configure_args
        if conf_args.get("process_revision_directives") is None:
            conf_args["process_revision_directives"] = process_revision_directives
    else:
        conf_args = {}

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
