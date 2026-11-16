"""V1.1-CONTRIBUYENTE-UNICIDAD.1 — documentos normalizados entre canales."""

from __future__ import annotations

import threading
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.database import db
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.attach.documento_identidad_errors import (
    MSG_DOCUMENTO_AMBIGUO,
    MSG_DOCUMENTO_LARGO,
    DocumentoIdentidadError,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_preview_service import (
    preview_correccion_establecimiento,
)
from app.domains.establecimientos.services.contribuyente_documento_unico_service import (
    lock_key_documento,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
    list_historial_por_documento,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_preview_service import (
    preview_vinculacion_establecimiento,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    eo_canonico_id_para_domicilio,
)
from app.models import (
    CatalogTipoActuacion,
    Contribuyente,
    ContribuyenteDocumentoUnico,
    Inspector,
    Rubro,
    RutaItem,
    User,
)
from tests.test_correccion_establecimiento_edicion_1 import _contrib, _dom, _eo
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


def _doc() -> str:
    return str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000)


def _seed_tipo_inspeccion() -> None:
    if CatalogTipoActuacion.query.filter_by(nombre="INSPECCION").first() is None:
        db.session.add(CatalogTipoActuacion(nombre="INSPECCION"))
        db.session.commit()


def _inspector_nombre() -> str:
    row = Inspector.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un inspector en la BD de test")
    return str(row.nombre)


def _rubro_nombre() -> str:
    row = Rubro.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    return str(row.nombre)


def _acta_num() -> str:
    """Número de OT/acta de 6 dígitos, válido para ActuacionGridRowIn."""
    return f"{int(uuid4().hex[:8], 16) % 900000 + 100000:06d}"


def _cargar_payload(*, doc: str, calle: str, numero: str = "100", **extra) -> dict:
    payload = {
        "orden_trabajo_numero": _acta_num(),
        "fecha_actuacion": "2026-09-09",
        "tipo_actuacion": "INSPECCION",
        "contraproducencia": "NO_HUBO",
        "inspectores": [_inspector_nombre()],
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": _rubro_nombre(),
        "contribuyente": {
            "doc_nro": doc,
            "apellido": extra.pop("apellido", "Perez"),
            "nombre": extra.pop("nombre", "Ana"),
        },
        "acta_inspeccion_num": _acta_num(),
    }
    payload.update(extra)
    return payload


def _activos_norm(doc: str) -> list[Contribuyente]:
    ids = contribuyente_ids_por_documento(doc)
    return list(Contribuyente.query.filter(Contribuyente.id.in_(ids or [-1])).all())


def _assert_lock_libre(doc: str) -> None:
    key = lock_key_documento(normalizar_documento(doc))
    used = db.session.execute(text("SELECT IS_USED_LOCK(:k)"), {"k": key}).scalar()
    assert used is None


def _assert_unico_coherente(doc: str, contrib_id: int) -> None:
    row = ContribuyenteDocumentoUnico.query.filter_by(
        documento_normalizado=normalizar_documento(doc)
    ).one()
    assert int(row.contribuyente_id) == int(contrib_id)


@pytest.fixture(autouse=True)
def _prep(app):
    with app.app_context():
        _seed_tipo_inspeccion()
    yield


def test_1_mismo_domicilio_reutiliza_contribuyente_y_ficha(app_ctx, actor_user_id) -> None:
    doc = _doc()
    calle = f"Unic1{uuid4().hex[:6]}"
    act1 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=calle, numero="50"),
        actor_user_id=actor_user_id,
    )
    act2 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=calle, numero="50"),
        actor_user_id=actor_user_id,
    )
    c1 = act1.domicilio.contribuyente
    c2 = act2.domicilio.contribuyente
    assert c1.id == c2.id
    eo1 = eo_canonico_id_para_domicilio(act1.domicilio)
    eo2 = eo_canonico_id_para_domicilio(act2.domicilio)
    assert eo1 is not None and eo1 == eo2
    _assert_unico_coherente(doc, c1.id)
    _assert_lock_libre(doc)


def test_2_otro_domicilio_mismo_titular_otra_ficha(app_ctx, actor_user_id) -> None:
    doc = _doc()
    act1 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=f"Unic2a{uuid4().hex[:6]}", numero="10"),
        actor_user_id=actor_user_id,
    )
    act2 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=f"Unic2b{uuid4().hex[:6]}", numero="20"),
        actor_user_id=actor_user_id,
    )
    assert act1.domicilio.contribuyente_id == act2.domicilio.contribuyente_id
    eo1 = eo_canonico_id_para_domicilio(act1.domicilio)
    eo2 = eo_canonico_id_para_domicilio(act2.domicilio)
    assert eo1 != eo2
    _assert_lock_libre(doc)


def test_3_historial_por_cuit_junta_ambos_locales(app_ctx, actor_user_id) -> None:
    doc = _doc()
    act1 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=f"HistA{uuid4().hex[:6]}"),
        actor_user_id=actor_user_id,
    )
    act2 = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=f"HistB{uuid4().hex[:6]}"),
        actor_user_id=actor_user_id,
    )
    entries, total, _norm = list_historial_por_documento(doc, limit=200)
    act_ids = {int(e.act.id) for e in entries if getattr(e, "act", None) is not None}
    assert int(act1.id) in act_ids
    assert int(act2.id) in act_ids
    assert total >= 2


def test_4_documento_inexistente_crea(app_ctx) -> None:
    doc = _doc()
    c = resolve_contribuyente({"doc_nro": doc, "apellido": "Nuevo", "nombre": "Alta"})
    db.session.commit()
    assert c is not None
    assert len(_activos_norm(doc)) == 1
    _assert_unico_coherente(doc, c.id)
    _assert_lock_libre(doc)


def test_5_nombres_claves_ausentes_y_vacias_sin_cambiar_regla(app_ctx) -> None:
    doc = _doc()
    c1 = resolve_contribuyente(
        {"doc_nro": doc, "apellido": "Garcia", "nombre": "Ana", "razon_social": None}
    )
    db.session.flush()
    c2 = resolve_contribuyente({"doc_nro": doc})
    assert c2 is c1
    assert c1.apellido == "Garcia"
    assert c1.nombre == "Ana"
    c3 = resolve_contribuyente(
        {"doc_nro": doc, "apellido": None, "nombre": None, "razon_social": "ACME SA"}
    )
    assert c3 is c1
    assert c1.apellido is None
    assert c1.nombre is None
    assert c1.razon_social == "ACME SA"
    db.session.commit()
    _assert_lock_libre(doc)


def _par_equivalente() -> tuple[str, str]:
    """Literal con punto y su equivalente solo dígitos, ambos ≤ 11 caracteres."""
    plain = _doc()
    dotted = f"{plain[:2]}.{plain[2:]}"
    assert len(dotted) <= 11
    return plain, dotted


def test_7_formato_no_admitido_no_trunca_ni_crea(app_ctx) -> None:
    before = Contribuyente.query.count()
    with pytest.raises(DocumentoIdentidadError) as exc:
        resolve_contribuyente({"doc_nro": "20-12345678-9", "apellido": "Largo"})
    assert MSG_DOCUMENTO_LARGO in str(exc.value)
    assert exc.value.codigo == "DOCUMENTO_INVALIDO"
    db.session.rollback()
    assert Contribuyente.query.count() == before
    _assert_lock_libre("20123456789")


def test_6_formatos_equivalentes_reutilizan(app_ctx) -> None:
    plain, dotted = _par_equivalente()
    c = resolve_contribuyente({"doc_nro": dotted, "apellido": "Fmt", "nombre": "Uno"})
    db.session.flush()
    cid = int(c.id)
    c2 = resolve_contribuyente({"doc_nro": plain, "apellido": "Fmt", "nombre": "Uno"})
    assert int(c2.id) == cid
    assert c2.documento == dotted
    db.session.commit()
    assert len(_activos_norm(plain)) == 1
    _assert_lock_libre(plain)


def test_8_varios_activos_error_controlado_no_crea_ni_fusiona(app_ctx) -> None:
    plain, dotted = _par_equivalente()
    c_a = Contribuyente(apellido="AmbA", nombre="A", documento=plain)
    c_b = Contribuyente(apellido="AmbB", nombre="B", documento=dotted)
    db.session.add_all([c_a, c_b])
    db.session.commit()
    ids_antes = sorted(contribuyente_ids_por_documento(plain))
    assert len(ids_antes) >= 2
    with pytest.raises(DocumentoIdentidadError) as exc:
        resolve_contribuyente({"doc_nro": plain, "apellido": "X", "nombre": "Y"})
    assert exc.value.codigo == "DOCUMENTO_AMBIGUO"
    assert MSG_DOCUMENTO_AMBIGUO in str(exc.value)
    db.session.rollback()
    ids_despues = sorted(contribuyente_ids_por_documento(plain))
    assert ids_despues == ids_antes
    assert Contribuyente.query.filter_by(id=c_a.id).one().apellido == "AmbA"
    assert Contribuyente.query.filter_by(id=c_b.id).one().apellido == "AmbB"
    _assert_lock_libre(plain)


def test_10_cargar_vs_cargar_una_identidad(app, actor_user_id) -> None:
    doc = _doc()
    calle_a = f"CcA{uuid4().hex[:6]}"
    calle_b = f"CcB{uuid4().hex[:6]}"
    barrier = threading.Barrier(2)
    results: list[tuple] = []

    def _run(calle: str) -> None:
        with app.app_context():
            barrier.wait()
            try:
                act = crear_actuacion_desde_payload(
                    _cargar_payload(doc=doc, calle=calle),
                    actor_user_id=actor_user_id,
                )
                results.append(("ok", int(act.id), int(act.domicilio.contribuyente_id)))
            except Exception as exc:
                results.append(("err", type(exc).__name__, str(exc)))

    t1 = threading.Thread(target=_run, args=(calle_a,))
    t2 = threading.Thread(target=_run, args=(calle_b,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    oks = [r for r in results if r[0] == "ok"]
    assert len(oks) == 2, results
    assert oks[0][2] == oks[1][2]
    with app.app_context():
        assert len(_activos_norm(doc)) == 1
        _assert_unico_coherente(doc, oks[0][2])
        _assert_lock_libre(doc)


def test_11_completar_vs_completar_una_identidad(app) -> None:
    with app.app_context():
        item_a, _act_a, _ini_a, user_a, _rb_a, _dom_a = _mk_relevamiento_en_ruta_publicada(
            uuid4().hex[:8]
        )
        item_b, _act_b, _ini_b, user_b, _rb_b, _dom_b = _mk_relevamiento_en_ruta_publicada(
            uuid4().hex[:8]
        )
        db.session.commit()
    doc = _doc()
    barrier = threading.Barrier(2)
    results: list[tuple] = []

    def _run(item_id: int, user_id: int) -> None:
        with app.app_context():
            barrier.wait()
            try:
                cerrar_completar_trabajo_por_ruta_item(
                    ruta_item_id=item_id,
                    payload=CompletarTrabajoCierreCompletoIn.model_validate(
                        {
                            "tipo_actuacion": "INSPECCION",
                            "acta_inspeccion_num": _acta_num(),
                            "caracter_persona_atendio": "ENCARGADO",
                            "posee_contrato_retiro_residuos_solidos_urbanos": True,
                            "solicita_carnet_manipulador": False,
                            "doc_nro": doc,
                            "contrib_apellido": "Comp",
                            "contrib_nombre": "Tit",
                        }
                    ),
                    ejecutado_por_user_id=user_id,
                )
                item = db.session.get(RutaItem, item_id)
                cid = item.actuacion.domicilio.contribuyente_id if item and item.actuacion else None
                results.append(("ok", item_id, cid))
            except Exception as exc:
                results.append(("err", type(exc).__name__, str(exc)))

    t1 = threading.Thread(target=_run, args=(item_a, user_a))
    t2 = threading.Thread(target=_run, args=(item_b, user_b))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    oks = [r for r in results if r[0] == "ok"]
    assert len(oks) == 2, results
    assert oks[0][2] == oks[1][2]
    with app.app_context():
        assert len(_activos_norm(doc)) == 1
        _assert_lock_libre(doc)


def test_12_cargar_vs_corregir_cuit(app, actor_user_id, service_actor) -> None:
    nuevo = _doc()
    with app.app_context():
        actor = db.session.get(User, service_actor)
        assert actor is not None
        c = _contrib(apellido="A2")
        d = _dom(c, calle=f"A2c{uuid4().hex[:6]}")
        eo = _eo(d, actor)
        db.session.commit()
        prev = preview_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
            actor=actor,
        )
        fp = prev["fingerprint"]
        eo_id = int(eo.id)
        c_id = int(c.id)
        calle_cargar = f"Cg{uuid4().hex[:6]}"

    barrier = threading.Barrier(2)
    results: list[tuple] = []

    def _cargar() -> None:
        with app.app_context():
            barrier.wait()
            try:
                act = crear_actuacion_desde_payload(
                    _cargar_payload(doc=nuevo, calle=calle_cargar),
                    actor_user_id=actor_user_id,
                )
                results.append(("cargar", int(act.domicilio.contribuyente_id)))
            except Exception as exc:
                results.append(("cargar_err", getattr(exc, "codigo", type(exc).__name__)))

    def _a2() -> None:
        with app.app_context():
            person = db.session.get(User, service_actor)
            barrier.wait()
            try:
                aplicar_correccion_establecimiento(
                    eo_id,
                    CorreccionEstablecimientoIn.model_validate(
                        {
                            "contribuyente": {"documento": nuevo},
                            "confirmado": True,
                            "fingerprint": fp,
                        }
                    ),
                    actor=person,
                )
                results.append(("a2", c_id))
            except Exception as exc:
                results.append(("a2_err", getattr(exc, "codigo", type(exc).__name__)))

    t1 = threading.Thread(target=_cargar)
    t2 = threading.Thread(target=_a2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert len(results) == 2, results
    with app.app_context():
        dueños = _activos_norm(nuevo)
        assert len(dueños) == 1
        _assert_lock_libre(nuevo)


def test_13_completar_vs_corregir_cuit(app, service_actor) -> None:
    nuevo = _doc()
    with app.app_context():
        actor = db.session.get(User, service_actor)
        assert actor is not None
        c = _contrib(apellido="A2b")
        d = _dom(c, calle=f"A2b{uuid4().hex[:6]}")
        eo = _eo(d, actor)
        item_id, _act_id, _ini, user_id, _rb, _domid = _mk_relevamiento_en_ruta_publicada(
            uuid4().hex[:8]
        )
        db.session.commit()
        prev = preview_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
            actor=actor,
        )
        fp = prev["fingerprint"]
        eo_id = int(eo.id)
        c_id = int(c.id)

    barrier = threading.Barrier(2)
    results: list[tuple] = []

    def _completar() -> None:
        with app.app_context():
            barrier.wait()
            try:
                cerrar_completar_trabajo_por_ruta_item(
                    ruta_item_id=item_id,
                    payload=CompletarTrabajoCierreCompletoIn.model_validate(
                        {
                            "tipo_actuacion": "INSPECCION",
                            "acta_inspeccion_num": _acta_num(),
                            "caracter_persona_atendio": "ENCARGADO",
                            "posee_contrato_retiro_residuos_solidos_urbanos": True,
                            "solicita_carnet_manipulador": False,
                            "doc_nro": nuevo,
                            "contrib_apellido": "CompA2",
                            "contrib_nombre": "Tit",
                        }
                    ),
                    ejecutado_por_user_id=user_id,
                )
                results.append(("completar", "ok"))
            except Exception as exc:
                results.append(("completar_err", getattr(exc, "codigo", type(exc).__name__)))

    def _a2() -> None:
        with app.app_context():
            person = db.session.get(User, service_actor)
            barrier.wait()
            try:
                aplicar_correccion_establecimiento(
                    eo_id,
                    CorreccionEstablecimientoIn.model_validate(
                        {
                            "contribuyente": {"documento": nuevo},
                            "confirmado": True,
                            "fingerprint": fp,
                        }
                    ),
                    actor=person,
                )
                results.append(("a2", c_id))
            except Exception as exc:
                results.append(("a2_err", getattr(exc, "codigo", type(exc).__name__)))

    t1 = threading.Thread(target=_completar)
    t2 = threading.Thread(target=_a2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert len(results) == 2, results
    with app.app_context():
        assert len(_activos_norm(nuevo)) == 1
        _assert_lock_libre(nuevo)


def test_14_put_vs_cargar_una_identidad(app, actor_user_id) -> None:
    """PUT de actuación (mismo helper) vs Cargar: una identidad activa."""
    from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
    from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
    from app.domains.actuaciones.services.update_service import actualizar_actuacion

    doc = _doc()
    with app.app_context():
        act = crear_actuacion_desde_payload(
            _cargar_payload(doc=_doc(), calle=f"Put{uuid4().hex[:6]}"),
            actor_user_id=actor_user_id,
        )
        act_id = int(act.id)
        ot = act.orden_trabajo.numero_acta
        fecha = act.fecha.isoformat()
        inspectores = [str(i.nombre) for i in (act.inspector or []) if getattr(i, "nombre", None)]
        db.session.commit()

    barrier = threading.Barrier(2)
    results: list[tuple] = []

    def _put() -> None:
        from tests.helpers.service_actor import jwt_request_context

        with jwt_request_context(app, actor_user_id):
            barrier.wait()
            try:
                row = ActuacionGridRowIn.model_validate(
                    {
                        "id": act_id,
                        "orden_trabajo_numero": ot,
                        "fecha_actuacion": fecha,
                        "rubro_nombre": _rubro_nombre(),
                        "tipo_actuacion": "INSPECCION",
                        "inspectores": inspectores,
                        "doc_nro": doc,
                        "contrib_apellido": "PutAp",
                        "contrib_nombre": "PutNom",
                        "calle": f"PutB{uuid4().hex[:6]}",
                        "numero": "33",
                    }
                )
                actualizar_actuacion(act_id, map_actuacion_row(row), actor_user_id=actor_user_id)
                results.append(("put", "ok"))
            except Exception as exc:
                results.append(("put_err", type(exc).__name__, str(exc)))

    def _cargar() -> None:
        with app.app_context():
            barrier.wait()
            try:
                crear_actuacion_desde_payload(
                    _cargar_payload(doc=doc, calle=f"PutC{uuid4().hex[:6]}"),
                    actor_user_id=actor_user_id,
                )
                results.append(("cargar", "ok"))
            except Exception as exc:
                results.append(("cargar_err", type(exc).__name__, str(exc)))

    t1 = threading.Thread(target=_put)
    t2 = threading.Thread(target=_cargar)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    oks = [r for r in results if r[0] in {"put", "cargar"}]
    assert len(oks) == 2, results
    with app.app_context():
        assert len(_activos_norm(doc)) == 1
        _assert_lock_libre(doc)


def test_15_rollback_sin_escritura_parcial_ni_lock(app_ctx, actor_user_id) -> None:
    doc = _doc()
    with patch.object(db.session, "commit", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            crear_actuacion_desde_payload(
                _cargar_payload(doc=doc, calle=f"Boom{uuid4().hex[:6]}"),
                actor_user_id=actor_user_id,
            )
    db.session.rollback()
    assert _activos_norm(doc) == []
    assert (
        ContribuyenteDocumentoUnico.query.filter_by(
            documento_normalizado=normalizar_documento(doc)
        ).count()
        == 0
    )
    _assert_lock_libre(doc)


def test_16_http_ambiguo_y_sin_token(client, app, auth_headers) -> None:
    plain, dotted = _par_equivalente()
    with app.app_context():
        db.session.add_all(
            [
                Contribuyente(apellido="Ha", nombre="A", documento=plain),
                Contribuyente(apellido="Hb", nombre="B", documento=dotted),
            ]
        )
        db.session.commit()
        inspector = _inspector_nombre()
        rubro = _rubro_nombre()
        from app.models import CatalogContraproducencia

        contra = CatalogContraproducencia.query.order_by(CatalogContraproducencia.id.asc()).first()
        contra_nombre = contra.nombre if contra is not None else None
    grid = {
        "orden_trabajo_numero": _acta_num(),
        "fecha_actuacion": "09/09/2026",
        "tipo_actuacion": "INSPECCION",
        "inspectores": [inspector],
        "calle": f"Http{uuid4().hex[:6]}",
        "numero": "100",
        "rubro_nombre": rubro,
        "doc_nro": plain,
        "contrib_apellido": "Perez",
        "contrib_nombre": "Ana",
        "acta_inspeccion_num": _acta_num(),
    }
    if contra_nombre:
        grid["contraproducencia"] = contra_nombre
    denied = client.post("/actuaciones/", json=grid)
    assert denied.status_code == 401

    r = client.post("/actuaciones/", json=grid, headers=auth_headers)
    assert r.status_code == 409, r.get_json()
    body = r.get_json()
    assert body["codigo"] == "DOCUMENTO_AMBIGUO"
    assert body["errors"]["doc_nro"] == MSG_DOCUMENTO_AMBIGUO
    assert "éxito" not in (body.get("detail") or "").lower()


def test_17_tipo_contraproducencia_intactos(app_ctx, actor_user_id) -> None:
    doc = _doc()
    act = crear_actuacion_desde_payload(
        _cargar_payload(doc=doc, calle=f"Reg{uuid4().hex[:6]}"),
        actor_user_id=actor_user_id,
    )
    assert act.tipo == "INSPECCION"
    assert (act.contraproducencia or "").upper() in {"NO_HUBO", "NO HUBO"}


def test_18_vinculacion_ambiguo_no_elige_ficha(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    plain, dotted = _par_equivalente()
    a = Contribuyente(apellido="Va", nombre="A", documento=plain)
    b = Contribuyente(apellido="Vb", nombre="B", documento=dotted)
    db.session.add_all([a, b])
    db.session.flush()
    d = _dom(a, calle=f"Vinc{uuid4().hex[:6]}")
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(
        int(eo.id),
        VinculacionEstablecimientoIn.model_validate({"documento": plain}),
        actor=actor,
    )
    conflicto = prev.get("conflicto") or {}
    assert conflicto.get("codigo") == "DOCUMENTO_AMBIGUO"
    assert prev.get("puede_aplicar") is False


def test_19_limpiar_contribuyente_sigue_bloqueado() -> None:
    from pydantic import ValidationError

    from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
        CorreccionEstablecimientoIn,
    )

    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}}
        )
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate(
            {"documento": "20111222", "limpiar_contribuyente": True}
        )
