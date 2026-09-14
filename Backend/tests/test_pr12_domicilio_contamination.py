"""PR12 — Cargar Actuación / Relevamiento / Denuncia / Completar Trabajo sin contaminación por domicilio."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    list_historial_por_documento,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    eo_canonico_id_para_domicilio,
)
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Motivo,
    Relevamiento,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_fixture_aislada, uniq_ruta_numero, unique_ot_numero
from tests.relevamiento_test_helpers import get_or_create_test_relevador


def _contrib_doc_aislado() -> str:
    return str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000)


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _fecha_fixture_aislada() -> date:
    """Día aislado para evitar colisiones en BD compartida."""
    return fecha_fixture_aislada()


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
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return ins


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return rows[0], rows[1]


def _payload_esquina(*, calle: str, rubro: str, relevador: str, fecha: str):
    return {
        "fecha": fecha,
        "relevadores_nombres": [relevador],
        "domicilio": {"calle": calle, "numero": "y Maipu", "numero_tipo": "ESQUINA"},
        "rubro_nombre": rubro,
    }


def _setup_ruta_y_publicar(ini_ids: list[int], *, fecha_ruta: date | None = None) -> list[RutaItem]:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    f = fecha_ruta or _fecha_fixture_aislada()
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()

    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR12", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=ini_ids,
    )
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=unique_ot_numero(),
        )
    db.session.commit()
    publicar_ruta_trabajo(ruta_id=ruta.id)
    return (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta)
            .joinedload(IniciadorRuta.relevamiento)
            .joinedload(Relevamiento.rubro),
            joinedload(RutaItem.actuacion)
            .joinedload(Actuaciones.domicilio)
            .joinedload(Domicilio.rubro),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.notificacion),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )


def _cargar_actuacion_manual_esquina(
    *,
    calle: str,
    rubro: Rubro,
    contrib_doc: str,
    acta_notif: str,
    fecha_actuacion: str | None = None,
) -> Actuaciones:
    ins = _inspector()
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo en catálogo")
    payload = {
        "fecha_actuacion": fecha_actuacion or "21/07/2026",
        "orden_trabajo_numero": unique_ot_numero(),
        "tipo_actuacion": "INSPECCION",
        "rubro_nombre": rubro.nombre,
        "contribuyente": {
            "doc_nro": contrib_doc,
            "apellido": "ManualPR12",
            "nombre": "Titular",
        },
        "domicilio": {"calle": calle, "numero": "y Maipu", "numero_tipo": "ESQUINA"},
        "inspectores": [ins.nombre],
        "acta_inspeccion_num": unique_ot_numero(),
        "notificacion": {"acta_num": acta_notif, "motivos": [motivo.nombre]},
    }
    return crear_actuacion_desde_payload(payload)


def test_cargar_actuacion_no_contamina_relevamiento(app_ctx, require_pr72_migration) -> None:
    try:
        rev = get_or_create_test_relevador()
        rub_pan = Rubro(nombre=_uniq("PanaderiaPR12"))
        rub_carn = Rubro(nombre=_uniq("CarniceriaPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("SanMartinMaipuPR12")
        acta_notif = unique_ot_numero()
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=_contrib_doc_aislado(),
            acta_notif=acta_notif,
        )
        dom_manual_id = act_manual.domicilio_id
        dom_manual = db.session.get(Domicilio, dom_manual_id)
        assert dom_manual is not None
        assert dom_manual.rubro_id == rub_pan.id

        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                relevador=rev.nombre,
                fecha="2026-07-22",
            )
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None

        items = _setup_ruta_y_publicar([ini.id])
        item = items[0]
        row = ruta_item_completar_trabajo_to_row(item)

        assert row["rubro_nombre"] == rub_carn.nombre
        assert row["rubro_nombre"] != rub_pan.nombre
        assert row.get("acta_notificacion_num") in (None, "")
        assert row.get("doc_nro") in (None, "")

        db.session.refresh(dom_manual)
        assert dom_manual.rubro_id == rub_pan.id
    finally:
        db.session.rollback()


def test_cargar_actuacion_no_contamina_denuncia(app_ctx, require_pr72_migration, monkeypatch) -> None:
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub_pan = Rubro(nombre=_uniq("PanDenPR12"))
        db.session.add(rub_pan)
        db.session.flush()

        calle = _uniq("DenunciaPR12")
        acta_notif = unique_ot_numero()
        _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=_contrib_doc_aislado(),
            acta_notif=acta_notif,
        )

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 22),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 denuncia misma esquina",
        )
        assert den.domicilio_id is not None

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])

        assert row.get("rubro_nombre") in (None, "")
        assert row.get("acta_notificacion_num") in (None, "")
        assert row.get("doc_nro") in (None, "")
    finally:
        db.session.rollback()


def test_relevamiento_no_pisa_rubro_actuacion_manual(app_ctx, require_pr72_migration) -> None:
    try:
        rev = get_or_create_test_relevador()
        rub_pan = Rubro(nombre=_uniq("PanManualPR12"))
        rub_carn = Rubro(nombre=_uniq("CarnRelPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("NoPisaPR12")
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=_contrib_doc_aislado(),
            acta_notif=unique_ot_numero(),
        )
        act_manual_id = act_manual.id
        dom_manual_id = act_manual.domicilio_id
        rub_pan_id = rub_pan.id
        rub_pan_nombre = rub_pan.nombre

        crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                relevador=rev.nombre,
                fecha="2026-07-23",
            )
        )

        db.session.expunge_all()
        act_db = db.session.get(Actuaciones, act_manual_id)
        dom_db = db.session.get(Domicilio, dom_manual_id)
        assert act_db is not None and dom_db is not None
        assert dom_db.rubro_id == rub_pan_id

        ini_map = build_iniciador_ruta_por_actuacion_id([act_db.id])
        row = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_map.get(act_db.id))
        assert row["rubro_nombre"] == rub_pan_nombre
    finally:
        db.session.rollback()


def test_completar_trabajo_no_hereda_actas_por_domicilio(app_ctx, require_pr72_migration) -> None:
    try:
        rev = get_or_create_test_relevador()
        rub_pan = Rubro(nombre=_uniq("ActasPR12"))
        rub_carn = Rubro(nombre=_uniq("ActasRelPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("ActasEsquinaPR12")
        acta_notif = unique_ot_numero()
        _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=_contrib_doc_aislado(),
            acta_notif=acta_notif,
        )

        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                relevador=rev.nombre,
                fecha="2026-07-24",
            )
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])

        assert row.get("acta_notificacion_num") not in (acta_notif, f"{acta_notif}")
        assert row.get("acta_inspeccion_num") in (None, "")
        assert row.get("acta_comprobacion_num") in (None, "")
    finally:
        db.session.rollback()


def test_historial_dni_agrupa_sin_prefill_operativo(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """Mismo DNI en dos actuaciones: historial puede agrupar; Completar Trabajo no prellena titular."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        doc = _contrib_doc_aislado()
        rub = Rubro(nombre=_uniq("HistPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("HistDniPR12")
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub,
            contrib_doc=doc,
            acta_notif=unique_ot_numero(),
        )

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 25),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 historial DNI",
        )
        assert den.domicilio_id is not None

        acts_mismo_doc = (
            Actuaciones.query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
            .join(Contribuyente, Domicilio.contribuyente_id == Contribuyente.id)
            .filter(Contribuyente.documento == doc)
            .count()
        )
        assert acts_mismo_doc >= 1

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])
        assert row.get("doc_nro") in (None, "")
        assert act_manual.domicilio.contribuyente.documento == doc
    finally:
        db.session.rollback()


def test_denuncia_fork_preserva_domicilio_historico(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """Alta denuncia sin titular: fork COW; fila histórica de actuación manual intacta."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub = Rubro(nombre=_uniq("ForkDenPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("ForkDenPR12")
        doc_a = _contrib_doc_aislado()
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub,
            contrib_doc=doc_a,
            acta_notif=unique_ot_numero(),
        )
        dom_hist_id = act_manual.domicilio_id

        den, _ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 26),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 fork denuncia",
        )
        dom_den = db.session.get(Domicilio, den.domicilio_id)
        dom_hist = db.session.get(Domicilio, dom_hist_id)
        assert dom_den is not None and dom_hist is not None
        assert den.domicilio_id != dom_hist_id
        assert dom_hist.contribuyente_id is not None
        assert dom_den.contribuyente_id is None
    finally:
        db.session.rollback()


def test_relevamiento_mismo_rubro_no_hereda_titular(app_ctx, require_pr72_migration) -> None:
    """Relevamiento mismo rubro/geo que actuación manual sin titular propio: no hereda DNI."""
    try:
        rev = get_or_create_test_relevador()
        rub = Rubro(nombre=_uniq("MismoRubPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("MismoRubPR12")
        doc_a = _contrib_doc_aislado()
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub,
            contrib_doc=doc_a,
            acta_notif=unique_ot_numero(),
        )

        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub.nombre,
                relevador=rev.nombre,
                fecha="2026-07-27",
            )
        )
        dom_rel = db.session.get(Domicilio, rel.domicilio_id)
        dom_hist = db.session.get(Domicilio, act_manual.domicilio_id)
        assert dom_rel is not None and dom_hist is not None
        assert rel.domicilio_id != act_manual.domicilio_id
        assert dom_hist.contribuyente_id is not None
        assert dom_rel.contribuyente_id is None

        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None
        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])
        assert row.get("doc_nro") in (None, "")
    finally:
        db.session.rollback()


def test_denuncia_numero_no_hereda_titular(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """Calle + número (no esquina): denuncia sin titular no hereda contrib histórico."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub = Rubro(nombre=_uniq("NumDenPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("SanJuanPR12")
        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere motivo")
        doc_a = _contrib_doc_aislado()
        act_manual = crear_actuacion_desde_payload(
            {
                "fecha_actuacion": "21/07/2026",
                "orden_trabajo_numero": unique_ot_numero(),
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc_a, "apellido": "Hist", "nombre": "A"},
                "domicilio": {"calle": calle, "numero": "500", "numero_tipo": "NUMERO"},
                "inspectores": [ins.nombre],
                "acta_inspeccion_num": unique_ot_numero(),
                "notificacion": {"acta_num": unique_ot_numero(), "motivos": [motivo.nombre]},
            }
        )

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 28),
            domicilio_id=None,
            calle=calle,
            numero="500",
            interseccion=None,
            motivo="PR12 numero",
        )
        assert den.domicilio_id != act_manual.domicilio_id

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])
        assert row.get("doc_nro") in (None, "")
    finally:
        db.session.rollback()


def test_cambio_titular_denuncia_t0_t1_t2(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """T0 histórico A → T1 denuncia sin titular → T2 visita captura B; EO distintos."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub = Rubro(nombre=_uniq("CambioTitPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("CambioTitPR12")
        doc_a = _contrib_doc_aislado()
        doc_b = _contrib_doc_aislado()
        while doc_b == doc_a:
            doc_b = _contrib_doc_aislado()

        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere motivo")

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
        dom_hist_id = act_hist.domicilio_id

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 29),
            domicilio_id=None,
            calle=calle,
            numero="500",
            interseccion=None,
            motivo="PR12 cambio titular",
        )
        items = _setup_ruta_y_publicar([ini.id])
        item = items[0]
        row_pre = ruta_item_completar_trabajo_to_row(item)
        assert row_pre.get("doc_nro") in (None, "")

        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "tipo_actuacion": "INSPECCION",
                    "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                    "contrib_apellido": "Titular",
                    "contrib_nombre": "B",
                    "doc_nro": doc_b,
                }
            ),
            ejecutado_por_user_id=int(u.id),
        )
        db.session.expire_all()

        act_hist_db = db.session.get(Actuaciones, act_hist.id)
        act_nueva = db.session.get(Actuaciones, item.actuacion_id)
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


def test_denuncia_mismo_titular_explicito_valido(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """Captura explícita del mismo titular histórico A en visita denuncia: válido."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub = Rubro(nombre=_uniq("MismoTitPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("MismoTitPR12")
        doc_a = _contrib_doc_aislado()
        ins = _inspector()
        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere motivo")

        crear_actuacion_desde_payload(
            {
                "fecha_actuacion": "21/07/2026",
                "orden_trabajo_numero": unique_ot_numero(),
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc_a, "apellido": "Titular", "nombre": "A"},
                "domicilio": {"calle": calle, "numero": "600", "numero_tipo": "NUMERO"},
                "inspectores": [ins.nombre],
                "acta_inspeccion_num": unique_ot_numero(),
                "notificacion": {"acta_num": unique_ot_numero(), "motivos": [motivo.nombre]},
            }
        )

        _den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 30),
            domicilio_id=None,
            calle=calle,
            numero="600",
            interseccion=None,
            motivo="PR12 mismo titular explícito",
        )
        items = _setup_ruta_y_publicar([ini.id])
        item = items[0]

        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "tipo_actuacion": "INSPECCION",
                    "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                    "contrib_apellido": "Titular",
                    "contrib_nombre": "A",
                    "doc_nro": doc_a,
                }
            ),
            ejecutado_por_user_id=int(u.id),
        )
        db.session.expire_all()
        act_nueva = db.session.get(Actuaciones, item.actuacion_id)
        assert act_nueva is not None
        assert str(act_nueva.domicilio.contribuyente.documento) == doc_a
        row = ruta_item_completar_trabajo_to_row(
            RutaItem.query.filter_by(id=item.id)
            .options(
                joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
                joinedload(RutaItem.iniciador_ruta),
            )
            .first()
        )
        assert str(row.get("doc_nro") or "").replace(".", "") == doc_a
    finally:
        db.session.rollback()


def test_historial_no_agrupa_denuncia_pendiente_sin_titular(
    app_ctx, require_pr72_migration, monkeypatch
) -> None:
    """Denuncia publicada sin titular no aparece en historial del DNI ajeno."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub = Rubro(nombre=_uniq("HistNoAgrPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("HistNoAgrPR12")
        doc_a = _contrib_doc_aislado()
        _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub,
            contrib_doc=doc_a,
            acta_notif=unique_ot_numero(),
        )

        _den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 31),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 historial no agrupa",
        )
        items = _setup_ruta_y_publicar([ini.id])
        act_den = items[0].actuacion
        assert act_den is not None

        entries, total, _norm = list_historial_por_documento(doc_a, limit=200)
        act_ids = {e.act.id for e in entries if e.act is not None}
        assert act_den.id not in act_ids
        assert total >= 1
    finally:
        db.session.rollback()
