"""Bandeja GET /comprobacion/pendientes-reinspeccion-oficio: circuito documental completo sin ítem en ruta activa."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from tests.helpers.fixture_isolation import unique_ot_numero, uniq_ruta_numero

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    iniciador_reinspeccion_oficio_vigente,
    reinspeccion_oficio_bandeja_row,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Oficio,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return unique_ot_numero()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"u_rein_b_{_unique_num()}",
        email=f"rein_b_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ruta_item_reinspeccion_oficio(
    act: Actuaciones,
    ini: IniciadorRuta,
    u: User,
    *,
    estado_ruta: str,
) -> RutaItem:
    """Ruta (única por fecha+turno+numero) e ítem ligado al iniciador REINSPECCION_OFICIO."""
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 15),
        turno="TARDE",
        estado_ruta=estado_ruta,
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="PENDIENTE_ASIGNACION",
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _mk_circuito_completo() -> tuple[int, str, int]:
    """
    Retorna (actuacion_id, numero_oficio, juzgado_id) con envío + oficio + respuesta; sin iniciador.
    """
    jz = JuzgadoCatalogo(codigo=f"JZRB{_unique_num()}"[:32], nombre=f"Jz Rein B {_unique_num()}")
    db.session.add(jz)
    db.session.flush()
    dom = Domicilio(calle=f"CReinB{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="rein bandeja")
    db.session.add(comp)
    db.session.flush()
    nof = _unique_num()[:8]
    act = Actuaciones(
        fecha=date(2026, 3, 10),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ex_env = Expediente(
        numero_expediente=_unique_num()[:6],
        anio="2026",
        fecha_expediente=date(2026, 3, 12),
        tipo_expediente="ENVIO_ACTA",
        comprobacion_id=comp.id,
        oficio_id=None,
    )
    db.session.add(ex_env)
    db.session.flush()
    ofi = Oficio(
        numero_oficio=nof,
        anio=2026,
        fecha_oficio=date(2026, 3, 14),
        causa=f"Causa {_unique_num()}",
        juzgado_id=jz.id,
        comprobacion_id=comp.id,
    )
    db.session.add(ofi)
    db.session.flush()
    ex_resp = Expediente(
        numero_expediente=_unique_num()[:6],
        anio="2026",
        fecha_expediente=date(2026, 3, 18),
        tipo_expediente="RESPUESTA_OFICIO",
        comprobacion_id=comp.id,
        oficio_id=ofi.id,
    )
    db.session.add(ex_resp)
    db.session.flush()
    return act.id, nof, jz.id


def _mk_actuacion_solo_expediente_envio() -> tuple[int, int]:
    """
    Actuación con comprobación y solo expediente de envío (sin oficio ni respuesta).
    Retorna (actuacion_id, juzgado_id).
    """
    jz = JuzgadoCatalogo(codigo=f"JZSO{_unique_num()}"[:32], nombre=f"Jz Solo Env {_unique_num()}")
    db.session.add(jz)
    db.session.flush()
    dom = Domicilio(calle=f"CSoloEnv{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=4)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=4, motivo="solo envío rein")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 4, 5),
        mes=4,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ex_env = Expediente(
        numero_expediente=_unique_num()[:6],
        anio="2026",
        fecha_expediente=date(2026, 4, 6),
        tipo_expediente="ENVIO_ACTA",
        comprobacion_id=comp.id,
        oficio_id=None,
    )
    db.session.add(ex_env)
    db.session.flush()
    return act.id, jz.id


def test_alta_oficio_endpoint_completa_circuito_y_crea_iniciador_reinspeccion_oficio(app, client, auth_headers) -> None:
    """Tras POST /oficio se materializa iniciador REINSPECCION_OFICIO (idempotente vía servicio dedicado)."""
    with app.app_context():
        try:
            aid, jz_id = _mk_actuacion_solo_expediente_envio()
            db.session.commit()
        finally:
            db.session.rollback()

    resp_post = client.post(
        f"/actuaciones/{aid}/oficio",
        headers=auth_headers,
        json={
            "numero_oficio": f"OF{_unique_num()[:4]}",
            "fecha_oficio": "2026-04-10",
            "juzgado_id": jz_id,
            "causa": None,
            "numero_expediente_oficio": _unique_num()[:6],
            "fecha_expediente_oficio": "2026-04-10",
        },
    )
    assert resp_post.status_code == 201, resp_post.get_data(as_text=True)
    meta = resp_post.get_json()["meta"]
    assert meta.get("iniciador_ruta_id") is not None

    with app.app_context():
        count_ini = (
            IniciadorRuta.query.filter_by(actuacion_id=aid, tipo_iniciador="REINSPECCION_OFICIO")
            .filter(IniciadorRuta.deleted_at.is_(None))
            .count()
        )
        assert count_ini == 1

    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    ids = {x["id"] for x in resp.get_json()["items"]}
    assert aid in ids
    row = next(x for x in resp.get_json()["items"] if x["id"] == aid)
    assert row.get("iniciador_id") == meta.get("iniciador_ruta_id")
    assert row.get("tipo_iniciador") == "REINSPECCION_OFICIO"


def test_pendiente_reinspeccion_aparece_sin_iniciador(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, nof, _ = _mk_circuito_completo()
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    items = resp.get_json()["items"]
    match = next((x for x in items if x["id"] == aid), None)
    assert match is not None
    assert match.get("iniciador_id") == 0
    assert match.get("estado_iniciador") == ""
    assert match.get("oficio_numero") == nof


def test_pendiente_reinspeccion_incluye_expediente_respuesta_tipo_null_legado(app, client, auth_headers) -> None:
    """Circuito completo con expediente de respuesta sin enum (NULL) debe listarse igual."""
    with app.app_context():
        try:
            aid, nof, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            ex_r = (
                Expediente.query.filter_by(comprobacion_id=act.comprobacion_id)
                .filter(Expediente.oficio_id.isnot(None))
                .first()
            )
            assert ex_r is not None
            ex_r.tipo_expediente = None
            db.session.add(ex_r)
            db.session.commit()
        finally:
            db.session.rollback()

    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    match = next((x for x in resp.get_json()["items"] if x["id"] == aid), None)
    assert match is not None
    assert match.get("oficio_numero") == nof


def test_pendiente_reinspeccion_incluye_con_iniciador_sin_item_en_ruta(app, client, auth_headers) -> None:
    """Iniciador REINSPECCION_OFICIO en backlog (sin RutaItem en ruta activa) sigue en bandeja."""
    aid: int | None = None
    iniciador_id: int | None = None
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            iniciador_id = ini.id
            db.session.commit()
        finally:
            db.session.rollback()
    assert aid is not None and iniciador_id is not None
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    row = next((x for x in resp.get_json()["items"] if x["id"] == aid), None)
    assert row is not None
    assert row.get("iniciador_id") == iniciador_id
    assert row.get("tipo_iniciador") == "REINSPECCION_OFICIO"


def test_pendiente_reinspeccion_incluye_con_ruta_borrador(app, client, auth_headers) -> None:
    """STAB-3: ruta BORRADOR no oculta la fila (oficio sigue accionable)."""
    aid: int | None = None
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            _mk_ruta_item_reinspeccion_oficio(act, ini, u, estado_ruta="BORRADOR")
            db.session.commit()
        finally:
            db.session.rollback()
    assert aid is not None
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = {x["id"] for x in resp.get_json()["items"]}
    assert aid in ids


def test_pendiente_reinspeccion_excluye_con_iniciador_en_ruta_operativa(app, client, auth_headers) -> None:
    for estado in ("PUBLICADA", "EN_CURSO"):
        aid: int | None = None
        with app.app_context():
            try:
                aid, _, _ = _mk_circuito_completo()
                act = Actuaciones.query.get(aid)
                assert act is not None
                u = _mk_user()
                db.session.flush()
                ini = IniciadorRuta(
                    tipo_iniciador="REINSPECCION_OFICIO",
                    estado_iniciador="PENDIENTE",
                    fecha_origen=date(2026, 3, 20),
                    anio=2026,
                    mes=3,
                    domicilio_id=act.domicilio_id,
                    actuacion_id=act.id,
                    created_by_user_id=u.id,
                )
                db.session.add(ini)
                db.session.flush()
                _mk_ruta_item_reinspeccion_oficio(act, ini, u, estado_ruta=estado)
                db.session.commit()
            finally:
                db.session.rollback()
        assert aid is not None
        resp = client.get(
            "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        ids = {x["id"] for x in resp.get_json()["items"]}
        assert aid not in ids, estado


def test_pendiente_reinspeccion_incluye_ruta_cancelada(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            _mk_ruta_item_reinspeccion_oficio(act, ini, u, estado_ruta="CANCELADA")
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert aid in {x["id"] for x in resp.get_json()["items"]}


def test_pendiente_reinspeccion_incluye_ruta_cerrada(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            _mk_ruta_item_reinspeccion_oficio(act, ini, u, estado_ruta="CERRADA")
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert aid in {x["id"] for x in resp.get_json()["items"]}


def test_pendiente_reinspeccion_incluye_item_ruta_soft_deleted(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            item = _mk_ruta_item_reinspeccion_oficio(act, ini, u, estado_ruta="PUBLICADA")
            item.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert aid in {x["id"] for x in resp.get_json()["items"]}


def test_pendiente_reinspeccion_excluye_soft_delete_oficio(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            ofi = Oficio.query.filter_by(comprobacion_id=act.comprobacion_id, deleted_at=None).first()
            assert ofi is not None
            ofi.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = {x["id"] for x in resp.get_json()["items"]}
    assert aid not in ids


def test_pendiente_reinspeccion_excluye_sin_expediente_respuesta(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            ex_r = (
                Expediente.query.filter_by(comprobacion_id=act.comprobacion_id)
                .filter(Expediente.oficio_id.isnot(None))
                .first()
            )
            assert ex_r is not None
            db.session.delete(ex_r)
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = {x["id"] for x in resp.get_json()["items"]}
    assert aid not in ids


def test_reinspeccion_oficio_bandeja_row_tiene_campos_operativos(app_ctx) -> None:
    try:
        aid, nof, _ = _mk_circuito_completo()
        act = Actuaciones.query.get(aid)
        assert act is not None
        row = reinspeccion_oficio_bandeja_row(act)
        assert row["id"] == aid
        assert row["iniciador_id"] == 0
        assert row["oficio_numero"] == nof
        assert row.get("expediente_envio_numero")
        assert row.get("expediente_respuesta_numero")
    finally:
        db.session.rollback()


def test_reinspeccion_oficio_bandeja_row_incluye_iniciador_cuando_se_pasa(app_ctx) -> None:
    try:
        aid, nof, _ = _mk_circuito_completo()
        act = Actuaciones.query.get(aid)
        assert act is not None
        u = _mk_user()
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 3, 20),
            anio=2026,
            mes=3,
            domicilio_id=act.domicilio_id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        row = reinspeccion_oficio_bandeja_row(act, iniciador=iniciador_reinspeccion_oficio_vigente(aid))
        assert row["id"] == aid
        assert row["iniciador_id"] == ini.id
        assert row["tipo_iniciador"] == "REINSPECCION_OFICIO"
        assert row["oficio_numero"] == nof
    finally:
        db.session.rollback()


def test_pendiente_reinspeccion_iniciador_soft_deleted_vuelve_a_aparecer(app, client, auth_headers) -> None:
    """Si el único iniciador REINSPECCION_OFICIO está soft-deleted, la bandeja vuelve a listar la actuación."""
    with app.app_context():
        try:
            aid, _, _ = _mk_circuito_completo()
            act = Actuaciones.query.get(aid)
            assert act is not None
            u = _mk_user()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            ini.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        finally:
            db.session.rollback()
    resp = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio?omitir_rango_fecha=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = {x["id"] for x in resp.get_json()["items"]}
    assert aid in ids
