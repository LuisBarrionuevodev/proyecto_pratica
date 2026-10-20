"""HOTFIX V1.1-INSPECTOR-EDITAR-DATOS.1 — catálogos GET y PUT propio (Inspector)."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.domains.usuarios.security.role_permissions import relevador_may_access

from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture


def test_relevador_may_get_tipos_catalog_for_editar_datos() -> None:
    assert relevador_may_access("GET", "/grid/catalogs/tipos")


def test_relevador_put_actuacion_ajena_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    act_id = d["act_b"].id
    resp = client.put(f"/actuaciones/{act_id}", headers=headers, json={"nombre_local": "X"})
    assert resp.status_code == 403


def test_relevador_http_200_grid_catalog_tipos(client, app):
    from app.database import db
    from app.domains.usuarios.security.passwords import hash_password
    from app.models import Inspector, Turno, User
    from app.models.turno import TipoTurno
    import random

    with app.app_context():
        turno = Turno.query.first()
        if turno is None:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()
        suf = f"{random.randint(0, 999999):06d}"
        ins = Inspector(nombre=f"Insp {suf}", legajo=suf[:5], turno_id=turno.id)
        db.session.add(ins)
        db.session.flush()
        user = User(
            username=f"rel_{suf}",
            email=f"rel_{suf}@t.local",
            password_hash=hash_password("x"),
            role="relevador",
            is_active=True,
            inspector_id=ins.id,
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/grid/catalogs/tipos", headers=headers)
    assert resp.status_code == 200
