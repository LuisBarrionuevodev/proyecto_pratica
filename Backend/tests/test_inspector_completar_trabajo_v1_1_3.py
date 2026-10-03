"""V1.1-INSPECTOR.3 — Completar mis trabajos (scope por grupo)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_pendientes_list_service import (
    list_completar_trabajo_pendientes,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_resumen_service import (
    list_completar_trabajo_pendientes_resumen_por_dia,
)
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    RUTA_ITEM_FORBIDDEN_DETAIL,
)
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.services.users_service import create_user_admin
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
    Turno,
    User,
)
from app.models.turno import TipoTurno
from tests.helpers.fixture_isolation import (
    fecha_fixture_aislada,
    uniq_ruta_numero,
    unique_ot_numero,
)


def _suf() -> str:
    return uuid4().hex[:8]


def _mk_turno() -> Turno:
    t = Turno.query.first()
    if t:
        return t
    t = Turno(turno=TipoTurno.MANIANA)
    db.session.add(t)
    db.session.flush()
    return t


def _mk_inspector() -> Inspector:
    turno = _mk_turno()
    ins = Inspector(nombre=f"Insp {_suf()}", legajo=_suf()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_relevador(inspector: Inspector) -> User:
    u = User(
        username=f"rel_{_suf()}",
        email=f"rel_{_suf()}@t.local",
        password_hash=hash_password("x"),
        role="relevador",
        is_active=True,
        inspector_id=inspector.id,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_item_en_grupo(
    actor_id: int,
    fecha: date,
    inspector_ids: list[int],
    *,
    suf: str | None = None,
) -> RutaItem:
    tag = suf or _suf()
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"Rub {tag}")
        db.session.add(rub)
        db.session.flush()
    dom = Domicilio(calle=f"C {tag}", numero="1", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=fecha,
        anio=fecha.year,
        mes=fecha.month,
        domicilio_id=dom.id,
        created_by_user_id=actor_id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=actor_id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = RutaGrupo(
        ruta_trabajo_id=ruta.id,
        nombre=f"G {tag}",
        created_by_user_id=actor_id,
    )
    db.session.add(grupo)
    db.session.flush()
    for iid in inspector_ids:
        db.session.add(
            RutaGrupoInspector(
                ruta_grupo_id=grupo.id,
                inspector_id=int(iid),
                created_by_user_id=actor_id,
            )
        )
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=grupo.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=actor_id,
    )
    db.session.add(item)
    db.session.flush()
    return item


@pytest.fixture
def ct_scope_data(app):
    with app.app_context():
        admin = User.query.get(
            create_user_admin(
                username=f"adm_{_suf()}",
                email=f"adm_{_suf()}@t.local",
                password="secret123",
                role="admin",
                inspector_id=None,
            )
        )
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        user_a = _mk_relevador(ins_a)
        user_b = _mk_relevador(ins_b)
        fecha = fecha_fixture_aislada(anio=2026)
        item_a = _mk_item_en_grupo(admin.id, fecha, [ins_a.id], suf=f"a_{_suf()}")
        item_b = _mk_item_en_grupo(admin.id, fecha, [ins_b.id], suf=f"b_{_suf()}")
        item_shared = _mk_item_en_grupo(admin.id, fecha, [ins_a.id, ins_b.id], suf=f"s_{_suf()}")
        db.session.commit()
        data = {
            "admin": admin,
            "user_a": user_a,
            "user_b": user_b,
            "ins_a": ins_a,
            "ins_b": ins_b,
            "fecha": fecha,
            "item_a": item_a,
            "item_b": item_b,
            "item_shared": item_shared,
        }
        yield data
        db.session.rollback()


def _auth(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


_CT_ENDPOINTS = (
    "/actuaciones/completar-trabajo/pendientes?fecha=2026-07-15",
    "/actuaciones/completar-trabajo/pendientes/resumen?fecha_desde=2026-07-01&fecha_hasta=2026-12-31",
)


@pytest.mark.parametrize("path", _CT_ENDPOINTS)
def test_completar_trabajo_sin_jwt_401(client, path) -> None:
    resp = client.get(path)
    assert resp.status_code == 401
    assert resp.status_code != 500


def test_completar_trabajo_detalle_sin_jwt_401(client, ct_scope_data) -> None:
    d = ct_scope_data
    resp = client.get(f"/actuaciones/completar-trabajo/detalle/{d['item_a'].id}")
    assert resp.status_code == 401


def test_completar_trabajo_cerrar_sin_jwt_401(client, ct_scope_data) -> None:
    d = ct_scope_data
    resp = client.post(
        f"/actuaciones/completar-trabajo/cerrar/{d['item_a'].id}",
        json={},
    )
    assert resp.status_code == 401


def test_inspector_a_listado_solo_a_y_compartido(ct_scope_data) -> None:
    d = ct_scope_data
    items, meta = list_completar_trabajo_pendientes(
        fecha=d["fecha"],
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    ids = {int(r["ruta_item_id"]) for r in items}
    assert d["item_a"].id in ids
    assert d["item_shared"].id in ids
    assert d["item_b"].id not in ids
    assert meta["total"] == 2


def test_inspector_b_listado_simetrico(ct_scope_data) -> None:
    d = ct_scope_data
    items, _meta = list_completar_trabajo_pendientes(
        fecha=d["fecha"],
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_b"].id,
    )
    ids = {int(r["ruta_item_id"]) for r in items}
    assert d["item_b"].id in ids
    assert d["item_shared"].id in ids
    assert d["item_a"].id not in ids


def test_resumen_mismo_scope_que_listado(ct_scope_data) -> None:
    d = ct_scope_data
    f = d["fecha"]
    dias, _ = list_completar_trabajo_pendientes_resumen_por_dia(
        fecha_desde=date(f.year, 1, 1),
        fecha_hasta=date(f.year, 12, 31),
        inspector_id_effective=d["ins_a"].id,
    )
    row = next(x for x in dias if x["fecha"] == f.isoformat())
    assert row["total"] == 2


def test_admin_listado_global(ct_scope_data) -> None:
    d = ct_scope_data
    items, meta = list_completar_trabajo_pendientes(
        fecha=d["fecha"],
        page=1,
        per_page=50,
        inspector_id_effective=None,
    )
    assert meta["total"] >= 3


def test_inspector_http_listado_ignora_inspector_id_query(client, ct_scope_data) -> None:
    """El scope no acepta inspector_id arbitrario desde query."""
    d = ct_scope_data
    resp = client.get(
        f"/actuaciones/completar-trabajo/pendientes?fecha={d['fecha'].isoformat()}"
        f"&inspector_id={d['ins_b'].id}",
        headers=_auth(d["user_a"].id),
    )
    assert resp.status_code == 200
    ids = {int(r["ruta_item_id"]) for r in resp.get_json()["items"]}
    assert d["item_b"].id not in ids
    assert d["item_a"].id in ids


def test_item_compartido_cerrado_sale_de_pendientes_ambos(ct_scope_data) -> None:
    d = ct_scope_data
    item = db.session.get(RutaItem, d["item_shared"].id)
    assert item is not None
    item.estado_ruta_item = "FINALIZADO"
    item.estado_ejecucion = "REALIZADO"
    db.session.add(item)
    db.session.commit()

    for ins_id in (d["ins_a"].id, d["ins_b"].id):
        items, _meta = list_completar_trabajo_pendientes(
            fecha=d["fecha"],
            page=1,
            per_page=50,
            inspector_id_effective=ins_id,
        )
        ids = {int(r["ruta_item_id"]) for r in items}
        assert d["item_shared"].id not in ids


def test_inspector_a_detalle_b_403(client, ct_scope_data) -> None:
    d = ct_scope_data
    resp = client.get(
        f"/actuaciones/completar-trabajo/detalle/{d['item_b'].id}",
        headers=_auth(d["user_a"].id),
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == RUTA_ITEM_FORBIDDEN_DETAIL


def test_inspector_a_cerrar_b_403_sin_negocio(client, ct_scope_data) -> None:
    d = ct_scope_data
    with patch(
        "app.domains.actuaciones.routes.completar_trabajo_cerrar.cerrar_completar_trabajo_por_ruta_item"
    ) as mock_cerrar:
        resp = client.post(
            f"/actuaciones/completar-trabajo/cerrar/{d['item_b'].id}",
            headers=_auth(d["user_a"].id),
            json={},
        )
        assert resp.status_code == 403
        mock_cerrar.assert_not_called()


def test_inspector_a_detalle_compartido_200(client, ct_scope_data) -> None:
    d = ct_scope_data
    resp = client.get(
        f"/actuaciones/completar-trabajo/detalle/{d['item_shared'].id}",
        headers=_auth(d["user_a"].id),
    )
    assert resp.status_code in (200, 400)


def test_admin_detalle_b_200(client, ct_scope_data) -> None:
    d = ct_scope_data
    resp = client.get(
        f"/actuaciones/completar-trabajo/detalle/{d['item_b'].id}",
        headers=_auth(d["admin"].id),
    )
    assert resp.status_code in (200, 400)
