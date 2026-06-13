"""STAB-10 — filtros M3 urgentes a nivel servicio (datos reales en DB de test)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.planificacion_service import get_planificacion_urgentes
from app.models import (
    Comprobacion,
    Denuncia,
    Domicilio,
    IniciadorRuta,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"u_stab10_{_unique_num()}",
        email=f"stab10_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ruta_borrador(u: User) -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=date.today(),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def _mk_ini(
    u: User,
    dom: Domicilio,
    *,
    tipo: str,
    prioridad: int = 3,
    denuncia_id=None,
    notificacion_id=None,
    oficio_id=None,
    comprobacion_id=None,
) -> IniciadorRuta:
    ini = IniciadorRuta(
        tipo_iniciador=tipo,
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=prioridad,
        created_by_user_id=u.id,
        denuncia_id=denuncia_id,
        notificacion_id=notificacion_id,
        oficio_id=oficio_id,
        comprobacion_id=comprobacion_id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def test_urgentes_filtra_denuncia(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10Den{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    den = Denuncia(
        fecha=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        motivo="test",
        created_by_user_id=u.id,
    )
    db.session.add(den)
    db.session.flush()
    _mk_ini(u, dom, tipo="DENUNCIA", denuncia_id=den.id)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, tipo_urgente="DENUNCIA"
    )
    assert total >= 1
    assert all(i.tipo_iniciador == "DENUNCIA" for i in items)


def test_urgentes_filtra_notificacion(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10Not{_unique_num()}", numero="2")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    _mk_ini(u, dom, tipo="REINSPECCION_NOTIFICACION", notificacion_id=noti.id)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, tipo_urgente="NOTIFICACION"
    )
    assert total >= 1
    assert all(i.tipo_iniciador == "REINSPECCION_NOTIFICACION" for i in items)


def test_urgentes_busca_numero_oficio(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10Ofi{_unique_num()}", numero="3")
    db.session.add(dom)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(comp)
    db.session.flush()
    nof = f"OF{_unique_num()[:6]}"
    ofi = Oficio(numero_oficio=nof, anio=2026, comprobacion_id=comp.id)
    db.session.add(ofi)
    db.session.flush()
    _mk_ini(
        u,
        dom,
        tipo="REINSPECCION_OFICIO",
        oficio_id=ofi.id,
        comprobacion_id=comp.id,
    )
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, numero_oficio=nof
    )
    assert total >= 1
    ids = {i.oficio_id for i in items}
    assert ofi.id in ids


def test_urgentes_busca_numero_comprobacion(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10Comp{_unique_num()}", numero="4")
    db.session.add(dom)
    db.session.flush()
    nacta = _unique_num()
    comp = Comprobacion(numero_acta=nacta, anio=2026, mes=3)
    db.session.add(comp)
    db.session.flush()
    _mk_ini(u, dom, tipo="REINSPECCION_OFICIO", comprobacion_id=comp.id)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, numero_comprobacion=nacta
    )
    assert total >= 1
    assert any(i.comprobacion_id == comp.id for i in items)


def test_urgentes_sin_filtros_compat(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10All{_unique_num()}", numero="5")
    db.session.add(dom)
    db.session.flush()
    den = Denuncia(
        fecha=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        motivo="x",
        created_by_user_id=u.id,
    )
    db.session.add(den)
    db.session.flush()
    _mk_ini(u, dom, tipo="DENUNCIA", denuncia_id=den.id)
    db.session.commit()

    items, total = get_planificacion_urgentes(ruta.id, page=1, per_page=25)
    assert total >= 1
    assert len(items) >= 1


def test_urgentes_sin_distrito_es_global(app_ctx) -> None:
    """Sin distrito_id el universo es global; con distrito_id acota territorialmente."""
    from app.models import Distrito

    u = _mk_user()
    ruta = RutaTrabajo(
        fecha=date.today(),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=u.id,
        numero=int(_unique_num()) % 31_000 + 2,
    )
    db.session.add(ruta)
    db.session.flush()

    distritos = Distrito.query.limit(2).all()
    assert len(distritos) >= 2
    d_a, d_b = distritos[0], distritos[1]
    if d_a.id == d_b.id:
        pytest.skip("Se necesitan al menos dos distritos distintos en la DB de test")

    dom_a = Domicilio(calle=f"UGA{_unique_num()}", numero="1", distrito_id=d_a.id)
    dom_b = Domicilio(calle=f"UGB{_unique_num()}", numero="2", distrito_id=d_b.id)
    db.session.add_all([dom_a, dom_b])
    db.session.flush()
    den_a = Denuncia(
        fecha=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom_a.id,
        motivo="a",
        created_by_user_id=u.id,
    )
    den_b = Denuncia(
        fecha=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom_b.id,
        motivo="b",
        created_by_user_id=u.id,
    )
    db.session.add_all([den_a, den_b])
    db.session.flush()
    ini_a = _mk_ini(u, dom_a, tipo="DENUNCIA", denuncia_id=den_a.id)
    ini_b = _mk_ini(u, dom_b, tipo="DENUNCIA", denuncia_id=den_b.id)
    db.session.commit()

    # Aislar con calle única: la DB de test tiene muchos urgentes y page=1 no garantiza nuestros IDs.
    items_global_a, _ = get_planificacion_urgentes(
        ruta.id, page=1, per_page=10, q_domicilio=dom_a.calle
    )
    items_global_b, _ = get_planificacion_urgentes(
        ruta.id, page=1, per_page=10, q_domicilio=dom_b.calle
    )
    items_dist_a, _ = get_planificacion_urgentes(
        ruta.id, page=1, per_page=10, distrito_id=d_a.id, q_domicilio=dom_a.calle
    )
    items_dist_b, _ = get_planificacion_urgentes(
        ruta.id, page=1, per_page=10, distrito_id=d_a.id, q_domicilio=dom_b.calle
    )
    _, total_global = get_planificacion_urgentes(ruta.id, page=1, per_page=1)
    _, total_a = get_planificacion_urgentes(ruta.id, page=1, per_page=1, distrito_id=d_a.id)

    assert any(i.id == ini_a.id for i in items_global_a)
    assert any(i.id == ini_b.id for i in items_global_b)
    assert any(i.id == ini_a.id for i in items_dist_a)
    assert not any(i.id == ini_b.id for i in items_dist_b)
    assert total_global >= total_a


def test_urgentes_q_identificador_notificacion(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10dNot{_unique_num()}", numero="6")
    db.session.add(dom)
    db.session.flush()
    nacta = _unique_num()
    noti = Notificacion(numero_acta=nacta, anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    _mk_ini(u, dom, tipo="REINSPECCION_NOTIFICACION", notificacion_id=noti.id)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, q_identificador=nacta
    )
    assert total >= 1
    assert any(i.notificacion_id == noti.id for i in items)


def test_urgentes_q_identificador_oficio(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"Stab10dOfi{_unique_num()}", numero="7")
    db.session.add(dom)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(comp)
    db.session.flush()
    nof = f"OF{_unique_num()[:6]}"
    ofi = Oficio(numero_oficio=nof, anio=2026, comprobacion_id=comp.id)
    db.session.add(ofi)
    db.session.flush()
    _mk_ini(
        u,
        dom,
        tipo="REINSPECCION_OFICIO",
        oficio_id=ofi.id,
        comprobacion_id=comp.id,
    )
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, q_identificador=nof
    )
    assert total >= 1
    assert any(i.oficio_id == ofi.id for i in items)


def test_urgentes_q_domicilio(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    calle = f"Stab10dDom{_unique_num()}"
    dom = Domicilio(calle=calle, numero="8")
    db.session.add(dom)
    db.session.flush()
    _mk_ini(u, dom, tipo="DENUNCIA", prioridad=4)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, q_domicilio=calle
    )
    assert total >= 1
    assert any(i.domicilio_id == dom.id for i in items)


def test_urgentes_rubro_id(app_ctx) -> None:
    from app.models import Rubro

    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    rub = Rubro(nombre=f"RubStab10d{_unique_num()}")
    db.session.add(rub)
    db.session.flush()
    dom_match = Domicilio(calle=f"Stab10dRubM{_unique_num()}", numero="9", rubro_id=rub.id)
    dom_other = Domicilio(calle=f"Stab10dRubO{_unique_num()}", numero="10")
    db.session.add_all([dom_match, dom_other])
    db.session.flush()
    _mk_ini(u, dom_match, tipo="DENUNCIA", prioridad=4)
    _mk_ini(u, dom_other, tipo="DENUNCIA", prioridad=4)
    db.session.commit()

    items, total = get_planificacion_urgentes(
        ruta.id, page=1, per_page=25, rubro_id=rub.id
    )
    assert total >= 1
    assert all(i.domicilio_id == dom_match.id for i in items)
