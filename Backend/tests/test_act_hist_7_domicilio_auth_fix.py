"""ACT-HIST.7 — domicilio histórico + auth declarar sin expediente."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.declarar_sin_expediente_envio_service import (
    declarar_sin_expediente_envio,
)
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.models import Contribuyente, Domicilio, IniciadorRuta, JuzgadoCatalogo, OrdenTrabajo, User
from app.models.inspector import Inspector


def _unique_acta() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _inspector_nombre() -> str:
    row = Inspector.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return str(row.nombre)


def _motivo_comprobacion() -> str:
    from app.models import CatalogMotivoComprobacion

    row = CatalogMotivoComprobacion.query.first()
    if row is None:
        pytest.skip("Se requiere catálogo de motivos de comprobación")
    return str(row.nombre)


def _mk_user() -> User:
    u = User(
        username=f"u_ah7_{_unique_num()}",
        email=f"ah7_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _historical_payload(**overrides) -> dict:
    calle = overrides.pop("calle", f"AH7 {_unique_acta()}")
    numero = overrides.pop("numero", "200")
    row = ActuacionGridRowIn.model_validate(
        {
            "carga_solo_comprobacion": True,
            "fecha_actuacion": "2026-09-21",
            "inspectores": [_inspector_nombre()],
            "contrib_apellido": "Histórico",
            "contrib_nombre": "Apellido",
            "calle": calle,
            "numero": numero,
            "acta_comprobacion_num": _unique_acta(),
            "comprobacion_motivo": _motivo_comprobacion(),
            **overrides,
        }
    )
    payload = map_actuacion_row(row)
    payload.update(overrides)
    return payload


def _pendientes_filters() -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": "comprobacion",
        }
    )


def _payload_oficio(juzgado_id: int) -> dict:
    return {
        "numero_oficio": f"OF{_unique_num()[:4]}",
        "fecha_oficio": date(2026, 9, 25),
        "juzgado_id": juzgado_id,
        "numero_expediente_oficio": _unique_num()[:6],
        "fecha_expediente_oficio": date(2026, 9, 25),
    }


def test_historical_create_hard_contract(app_ctx) -> None:
    try:
        ot_before = OrdenTrabajo.query.count()
        contrib_before = Contribuyente.query.count()
        calle = f"Contrato {_unique_acta()}"
        act = crear_actuacion_desde_payload(_historical_payload(calle=calle, numero="321"))
        db.session.flush()
        dom = Domicilio.query.get(act.domicilio_id)
        assert act.orden_trabajo_id is None
        assert act.domicilio_id is not None
        assert dom is not None
        assert dom.calle == calle
        assert dom.numero == "321"
        assert dom.contribuyente_id is None
        assert dom.rubro_id is None
        assert Contribuyente.query.count() == contrib_before
        assert OrdenTrabajo.query.count() == ot_before
    finally:
        db.session.rollback()


def test_e2e_historica_declarar_oficio_materializado_pendiente_reinspeccion(app_ctx) -> None:
    try:
        u = _mk_user()
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        fl = _pendientes_filters()
        assert act.id in [a.id for a in get_pendientes_expediente(fl)]

        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        db.session.expire_all()
        assert act.id not in [a.id for a in get_pendientes_expediente(fl)]
        assert act.id in [a.id for a in get_pendientes_oficio(fl)]

        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz AH7 {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        db.session.expire_all()

        assert result["iniciador_materializacion_estado"] == "MATERIALIZADO"
        assert result["iniciador_ruta"] is not None
        assert (
            IniciadorRuta.query.filter_by(
                actuacion_id=act.id, tipo_iniciador="REINSPECCION_OFICIO", deleted_at=None
            ).count()
            == 1
        )
        filas = list_pendientes_reinspeccion_oficio_filas(fl)
        assert any(a.id == act.id for a, _o, _i in filas)
    finally:
        db.session.rollback()


def test_declarar_sin_expediente_endpoint_sin_jwt_401(client) -> None:
    resp = client.post("/actuaciones/1/comprobacion/declarar-sin-expediente-envio")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_declarar_sin_expediente_endpoint_actor_auditado(app_ctx, client, auth_headers, actor_user_id) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload(), actor_user_id=actor_user_id)
        db.session.commit()
        aid = act.id
    finally:
        db.session.remove()

    resp = client.post(
        f"/actuaciones/{aid}/comprobacion/declarar-sin-expediente-envio",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    with client.application.app_context():
        from app.models import Comprobacion

        comp = Comprobacion.query.get(resp.get_json()["comprobacion_id"])
        assert comp is not None
        assert comp.sin_expediente_envio is True
        assert comp.sin_expediente_envio_declarado_by_user_id == actor_user_id
        assert comp.sin_expediente_envio_declarado_at is not None
