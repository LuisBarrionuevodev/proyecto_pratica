"""GESTIÓN-FIX.7 — inspectores en reintentos, bloqueo identidad Oficio, identidad lógica EO."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
    total_actuaciones_identidad_logica_establecimiento,
)
from app.domains.establecimientos.services.list_establecimientos_operativos_service import (
    list_establecimientos_operativos,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    business_key_tuple,
    domicilio_coincide_identidad_logica,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    Contribuyente,
    Domicilio,
    EstablecimientoOperativo,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    User,
)

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import RutaTrabajo


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


def _inspector_nombres(n: int = 4) -> list[str]:
    rows = Inspector.query.limit(n).all()
    if len(rows) < n:
        pytest.skip(f"Se requieren al menos {n} inspectores en catálogo")
    return [r.nombre for r in rows[:n]]


def _inspector_ids(n: int = 4) -> list[int]:
    rows = Inspector.query.limit(n).all()
    if len(rows) < n:
        pytest.skip(f"Se requieren al menos {n} inspectores en catálogo")
    return [int(r.id) for r in rows[:n]]


def _nombres_inspectores_actuacion(act_id: int) -> list[str]:
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    return [i.nombre for i in (act.inspector or [])]


def _republicar_con_inspectores(
    ini: IniciadorRuta,
    user_id: int,
    fecha: date,
    inspector_ids: list[int],
) -> RutaItem:
    """Republica iniciador con inspectores de grupo distintos (antes de publicar)."""
    ruta = RutaTrabajo(
        fecha=fecha,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=user_id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre=f"G_{uuid4().hex[:6]}", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=inspector_ids,
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=f"{random.randint(0, 999999):06d}",
    )
    db.session.commit()
    ruta_id = int(ruta.id)
    publicar_ruta_trabajo(ruta_id=ruta_id)
    db.session.expunge_all()
    refreshed = RutaItem.query.filter(RutaItem.ruta_trabajo_id == ruta_id).first()
    assert refreshed is not None
    return refreshed


def test_reintento_inspectores_explicitos_sin_tocar_selector(app_ctx) -> None:
    """I1/I2: act1 conserva A/B; act2 recibe C/D aunque el usuario no edite el selector."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act1_id, ini_id, user_id, _, _ = _mk_relevamiento_en_ruta_publicada(suf)
    insp = _inspector_nombres(4)
    insp_ab = insp[:2]
    insp_cd = insp[2:4]

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "LOCAL CERRADO",
                "tipo_actuacion": "INSPECCION",
                "inspectores": insp_ab,
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    assert _nombres_inspectores_actuacion(act1_id) == insp_ab

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    ids_cd = _inspector_ids(4)[2:4]
    item2 = _republicar_con_inspectores(ini_db, user_id, date(2099, 4, 1), ids_cd)
    act2_id = int(item2.actuacion_id)
    assert act2_id != act1_id

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=int(item2.id),
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "",
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": f"{random.randint(10000, 99999)}",
                "inspectores": insp_cd,
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    assert _nombres_inspectores_actuacion(act1_id) == insp_ab
    assert _nombres_inspectores_actuacion(act2_id) == insp_cd


def test_oficio_put_identidad_maliciosa_rechazada(app_ctx) -> None:
    """O3: PUT con calle/rubro/nombre_local no modifica identidad."""
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, int(act.id))
    assert act_db is not None
    dom_before = db.session.get(Domicilio, int(act_db.domicilio_id))
    assert dom_before is not None
    calle_orig = dom_before.calle
    rubro_id_orig = dom_before.rubro_id
    nombre_local_orig = act_db.nombre_local

    with pytest.raises(ValueError, match="reinspección por oficio"):
        actualizar_actuacion(
            int(act.id),
            {
                "rubro_nombre": "OTRO",
                "calle": "OTRA",
                "nombre_local": "OTRO LOCAL",
                "contribuyente": {"documento": "99999999", "apellido": "X", "nombre": "Y"},
            },
        )

    db.session.expunge_all()
    act_after = db.session.get(Actuaciones, int(act.id))
    dom_after = db.session.get(Domicilio, int(act_after.domicilio_id))
    assert dom_after.calle == calle_orig
    assert dom_after.rubro_id == rubro_id_orig
    assert act_after.nombre_local == nombre_local_orig


def test_oficio_completar_trabajo_no_aplica_identidad_en_payload(app_ctx) -> None:
    """O4: cierre Oficio con identidad en payload no muta domicilio/contrib/nombre_local."""
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_db = db.session.get(Actuaciones, int(act.id))
    dom = db.session.get(Domicilio, int(act_db.domicilio_id))
    calle_orig = dom.calle
    nombre_orig = act_db.nombre_local

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                "calle": "CALLE MALICIOSA",
                "rubro_nombre": "OTRO RUBRO",
                "nombre_local": "LOCAL MALICIOSO",
                "doc_nro": "88888888",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_after = db.session.get(Actuaciones, int(act.id))
    dom_after = db.session.get(Domicilio, int(act_after.domicilio_id))
    assert dom_after.calle == calle_orig
    assert act_after.nombre_local == nombre_orig


def _mk_user() -> User:
    n = random.randint(0, 999999)
    u = User(
        username=f"u_fix7_{n}",
        email=f"fix7_{n}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_contrib(doc: str) -> Contribuyente:
    c = Contribuyente(apellido="Fix7", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    return c


def _mk_dom(contrib_id: int, rubro_id: int, *, calle: str, numero: str) -> Domicilio:
    d = Domicilio(calle=calle, numero=numero, contribuyente_id=contrib_id, rubro_id=rubro_id)
    db.session.add(d)
    db.session.flush()
    return d


def test_resolve_mismo_eo_para_cow_forks(app_ctx) -> None:
    """E1: dos domicilios misma identidad lógica → mismo EO canónico."""
    u = _mk_user()
    rub_a = Rubro(nombre=f"RubA_{uuid4().hex[:6]}")
    rub_b = Rubro(nombre=f"RubB_{uuid4().hex[:6]}")
    db.session.add_all([rub_a, rub_b])
    db.session.flush()
    doc = str(random.randint(20_000_000, 89_000_000))
    c = _mk_contrib(doc)
    dom1 = _mk_dom(c.id, rub_a.id, calle="Chacabuco", numero="230")
    dom2 = _mk_dom(c.id, rub_b.id, calle="Chacabuco", numero="230")

    eo1 = resolve_establecimiento_por_domicilio(dom1.id, created_by_user_id=u.id)
    eo2 = resolve_establecimiento_por_domicilio(dom2.id, created_by_user_id=u.id)
    db.session.commit()

    assert eo1 is not None and eo2 is not None
    assert eo1 == eo2
    assert domicilio_coincide_identidad_logica(dom1, dom2)


def test_misma_persona_distinto_domicilio_dos_fichas(app_ctx) -> None:
    """E3/E4: distinta dirección o distinto DNI → fichas distintas."""
    u = _mk_user()
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    c = _mk_contrib(str(random.randint(20_000_000, 89_000_000)))
    dom_a = _mk_dom(c.id, rub.id, calle="Chacabuco", numero="230")
    dom_b = _mk_dom(c.id, rub.id, calle="Chacabuco", numero="500")
    eo_a = resolve_establecimiento_por_domicilio(dom_a.id, created_by_user_id=u.id)
    eo_b = resolve_establecimiento_por_domicilio(dom_b.id, created_by_user_id=u.id)
    assert eo_a != eo_b

    c2 = _mk_contrib(str(random.randint(90_000_000, 99_000_000)))
    dom_c = _mk_dom(c2.id, rub.id, calle="Chacabuco", numero="230")
    eo_c = resolve_establecimiento_por_domicilio(dom_c.id, created_by_user_id=u.id)
    assert eo_c != eo_a


def test_listado_deduplica_eo_historicos(app_ctx) -> None:
    """E43: tres EO misma business key → una fila en listado."""
    u = _mk_user()
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    doc = str(random.randint(20_000_000, 89_000_000))
    c = _mk_contrib(doc)
    calle = f"ListDedup_{uuid4().hex[:6]}"
    doms = [_mk_dom(c.id, rub.id, calle=calle, numero="100") for _ in range(3)]
    eo_ids = []
    for d in doms:
        eid = resolve_establecimiento_por_domicilio(d.id, created_by_user_id=u.id)
        if eid is not None:
            eo_ids.append(eid)
    ot = OrdenTrabajo(numero_acta=f"{random.randint(0, 999999):06d}", anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 8, 1),
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=doms[0].id,
        establecimiento_operativo_id=min(eo_ids) if eo_ids else None,
    )
    db.session.add(act)
    db.session.commit()

    items, total = list_establecimientos_operativos(page=1, page_size=500, calle=calle)
    canon_ids = {int(eo.id) for eo in items}
    assert len([eo for eo in items if eo.domicilio and calle in (eo.domicilio.calle or "")]) == 1
    assert min(eo_ids) in canon_ids


def test_historial_unifica_forks_y_contador(app_ctx) -> None:
    """E42: actuaciones en forks COW aparecen en historial y contador."""
    u = _mk_user()
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    doc = str(random.randint(20_000_000, 89_000_000))
    c = _mk_contrib(doc)
    calle = f"HistFork_{uuid4().hex[:6]}"
    doms = [_mk_dom(c.id, rub.id, calle=calle, numero="77") for _ in range(3)]
    act_ids = []
    for i, dom in enumerate(doms):
        eo_id = resolve_establecimiento_por_domicilio(dom.id, created_by_user_id=u.id)
        ot = OrdenTrabajo(numero_acta=f"{random.randint(0, 999999):06d}", anio=2026, mes=8)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 8, i + 1),
            mes=8,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            establecimiento_operativo_id=eo_id,
            contraproducencia="LOCAL CERRADO" if i < 2 else None,
        )
        db.session.add(act)
        db.session.flush()
        act_ids.append(int(act.id))
    db.session.commit()

    canon_eo = min(
        r[0]
        for r in EstablecimientoOperativo.query.filter(
            EstablecimientoOperativo.domicilio_id.in_([d.id for d in doms])
        )
        .with_entities(EstablecimientoOperativo.id)
        .all()
    )

    items, total = list_actuaciones_por_establecimiento_operativo(canon_eo, page=1, page_size=50)
    assert total == 3
    assert {int(a.id) for a in items} == set(act_ids)
    assert total_actuaciones_identidad_logica_establecimiento(canon_eo) == 3


def test_business_key_excluye_rubro(app_ctx) -> None:
    """E2: mismo doc+calle+número con distinto rubro → misma business key."""
    rub_a = Rubro(nombre=f"Bebidas_{uuid4().hex[:4]}")
    rub_b = Rubro(nombre=f"Bar_{uuid4().hex[:4]}")
    db.session.add_all([rub_a, rub_b])
    db.session.flush()
    c = _mk_contrib(str(random.randint(20_000_000, 89_000_000)))
    dom_a = _mk_dom(c.id, rub_a.id, calle="Chacabuco", numero="230")
    dom_b = _mk_dom(c.id, rub_b.id, calle="Chacabuco", numero="230")
    assert business_key_tuple(dom_a) == business_key_tuple(dom_b)
