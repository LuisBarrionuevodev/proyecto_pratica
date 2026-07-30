"""PR10.4a — Historial por DNI/CUIT para Establecimientos (solo consulta)."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.establecimientos.presenters.historial_contribuyente_presenters import (
    historial_contribuyente_rows,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    list_historial_por_documento,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Contribuyente,
    Decomiso,
    Denuncia,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Inspector,
    Motivo,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return uuid4().hex[:6].upper()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere inspector en catálogo")
    return ins


def _historial(doc: str) -> tuple[list[dict], int, str]:
    entries, total, norm = list_historial_por_documento(doc, limit=200)
    return historial_contribuyente_rows(entries), total, norm


def _mk_contrib(doc: str, *, apellido: str = "Hist", nombre: str = "Test") -> Contribuyente:
    c = Contribuyente(apellido=apellido, nombre=nombre, documento=doc)
    db.session.add(c)
    db.session.flush()
    return c


def _mk_act_base(
    contrib: Contribuyente,
    *,
    rubro: Rubro | None = None,
    tipo: str | None = "INSPECCION",
    fecha: date | None = None,
) -> Actuaciones:
    rub = rubro or Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    dom = Domicilio(
        calle=f"Hist{_unique_num()}",
        numero="100",
        contribuyente_id=contrib.id,
        rubro_id=rub.id,
    )
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    f = fecha or date(2026, 8, 10)
    act = Actuaciones(
        fecha=f,
        mes=f.month,
        anio=f.year,
        tipo=tipo,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_normalizar_documento_quita_separadores() -> None:
    assert normalizar_documento("20-33344455-5") == "20333444555"
    assert normalizar_documento("20.333.44455.5") == "20333444555"
    assert normalizar_documento("33.344.455") == "33344455"


def test_api_busca_dni_con_puntos_y_guiones(client, auth_headers, app) -> None:
    doc = "20333444555"
    with app.app_context():
        try:
            contrib = _mk_contrib(doc)
            _mk_act_base(contrib)
            db.session.commit()
            for fmt in (doc, "20-33344455-5", "20.333.44455.5"):
                r = client.get(
                    f"/establecimientos/historial-contribuyente?documento={fmt}",
                    headers=auth_headers,
                )
                assert r.status_code == 200, r.get_json()
                data = r.get_json()
                assert data["meta"]["total"] >= 1
                assert len(data["rows"]) >= 1
        finally:
            db.session.rollback()


def test_incluye_actuacion_realizada(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib, tipo="INSPECCION")
        db.session.commit()
        rows, total, _ = _historial(doc)
        assert total >= 1
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["estado"] == "REALIZADA"
        assert match["realizada"] is True
    finally:
        db.session.rollback()


def test_incluye_no_realizada_con_contraproducencia(app_ctx) -> None:
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib, tipo="REINSPECCION")
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="EN_EJECUCION",
            fecha_origen=date(2026, 8, 11),
            anio=2026,
            mes=8,
            domicilio_id=act.domicilio_id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 11),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=act.orden_trabajo_id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="NO_REALIZADO",
            motivo_no_realizado="LOCAL_CERRADO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["estado"] == "NO_REALIZADA"
        assert match["realizada"] is False
        assert match["contraproducencia"] == "LOCAL CERRADO"
    finally:
        db.session.rollback()


def test_incluye_notificacion(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=8)
        db.session.add(noti)
        db.session.flush()
        act.notificacion_id = noti.id
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["notificacion"]["numero"] == noti.numero_acta
        assert "Notif." in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_incluye_comprobacion(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=8, motivo="hist")
        db.session.add(comp)
        db.session.flush()
        act.comprobacion_id = comp.id
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["comprobacion"]["numero"] == comp.numero_acta
        assert "Comp." in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_incluye_expediente(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=8, motivo="exp hist")
        db.session.add(comp)
        db.session.flush()
        act.comprobacion_id = comp.id
        ex = Expediente(
            numero_expediente=_unique_num()[:6],
            anio="2026",
            fecha_expediente=date(2026, 8, 12),
            tipo_expediente="ENVIO_ACTA",
            comprobacion_id=comp.id,
        )
        db.session.add(ex)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["tramites"]["expediente"]["numero"] == ex.numero_expediente
        assert "Exp." in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_incluye_oficio(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=8, motivo="ofi hist")
        db.session.add(comp)
        db.session.flush()
        ofi = Oficio(numero_oficio=_unique_num()[:8], anio=2026, causa="HistPR104", comprobacion_id=comp.id)
        db.session.add(ofi)
        db.session.flush()
        act.comprobacion_id = comp.id
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["tramites"]["oficio"]["numero"] == ofi.numero_oficio
        assert "Oficio" in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_incluye_ratificacion_y_verificar_informar(app_ctx) -> None:
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        contrib = _mk_contrib(doc)
        act_rat = _mk_act_base(contrib, tipo="RATIFICACION DE CLAUSURA", fecha=date(2026, 8, 13))
        act_vi = _mk_act_base(contrib, tipo="VERIFICAR E INFORMAR", fecha=date(2026, 8, 14))
        db.session.commit()

        rows, total, _ = _historial(doc)
        assert total >= 2
        tipos = {r["tipo_actuacion"] for r in rows if r["actuacion_id"] in (act_rat.id, act_vi.id)}
        assert "RATIFICACION DE CLAUSURA" in tipos
        assert "VERIFICAR E INFORMAR" in tipos
    finally:
        db.session.rollback()


def test_no_duplica_misma_actuacion(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        db.session.commit()
        entries, _, _ = list_historial_por_documento(doc, limit=50)
        ids = [e.act.id for e in entries if e.act is not None]
        assert ids.count(act.id) == 1
    finally:
        db.session.rollback()


def test_no_toma_rubro_contaminado_desde_domicilio_compartido(app_ctx) -> None:
    """PR12: rubro operativo del relevamiento, no del domicilio compartido contaminado."""
    doc = _unique_num()
    try:
        rub_hist = Rubro(nombre=f"HistRub{_unique_num()}")
        rub_otro = Rubro(nombre=f"HistOtro{_unique_num()}")
        db.session.add_all([rub_hist, rub_otro])
        db.session.flush()

        contrib = _mk_contrib(doc)
        dom_compartido = Domicilio(
            calle=f"Comp{_unique_num()}",
            numero="1",
            contribuyente_id=contrib.id,
            rubro_id=rub_otro.id,
        )
        db.session.add(dom_compartido)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 8, 15),
            mes=8,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom_compartido.id,
        )
        db.session.add(act)
        db.session.flush()

        from app.models import Relevamiento

        rel = Relevamiento(
            fecha=date(2026, 8, 15),
            mes=8,
            anio=2026,
            domicilio_id=dom_compartido.id,
            rubro_id=rub_hist.id,
            nombre_fantasia="HistFant",
        )
        db.session.add(rel)
        db.session.flush()
        u = User.query.filter(User.is_active.is_(True)).first()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 8, 15),
            anio=2026,
            mes=8,
            domicilio_id=dom_compartido.id,
            relevamiento_id=rel.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 15),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=ot.id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="REALIZADO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["rubro_nombre"] == rub_hist.nombre
        assert match["rubro_nombre"] != rub_otro.nombre
    finally:
        db.session.rollback()


def test_titular_visible_solo_cuando_corresponde(app_ctx) -> None:
    """PR12: relevamiento sin visita realizada no expone titular en historial."""
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        rub = Rubro.query.first()
        contrib = _mk_contrib(doc)
        dom = Domicilio(calle=f"Tit{_unique_num()}", numero="2", contribuyente_id=contrib.id, rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()
        from app.models import Relevamiento

        rel = Relevamiento(
            fecha=date(2026, 8, 16),
            mes=8,
            anio=2026,
            domicilio_id=dom.id,
            rubro_id=rub.id,
        )
        db.session.add(rel)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 8, 16),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 16),
            turno="TARDE",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            estado_ruta_item="EN_PROCESO",
            actuacion_id=None,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, _, _ = _historial(doc)
        pending = [r for r in rows if r.get("ruta_item_id") == item.id]
        if pending:
            assert pending[0]["titular_visible"] is False
    finally:
        db.session.rollback()


def test_sin_resultados_devuelve_vacio(client, auth_headers, app_ctx) -> None:
    doc = f"999{_unique_num()}"
    r = client.get(
        f"/establecimientos/historial-contribuyente?documento={doc}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["meta"]["total"] == 0
    assert data["rows"] == []


def test_api_requiere_jwt(client) -> None:
    r = client.get("/establecimientos/historial-contribuyente?documento=12345678")
    assert r.status_code == 401


def test_api_requiere_documento(client, auth_headers) -> None:
    r = client.get("/establecimientos/historial-contribuyente", headers=auth_headers)
    assert r.status_code == 400


def test_incluye_clausura_y_decomiso(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib, tipo="CLAUSURA")
        cla = Clausura(numero_acta=_unique_num(), anio=2026, mes=8, actuacion_id=act.id)
        db.session.add(cla)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["clausura"]["numero"] == cla.numero_acta
        assert "Claus." in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_actuacion_manual_con_notificacion_y_expediente(app_ctx) -> None:
    """Integración create_service + expediente en historial."""
    doc = _unique_num()
    try:
        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere motivo")
        payload = {
            "fecha_actuacion": "18/08/2026",
            "orden_trabajo_numero": _unique_num(),
            "tipo_actuacion": "INSPECCION",
            "rubro_nombre": Rubro.query.first().nombre,
            "contribuyente": {"doc_nro": doc, "apellido": "Manual", "nombre": "Hist"},
            "domicilio": {"calle": f"Man{_unique_num()}", "numero": "50"},
            "inspectores": [ins.nombre],
            "acta_inspeccion_num": _unique_num(),
            "notificacion": {"acta_num": _unique_num(), "motivos": [motivo.nombre]},
        }
        act = crear_actuacion_desde_payload(payload)
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num()[:6],
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 0,
            },
        )
        db.session.commit()

        rows, total, norm = _historial(doc)
        assert normalizar_documento(doc) == norm
        assert total >= 1
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["inspeccion"] is not None
        assert match["actas"]["notificacion"] is not None
        assert match["tramites"]["expediente"] is not None
        assert "Insp." in match["actas_tramites_texto"]
        assert "Exp." in match["actas_tramites_texto"]
    finally:
        db.session.rollback()


def test_formato_actas_tramites_incluye_texto(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib)
        noti_num = _unique_num()
        noti = Notificacion(numero_acta=noti_num, anio=2026, mes=8)
        db.session.add(noti)
        db.session.flush()
        act.notificacion_id = noti.id
        from app.models import Inspeccion

        ins = Inspeccion(numero_acta=_unique_num(), anio=2026, mes=8, actuacion_id=act.id)
        db.session.add(ins)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["inspeccion"]["texto"] == f"{match['actas']['inspeccion']['numero']}/2026"
        assert match["actas"]["notificacion"]["texto"] == f"{noti_num}/2026"
        assert f"Insp. {match['actas']['inspeccion']['texto']}" in match["actas_tramites_texto"]
        assert f"Notif. {noti_num}/2026" in match["actas_tramites_texto"]
    finally:
        db.session.rollback()


def test_incluye_decomiso_explicito(app_ctx) -> None:
    doc = _unique_num()
    try:
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib, tipo="DECOMISO")
        dec_num = _unique_num()
        dec = Decomiso(numero_acta=dec_num, anio=2026, mes=8, actuacion_id=act.id, cantidad=2.5)
        db.session.add(dec)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["actas"]["decomiso"] is not None
        assert match["actas"]["decomiso"]["numero"] == dec_num
        assert match["actas"]["decomiso"]["texto"] == f"{dec_num}/2026"
        assert "Decom." in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_incluye_denuncia_pendiente(app_ctx) -> None:
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        rub = Rubro.query.first()
        contrib = _mk_contrib(doc)
        dom = Domicilio(calle=f"Den{_unique_num()}", numero="5", contribuyente_id=contrib.id, rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()
        den = Denuncia(
            fecha=date(2026, 8, 17),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            motivo="Historial PR10.4a",
            created_by_user_id=u.id,
        )
        db.session.add(den)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 8, 17),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            denuncia_id=den.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 17),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            estado_ruta_item="EN_PROCESO",
            actuacion_id=None,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, total, _ = _historial(doc)
        assert total >= 1
        pending = next(r for r in rows if r.get("ruta_item_id") == item.id)
        assert pending["tipo_actuacion"] == "DENUNCIA"
        assert pending["estado"] == "PENDIENTE"
        assert pending["origen"] == "RUTA_ITEM_PENDIENTE"
    finally:
        db.session.rollback()


def test_incluye_reinspeccion_oficio_con_oficio(app_ctx) -> None:
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        rub = Rubro.query.first()
        contrib = _mk_contrib(doc)
        dom = Domicilio(calle=f"ReOf{_unique_num()}", numero="7", contribuyente_id=contrib.id, rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
        db.session.add(ot)
        db.session.flush()
        ofi_num = _unique_num()[:8]
        ofi = Oficio(numero_oficio=ofi_num, anio=2026, causa="Hist reinsp of")
        db.session.add(ofi)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 8, 18),
            mes=8,
            anio=2026,
            tipo="REINSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
        )
        db.session.add(act)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="EN_EJECUCION",
            fecha_origen=date(2026, 8, 18),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            oficio_id=ofi.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 18),
            turno="TARDE",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=ot.id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="REALIZADO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["tipo_actuacion"] == "REINSPECCION"
        assert match["tramites"]["oficio"]["numero"] == ofi_num
        assert match["oficio_id"] == ofi.id
        assert f"Oficio {ofi_num}/2026" in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_reinspeccion_notificacion_muestra_notificacion_origen(app_ctx) -> None:
    """Reinspección por notificación: notificación origen desde iniciador si acta no la trae."""
    doc = _unique_num()
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        contrib = _mk_contrib(doc)
        act = _mk_act_base(contrib, tipo="REINSPECCION")
        noti_num = _unique_num()
        noti = Notificacion(numero_acta=noti_num, anio=2026, mes=8)
        db.session.add(noti)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="EN_EJECUCION",
            fecha_origen=date(2026, 8, 19),
            anio=2026,
            mes=8,
            domicilio_id=act.domicilio_id,
            notificacion_id=noti.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 8, 19),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=int(uuid4().hex[:4], 16) % 31000 + 2,
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=act.orden_trabajo_id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="REALIZADO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.commit()

        rows, _, _ = _historial(doc)
        match = next(r for r in rows if r["actuacion_id"] == act.id)
        assert match["tipo_actuacion"] == "REINSPECCION"
        assert match["actas"]["notificacion"] is not None
        assert match["actas"]["notificacion"]["numero"] == noti_num
        assert match["actas"]["notificacion"]["texto"] == f"{noti_num}/2026"
        assert f"Notif. {noti_num}/2026" in (match["actas_tramites_texto"] or "")
    finally:
        db.session.rollback()


def test_service_es_solo_consulta() -> None:
    """PR10.4a no debe importar ni invocar servicios de escritura operativa."""
    import inspect

    from app.domains.establecimientos.services import historial_contribuyente_service as svc

    source = inspect.getsource(svc)
    forbidden = (
        "on_domicilio_changed",
        "geocode",
        "crear_actuacion",
        "update_domicilio",
        "resolve_contribuyente",
        "publicar_ruta",
        "cerrar_completar_trabajo",
        "db.session.add",
        "db.session.commit",
    )
    for token in forbidden:
        assert token not in source, f"historial_contribuyente_service no debe usar {token}"
