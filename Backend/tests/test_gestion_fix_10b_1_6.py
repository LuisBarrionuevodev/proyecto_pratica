"""
GESTIÓN-FIX.10B.1.6 — Diagnóstico real PUT REALIZADO → borrar todo → LOCAL CERRADO.

Solo observación: reproduce matriz de casos y registra etapa/excepción con PUT_ACTUACION_DIAG=1.
No implementa fixes.
"""

from __future__ import annotations

import json
import logging
import os

# Activar trazas diagnósticas antes de importar la app.
os.environ.setdefault("PUT_ACTUACION_DIAG", "1")

import random
from typing import Any
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion, aplicar_payload_actuacion
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    Clausura,
    Decomiso,
    Domicilio,
    Inspeccion,
    Inspector,
    Motivo,
)

from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


@pytest.fixture(autouse=True)
def _caplog_diag(caplog):
    caplog.set_level(logging.WARNING, logger="put_actuacion_diag")
    caplog.set_level(logging.ERROR, logger="put_actuacion_diag")


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspectores() -> tuple[str, str]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    return rows[0].nombre, rows[1].nombre


def _motivo_nombre() -> str:
    m = Motivo.query.first()
    if m is None:
        pytest.skip("Se requiere al menos un motivo en catálogo")
    return m.nombre


def _unique_acta() -> str:
    return f"{random.randint(100000, 999999):06d}"


def _cerrar_realizado_multi(
    *,
    item_id: int,
    user_id: int,
    acta_insp: str,
    acta_notif: str | None = None,
    acta_comp: str | None = None,
    acta_clausura: str | None = None,
    acta_decomiso: str | None = None,
) -> None:
    payload_data: dict[str, Any] = {
        "tipo_actuacion": "INSPECCION",
        "acta_inspeccion_num": acta_insp,
    }
    if acta_notif:
        payload_data["acta_notificacion_num"] = acta_notif
        payload_data["notificacion_motivo_1"] = _motivo_nombre()
    if acta_comp:
        payload_data["acta_comprobacion_num"] = acta_comp
        payload_data["comprobacion_motivo"] = "Motivo comprobación FIX.10B.1.6"
    if acta_clausura:
        payload_data["acta_clausura_num"] = acta_clausura
    if acta_decomiso:
        payload_data["acta_decomiso_num"] = acta_decomiso
        payload_data["decomiso_kilos_total"] = 1.5
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(payload_data),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _fila_put_clear_local_cerrado(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    calle: str,
    numero: str,
    rubro_nombre: str,
    actas_a_quitar: list[str],
    limpiar_contribuyente: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": "INSPECCION",
        "inspector1": insp1,
        "inspector2": insp2,
        "calle": calle,
        "numero": numero,
        "rubro_nombre": rubro_nombre,
        "limpiar_contribuyente": limpiar_contribuyente,
        "contraproducencia": "LOCAL CERRADO",
        "actas_a_quitar": actas_a_quitar,
        # Campos vacíos como envía el front tras sanitizeEmptyActasForPut
        "acta_inspeccion_num": None,
        "acta_notificacion_num": None,
        "acta_comprobacion_num": None,
        "acta_clausura_num": None,
        "acta_decomiso_num": None,
        "notificacion_motivo_1": None,
        "notificacion_motivo_2": None,
        "notificacion_motivo_3": None,
        "comprobacion_motivo": None,
        "doc_nro": None,
        "contrib_nombre": None,
        "contrib_apellido": None,
        "razon_social": None,
    }
    if extra:
        row.update(extra)
    return row


def _setup_realizado_con_actas(
    *,
    with_notif: bool = False,
    with_comp: bool = False,
    with_clausura: bool = False,
    with_decomiso: bool = False,
) -> tuple[int, int, str, str, str, str, str, str]:
    """Retorna act_id, dom_id, ot, fecha, insp1, insp2, calle, rubro."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    acta_insp = _unique_acta()
    acta_notif = _unique_acta() if with_notif else None
    acta_comp = _unique_acta() if with_comp else None
    acta_clausura = _unique_acta() if with_clausura else None
    acta_decomiso = _unique_acta() if with_decomiso else None

    _cerrar_realizado_multi(
        item_id=item_id,
        user_id=user_id,
        acta_insp=acta_insp,
        acta_notif=acta_notif,
        acta_comp=acta_comp,
        acta_clausura=acta_clausura,
        acta_decomiso=acta_decomiso,
    )

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    assert act.inspeccion is not None
    if with_notif:
        assert act.notificacion_id is not None
    if with_comp:
        assert act.comprobacion_id is not None
    if with_clausura:
        assert Clausura.query.filter_by(actuacion_id=act_id).first() is not None
    if with_decomiso:
        assert Decomiso.query.filter_by(actuacion_id=act_id).first() is not None
    assert dom.contribuyente_id is not None

    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    return (
        act_id,
        dom_id,
        ot_num,
        fecha,
        insp1,
        insp2,
        dom.calle or "San Martín",
        dom.rubro.nombre if dom.rubro else "Bar",
    )


def _run_put_matrix(
    actas_a_quitar: list[str],
    *,
    limpiar_contribuyente: bool = True,
    extra_row: dict[str, Any] | None = None,
    with_notif: bool = False,
    with_comp: bool = False,
) -> tuple[int, dict[str, Any], Exception | None, list[str]]:
    """
    Ejecuta PUT y devuelve (act_id, mapped_payload, excepción|None, líneas caplog).
    """
    act_id, dom_id, ot, fecha, insp1, insp2, calle, rubro = _setup_realizado_con_actas(
        with_notif=with_notif,
        with_comp=with_comp,
    )
    row = _fila_put_clear_local_cerrado(
        act_id=act_id,
        ot=ot,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=calle,
        numero="10",
        rubro_nombre=rubro,
        actas_a_quitar=actas_a_quitar,
        limpiar_contribuyente=limpiar_contribuyente,
        extra=extra_row,
    )
    payload = map_actuacion_row(ActuacionGridRowIn.model_validate(row))

    exc: Exception | None = None
    try:
        actualizar_actuacion(act_id, payload)
        db.session.expunge_all()
    except Exception as e:
        db.session.rollback()
        exc = e

    return act_id, payload, exc, []


MATRIX_CASES = [
    pytest.param(["INSPECCION"], {"with_notif": False, "with_comp": False}, id="solo_insp"),
    pytest.param(
        ["INSPECCION", "NOTIFICACION"],
        {"with_notif": True, "with_comp": False},
        id="insp_notif",
    ),
    pytest.param(
        ["INSPECCION", "COMPROBACION"],
        {"with_notif": False, "with_comp": True},
        id="insp_comp",
    ),
    pytest.param(
        ["INSPECCION", "NOTIFICACION", "COMPROBACION"],
        {"with_notif": True, "with_comp": True},
        id="insp_notif_comp",
    ),
]


@pytest.mark.parametrize("actas_a_quitar,setup_flags", MATRIX_CASES)
def test_m1_matriz_put_local_cerrado(
    app_ctx,
    caplog,
    actas_a_quitar: list[str],
    setup_flags: dict[str, bool],
) -> None:
    """Matriz §6 — resultado y última etapa alcanzada."""
    act_id, payload, exc, _ = _run_put_matrix(
        actas_a_quitar,
        with_notif=setup_flags.get("with_notif", False),
        with_comp=setup_flags.get("with_comp", False),
    )

    stages = [r.message for r in caplog.records if "STAGE act_id=" in r.message]
    quitars = [r.message for r in caplog.records if "QUITAR act_id=" in r.message]
    deps = [r.message for r in caplog.records if "DEPS act_id=" in r.message]
    errors = [r.message for r in caplog.records if r.levelno >= logging.ERROR]

    print(f"\n=== FIX.10B.1.6 act_id={act_id} actas_a_quitar={actas_a_quitar} ===")
    print("MAPPED_PAYLOAD:", json.dumps(payload, ensure_ascii=False, default=str))
    print("STAGES:", stages)
    print("QUITAR:", quitars)
    print("DEPS:", deps)
    if exc:
        print("EXCEPTION:", type(exc).__name__, exc)
    if errors:
        print("LOG_ERRORS:", errors)

    if exc is not None:
        # Diagnóstico: registrar sin fallar la suite entera (el objetivo es observar).
        pytest.fail(
            f"PUT falló act_id={act_id} actas={actas_a_quitar}: "
            f"{type(exc).__name__}: {exc}\n"
            f"última_etapa={stages[-1] if stages else '?'}\n"
            f"quitars={quitars}"
        )


def test_m2_caso_completo_todas_actas_y_contrib(app_ctx, caplog) -> None:
    """Caso más cercano al reporte: INSP+NOTIF+COMP+CLAUSURA+DECOMISO + limpiar contrib."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    _cerrar_realizado_multi(
        item_id=item_id,
        user_id=user_id,
        acta_insp=_unique_acta(),
        acta_notif=_unique_acta(),
        acta_comp=_unique_acta(),
        acta_clausura=_unique_acta(),
        acta_decomiso=_unique_acta(),
    )

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None

    row = _fila_put_clear_local_cerrado(
        act_id=act_id,
        ot=act.orden_trabajo.numero_acta if act.orden_trabajo else "000001",
        fecha=act.fecha.strftime("%d/%m/%Y"),
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "X",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        actas_a_quitar=[
            "INSPECCION",
            "NOTIFICACION",
            "COMPROBACION",
            "CLAUSURA",
            "DECOMISO",
        ],
        limpiar_contribuyente=True,
    )
    payload = map_actuacion_row(ActuacionGridRowIn.model_validate(row))

    exc: Exception | None = None
    try:
        actualizar_actuacion(act_id, payload)
        db.session.expunge_all()
    except Exception as e:
        db.session.rollback()
        exc = e

    stages = [r.message for r in caplog.records if "STAGE act_id=" in r.message]
    print(f"\n=== CASO COMPLETO act_id={act_id} ===")
    print("PAYLOAD:", json.dumps(payload, ensure_ascii=False, default=str))
    print("STAGES:", stages)
    if exc:
        print("EXCEPTION:", type(exc).__name__, exc)
        pytest.fail(f"{type(exc).__name__}: {exc} en etapa {stages[-1] if stages else '?'}")

    act_db = db.session.get(Actuaciones, act_id)
    dom_db = db.session.get(Domicilio, dom_id)
    assert act_db is not None and dom_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert act_db.notificacion_id is None
    assert act_db.comprobacion_id is None
    assert Clausura.query.filter_by(actuacion_id=act_id).first() is None
    assert Decomiso.query.filter_by(actuacion_id=act_id).first() is None
    assert dom_db.contribuyente_id is None


def _assert_put_local_cerrado_sin_actas_ni_contrib_ni_eo(act_id: int, dom_id: int) -> None:
    act_db = db.session.get(Actuaciones, act_id)
    dom_db = db.session.get(Domicilio, dom_id)
    assert act_db is not None and dom_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.inspeccion is None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert act_db.notificacion_id is None
    assert act_db.comprobacion_id is None
    assert dom_db.contribuyente_id is None
    assert act_db.establecimiento_operativo_id is None


def test_fix_10b_1_6_put_exacto_tres_actas_contrib_local_cerrado(app_ctx) -> None:
    """
    Caso confirmado act #13639: REALIZADO + INSP+NOTIF+COMP + contrib + EO
    → PUT quitar actas + limpiar_contribuyente + LOCAL CERRADO → HTTP 200.
    """
    act_id, dom_id, ot, fecha, insp1, insp2, calle, rubro = _setup_realizado_con_actas(
        with_notif=True,
        with_comp=True,
    )
    act_before = db.session.get(Actuaciones, act_id)
    dom_before = db.session.get(Domicilio, dom_id)
    assert act_before is not None and dom_before is not None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is not None
    assert act_before.notificacion_id is not None
    assert act_before.comprobacion_id is not None
    assert dom_before.contribuyente_id is not None

    payload = map_actuacion_row(
        ActuacionGridRowIn.model_validate(
            _fila_put_clear_local_cerrado(
                act_id=act_id,
                ot=ot,
                fecha=fecha,
                insp1=insp1,
                insp2=insp2,
                calle=calle,
                numero="10",
                rubro_nombre=rubro,
                actas_a_quitar=["INSPECCION", "NOTIFICACION", "COMPROBACION"],
                limpiar_contribuyente=True,
            )
        )
    )
    assert payload.get("contribuyente") is None
    assert payload.get("actas_a_quitar") == ["INSPECCION", "NOTIFICACION", "COMPROBACION"]

    out = actualizar_actuacion(act_id, payload)
    assert int(out.id) == act_id
    db.session.expunge_all()
    _assert_put_local_cerrado_sin_actas_ni_contrib_ni_eo(act_id, dom_id)


def test_fix_10b_1_6_limpiar_contrib_sin_domicilio_payload_no_unbound(app_ctx) -> None:
    """
    Rama que llama ``_aplicar_rubro_contrib_seguro`` con ``limpiar_contribuyente``
    cuando el payload NO incluye ``domicilio`` (evita UnboundLocalError por shadowing).
    """
    act_id, dom_id, ot, fecha, insp1, insp2, _calle, rubro = _setup_realizado_con_actas(
        with_notif=True,
        with_comp=True,
    )
    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    assert dom.contribuyente_id is not None

    payload: dict = {
        "orden_trabajo_numero": ot,
        "fecha_actuacion": act.fecha.isoformat(),
        "tipo_actuacion": "INSPECCION",
        "rubro_nombre": rubro,
        "contribuyente": None,
        "contraproducencia": "LOCAL CERRADO",
        "inspectores": [insp1, insp2],
        "actas_a_quitar": ["INSPECCION", "NOTIFICACION", "COMPROBACION"],
    }
    assert "domicilio" not in payload

    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()
    _assert_put_local_cerrado_sin_actas_ni_contrib_ni_eo(act_id, dom_id)


def test_fix_10b_1_6_aplicar_payload_limpiar_contrib_rama_segura(app_ctx) -> None:
    """``aplicar_payload_actuacion`` directo: contrib_clear sin domicilio en payload."""
    act_id, dom_id, _ot, _fecha, insp1, insp2, _calle, rubro = _setup_realizado_con_actas(
        with_notif=False,
        with_comp=False,
    )
    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    assert dom.contribuyente_id is not None

    aplicar_payload_actuacion(
        act,
        {
            "rubro_nombre": rubro,
            "contribuyente": None,
            "inspectores": [insp1, insp2],
        },
        ejecutar_resolver_previas=False,
    )
    db.session.flush()
    dom_db = db.session.get(Domicilio, dom_id)
    assert dom_db is not None
    assert dom_db.contribuyente_id is None


def test_fix_10b_1_6_put_http_tres_actas_contrib_200(app, client, auth_headers) -> None:
    """PUT HTTP end-to-end: mismo caso que #13639 → 200."""
    with app.app_context():
        act_id, dom_id, ot, fecha, insp1, insp2, calle, rubro = _setup_realizado_con_actas(
            with_notif=True,
            with_comp=True,
        )
        body = _fila_put_clear_local_cerrado(
            act_id=act_id,
            ot=ot,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            calle=calle,
            numero="10",
            rubro_nombre=rubro,
            actas_a_quitar=["INSPECCION", "NOTIFICACION", "COMPROBACION"],
            limpiar_contribuyente=True,
        )
        r = client.put(f"/actuaciones/{act_id}", headers=auth_headers, json=body)
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None
        assert int(data["id"]) == act_id
        assert data.get("contraproducencia") == "LOCAL CERRADO"
        assert data.get("acta_inspeccion_num") in (None, "")
        assert data.get("acta_notificacion_num") in (None, "")
        assert data.get("acta_comprobacion_num") in (None, "")
        assert data.get("doc_nro") in (None, "")
        assert data.get("establecimiento_operativo_id") in (None, "")
        db.session.expunge_all()
        _assert_put_local_cerrado_sin_actas_ni_contrib_ni_eo(act_id, dom_id)


def test_m3_motivos_residual_en_raw_no_entran_al_mapper(app_ctx) -> None:
    """
    §7 — Si acta está vacía, el mapper no debe emitir notificacion/comprobacion
    aunque queden motivos en la fila cruda.
    """
    row = _fila_put_clear_local_cerrado(
        act_id=1,
        ot="000001",
        fecha="10/06/2026",
        insp1="A",
        insp2="B",
        calle="X",
        numero="1",
        rubro_nombre="Bar",
        actas_a_quitar=["INSPECCION", "NOTIFICACION", "COMPROBACION"],
        extra={
            "notificacion_motivo_1": "",
            "comprobacion_motivo": "  ",
        },
    )
    payload = map_actuacion_row(ActuacionGridRowIn.model_validate(row))
    assert "notificacion" not in payload
    assert "comprobacion" not in payload
    assert payload.get("actas_a_quitar") == ["INSPECCION", "NOTIFICACION", "COMPROBACION"]
    assert payload.get("contribuyente") is None  # limpiar_contribuyente


def test_m4_put_http_ruta_registra_500(app, client, auth_headers, caplog) -> None:
    """§2 — PUT HTTP con diag: captura status y excepción en logs (no solo 500)."""
    caplog.set_level(logging.WARNING, logger="put_actuacion_diag")
    caplog.set_level(logging.ERROR, logger="put_actuacion_diag")
    with app.app_context():
        act_id, _dom_id, ot, fecha, insp1, insp2, calle, rubro = _setup_realizado_con_actas(
            with_notif=True,
            with_comp=True,
        )
        body = _fila_put_clear_local_cerrado(
            act_id=act_id,
            ot=ot,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            calle=calle,
            numero="10",
            rubro_nombre=rubro,
            actas_a_quitar=["INSPECCION", "NOTIFICACION", "COMPROBACION"],
        )
        r = client.put(f"/actuaciones/{act_id}", headers=auth_headers, json=body)
        errors = [rec.message for rec in caplog.records if rec.levelno >= logging.ERROR]
        stages = [rec.message for rec in caplog.records if "STAGE act_id=" in rec.message]
        print(f"\n=== HTTP PUT status={r.status_code} ===")
        print("body_response:", r.get_json())
        print("STAGES:", stages)
        print("LOG_ERRORS:", errors)
        assert r.status_code == 200
