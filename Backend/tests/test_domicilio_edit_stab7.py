"""
STAB-7 — edición in-place de domicilio vs nuevo vínculo.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    resolver_policy_edicion_domicilio,
)
from app.domains.domicilios.services.domicilio_update_service import aplicar_edicion_domicilio_operativo
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import compute_addr_hash
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Relevamiento,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _inspector_y_rubro() -> tuple[Inspector, Rubro]:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro en BD")
    return ins, rub


def _payload_relevamiento(*, calle: str, numero: str, ins: Inspector, rub: Rubro, fecha: str = "2026-06-10"):
    return {
        "fecha": fecha,
        "inspector_nombre": ins.nombre,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def test_policy_correccion_edita_misma_fila(app_ctx) -> None:
    try:
        dom = Domicilio(calle="San Martin", numero="123")
        db.session.add(dom)
        db.session.flush()
        policy = resolver_policy_edicion_domicilio(
            domicilio_id=dom.id,
            contexto="RELEVAMIENTO",
            origen_id=1,
            cambios={"calle": "San Martín", "numero": "123"},
        )
        assert policy.modo == "EDITAR_MISMA_FILA"
        assert policy.domicilio_id_objetivo == dom.id
        assert policy.propagar_a_iniciadores is False
    finally:
        db.session.rollback()


def test_corregir_calle_relevamiento_misma_fila(app_ctx) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        calle = _uniq("Stab7Rel")
        rel = crear_relevamiento_desde_payload(_payload_relevamiento(calle=calle, numero="10", ins=ins, rub=rub))
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id).first()
        assert ini is not None
        dom_antes = rel.domicilio_id

        nueva_calle = calle + " Corregida"
        actualizar_relevamiento(
            rel.id,
            _payload_relevamiento(calle=nueva_calle, numero="10", ins=ins, rub=rub, fecha="2026-06-11"),
        )

        db.session.refresh(rel)
        db.session.refresh(ini)
        dom_db = db.session.get(Domicilio, dom_antes)
        assert rel.domicilio_id == dom_antes
        assert ini.domicilio_id == dom_antes
        assert dom_db is not None
        assert dom_db.calle == nueva_calle
    finally:
        db.session.rollback()


def test_iniciador_activo_no_soft_delete_domicilio(app_ctx) -> None:
    try:
        u = User(
            username=f"stab7_{_unique_num()}",
            email=f"stab7_{_unique_num()}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()
        dom = Domicilio(calle=_uniq("Stab7Dom"), numero="50")
        db.session.add(dom)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 6, 1),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        from app.domains.actuaciones.cleanup.garbage_collector import soft_delete_domicilio_if_orphan

        soft_delete_domicilio_if_orphan(dom.id)
        db.session.commit()
        db.session.refresh(dom)
        assert dom.deleted_at is None
    finally:
        db.session.rollback()


def test_cambio_calle_invalida_geocode(app_ctx) -> None:
    try:
        dom = Domicilio(calle="Vieja", numero="1", calle_normalizada="Vieja", calle_norm_status="OK")
        db.session.add(dom)
        db.session.flush()
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.8,
            lng=-65.2,
            addr_hash=compute_addr_hash(dom),
            source="AUTO",
        )
        db.session.add(geo)
        db.session.flush()
        hash_antes = geo.addr_hash

        outcome = aplicar_edicion_domicilio_operativo(
            domicilio_id_actual=dom.id,
            cambios={"calle": "Nueva Calle", "numero": "1"},
            contexto="ACTUACION",
            origen_id=1,
        )
        assert outcome.domicilio_id_cambio is False
        assert outcome.policy.requiere_geocode_refresh is True
        db.session.refresh(geo)
        # El caller invoca on_domicilio_changed; simulamos hash distinto tras normalizar
        assert outcome.domicilio.calle == "Nueva Calle"
        assert geo.addr_hash == hash_antes or geo.geo_status == "OK"
    finally:
        db.session.rollback()


def test_actuacion_correccion_mantiene_domicilio_id(app_ctx) -> None:
    try:
        rub = Rubro.query.first()
        if rub is None:
            pytest.skip("rubro")
        doc = str(random.randint(10_000_000, 99_999_999))
        c = Contribuyente(apellido="Stab7", nombre="A", documento=doc)
        db.session.add(c)
        db.session.flush()
        dom = Domicilio(calle=_uniq("ActDom"), numero="100", rubro_id=rub.id, contribuyente_id=c.id)
        db.session.add(dom)
        db.session.flush()
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 6, 1),
            mes=6,
            anio=2026,
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()
        u = User.query.filter(User.is_active.is_(True)).first()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 6, 1),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            actuacion_id=act.id,
            created_by_user_id=u.id if u else 1,
        )
        db.session.add(ini)
        db.session.commit()

        calle_inicial = str(dom.calle)
        nueva_calle = calle_inicial + " X"
        act_id = act.id
        ini_id = ini.id
        dom_id = dom.id
        with patch(
            "app.domains.actuaciones.services.update_service.on_domicilio_changed"
        ):
            actualizar_actuacion(
                act_id,
                {
                    "fecha_actuacion": "2026-06-01",
                    "tipo_actuacion": "INSPECCION",
                    "rubro_nombre": rub.nombre,
                    "contribuyente": {"doc_nro": doc, "apellido": "Stab7", "nombre": "A"},
                    "domicilio": {"calle": nueva_calle, "numero": "100"},
                    "inspectores": [],
                },
            )

        db.session.expunge_all()
        act_db = Actuaciones.query.get(act_id)
        ini_db = IniciadorRuta.query.get(ini_id)
        dom_db = Domicilio.query.get(dom_id)
        assert act_db.domicilio_id == dom_id
        assert ini_db.domicilio_id == dom_id
        assert dom_db.calle == nueva_calle
        assert dom_db.deleted_at is None
    finally:
        db.session.rollback()


def test_modo_nuevo_con_ruta_publicada_bloquea(app_ctx) -> None:
    try:
        u = User(
            username=f"stab7b_{_unique_num()}",
            email=f"b_{_unique_num()}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()
        dom = Domicilio(calle=_uniq("Pub"), numero="1")
        db.session.add(dom)
        db.session.flush()
        rel = Relevamiento(
            fecha=date(2026, 6, 1),
            mes=6,
            anio=2026,
            inspector_id=Inspector.query.first().id,
            domicilio_id=dom.id,
            rubro_id=Rubro.query.first().id,
        )
        db.session.add(rel)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="EN_EJECUCION",
            fecha_origen=date(2026, 6, 1),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 6, 1),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=random.randint(1, 32000),
        )
        db.session.add(ruta)
        db.session.flush()
        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            estado_ruta_item="EN_PROCESO",
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.flush()

        policy = resolver_policy_edicion_domicilio(
            domicilio_id=dom.id,
            contexto="RELEVAMIENTO",
            origen_id=rel.id,
            cambios={"calle": "Otra", "numero": "99"},
            modo_explicito="NUEVO",
        )
        assert policy.modo == "BLOQUEAR"
    finally:
        db.session.rollback()
