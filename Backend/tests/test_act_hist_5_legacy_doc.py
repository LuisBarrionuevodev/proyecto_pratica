"""ACT-HIST.5 / LEGACY-DOC.2 — sin expediente envío + materialización diferida de oficio."""

from __future__ import annotations

import random
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_oficio_row
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import estado_recorrido_label
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.declarar_sin_expediente_envio_service import (
    declarar_sin_expediente_envio,
)
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.domains.rutas_trabajo.utils.iniciadores_pendientes_stock_query import (
    query_iniciadores_pendientes_stock,
)
from app.models import (
    Actuaciones,
    CatalogMotivoComprobacion,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Oficio,
    OrdenTrabajo,
    User,
)
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
    row = CatalogMotivoComprobacion.query.first()
    if row is None:
        pytest.skip("Se requiere catálogo de motivos de comprobación")
    return str(row.nombre)


def _mk_user() -> User:
    u = User(
        username=f"u_ah5_{_unique_num()}",
        email=f"ah5_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _historical_row(**overrides) -> dict:
    return {
        "carga_solo_comprobacion": True,
        "fecha_actuacion": "2026-09-21",
        "inspectores": [_inspector_nombre()],
        "contrib_apellido": "Histórico",
        "contrib_nombre": "Apellido",
        "calle": f"Hist {_unique_acta()}",
        "numero": "100",
        "acta_comprobacion_num": _unique_acta(),
        "comprobacion_motivo": _motivo_comprobacion(),
        **overrides,
    }


def _historical_payload(**overrides) -> dict:
    row = ActuacionGridRowIn.model_validate(_historical_row(**overrides))
    payload = map_actuacion_row(row)
    payload.update(overrides)
    return payload


def _historical_act_legacy_sin_domicilio(**overrides) -> Actuaciones:
    """Simula actuación histórica legacy sin domicilio (pre ACT-HIST.7)."""
    act = crear_actuacion_desde_payload(_historical_payload(**overrides))
    act.domicilio_id = None
    db.session.flush()
    return act


def _pendientes_filters() -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": "comprobacion",
        }
    )


def _circuito_con_domicilio() -> tuple[Actuaciones, JuzgadoCatalogo]:
    jz = JuzgadoCatalogo(codigo=f"JZAH5{_unique_num()}"[:32], nombre=f"Jz AH5 {_unique_num()}")
    db.session.add(jz)
    db.session.flush()
    dom = Domicilio(calle=f"CAH5{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=9)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_acta(), anio=2026, mes=9, motivo="ah5 normal")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 9, 21),
        mes=9,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.add(
        Expediente(
            numero_expediente=_unique_num()[:6],
            anio="2026",
            fecha_expediente=date(2026, 9, 22),
            tipo_expediente="ENVIO_ACTA",
            comprobacion_id=comp.id,
        )
    )
    db.session.flush()
    return act, jz


def _payload_oficio(juzgado_id: int) -> dict:
    return {
        "numero_oficio": f"OF{_unique_num()[:4]}",
        "fecha_oficio": date(2026, 9, 25),
        "juzgado_id": juzgado_id,
        "numero_expediente_oficio": _unique_num()[:6],
        "fecha_expediente_oficio": date(2026, 9, 25),
    }


# --- Declaración sin expediente ---


def test_declarar_sin_expediente_ok(app_ctx) -> None:
    try:
        u = _mk_user()
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        result = declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        comp = result["comprobacion"]
        assert comp.sin_expediente_envio is True
        assert comp.sin_expediente_envio_declarado_by_user_id == u.id
        assert comp.sin_expediente_envio_declarado_at is not None
        assert Expediente.query.filter_by(comprobacion_id=comp.id).count() == 0
    finally:
        db.session.rollback()


def test_declarar_sin_expediente_idempotente(app_ctx) -> None:
    try:
        u = _mk_user()
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        r1 = declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        r2 = declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        assert r1["idempotent"] is False
        assert r2["idempotent"] is True
    finally:
        db.session.rollback()


def test_declarar_sin_expediente_reject_si_hay_expediente(app_ctx) -> None:
    try:
        act, _jz = _circuito_con_domicilio()
        u = _mk_user()
        with pytest.raises(ValueError, match="expediente de envío"):
            declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
    finally:
        db.session.rollback()


def test_declarar_desaparece_pendiente_expediente_aparece_oficio(app_ctx) -> None:
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
        row = actuacion_to_pendiente_oficio_row(act)
        assert row["sin_expediente_envio"] is True
        assert row["expediente_envio_label"] == "Sin expediente de envío"
    finally:
        db.session.rollback()


# --- Oficio completion ---


def test_oficio_reject_sin_expediente_ni_flag(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz AH5 {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        with pytest.raises(LookupError, match="expediente de envío"):
            complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id))
    finally:
        db.session.rollback()


def test_oficio_permitido_con_flag_sin_expediente(app_ctx) -> None:
    try:
        u = _mk_user()
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz AH5 {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        assert result["oficio"].id is not None
        assert result["expediente_respuesta_oficio"].id is not None
    finally:
        db.session.rollback()


def test_oficio_sin_domicilio_pendiente_domicilio_sin_iniciador(app_ctx) -> None:
    try:
        u = _mk_user()
        act = _historical_act_legacy_sin_domicilio()
        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz AH5 {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        assert result["iniciador_ruta"] is None
        assert result["iniciador_materializacion_estado"] == "PENDIENTE_DOMICILIO"
        assert (
            IniciadorRuta.query.filter_by(actuacion_id=act.id, deleted_at=None).count()
            == 0
        )
        assert estado_recorrido_label(act) == "Oficio cargado — pendiente domicilio operativo"
    finally:
        db.session.rollback()


def test_oficio_con_domicilio_materializado(app_ctx) -> None:
    try:
        u = _mk_user()
        act, jz = _circuito_con_domicilio()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        assert result["iniciador_ruta"] is not None
        assert result["iniciador_materializacion_estado"] == "MATERIALIZADO"
        assert (
            IniciadorRuta.query.filter_by(
                actuacion_id=act.id, tipo_iniciador="REINSPECCION_OFICIO", deleted_at=None
            ).count()
            == 1
        )
    finally:
        db.session.rollback()


def test_oficio_error_iniciador_hace_rollback(app_ctx) -> None:
    try:
        u = _mk_user()
        act, jz = _circuito_con_domicilio()
        with patch(
            "app.domains.actuaciones.services.oficio_materializacion_service.get_or_create_iniciador_from_oficio",
            side_effect=RuntimeError("fallo inesperado iniciador"),
        ):
            with pytest.raises(RuntimeError, match="fallo inesperado"):
                complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        db.session.rollback()
        assert Oficio.query.filter_by(comprobacion_id=act.comprobacion_id, deleted_at=None).count() == 0
    finally:
        db.session.rollback()


# --- E2E caminos ---


def test_e2e_camino_1_legacy_sin_domicilio_pendiente_domicilio(app_ctx) -> None:
    """Regresión legacy: actuación sin domicilio → oficio → PENDIENTE_DOMICILIO."""
    try:
        u = _mk_user()
        act = _historical_act_legacy_sin_domicilio()
        fl = _pendientes_filters()
        assert act.id in [a.id for a in get_pendientes_expediente(fl)]

        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        db.session.expire_all()
        assert act.id not in [a.id for a in get_pendientes_expediente(fl)]
        assert act.id in [a.id for a in get_pendientes_oficio(fl)]

        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz E2E {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        db.session.expire_all()

        assert result["iniciador_materializacion_estado"] == "PENDIENTE_DOMICILIO"
        assert IniciadorRuta.query.filter_by(actuacion_id=act.id).count() == 0
        assert act.id not in [a.id for a in get_pendientes_oficio(fl)]
        filas = list_pendientes_reinspeccion_oficio_filas(fl)
        assert not any(a.id == act.id for a, _o, _i in filas)
    finally:
        db.session.rollback()


def test_e2e_camino_2_normal_con_domicilio_materializado(app_ctx) -> None:
    try:
        u = _mk_user()
        act, jz = _circuito_con_domicilio()
        fl = _pendientes_filters()
        assert act.id in [a.id for a in get_pendientes_oficio(fl)]
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        assert result["iniciador_materializacion_estado"] == "MATERIALIZADO"
        assert result["iniciador_ruta"] is not None
    finally:
        db.session.rollback()


# --- Legacy backfill classification (simulado en datos de prueba) ---


def test_legacy_oficio_sin_iniciador_sin_domicilio_pendiente_domicilio(app_ctx) -> None:
    try:
        act = _historical_act_legacy_sin_domicilio()
        comp_id = act.comprobacion_id
        ofi = Oficio(
            numero_oficio=f"LEG{_unique_num()[:4]}",
            anio=2026,
            fecha_oficio=date(2026, 1, 1),
            comprobacion_id=comp_id,
            iniciador_materializacion_estado="PENDIENTE_DOMICILIO",
        )
        db.session.add(ofi)
        db.session.flush()
        assert ofi.iniciador_materializacion_estado == "PENDIENTE_DOMICILIO"
        assert IniciadorRuta.query.filter_by(oficio_id=ofi.id).count() == 0
    finally:
        db.session.rollback()


def test_legacy_oficio_sin_iniciador_con_domicilio_pendiente_materializacion(app_ctx) -> None:
    try:
        act, _jz = _circuito_con_domicilio()
        ofi = Oficio(
            numero_oficio=f"LEG{_unique_num()[:4]}",
            anio=2026,
            fecha_oficio=date(2026, 1, 1),
            comprobacion_id=act.comprobacion_id,
            iniciador_materializacion_estado="PENDIENTE_MATERIALIZACION",
        )
        db.session.add(ofi)
        db.session.flush()
        assert ofi.iniciador_materializacion_estado == "PENDIENTE_MATERIALIZACION"
    finally:
        db.session.rollback()


def test_legacy_oficio_con_iniciador_materializado(app_ctx) -> None:
    try:
        u = _mk_user()
        act, jz = _circuito_con_domicilio()
        result = complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        ofi = result["oficio"]
        assert ofi.iniciador_materializacion_estado == "MATERIALIZADO"
        assert IniciadorRuta.query.filter_by(oficio_id=ofi.id, deleted_at=None).count() == 1
    finally:
        db.session.rollback()


# --- Dashboard / bandejas ---


def test_dashboard_no_cuenta_oficio_pendiente_domicilio_como_iniciador(app_ctx) -> None:
    try:
        u = _mk_user()
        act = _historical_act_legacy_sin_domicilio()
        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()}"[:32], nombre=f"Jz AH5 {_unique_num()}")
        db.session.add(jz)
        db.session.flush()
        complete_oficio_from_actuacion(act.id, _payload_oficio(jz.id), actor_user_id=u.id)
        stock = query_iniciadores_pendientes_stock()
        assert not any(i.actuacion_id == act.id for i in stock)
    finally:
        db.session.rollback()


def test_estado_recorrido_sin_expediente_declarado(app_ctx) -> None:
    try:
        u = _mk_user()
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        declarar_sin_expediente_envio(act.id, actor_user_id=u.id)
        db.session.expire_all()
        assert estado_recorrido_label(act) == "Sin expediente de envío — pendiente oficio"
    finally:
        db.session.rollback()


def test_declarar_endpoint_http(app_ctx, client, auth_headers, actor_user_id) -> None:
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
    body = resp.get_json()
    assert body["ok"] is True
    assert body["sin_expediente_envio"] is True
