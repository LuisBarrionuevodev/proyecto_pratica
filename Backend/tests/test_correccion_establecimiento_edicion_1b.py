"""V1.1-ESTABLECIMIENTOS-EDICION.1B — rubro/nombre del local y formularios de corrección."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_preview_service import (
    preview_correccion_establecimiento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoError,
    CorreccionEstablecimientoPermisoError,
)
from app.models import CorreccionEstablecimientoAudit, Rubro, User
from tests.test_correccion_establecimiento_edicion_1 import (
    _act,
    _contrib,
    _dom,
    _eo,
    _geo,
    _suf,
    _user,
)


def _otro_rubro(nombre: str | None = None) -> Rubro:
    r = Rubro(nombre=nombre or f"Rub1b{_suf()}")
    db.session.add(r)
    db.session.flush()
    return r


def test_schema_local_no_se_mezcla_con_domicilio() -> None:
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {
                "local": {"rubro_nombre": "Panadería"},
                "domicilio": {"calle": "Mitre", "numero": "1"},
            }
        )


def test_preview_y_apply_local_no_toca_otro_establecimiento(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d1 = _dom(c, calle=f"LocA{_suf()}", numero="10")
    d2 = _dom(c, calle=f"LocB{_suf()}", numero="20")
    rubro_orig_2 = d2.rubro_id
    eo1 = _eo(d1, actor)
    eo2 = _eo(d2, actor)
    act1 = _act(d1)
    act1.nombre_local = "Historico A"
    act2 = _act(d2)
    act2.nombre_local = "Historico B"
    db.session.add_all([act1, act2])
    db.session.flush()
    nuevo = _otro_rubro()
    body = CorreccionEstablecimientoIn.model_validate(
        {
            "local": {"rubro_nombre": nuevo.nombre, "nombre_local": "Kiosco Norte"},
            "confirmado": True,
        }
    )
    prev = preview_correccion_establecimiento(eo1.id, body, actor=actor)
    assert prev["puede_aplicar"] is True
    assert prev["local"]["reescribe_actuaciones_nombre_local"] is False
    assert prev["local"]["otros_establecimientos_contribuyente"]["cantidad"] >= 1
    out = aplicar_correccion_establecimiento(eo1.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(d1)
    db.session.refresh(d2)
    db.session.refresh(eo1)
    db.session.refresh(eo2)
    db.session.refresh(act1)
    db.session.refresh(act2)
    assert d1.rubro_id == nuevo.id
    assert d2.rubro_id == rubro_orig_2
    assert eo1.nombre_local == "Kiosco Norte"
    assert eo2.nombre_local is None
    assert act1.nombre_local == "Historico A"
    assert act2.nombre_local == "Historico B"
    audit = CorreccionEstablecimientoAudit.query.filter_by(
        establecimiento_operativo_id=eo1.id, tipo="LOCAL"
    ).one()
    assert audit.valores_nuevos["local"]["nombre_local"] == "Kiosco Norte"


def test_sin_cambios_local_no_escribe(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    rub_nombre = d.rubro.nombre if d.rubro is not None else None
    body = CorreccionEstablecimientoIn.model_validate(
        {"local": {"rubro_nombre": rub_nombre, "nombre_local": None}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is False
    assert out["sin_cambios"] is True
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0


def test_rubro_inexistente_400(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    body = CorreccionEstablecimientoIn.model_validate(
        {"local": {"rubro_nombre": f"NoExiste{_suf()}"}, "confirmado": True}
    )
    with pytest.raises(CorreccionEstablecimientoError):
        aplicar_correccion_establecimiento(eo.id, body, actor=actor)


def test_permiso_relevador_local(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    body = CorreccionEstablecimientoIn.model_validate(
        {"local": {"nombre_local": "X"}, "confirmado": True}
    )
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        preview_correccion_establecimiento(eo.id, body, actor=rel)


def test_local_no_toca_coordenadas_ni_contribuyente(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Keep")
    d = _dom(c, calle=f"Geo{_suf()}", numero="77")
    geo = _geo(d, lat="-26.1111111", lng="-65.2222222")
    distrito = d.distrito_id
    eo = _eo(d, actor)
    nuevo = _otro_rubro()
    aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"local": {"rubro_nombre": nuevo.nombre, "nombre_local": "Local Geo"}, "confirmado": True}
        ),
        actor=actor,
    )
    db.session.refresh(d)
    db.session.refresh(c)
    db.session.refresh(geo)
    assert c.apellido == "Keep"
    assert d.distrito_id == distrito
    assert str(geo.lat).startswith("-26.111")
    assert str(geo.lng).startswith("-65.222")
    assert d.contribuyente_id == c.id


def test_contribuyente_sin_cambios_conserva_persona_y_razon(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Pérez", nombre="Ana")
    c.razon_social = "Panadería SRL"
    db.session.add(c)
    db.session.flush()
    d = _dom(c)
    eo = _eo(d, actor)
    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": {
                "documento": c.documento,
                "apellido": "Pérez",
                "nombre": "Ana",
                "razon_social": "Panadería SRL",
            },
            "confirmado": True,
        }
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is False
    db.session.refresh(c)
    assert c.apellido == "Pérez"
    assert c.nombre == "Ana"
    assert c.razon_social == "Panadería SRL"
    assert c.documento
