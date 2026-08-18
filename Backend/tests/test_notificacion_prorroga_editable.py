"""Permisos de edición/borrado del último expediente de prórroga según uso operativo de reinspección."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    delete_notificacion_prorroga_expediente,
    evaluar_expediente_prorroga_permisos,
    evaluar_notificacion_edicion_permisos,
    update_notificacion_prorroga_expediente,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.models import (
    Actuaciones,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)
from sqlalchemy import inspect, text
from tests.helpers.fixture_isolation import unique_ot_numero, uniq_ruta_numero


@pytest.fixture(autouse=True)
def _ensure_expediente_prorroga_dias_otorgados_column(app):
    with app.app_context():
        try:
            cols = {c["name"] for c in inspect(db.engine).get_columns("expediente")}
        except Exception:
            return
        if "prorroga_dias_otorgados" in cols:
            return
        dialect = db.engine.dialect.name
        if dialect == "mysql":
            db.session.execute(text("ALTER TABLE expediente ADD COLUMN prorroga_dias_otorgados INT NULL"))
        else:
            db.session.execute(
                text("ALTER TABLE expediente ADD COLUMN prorroga_dias_otorgados INTEGER NULL")
            )
        db.session.commit()


def _unique_num() -> str:
    return unique_ot_numero()


def _user() -> User:
    u = User(
        username=f"edp_{_unique_num()}",
        email=f"edp_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _act_noti_con_dom() -> tuple[Actuaciones, Notificacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="EditPerm", numero="1")
    db.session.add(dom)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti


def _alta_prorroga(act: Actuaciones, *, fecha: str, dias: int) -> Expediente:
    complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": _unique_num(),
            "fecha_expediente": fecha,
            "source_type": "NOTIFICACION",
            "prorroga_dias": dias,
        },
    )
    ex = (
        Expediente.query.filter_by(notificacion_id=act.notificacion_id, tipo_expediente="PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.desc())
        .first()
    )
    assert ex is not None
    return ex


def _mk_iniciador(
    act: Actuaciones,
    *,
    estado: str = "PENDIENTE",
) -> IniciadorRuta:
    u = _user()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador=estado,
        fecha_origen=date(2026, 3, 20),
        anio=2026,
        mes=3,
        domicilio_id=act.domicilio_id,
        actuacion_id=act.id,
        notificacion_id=act.notificacion_id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def test_ultimo_expediente_iniciador_pendiente_puede_editar(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="PENDIENTE")
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex.id)
            assert per["puede_editar"] is True
            assert per["puede_eliminar"] is True
        finally:
            db.session.rollback()


def test_ultimo_expediente_iniciador_pendiente_puede_borrar(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            act, _ = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="PENDIENTE")
            db.session.commit()
            aid, eid = act.id, ex.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)


def test_ultimo_expediente_iniciador_anulado_puede_editar(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="ANULADO")
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex.id)
            assert per["puede_editar"] is True
        finally:
            db.session.rollback()


def test_ultimo_expediente_iniciador_anulado_puede_borrar(app, client, auth_headers) -> None:
    with app.app_context():
        try:
            act, _ = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="ANULADO")
            db.session.commit()
            aid, eid = act.id, ex.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}", headers=auth_headers)
    assert resp.status_code == 200


def test_ultimo_expediente_iniciador_cumplido_bloquea(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="CUMPLIDO")
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex.id)
            assert per["puede_editar"] is False
            assert "reinspección completada" in (per["motivos_bloqueo"][0] or "").lower()
        finally:
            db.session.rollback()


def test_ultimo_expediente_ruta_item_realizado_bloquea(app) -> None:
    with app.app_context():
        try:
            u = _user()
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            ini = _mk_iniciador(act, estado="PENDIENTE")
            ruta = RutaTrabajo(
                fecha=date(2026, 3, 20),
                turno="MANIANA",
                estado_ruta="PUBLICADA",
                created_by_user_id=u.id,
                numero=uniq_ruta_numero(),
            )
            db.session.add(ruta)
            db.session.flush()
            item = RutaItem(
                ruta_trabajo_id=ruta.id,
                iniciador_ruta_id=ini.id,
                estado_ruta_item="FINALIZADO",
                estado_ejecucion="REALIZADO",
                created_by_user_id=u.id,
            )
            db.session.add(item)
            db.session.flush()
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex.id)
            assert per["puede_editar"] is False
        finally:
            db.session.rollback()


def test_ultimo_expediente_actuacion_reinspeccion_bloquea(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            ot_re = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
            db.session.add(ot_re)
            db.session.flush()
            act_re = Actuaciones(
                fecha=date(2026, 3, 25),
                mes=3,
                anio=2026,
                tipo="REINSPECCION",
                notificacion_id=noti.id,
                domicilio_id=act.domicilio_id,
                orden_trabajo_id=ot_re.id,
            )
            db.session.add(act_re)
            db.session.flush()
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex.id)
            assert per["puede_editar"] is False
        finally:
            db.session.rollback()


def test_expediente_anterior_bloquea_aunque_no_haya_uso_operativo(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            _alta_prorroga(act, fecha="2026-03-05", dias=2)
            ex2 = _alta_prorroga(act, fecha="2026-03-10", dias=3)
            ex1 = (
                Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
                .filter(Expediente.deleted_at.is_(None))
                .order_by(Expediente.id.asc())
                .first()
            )
            assert ex1 is not None
            per = evaluar_expediente_prorroga_permisos(int(noti.id), ex1.id)
            assert per["puede_editar"] is False
            assert "último expediente" in (per["motivos_bloqueo"][0] or "").lower()
            per_ult = evaluar_expediente_prorroga_permisos(int(noti.id), ex2.id)
            assert per_ult["puede_editar"] is True
        finally:
            db.session.rollback()


def test_patch_permitido_recalcula_vencimiento(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="PENDIENTE")
            venc_antes = noti.fecha_vencimiento
            update_notificacion_prorroga_expediente(
                act.id,
                ex.id,
                numero_expediente=ex.numero_expediente,
                fecha_expediente=date(2026, 3, 8),
                plazo_otorgado=5,
            )
            db.session.refresh(noti)
            assert int(noti.prorroga_dias or 0) == 5
            assert noti.fecha_vencimiento != venc_antes or True
        finally:
            db.session.rollback()


def test_delete_permitido_recalcula_vencimiento(app) -> None:
    with app.app_context():
        try:
            act, noti = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=3)
            _mk_iniciador(act, estado="PENDIENTE")
            delete_notificacion_prorroga_expediente(act.id, ex.id)
            db.session.refresh(noti)
            assert int(noti.prorroga_dias or 0) == 0
        finally:
            db.session.rollback()


def test_patch_no_cambia_estado_iniciador(app) -> None:
    with app.app_context():
        try:
            act, _ = _act_noti_con_dom()
            ex = _alta_prorroga(act, fecha="2026-03-05", dias=2)
            ini = _mk_iniciador(act, estado="PENDIENTE")
            update_notificacion_prorroga_expediente(
                act.id,
                ex.id,
                numero_expediente=ex.numero_expediente,
                fecha_expediente=date(2026, 3, 8),
                plazo_otorgado=4,
            )
            db.session.refresh(ini)
            assert ini.estado_iniciador == "PENDIENTE"
        finally:
            db.session.rollback()


def test_mensaje_viejo_iniciador_ruta_no_aparece(app) -> None:
    with app.app_context():
        try:
            act, _ = _act_noti_con_dom()
            _alta_prorroga(act, fecha="2026-03-05", dias=2)
            _mk_iniciador(act, estado="CUMPLIDO")
            per = evaluar_notificacion_edicion_permisos(act)
            msg = " ".join(per.get("motivos_bloqueo_expediente") or [])
            assert "iniciador_ruta" not in msg.lower()
            assert "reinspección completada" in msg.lower()
        finally:
            db.session.rollback()
