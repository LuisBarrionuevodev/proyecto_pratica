"""Blueprint de catálogos operativos (STAB-8)."""

from flask import Blueprint

catalogos = Blueprint("catalogos", __name__)

from . import rubros  # noqa: E402,F401
