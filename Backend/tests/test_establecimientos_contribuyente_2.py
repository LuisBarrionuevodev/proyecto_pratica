"""V1.1-ESTABLECIMIENTOS-CONTRIBUYENTE.2 — corrección global vs ficha."""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.establecimientos.services.vinculacion_establecimiento_resolver import (
    MSG_SIN_DESTINO,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    eo_canonico_id_para_domicilio,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import Actuaciones, Domicilio, IniciadorRuta, Motivo, Rubro, RutaItem, User
from tests.helpers.fixture_isolation import unique_ot_numero
from tests.relevamiento_test_helpers import get_or_create_test_relevador
from tests.test_pr12_domicilio_contamination import (
    _contrib_doc_aislado,
    _inspector,
    _setup_ruta_y_publicar,
    _uniq,
)

_ROOT = Path(__file__).resolve().parents[1]
_HEADER = (
    _ROOT.parent
    / "Frontend"
    / "src"
    / "Containers"
    / "Establecimientos"
    / "components"
    / "EstablecimientoFichaHeader.tsx"
)
_DETALLE = (
    _ROOT.parent
    / "Frontend"
    / "src"
    / "Containers"
    / "Establecimientos"
    / "EstablecimientoDetallePage.tsx"
)
_CORRECCION = (
    _ROOT.parent
    / "Frontend"
    / "src"
    / "Containers"
    / "Establecimientos"
    / "components"
    / "CorreccionEstablecimientoDialog.tsx"
)


def _migration_pr72_aplicada() -> bool:
    cols = {c["name"] for c in sa_inspect(db.engine).get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def test_ficha_separa_correccion_global_y_de_ficha() -> None:
    """
    Qué hace: comprueba que la ficha expone dos acciones distintas y reutiliza el canal de vinculación.
    Parámetros: ninguno (lee fuentes).
    Retorno: None.
    Errores: AssertionError si se mezclan los canales o falta el diálogo de vinculación.
    """
    header = _HEADER.read_text(encoding="utf-8")
    detalle = _DETALLE.read_text(encoding="utf-8")
    correccion = _CORRECCION.read_text(encoding="utf-8")
    assert "CORRECCION_DATOS_CONTRIBUYENTE_ACCION" in header
    assert "CORRECCION_CONTRIBUYENTE_FICHA_ACCION" in header
    assert "CORRECCION_CONTRIBUYENTE_FICHA_HINT" in header
    assert "onCorregirContribuyenteFicha" in header
    assert "VinculacionEstablecimientoDialog" in detalle
    assert "CorreccionEstablecimientoDialog" in detalle
    assert "ofreceVinculacionDesdeConflicto" in correccion
    assert "previewVinculacionEstablecimiento" in correccion


def test_sin_destino_no_propone_alta() -> None:
    """
    Qué hace: documenta que el canal de ficha no crea contribuyente si el documento no existe.
    Parámetros: ninguno.
    Retorno: None.
    Errores: AssertionError si el mensaje invita a un alta o a pisar la identidad compartida.
    """
    msg = MSG_SIN_DESTINO.lower()
    assert "no da de alta" in msg
    assert "corregir datos del contribuyente" in msg
    assert "no se puede completar desde esta ficha" in msg
    assert "resolve_contribuyente" not in msg


def test_relevamiento_t0_t1_t2_otro_titular(app_ctx, require_pr72_migration) -> None:
    """
    Qué hace: inspección nueva desde relevamiento, mismo domicilio y otro titular.
    Parámetros: fixtures de app y migración PR7.2.
    Retorno: None.
    Errores: AssertionError si la actuación anterior pierde su contribuyente o la nueva no abre ficha propia.
    """
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        user_id = int(u.id)
        rev = get_or_create_test_relevador()
        rub = Rubro(nombre=_uniq("RelTitC2"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("RelTitC2")
        doc_a = _contrib_doc_aislado()
        doc_b = _contrib_doc_aislado()
        while doc_b == doc_a:
            doc_b = _contrib_doc_aislado()

        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            motivo = Motivo(nombre=_uniq("MotC2"))
            db.session.add(motivo)
            db.session.flush()

        act_hist = crear_actuacion_desde_payload(
            {
                "fecha_actuacion": "21/07/2026",
                "orden_trabajo_numero": unique_ot_numero(),
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc_a, "apellido": "Titular", "nombre": "A"},
                "domicilio": {"calle": calle, "numero": "500", "numero_tipo": "NUMERO"},
                "inspectores": [ins.nombre],
                "acta_inspeccion_num": unique_ot_numero(),
                "notificacion": {"acta_num": unique_ot_numero(), "motivos": [motivo.nombre]},
            }
        )
        act_hist_id = int(act_hist.id)
        dom_hist_id = int(act_hist.domicilio_id)

        rel = crear_relevamiento_desde_payload(
            {
                "fecha": "2026-07-29",
                "relevadores_nombres": [rev.nombre],
                "domicilio": {"calle": calle, "numero": "500", "numero_tipo": "NUMERO"},
                "rubro_nombre": rub.nombre,
            }
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None
        assert rel.domicilio_id != dom_hist_id

        items = _setup_ruta_y_publicar([int(ini.id)])
        item = items[0]
        item_id = int(item.id)
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "tipo_actuacion": "INSPECCION",
                    "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                    "caracter_persona_atendio": "ENCARGADO",
                    "posee_contrato_retiro_residuos_solidos_urbanos": True,
                    "solicita_carnet_manipulador": False,
                    "contrib_apellido": "Titular",
                    "contrib_nombre": "B",
                    "doc_nro": doc_b,
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=user_id,
        )
        db.session.expire_all()

        item_db = db.session.get(RutaItem, item_id)
        act_hist_db = db.session.get(Actuaciones, act_hist_id)
        act_nueva = db.session.get(Actuaciones, item_db.actuacion_id) if item_db else None
        dom_hist = db.session.get(Domicilio, dom_hist_id)
        assert act_hist_db is not None and act_nueva is not None and dom_hist is not None
        assert dom_hist.contribuyente.documento == doc_a
        assert act_nueva.domicilio_id != dom_hist_id
        assert act_nueva.domicilio.contribuyente.documento == doc_b

        eo_a = eo_canonico_id_para_domicilio(dom_hist)
        eo_b = eo_canonico_id_para_domicilio(act_nueva.domicilio)
        assert eo_a is not None and eo_b is not None
        assert int(eo_a) != int(eo_b)
    finally:
        db.session.rollback()


def test_denuncia_t0_t1_t2_otro_titular_conserva_ficha_anterior(
    app_ctx, require_pr72_migration, monkeypatch
) -> None:
    """
    Qué hace: inspección nueva desde denuncia, mismo domicilio y otro titular.
    Parámetros: fixtures de app, migración PR7.2 y monkeypatch de usuario.
    Retorno: None.
    Errores: AssertionError si la actuación histórica cambia de contribuyente.
    """
    from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador

    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        user_id = int(u.id)
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service.get_current_user_id",
            lambda: user_id,
        )

        rub = Rubro(nombre=_uniq("DenTitC2"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("DenTitC2")
        doc_a = _contrib_doc_aislado()
        doc_b = _contrib_doc_aislado()
        while doc_b == doc_a:
            doc_b = _contrib_doc_aislado()

        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            motivo = Motivo(nombre=_uniq("MotC2"))
            db.session.add(motivo)
            db.session.flush()

        act_hist = crear_actuacion_desde_payload(
            {
                "fecha_actuacion": "21/07/2026",
                "orden_trabajo_numero": unique_ot_numero(),
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc_a, "apellido": "Titular", "nombre": "A"},
                "domicilio": {"calle": calle, "numero": "500", "numero_tipo": "NUMERO"},
                "inspectores": [ins.nombre],
                "acta_inspeccion_num": unique_ot_numero(),
                "notificacion": {"acta_num": unique_ot_numero(), "motivos": [motivo.nombre]},
            }
        )
        act_hist_id = int(act_hist.id)
        dom_hist_id = int(act_hist.domicilio_id)

        den, _ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 8, 2),
            domicilio_id=None,
            calle=calle,
            numero="500",
            interseccion=None,
            motivo="CONTRIBUYENTE.2 denuncia otro titular",
        )
        denuncia_id = int(sa_inspect(den).identity[0])
        ini_id = (
            db.session.query(IniciadorRuta.id)
            .filter(
                IniciadorRuta.denuncia_id == denuncia_id,
                IniciadorRuta.deleted_at.is_(None),
            )
            .scalar()
        )
        assert ini_id is not None
        items = _setup_ruta_y_publicar([int(ini_id)])
        item = items[0]
        item_id = int(item.id)
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "tipo_actuacion": "INSPECCION",
                    "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                    "caracter_persona_atendio": "ENCARGADO",
                    "posee_contrato_retiro_residuos_solidos_urbanos": True,
                    "solicita_carnet_manipulador": False,
                    "contrib_apellido": "Titular",
                    "contrib_nombre": "B",
                    "doc_nro": doc_b,
                }
            ),
            ejecutado_por_user_id=user_id,
        )
        db.session.expire_all()

        item_db = db.session.get(RutaItem, item_id)
        act_hist_db = db.session.get(Actuaciones, act_hist_id)
        act_nueva = db.session.get(Actuaciones, item_db.actuacion_id) if item_db else None
        dom_hist = db.session.get(Domicilio, dom_hist_id)
        assert act_hist_db is not None and act_nueva is not None and dom_hist is not None
        assert dom_hist.contribuyente.documento == doc_a
        assert act_nueva.domicilio_id != dom_hist_id
        assert act_nueva.domicilio.contribuyente.documento == doc_b

        eo_a = eo_canonico_id_para_domicilio(dom_hist)
        eo_b = eo_canonico_id_para_domicilio(act_nueva.domicilio)
        assert eo_a is not None and eo_b is not None
        assert int(eo_a) != int(eo_b)
    finally:
        db.session.rollback()
