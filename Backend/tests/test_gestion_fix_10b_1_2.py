"""GESTIÓN-FIX.10B.1.2 — clear explícito de contribuyente + pertenencia EO."""

from __future__ import annotations

import random
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
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.establecimientos.services.list_establecimientos_operativos_service import (
    list_establecimientos_operativos,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    EstablecimientoOperativo,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    User,
)

from tests.test_gestion_fix_3 import _fila_realizado_a_contra
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspectores() -> tuple[str, str]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    return rows[0].nombre, rows[1].nombre


def _cerrar_realizado_con_acta(*, item_id: int, user_id: int, acta: str) -> None:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": acta,
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _put_local_cerrado_sin_contrib(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    calle: str,
    numero: str,
    rubro_nombre: str,
    actas_a_quitar: list[str] | None = None,
    tipo_actuacion: str | None = "INSPECCION",
) -> None:
    row_dict: dict = {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": tipo_actuacion,
        "inspector1": insp1,
        "inspector2": insp2,
        "calle": calle,
        "numero": numero,
        "rubro_nombre": rubro_nombre,
        "limpiar_contribuyente": True,
        "contraproducencia": "LOCAL CERRADO",
    }
    if actas_a_quitar:
        row_dict["actas_a_quitar"] = actas_a_quitar
    row = ActuacionGridRowIn.model_validate(row_dict)
    payload = map_actuacion_row(row)
    assert "contribuyente" in payload and payload["contribuyente"] is None
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()


def test_a1_mapper_clear_contribuyente_emite_null(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": 1,
            "orden_trabajo_numero": "000001",
            "fecha_actuacion": "10/06/2026",
            "calle": "San Martín",
            "numero": "100",
            "rubro_nombre": "Bar",
            "limpiar_contribuyente": True,
            "contraproducencia": "LOCAL CERRADO",
        }
    )
    payload = map_actuacion_row(row)
    assert payload.get("contribuyente") is None


def test_a1_clear_contribuyente_desvincula_domicilio(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    assert dom.contribuyente_id is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    calle = dom.calle or "San Martín"
    numero = dom.numero or "100"
    rubro = dom.rubro.nombre if dom.rubro else "Bar"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=calle,
        numero=numero,
        rubro_nombre=rubro,
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    dom_final = db.session.get(Domicilio, act_db.domicilio_id)
    assert dom_final is not None
    assert dom_final.contribuyente_id is None


def test_a2_edicion_no_relacionada_preserva_contribuyente(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    dom_antes = db.session.get(Domicilio, dom_id)
    assert dom_antes is not None
    contrib_id_antes = dom_antes.contribuyente_id
    c = db.session.get(Contribuyente, contrib_id_antes) if contrib_id_antes else None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    row = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "inspector1": insp2,
            "inspector2": insp1,
            "calle": dom_antes.calle,
            "numero": dom_antes.numero,
            "rubro_nombre": dom_antes.rubro.nombre if dom_antes.rubro else "Bar",
            "doc_nro": c.documento if c else None,
            "contrib_apellido": c.apellido if c else None,
            "contrib_nombre": c.nombre if c else None,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row))
    db.session.expunge_all()

    dom_db = db.session.get(Domicilio, dom_id)
    assert dom_db is not None
    assert dom_db.contribuyente_id == contrib_id_antes


def test_a3_cow_protege_domicilio_compartido(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    _item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    contrib_id_orig = dom.contribuyente_id

    act_base = db.session.get(Actuaciones, act_id)
    assert act_base is not None

    ot_hist = OrdenTrabajo(numero_acta=f"{random.randint(100000, 999999):06d}", anio=2026, mes=6)
    db.session.add(ot_hist)
    db.session.flush()
    act_hist = Actuaciones(
        fecha=act_base.fecha,
        mes=6,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot_hist.id,
        domicilio_id=dom_id,
        contraproducencia="LOCAL CERRADO",
    )
    db.session.add(act_hist)
    db.session.commit()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
    )

    dom_origen = db.session.get(Domicilio, dom_id)
    act_db = db.session.get(Actuaciones, act_id)
    assert dom_origen is not None and act_db is not None
    assert dom_origen.contribuyente_id == contrib_id_orig
    assert int(act_db.domicilio_id) != int(dom_id)
    dom_fork = db.session.get(Domicilio, act_db.domicilio_id)
    assert dom_fork is not None
    assert dom_fork.contribuyente_id is None


def test_b1_realizado_a_local_cerrado_sin_identidad_desvincula_eo(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    assert act_realizado.establecimiento_operativo_id is not None

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.establecimiento_operativo_id is None


def test_b2_local_cerrado_con_identidad_vincula_eo(app_ctx) -> None:
    """Regresión 10B.1: LOCAL CERRADO con contribuyente válido sigue vinculando EO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    act_realizado.establecimiento_operativo_id = None
    db.session.commit()
    db.session.expunge_all()

    row_dict = _fila_realizado_a_contra(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        include_domicilio=True,
    )
    row_dict["actas_a_quitar"] = ["INSPECCION"]
    actualizar_actuacion(act_id, map_actuacion_row(ActuacionGridRowIn.model_validate(row_dict)))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.establecimiento_operativo_id is not None
    eo_esperado = resolve_establecimiento_por_domicilio(
        int(act_db.domicilio_id),
        created_by_user_id=user_id,
    )
    assert act_db.establecimiento_operativo_id == eo_esperado


def test_b4_eo_con_historia_permanece_tras_desvincular_act_corregida(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    eo_id = resolve_establecimiento_por_domicilio(int(dom_id), created_by_user_id=user_id)
    assert eo_id is not None

    ot_hist = OrdenTrabajo(numero_acta=f"{random.randint(100000, 999999):06d}", anio=2026, mes=6)
    db.session.add(ot_hist)
    db.session.flush()
    act_hist = Actuaciones(
        fecha=db.session.get(Actuaciones, act_id).fecha,
        mes=6,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot_hist.id,
        domicilio_id=dom_id,
        establecimiento_operativo_id=eo_id,
        contraproducencia="LOCAL CERRADO",
    )
    db.session.add(act_hist)
    db.session.commit()

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.establecimiento_operativo_id is None
    assert db.session.get(EstablecimientoOperativo, eo_id) is not None

    dom_list = dom.calle or ""
    items, _total = list_establecimientos_operativos(page=1, page_size=500, calle=dom_list)
    assert int(eo_id) in {int(eo.id) for eo in items}


def test_b5_eo_huerfano_no_aparece_en_listado(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    eo_huerfano = act_realizado.establecimiento_operativo_id
    assert eo_huerfano is not None

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        actas_a_quitar=["INSPECCION"],
    )

    items, _total = list_establecimientos_operativos(
        page=1,
        page_size=500,
        calle=dom.calle or "",
    )
    assert int(eo_huerfano) not in {int(eo.id) for eo in items}


def test_a4_cow_clear_hereda_geocode(app_ctx) -> None:
    """COW al limpiar contribuyente conserva geocode en el fork operativo."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    _item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    geo_origen = DomicilioGeocode.query.filter_by(domicilio_id=int(dom_id)).first()
    assert geo_origen is not None
    lat_origen = float(geo_origen.lat)
    lng_origen = float(geo_origen.lng)

    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    contrib_id_orig = dom.contribuyente_id

    act_base = db.session.get(Actuaciones, act_id)
    assert act_base is not None
    ot_hist = OrdenTrabajo(numero_acta=f"{random.randint(100000, 999999):06d}", anio=2026, mes=6)
    db.session.add(ot_hist)
    db.session.flush()
    db.session.add(
        Actuaciones(
            fecha=act_base.fecha,
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot_hist.id,
            domicilio_id=dom_id,
            contraproducencia="LOCAL CERRADO",
        )
    )
    db.session.commit()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
    )

    act_db = db.session.get(Actuaciones, act_id)
    dom_origen = db.session.get(Domicilio, dom_id)
    assert act_db is not None and dom_origen is not None
    assert dom_origen.contribuyente_id == contrib_id_orig
    assert int(act_db.domicilio_id) != int(dom_id)

    geo_fork = DomicilioGeocode.query.filter_by(domicilio_id=int(act_db.domicilio_id)).first()
    assert geo_fork is not None
    assert float(geo_fork.lat) == lat_origen
    assert float(geo_fork.lng) == lng_origen


def test_b2_no_crea_eo_nuevo_sin_identidad(app_ctx) -> None:
    """Corregir sin identidad no debe crear EO fantasma adicional."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    count_antes = EstablecimientoOperativo.query.count()

    _put_local_cerrado_sin_contrib(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "Calle",
        numero=dom.numero or "10",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        actas_a_quitar=["INSPECCION"],
    )

    assert EstablecimientoOperativo.query.count() == count_antes
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.establecimiento_operativo_id is None


def test_b6_local_cerrado_a_realizado_vincula_eo_canonico(app_ctx) -> None:
    """Inverso: LOCAL CERRADO → limpiar contra + contrib + acta → mismo act_id + EO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act_lc = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act_lc is not None and dom is not None
    c = db.session.get(Contribuyente, dom.contribuyente_id) if dom.contribuyente_id else None
    assert c is not None
    ot_num = act_lc.orden_trabajo.numero_acta if act_lc.orden_trabajo else "000001"
    fecha = act_lc.fecha.strftime("%d/%m/%Y") if act_lc.fecha else "10/06/2026"
    calle = dom.calle or "Calle"
    numero = dom.numero or "10"
    rubro_nombre = dom.rubro.nombre if dom.rubro else "Bar"
    doc_nro = c.documento
    contrib_apellido = c.apellido
    contrib_nombre = c.nombre

    act_lc.establecimiento_operativo_id = None
    db.session.commit()
    db.session.expunge_all()

    acta_num = f"{random.randint(100000, 999999):06d}"

    row = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "inspector1": insp1,
            "inspector2": insp2,
            "calle": calle,
            "numero": numero,
            "rubro_nombre": rubro_nombre,
            "doc_nro": doc_nro,
            "contrib_apellido": contrib_apellido,
            "contrib_nombre": contrib_nombre,
            "acta_inspeccion_num": acta_num,
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None
    assert int(act_db.id) == int(act_id)
    assert act_db.contraproducencia is None
    assert act_db.establecimiento_operativo_id is not None
    eo_esperado = resolve_establecimiento_por_domicilio(
        int(act_db.domicilio_id),
        created_by_user_id=user_id,
    )
    assert act_db.establecimiento_operativo_id == eo_esperado
    assert item_db is not None
    assert item_db.estado_ejecucion == "REALIZADO"
    assert ini_db is not None
    assert ini_db.estado_iniciador == "CUMPLIDO"
