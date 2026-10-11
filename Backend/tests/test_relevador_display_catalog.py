"""V1.1-CATALOGOS-UX.1 — etiqueta y orden de catálogo Relevador."""

from __future__ import annotations

from app.domains.relevamientos.catalogs.relevador import listar_relevadores_catalogo
from app.domains.relevamientos.utils.relevador_display import (
    relevador_etiqueta_catalogo,
    relevador_nombres_equivalentes,
)


def test_etiqueta_apellido_nombre_desde_legacy(app_ctx) -> None:
    assert relevador_etiqueta_catalogo("Fabian Esquivel") == "Esquivel, Fabian"
    assert relevador_etiqueta_catalogo("Biscardi Roberto") == "Biscardi, Roberto"
    assert relevador_nombres_equivalentes("Fabian Esquivel", "Esquivel, Fabian")


def test_catalogo_ordenado_por_apellido(app_ctx) -> None:
    from app.domains.relevamientos.utils.relevador_display import relevador_sort_key

    items = listar_relevadores_catalogo(solo_activos=False)
    keys = [relevador_sort_key(i["nombre"]) for i in items]
    assert keys == sorted(keys)
    assert "Esquivel, Fabian" in [i["nombre"] for i in items]
