"""
AUDITORIA V1.1-TRAZABILIDAD-RELEVAMIENTOS.0 — tests de caracterización (comportamiento actual).

Demuestran por qué cierres terminales no aparecen en la bandeja «Realizados» de Gestión.
No validan el comportamiento deseado a futuro.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.database import db
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.list_service import (
    listar_relevamientos_operativos_con_filtros,
    listar_relevamientos_realizados_actuacion_completada_con_filtros,
)
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.models import Domicilio, DomicilioGeocode, IniciadorRuta, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


def _filters() -> RelevamientosListFilters:
    return RelevamientosListFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "page": 1,
            "page_size": 200,
        }
    )


def _set_geocode(domicilio_id: int) -> None:
    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id, deleted_at=None).first()
    if geo is None:
        geo = DomicilioGeocode(domicilio_id=domicilio_id)
        db.session.add(geo)
    geo.geo_status = "OK"
    geo.lat = Decimal("-26.8241000")
    geo.lng = Decimal("-65.2226000")
    geo.source = "MANUAL"
    db.session.flush()


def _mk_relevamiento_con_iniciador(*, estado_iniciador: str) -> tuple[Relevamiento, IniciadorRuta]:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-06-15",
            "relevadores_nombres": [rev.nombre],
            "domicilio": {"calle": uniq("AudTraz"), "numero": "50"},
            "rubro_nombre": rub.nombre,
            "esta_abierto": True,
        }
    )
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    _set_geocode(dom.id)
    ini = get_or_create_iniciador_from_relevamiento(rel, actor_user_id=1)
    ini.estado_iniciador = estado_iniciador
    if estado_iniciador == "CERRADO_NO_EXISTE_LOCAL":
        ini.cerrado_motivo = "NO_EXISTE_LOCAL"
        ini.cerrado_at = date(2026, 6, 15)
    db.session.add_all([rel, ini])
    db.session.commit()
    return rel, ini


def _ids_operativos() -> set[int]:
    result = listar_relevamientos_operativos_con_filtros(_filters())
    return {int(r.id) for r, _ in result["items"]}


def _ids_realizados() -> set[int]:
    result = listar_relevamientos_realizados_actuacion_completada_con_filtros(_filters())
    return {int(r.id) for r in result["items"]}


def test_char_gestion_realizados_solo_iniciador_cumplido(app_ctx) -> None:
    """GET /relevamientos/realizados exige exists(IniciadorRuta.estado_iniciador == CUMPLIDO)."""
    rel_ok, _ = _mk_relevamiento_con_iniciador(estado_iniciador="CUMPLIDO")
    rel_ne, _ = _mk_relevamiento_con_iniciador(estado_iniciador="CERRADO_NO_EXISTE_LOCAL")
    rel_re, _ = _mk_relevamiento_con_iniciador(estado_iniciador="PENDIENTE")

    realizados = _ids_realizados()
    operativos = _ids_operativos()

    assert rel_ok.id in realizados
    assert rel_ne.id not in realizados
    assert rel_re.id not in realizados

    assert rel_ok.id not in operativos
    assert rel_ne.id not in operativos
    assert rel_re.id in operativos


def test_char_cerrado_no_existe_local_invisible_en_realizados_legacy(app_ctx) -> None:
    """Legacy /realizados: solo CUMPLIDO; cierre NO EXISTE LOCAL sigue fuera de Pendientes."""
    rel, ini = _mk_relevamiento_con_iniciador(estado_iniciador="CERRADO_NO_EXISTE_LOCAL")
    assert ini.estado_iniciador == "CERRADO_NO_EXISTE_LOCAL"

    assert rel.id not in _ids_operativos()
    assert rel.id not in _ids_realizados()
