"""REL-MAP-CIERRE.4 — búsqueda ampliada GET /map/gestion-domicilios."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_query import (
    GestionDomiciliosQuery,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_service import (
    list_gestion_domicilios,
)
from app.models import Contribuyente, Domicilio, DomicilioGeocode, Relevamiento, Rubro

TEST_TAG = "GDomSearch4"


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_dom(
    *,
    tag: str,
    calle: str | None = None,
    numero: str = "100",
    numero_tipo: str | None = None,
    calle_normalizada: str | None = None,
    contribuyente: Contribuyente | None = None,
    rubro: Rubro | None = None,
    geo_status: str | None = "REVIEW",
    with_geo: bool = True,
) -> Domicilio:
    dom = Domicilio(
        calle=calle or f"{TEST_TAG}{tag}",
        numero=numero,
        numero_tipo=numero_tipo,
        calle_normalizada=calle_normalizada,
        calle_norm_status="OK",
        contribuyente_id=contribuyente.id if contribuyente else None,
        rubro_id=rubro.id if rubro else None,
    )
    db.session.add(dom)
    db.session.flush()
    if with_geo and geo_status is not None:
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
                geo_status=geo_status,
                source="AUTO",
                lat=-26.824,
                lng=-65.222,
                score=0.5,
            )
        )
        db.session.flush()
    return dom


def _mk_contribuyente(
    *,
    apellido: str | None = None,
    nombre: str | None = None,
    razon_social: str | None = None,
    documento: str | None = None,
) -> Contribuyente:
    suffix = _unique_num()
    c = Contribuyente(
        apellido=apellido or f"Ap{suffix}",
        nombre=nombre or f"No{suffix}",
        razon_social=razon_social,
        documento=documento or suffix.zfill(8),
    )
    db.session.add(c)
    db.session.flush()
    return c


def _mk_rubro(nombre: str) -> Rubro:
    rub = Rubro(nombre=nombre)
    db.session.add(rub)
    db.session.flush()
    return rub


def _mk_relevamiento(
    dom: Domicilio,
    *,
    nombre_fantasia: str | None = None,
    rubro: Rubro | None = None,
) -> Relevamiento:
    today = date.today()
    rel = Relevamiento(
        fecha=today,
        mes=today.month,
        anio=today.year,
        domicilio_id=dom.id,
        nombre_fantasia=nombre_fantasia,
        rubro_id=rubro.id if rubro else None,
    )
    db.session.add(rel)
    db.session.flush()
    return rel


def _ids(body) -> set[int]:
    return {r.domicilio_id for r in body.rows}


def test_search_calle(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="Calle", calle=f"{TEST_TAG}UniqueCalleXyz")
        _mk_dom(tag="OtroCalle")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="UniqueCalleXyz", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
        assert len(_ids(body)) == 1
    finally:
        db.session.rollback()


def test_search_calle_normalizada(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="Norm", calle_normalizada=f"{TEST_TAG}NormAliasQ")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="NormAliasQ", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()


def test_search_esquina_en_numero(app_ctx) -> None:
    try:
        dom = _mk_dom(
            tag="Esquina",
            calle="Ayacucho",
            numero="Piedras",
            numero_tipo="ESQUINA",
        )
        _mk_dom(tag="OtraCalle", calle="San Martin", numero="500")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="Piedras", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()


def test_search_nombre_fantasia_relevamiento(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="Fantasia")
        _mk_relevamiento(dom, nombre_fantasia=f"{TEST_TAG}PanaderiaSol")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="PanaderiaSol", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()


def test_search_contribuyente_nombre_apellido_razon(app_ctx) -> None:
    try:
        c = _mk_contribuyente(
            apellido=f"{TEST_TAG}Gomez",
            nombre="Carlos",
            razon_social=f"{TEST_TAG}Comercial SA",
        )
        dom = _mk_dom(tag="Contrib", contribuyente=c)
        body_ap = list_gestion_domicilios(
            GestionDomiciliosQuery(q="Gomez", status_operativo="todos", page_size=50)
        )
        body_nom = list_gestion_domicilios(
            GestionDomiciliosQuery(q="Carlos", status_operativo="todos", page_size=50)
        )
        body_rs = list_gestion_domicilios(
            GestionDomiciliosQuery(q="Comercial SA", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body_ap)
        assert dom.id in _ids(body_nom)
        assert dom.id in _ids(body_rs)
    finally:
        db.session.rollback()


def test_search_dni_y_cuit_documento(app_ctx) -> None:
    try:
        dni = "30123456"
        cuit = "20301234567"
        dom_dni = _mk_dom(tag="Dni", contribuyente=_mk_contribuyente(documento=dni))
        dom_cuit = _mk_dom(tag="Cuit", contribuyente=_mk_contribuyente(documento=cuit))
        body_dni = list_gestion_domicilios(
            GestionDomiciliosQuery(q=dni, status_operativo="todos", page_size=50)
        )
        body_cuit = list_gestion_domicilios(
            GestionDomiciliosQuery(q="3012345", status_operativo="todos", page_size=50)
        )
        assert dom_dni.id in _ids(body_dni)
        assert dom_cuit.id in _ids(body_cuit)
    finally:
        db.session.rollback()


def test_search_rubro_domicilio(app_ctx) -> None:
    try:
        rub = _mk_rubro(f"{TEST_TAG}Carniceria")
        dom = _mk_dom(tag="RubDom", rubro=rub)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="Carniceria", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()


def test_search_rubro_relevamiento(app_ctx) -> None:
    try:
        rub = _mk_rubro(f"{TEST_TAG}VerduleriaRel")
        dom = _mk_dom(tag="RubRel")
        _mk_relevamiento(dom, rubro=rub)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="VerduleriaRel", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()


def test_search_domicilio_id_exacto(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="ById")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=str(dom.id), status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
        assert len(_ids(body)) == 1
    finally:
        db.session.rollback()


def test_search_q_inexistente_cero(app_ctx) -> None:
    try:
        _mk_dom(tag="Existe")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=f"{TEST_TAG}ZZZNoMatchEver999",
                status_operativo="todos",
                page_size=50,
            )
        )
        assert body.rows == []
        assert body.pagination.total == 0
    finally:
        db.session.rollback()


def test_search_q_con_status_operativo(app_ctx) -> None:
    try:
        shared_ap = f"{TEST_TAG}ReqAccAp"
        dom = _mk_dom(
            tag="ReqAcc",
            contribuyente=_mk_contribuyente(apellido=shared_ap),
            geo_status="REVIEW",
            with_geo=True,
        )
        ok = _mk_dom(
            tag="ReqOk",
            contribuyente=_mk_contribuyente(apellido=shared_ap),
            geo_status="OK",
            with_geo=True,
        )
        geo_ok = DomicilioGeocode.query.filter_by(domicilio_id=ok.id).first()
        assert geo_ok is not None
        geo_ok.score = 0.99
        db.session.flush()
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q="ReqAccAp",
                status_operativo="requiere_accion",
                page_size=50,
            )
        )
        ids = _ids(body)
        assert dom.id in ids
        assert ok.id not in ids
    finally:
        db.session.rollback()


def test_search_q_con_paginacion(app_ctx) -> None:
    try:
        shared_ap = f"{TEST_TAG}PagAp"
        for i in range(3):
            _mk_dom(
                tag=f"Pag{i}",
                contribuyente=_mk_contribuyente(apellido=shared_ap, nombre=f"N{i}"),
            )
        body_p1 = list_gestion_domicilios(
            GestionDomiciliosQuery(q=shared_ap, status_operativo="todos", page=1, page_size=2)
        )
        body_p2 = list_gestion_domicilios(
            GestionDomiciliosQuery(q=shared_ap, status_operativo="todos", page=2, page_size=2)
        )
        assert body_p1.pagination.total >= 3
        assert len(body_p1.rows) == 2
        assert _ids(body_p1).isdisjoint(_ids(body_p2))
    finally:
        db.session.rollback()


def test_include_map_points_respeta_q(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="MapQ", geo_status="REVIEW")
        otro = _mk_dom(tag="MapOtro", geo_status="REVIEW")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=dom.calle,
                status_operativo="punto_dudoso",
                include_map_points=True,
                page_size=10,
            )
        )
        map_ids = {p.domicilio_id for p in body.map_points}
        assert dom.id in map_ids
        assert otro.id not in map_ids
    finally:
        db.session.rollback()


def test_search_no_duplica_por_multiples_relevamientos(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="DupRel")
        _mk_relevamiento(dom, nombre_fantasia=f"{TEST_TAG}DupFantasia")
        _mk_relevamiento(dom, nombre_fantasia=f"{TEST_TAG}DupFantasiaDos")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="DupFantasia", status_operativo="todos", page_size=50)
        )
        matches = [r for r in body.rows if r.domicilio_id == dom.id]
        assert len(matches) == 1
        assert body.pagination.total >= 1
    finally:
        db.session.rollback()


def test_search_case_insensitive(app_ctx) -> None:
    try:
        dom = _mk_dom(tag="Case", calle_normalizada=f"{TEST_TAG}RiodelaPlata")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="riodelaplata", status_operativo="todos", page_size=50)
        )
        assert dom.id in _ids(body)
    finally:
        db.session.rollback()
