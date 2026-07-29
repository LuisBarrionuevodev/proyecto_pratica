"""HOTFIX: contraproducencias reencolables vuelven a planificación/mapa."""

from __future__ import annotations

import random
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    list_mapa_operativo_pendientes_geo,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
    planificable_iniciadores_base_query,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    Distrito,
    IniciadorRuta,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _fecha_ruta_aislada(anio: int = 2026) -> date:
    """Día único por corrida (evita uq fecha+turno+numero en BD compartida)."""
    n = int(uuid4().hex[:8], 16) % 364
    return date(anio, 1, 1) + timedelta(days=n)


def _uniq_ruta_numero() -> int:
    return int(uuid4().hex[:4], 16) % 31_999 + 2


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user(suf: str) -> User:
    u = User(
        username=f"u_reenc_{suf}",
        email=f"reenc_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_relevamiento_en_ruta_publicada(
    suf: str,
    *,
    fecha_origen: date | None = None,
    with_geocode: bool = True,
) -> tuple[int, int, int, int, int, int]:
    """Retorna ids: item, act, ini, user, ruta_borrador, domicilio."""
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    dist = Distrito.query.first()
    u = _mk_user(suf)
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Reenc", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=f"ReencCalle_{suf}",
        numero="10",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=dist.id if dist else None,
    )
    db.session.add(dom)
    db.session.flush()
    if with_geocode:
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
                geo_status="OK",
                lat=-31.42,
                lng=-64.18,
            )
        )
        db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    fecha_ruta = _fecha_ruta_aislada(2026)
    act = Actuaciones(
        fecha=fecha_ruta,
        mes=fecha_ruta.month,
        anio=fecha_ruta.year,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    fo = fecha_origen or date(2026, 5, 1)
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=fo,
        anio=fo.year,
        mes=fo.month,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta_pub = RutaTrabajo(
        fecha=fecha_ruta,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=_uniq_ruta_numero(),
    )
    db.session.add(ruta_pub)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta_pub.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    fecha_borrador = fecha_ruta + timedelta(days=5)
    ruta_borrador = RutaTrabajo(
        fecha=fecha_borrador,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=u.id,
        numero=_uniq_ruta_numero(),
    )
    db.session.add(ruta_borrador)
    db.session.commit()
    return item.id, act.id, ini.id, u.id, ruta_borrador.id, dom.id


@pytest.mark.parametrize("contra", ["LOCAL CERRADO", "CLIMA"])
def test_reencolado_generico_aparece_en_planificable(app_ctx, contra: str) -> None:
    suf = uuid4().hex[:8]
    item_id, _act_id, ini_id, user_id, ruta_borrador_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": contra, "tipo_actuacion": "INSPECCION"}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini_id)
    item_db = db.session.get(RutaItem, item_id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert int(ini_db.prioridad or 0) >= 5
    assert ini_db.fecha_origen >= date.today() - timedelta(days=1)
    assert item_db is not None
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"

    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif_ids

    dom = db.session.get(Domicilio, dom_id)
    if dom and dom.distrito_id:
        items, total = get_iniciadores_pendientes_para_ruta(
            ruta_id=ruta_borrador_id,
            tipo=None,
            prioridad=None,
            prioridad_categoria=None,
            distrito=dom.distrito_id,
            q=f"ReencCalle_{suf}",
            turno_sugerido=None,
            calle_catalogo_id=None,
            page=1,
            per_page=50,
        )
        assert total >= 1
        assert ini_id in {i.id for i in items}


@pytest.mark.parametrize("contra", ["NO SE RATIFICÓ", "NO PAGÓ TODAVÍA EL DECOMISO"])
def test_reencolado_oficio_aparece_en_planificable(app_ctx, contra: str) -> None:
    from tests.test_completar_trabajo_stab4 import _ensure_catalog_contraproducencia, _mk_reinspeccion_oficio_item

    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    _ensure_catalog_contraproducencia(app_ctx, contra)
    tipo = "RATIFICACION DE CLAUSURA" if "RATIFIC" in contra else "RATIFICACION DE DECOMISO"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": contra, "tipo_actuacion": tipo}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    item_db = db.session.get(RutaItem, item.id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert int(ini_db.prioridad or 0) >= 5
    assert item_db is not None and item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id in planif_ids


def test_local_cerrado_aparece_en_mapa_con_fecha_reencolado(app_ctx) -> None:
    """Tras reencolado, fecha_origen refleja reingreso para el filtro del mapa operativo."""
    suf = uuid4().hex[:8]
    old_fecha = date.today() - timedelta(days=45)
    item_id, _act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(
        suf, fecha_origen=old_fecha
    )
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini_id)
    dom = db.session.get(Domicilio, _dom_id)
    assert ini_db is not None
    assert ini_db.fecha_origen >= date.today() - timedelta(days=1)

    ref = ini_db.fecha_origen.isoformat()
    points = list_mapa_operativo_pendientes_geo(
        desde=ref,
        hasta=ref,
        distrito_id=dom.distrito_id if dom else None,
    )
    ids = {p["iniciador_id"] for p in points}
    assert ini_id in ids


def test_ruta_item_finalizado_no_realizado_no_bloquea_planificable(app_ctx) -> None:
    """Un RutaItem FINALIZADO+NO_REALIZADO en ruta PUBLICADA no oculta al iniciador PENDIENTE."""
    suf = uuid4().hex[:8]
    item_id, _act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    q = planificable_iniciadores_base_query().filter(IniciadorRuta.id == ini_id).all()
    assert len(q) == 1


def test_no_cumple_oficio_reencolado_aparece_en_planificable(app_ctx) -> None:
    """NO_CUMPLE deja item REALIZADO; iniciador PENDIENTE debe seguir planificable."""
    from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item, _ot_num

    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "NO_CUMPLE",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id in planif_ids
