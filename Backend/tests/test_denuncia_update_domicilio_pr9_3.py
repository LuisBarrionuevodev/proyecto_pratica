"""
PR9.3 — Edición de domicilio en Gestión Denuncias: copy-on-write, geocode, iniciador.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.denuncias.schemas import DenunciaGestionRowIn
from app.domains.denuncias.services.denuncias_service import (
    actualizar_denuncia_gestion,
    crear_denuncia_con_iniciador,
)
from app.domains.denuncias.services.operational_guard_service import (
    DenunciaNoOperativaError,
    get_iniciador_pendiente_denuncia,
)
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    domicilio_compartido_para_edicion_denuncia,
    resolver_policy_edicion_domicilio,
)
from app.models import Domicilio, IniciadorRuta, RutaItem, RutaTrabajo, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _ensure_active_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"pr93_{_unique_num()}",
        email=f"pr93_{_unique_num()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _row(
    denuncia_id: int,
    *,
    calle: str,
    numero: str,
    fecha: str = "2026-06-10",
    motivo: str = "Motivo test",
    estado: str = "ABIERTA",
    numero_tipo: str | None = None,
) -> DenunciaGestionRowIn:
    return DenunciaGestionRowIn.model_validate(
        {
            "id": denuncia_id,
            "fecha": fecha,
            "calle": calle,
            "numero": numero,
            "numero_tipo": numero_tipo,
            "motivo": motivo,
            "estado": estado,
        }
    )


@pytest.fixture
def mock_user(monkeypatch):
    u = _ensure_active_user()
    monkeypatch.setattr(
        "app.domains.denuncias.services.denuncias_service._get_current_user_id",
        lambda: int(u.id),
    )
    return u


def test_pr93_policy_compartido_cow_al_cambiar_geo(app_ctx, mock_user) -> None:
    try:
        dom = Domicilio(calle=_uniq("Pr93Pol"), numero="10")
        db.session.add(dom)
        db.session.flush()
        den1, _ = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="Denuncia A",
        )
        crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 11),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="Denuncia B",
        )
        assert domicilio_compartido_para_edicion_denuncia(
            int(dom.id),
            exclude_denuncia_id=den1.id,
        )
        policy = resolver_policy_edicion_domicilio(
            domicilio_id=dom.id,
            contexto="DENUNCIA",
            origen_id=den1.id,
            cambios={"calle": _uniq("MendozaPr93"), "numero": "500"},
        )
        assert policy.modo == "CREAR_NUEVO"
        assert policy.motivo == "copy_on_write_denuncia_compartido"
    finally:
        db.session.rollback()


@patch("app.domains.denuncias.services.denuncias_service.on_domicilio_changed")
def test_pr93_edit_pendiente_actualiza_iniciador_y_geocode(mock_geo, app_ctx, mock_user) -> None:
    calle = _uniq("Pr93Edit")
    nueva_calle = _uniq("MendozaPr93")
    try:
        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=None,
            calle=calle,
            numero="34",
            interseccion=None,
            motivo="Ruidos",
        )
        dom_id_antes = den.domicilio_id
        mock_geo.reset_mock()
        actualizar_denuncia_gestion(
            den.id,
            _row(den.id, calle=nueva_calle, numero="500"),
        )
        db.session.refresh(den)
        db.session.refresh(ini)
        assert den.domicilio_id is not None
        assert ini.domicilio_id == den.domicilio_id
        dom = db.session.get(Domicilio, den.domicilio_id)
        assert dom is not None
        assert dom.calle == nueva_calle
        assert dom.numero == "500"
        mock_geo.assert_called_once_with(den.domicilio_id)
        if dom_id_antes != den.domicilio_id:
            dom_viejo = db.session.get(Domicilio, dom_id_antes)
            assert dom_viejo is not None
    finally:
        db.session.rollback()


def test_pr93_edit_compartido_otra_denuncia_intacta(app_ctx, mock_user) -> None:
    calle = _uniq("Pr93Share")
    nueva_calle = _uniq("MendozaShare93")
    try:
        dom = Domicilio(calle=calle, numero="34")
        db.session.add(dom)
        db.session.flush()
        den1, ini1 = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="A",
        )
        den2, ini2 = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 11),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="B",
        )
        dom_id_antes = dom.id
        actualizar_denuncia_gestion(
            den1.id,
            _row(den1.id, calle=nueva_calle, numero="500"),
        )
        db.session.refresh(den1)
        db.session.refresh(den2)
        db.session.refresh(ini1)
        db.session.refresh(ini2)
        assert den1.domicilio_id != dom_id_antes
        assert den2.domicilio_id == dom_id_antes
        assert ini1.domicilio_id == den1.domicilio_id
        assert ini2.domicilio_id == dom_id_antes
    finally:
        db.session.rollback()


def test_pr93_iniciador_no_pendiente_bloquea_edicion(app_ctx, mock_user) -> None:
    try:
        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=None,
            calle=_uniq("Pr93NoOp"),
            numero="1",
            interseccion=None,
            motivo="Cerrada",
        )
        ini.estado_iniciador = "CUMPLIDO"
        db.session.add(ini)
        db.session.commit()
        with pytest.raises(DenunciaNoOperativaError):
            actualizar_denuncia_gestion(
                den.id,
                _row(den.id, calle="Otra", numero="2"),
            )
    finally:
        db.session.rollback()


def test_pr93_ruta_publicada_bloquea_cambio_domicilio(app_ctx, mock_user) -> None:
    try:
        dom = Domicilio(calle=_uniq("Pr93Pub"), numero="1")
        db.session.add(dom)
        db.session.flush()
        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="En ruta",
        )
        ruta = RutaTrabajo(
            fecha=date(2026, 6, 10),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=mock_user.id,
            numero=random.randint(1, 32000),
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            estado_ruta_item="EN_PROCESO",
            created_by_user_id=mock_user.id,
        )
        db.session.add(item)
        db.session.flush()

        policy = resolver_policy_edicion_domicilio(
            domicilio_id=dom.id,
            contexto="DENUNCIA",
            origen_id=den.id,
            cambios={"calle": _uniq("Bloqueada"), "numero": "99"},
            modo_explicito="NUEVO",
        )
        assert policy.modo == "BLOQUEAR"
    finally:
        db.session.rollback()


def test_pr93_edit_esquina_a_numero(app_ctx, mock_user) -> None:
    calle = _uniq("Pr93Esq")
    try:
        den, _ = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 10),
            domicilio_id=None,
            calle=calle,
            numero=None,
            interseccion="y Maipú",
            motivo="Esquina",
        )
        actualizar_denuncia_gestion(
            den.id,
            _row(den.id, calle=calle, numero="500", numero_tipo="NUMERO"),
        )
        db.session.refresh(den)
        dom = db.session.get(Domicilio, den.domicilio_id)
        assert dom is not None
        assert dom.numero == "500"
        assert (dom.numero_tipo or "").upper() == "NUMERO"
    finally:
        db.session.rollback()
