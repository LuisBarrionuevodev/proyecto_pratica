"""V1.1-ESTABLECIMIENTOS-EDICION.1A — domicilio vigente en GET /gestion (Ver actuación)."""

from __future__ import annotations

from types import SimpleNamespace

from app.database import db
from app.domains.actuaciones.presenters.actuacion_gestion_seguimiento_presenter import (
    build_actuacion_gestion_contexto_detalle,
)
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.models import User
from tests.test_correccion_establecimiento_edicion_1 import (
    _act,
    _contrib,
    _dom as _dom_orm,
    _eo,
    _suf,
)


def _dom_ns(**kwargs) -> SimpleNamespace:
    base = dict(
        calle=None,
        numero=None,
        calle_raw=None,
        calle_normalizada=None,
        calle_norm_status=None,
        calle_key=None,
        numero_tipo="NUMERO",
        esquina_raw=None,
        esquina_normalizada=None,
        rubro=None,
        contribuyente=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_contexto_gestion_usa_calle_vigente_no_raw_historico() -> None:
    """Tras corregir desde Establecimientos, Ver no debe leer calle_raw."""
    act = SimpleNamespace(
        domicilio=_dom_ns(
            calle="Ejército del Norte",
            numero="602",
            calle_raw="Corrientes",
            calle_normalizada="Ejército del Norte",
            calle_norm_status="OK",
        )
    )
    ctx = build_actuacion_gestion_contexto_detalle(act)
    assert ctx["domicilio"]["calle"] == "Ejército del Norte"
    assert ctx["domicilio"]["numero"] == "602"


def test_contexto_gestion_sin_match_usa_calle_corregida() -> None:
    act = SimpleNamespace(
        domicilio=_dom_ns(
            calle="Ejército del Norte",
            numero="602",
            calle_raw="Corrientes",
            calle_norm_status="NO_MATCH",
        )
    )
    ctx = build_actuacion_gestion_contexto_detalle(act)
    assert ctx["domicilio"]["calle"] == "Ejército del Norte"


def test_contexto_gestion_esquina_vigente() -> None:
    act = SimpleNamespace(
        domicilio=_dom_ns(
            calle="San Martín",
            numero="Mitre",
            numero_tipo="ESQUINA",
            calle_raw="vieja",
            calle_normalizada="San Martín",
            calle_norm_status="OK",
            esquina_raw="otra",
            esquina_normalizada="Mitre",
        )
    )
    ctx = build_actuacion_gestion_contexto_detalle(act)
    assert ctx["domicilio"]["calle"] == "San Martín"
    assert ctx["domicilio"]["esquina"] == "Mitre"


def test_contexto_gestion_historico_incompleto_no_inventa() -> None:
    act = SimpleNamespace(domicilio=_dom_ns())
    ctx = build_actuacion_gestion_contexto_detalle(act)
    assert ctx["domicilio"]["calle"] is None
    assert ctx["domicilio"]["numero"] is None
    assert ctx["domicilio"]["esquina"] is None


def test_correccion_establecimiento_no_reescribe_raw_y_gestion_lee_vigente(
    app_ctx, service_actor
) -> None:
    """
    Tras corregir desde la ficha: se conserva calle_raw histórico y el detalle
    de Gestión expone la calle vigente para Ver actuación, sin re-guardar la actuación.
    """
    actor = db.session.get(User, service_actor)
    assert actor is not None
    contrib = _contrib()
    dom = _dom_orm(contrib, calle="Corrientes", numero="602")
    dom.calle_raw = "Corrientes"
    db.session.add(dom)
    db.session.flush()
    eo = _eo(dom, actor)
    act = _act(dom)
    nueva = f"Ejercito{_suf()}"
    body = CorreccionEstablecimientoIn.model_validate(
        {"domicilio": {"calle": nueva, "numero": "602"}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(dom)
    db.session.refresh(act)
    assert dom.calle_raw == "Corrientes"
    assert dom.calle == nueva
    assert act.domicilio_id == dom.id
    ctx = build_actuacion_gestion_contexto_detalle(act)
    assert ctx["domicilio"]["calle"] == nueva
    assert ctx["domicilio"]["numero"] == "602"
    assert ctx["contribuyente"]["apellido"] == contrib.apellido
