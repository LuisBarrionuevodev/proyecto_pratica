"""GET /catalogos/items-acta-inspeccion."""

from __future__ import annotations

from flask import jsonify

from app.domains.catalogos.services.item_acta_inspeccion_catalog_service import (
    listar_items_acta_inspeccion_catalogo,
)

from . import catalogos


@catalogos.get("/items-acta-inspeccion")
def list_items_acta_inspeccion():
    """
    Catálogo de condiciones de acta de inspección (solo activos).

    Response: {"items": [{"id", "codigo", "nombre", "orden"}]}
    """
    return jsonify({"items": listar_items_acta_inspeccion_catalogo(solo_activos=True)}), 200
