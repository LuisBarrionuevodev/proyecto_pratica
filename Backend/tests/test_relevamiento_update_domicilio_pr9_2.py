"""
PR9.2 — Edición de domicilio en Gestión Relevamientos: copy-on-write, geocode, iniciador.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    domicilio_compartido_para_edicion_relevamiento,
    resolver_policy_edicion_domicilio,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import Domicilio, IniciadorRuta, Inspector, Relevamiento, Rubro


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


def _inspector_y_rubro():
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro en BD")
    return ins, rub


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _payload(
    *,
    calle: str,
    numero: str,
    rubro: str,
    inspector: str,
    fecha: str = "2026-03-10",
    tipo: str | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
):
    dom = {"calle": calle, "numero": numero}
    if tipo:
        dom["numero_tipo"] = tipo
    out = {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }
    if nombre_fantasia is not None:
        out["nombre_fantasia"] = nombre_fantasia
    if angulo_esquina is not None:
        out["angulo_esquina"] = angulo_esquina
    return out


def _mk_relevamiento_compartido_mismo_domicilio(
    *,
    base_payload: dict,
    rubro_nombre: str,
    nombre_fantasia: str,
    domicilio_id: int,
    ins,
) -> Relevamiento:
    """Segundo relevamiento en el mismo mes compartiendo domicilio_id (setup PR9.2)."""
    from app.utils.fechas import parse_fecha_grid

    mes, anio, fecha = parse_fecha_grid(base_payload["fecha"])
    rub = Rubro.query.filter_by(nombre=rubro_nombre).first()
    rel = Relevamiento(
        fecha=fecha,
        mes=mes,
        anio=anio,
        inspector_id=ins.id,
        domicilio_id=domicilio_id,
        rubro_id=rub.id if rub else None,
        nombre_fantasia=nombre_fantasia,
    )
    db.session.add(rel)
    db.session.flush()
    ini = get_or_create_iniciador_from_relevamiento(rel)
    db.session.add(ini)
    db.session.commit()
    return rel


def test_pr92_policy_compartido_cow_al_cambiar_geo(app_ctx) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        calle = _uniq("Pr92Pol")
        p = _payload(calle=calle, numero="10", rubro=rub.nombre, inspector=ins.nombre, nombre_fantasia="A")
        r1 = crear_relevamiento_desde_payload(p)
        _mk_relevamiento_compartido_mismo_domicilio(
            base_payload=p,
            rubro_nombre=rub.nombre,
            nombre_fantasia="B",
            domicilio_id=int(r1.domicilio_id),
            ins=ins,
        )
        assert domicilio_compartido_para_edicion_relevamiento(
            int(r1.domicilio_id),
            exclude_relevamiento_id=r1.id,
        )
        policy = resolver_policy_edicion_domicilio(
            domicilio_id=r1.domicilio_id,
            contexto="RELEVAMIENTO",
            origen_id=r1.id,
            cambios={"calle": _uniq("MendozaPr92"), "numero": "500"},
        )
        assert policy.modo == "CREAR_NUEVO"
        assert policy.motivo == "copy_on_write_relevamiento_compartido"
    finally:
        db.session.rollback()


@patch("app.domains.relevamientos.services.update_service.on_domicilio_changed")
def test_pr92_edit_solo_owner_recalcula_geocode(mock_geo, app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr92Geo")
    nueva_calle = _uniq("MendozaPr92Geo")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(calle=calle, numero="34", rubro=rub.nombre, inspector=ins.nombre, nombre_fantasia="Pan")
        )
        mock_geo.reset_mock()
        actualizar_relevamiento(
            rel.id,
            _payload(
                calle=nueva_calle,
                numero="500",
                rubro=rub.nombre,
                inspector=ins.nombre,
                nombre_fantasia="Pan",
            ),
        )
        db.session.refresh(rel)
        dom = db.session.get(Domicilio, rel.domicilio_id)
        assert dom is not None
        assert dom.calle == nueva_calle
        assert dom.numero == "500"
        mock_geo.assert_called_once_with(rel.domicilio_id)
    finally:
        db.session.rollback()


def test_pr92_edit_compartido_r2_intacto_iniciador_r1_actualizado(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if rub2 is None:
        pytest.skip("Se requiere segundo rubro")
    calle = _uniq("Pr92Share")
    nueva_calle = _uniq("MendozaPr92Share")
    try:
        p_base = _payload(
            calle=calle,
            numero="34",
            rubro=rub.nombre,
            inspector=ins.nombre,
            nombre_fantasia="Panadería",
        )
        r1 = crear_relevamiento_desde_payload(p_base)
        r2 = _mk_relevamiento_compartido_mismo_domicilio(
            base_payload=p_base,
            rubro_nombre=rub2.nombre,
            nombre_fantasia="Carnicería",
            domicilio_id=int(r1.domicilio_id),
            ins=ins,
        )
        assert r1.domicilio_id == r2.domicilio_id
        dom_id_antes = r1.domicilio_id
        ini1 = IniciadorRuta.query.filter_by(relevamiento_id=r1.id).first()
        ini2 = IniciadorRuta.query.filter_by(relevamiento_id=r2.id).first()
        assert ini1 is not None and ini2 is not None

        actualizar_relevamiento(
            r1.id,
            _payload(
                calle=nueva_calle,
                numero="500",
                rubro=rub.nombre,
                inspector=ins.nombre,
                nombre_fantasia="Panadería",
            ),
        )
        db.session.refresh(r1)
        db.session.refresh(r2)
        db.session.refresh(ini1)
        db.session.refresh(ini2)

        assert r1.domicilio_id != dom_id_antes
        assert r2.domicilio_id == dom_id_antes
        assert ini1.domicilio_id == r1.domicilio_id
        assert ini2.domicilio_id == dom_id_antes
        dom_viejo = db.session.get(Domicilio, dom_id_antes)
        dom_nuevo = db.session.get(Domicilio, r1.domicilio_id)
        assert dom_viejo is not None and dom_viejo.calle == calle
        assert dom_nuevo is not None and dom_nuevo.calle == nueva_calle
    finally:
        db.session.rollback()


def test_pr92_edit_esquina_a_numero_domicilio_correcto(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr92EsqNum")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Maipú",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                angulo_esquina="NE",
            )
        )
        actualizar_relevamiento(
            rel.id,
            _payload(
                calle=calle,
                numero="500",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="NUMERO",
            ),
        )
        db.session.refresh(rel)
        dom = db.session.get(Domicilio, rel.domicilio_id)
        assert dom is not None
        assert dom.calle == calle
        assert dom.numero == "500"
        assert (dom.numero_tipo or "").upper() == "NUMERO"
    finally:
        db.session.rollback()


def test_pr92_edit_mismo_establecimiento_otro_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr92Mes")
    try:
        p = _payload(
            calle=calle,
            numero="77",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-03-10",
            nombre_fantasia="Local",
        )
        r_mar = crear_relevamiento_desde_payload(p)
        r_may = crear_relevamiento_desde_payload({**p, "fecha": "2026-05-10"})
        assert r_mar.domicilio_id != r_may.domicilio_id or r_mar.id != r_may.id
        actualizar_relevamiento(
            r_may.id,
            _payload(
                calle=calle,
                numero="77",
                rubro=rub.nombre,
                inspector=ins.nombre,
                fecha="2026-05-15",
                nombre_fantasia="Local",
            ),
        )
        db.session.refresh(r_may)
        assert r_may.mes == 5
    finally:
        db.session.rollback()
