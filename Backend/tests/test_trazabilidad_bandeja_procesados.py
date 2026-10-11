"""

V1.1-TRAZABILIDAD-RELEVAMIENTOS.1 — bandeja Procesados (Relevamiento y Denuncia).

"""



from __future__ import annotations



from datetime import date

from decimal import Decimal



from app.database import db

from app.domains.denuncias.schemas import DenunciasGestionFilters

from app.domains.denuncias.services.denuncias_service import (

    crear_denuncia_con_iniciador,

    listar_denuncias_gestion_operativa,

    listar_denuncias_gestion_procesadas,

)

from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters

from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload

from app.domains.relevamientos.services.list_service import (

    listar_relevamientos_operativos_con_filtros,

    listar_relevamientos_procesados_con_filtros,

    listar_relevamientos_realizados_actuacion_completada_con_filtros,

)

from app.domains.relevamientos.services.relevamiento_iniciador_service import (

    get_or_create_iniciador_from_relevamiento,

)

from app.models import Denuncia, Domicilio, DomicilioGeocode, IniciadorRuta, Relevamiento

from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq





def _rel_filters() -> RelevamientosListFilters:

    return RelevamientosListFilters.model_validate(

        {"desde": "2026-01-01", "hasta": "2026-12-31", "page": 1, "page_size": 200}

    )





def _den_filters() -> DenunciasGestionFilters:

    return DenunciasGestionFilters.model_validate(

        {"desde": "2026-01-01", "hasta": "2026-12-31", "page": 1, "page_size": 200}

    )





def _set_geocode(domicilio_id: int) -> None:

    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id, deleted_at=None).first()

    if geo is None:

        geo = DomicilioGeocode(domicilio_id=domicilio_id)

        db.session.add(geo)

    geo.geo_status = "OK"

    geo.lat = Decimal("-26.8241000")

    geo.lng = Decimal("-65.2226000")

    geo.source = "MANUAL"

    db.session.flush()





def _mk_relevamiento(*, estado_iniciador: str) -> tuple[Relevamiento, IniciadorRuta]:

    rev = get_or_create_test_relevador()

    rub = get_test_rubro()

    rel = crear_relevamiento_desde_payload(

        {

            "fecha": "2026-06-15",

            "relevadores_nombres": [rev.nombre],

            "domicilio": {"calle": uniq("ProcRel"), "numero": "50"},

            "rubro_nombre": rub.nombre,

            "esta_abierto": True,

        }

    )

    dom = db.session.get(Domicilio, rel.domicilio_id)

    assert dom is not None

    _set_geocode(dom.id)

    ini = get_or_create_iniciador_from_relevamiento(rel, actor_user_id=1)

    ini.estado_iniciador = estado_iniciador

    if estado_iniciador == "CERRADO_NO_EXISTE_LOCAL":

        ini.cerrado_motivo = "NO_EXISTE_LOCAL"

        ini.cerrado_at = date(2026, 6, 15)

    db.session.add_all([rel, ini])

    db.session.commit()

    return rel, ini





def _mk_denuncia(*, estado_iniciador: str) -> tuple[int, IniciadorRuta]:

    motivo_tag = uniq("ProcDen")

    crear_denuncia_con_iniciador(

        fecha=date(2026, 6, 20),

        domicilio_id=None,

        calle=uniq("ProcDenCalle"),

        numero="99",

        interseccion=None,

        motivo=motivo_tag,

    )

    den = (
        Denuncia.query.filter(Denuncia.motivo == motivo_tag, Denuncia.deleted_at.is_(None))
        .order_by(Denuncia.id.desc())
        .limit(1)
        .one()
    )
    ini = (
        IniciadorRuta.query.filter(
            IniciadorRuta.denuncia_id == den.id,
            IniciadorRuta.tipo_iniciador == "DENUNCIA",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .limit(1)
        .one()
    )
    den_id = int(den.id)

    ini.estado_iniciador = estado_iniciador

    if estado_iniciador == "CERRADO_NO_EXISTE_LOCAL":

        ini.cerrado_motivo = "NO_EXISTE_LOCAL"

        ini.cerrado_at = date(2026, 6, 20)

    db.session.add(ini)

    db.session.commit()

    return den_id, ini





def _rel_procesados_by_id() -> dict[int, dict]:

    items = listar_relevamientos_procesados_con_filtros(_rel_filters())["items"]

    return {int(r["id"]): r for r in items}





def _den_procesados_by_id() -> dict[int, dict]:

    items = listar_denuncias_gestion_procesadas(_den_filters())["items"]

    return {int(r["id"]): r for r in items}





def test_relevamiento_pendiente_solo_operativos(app_ctx) -> None:

    rel, _ = _mk_relevamiento(estado_iniciador="PENDIENTE")

    assert rel.id not in _rel_procesados_by_id()

    oper = {int(r.id) for r, _ in listar_relevamientos_operativos_con_filtros(_rel_filters())["items"]}

    assert rel.id in oper





def test_relevamiento_cumplido_procesados_realizado(app_ctx) -> None:

    rel, _ = _mk_relevamiento(estado_iniciador="CUMPLIDO")

    row = _rel_procesados_by_id()[rel.id]

    assert row["resultado_label"] == "Realizado"

    assert row["resultado_codigo"] == "REALIZADO"

    assert row["iniciador_estado"] == "CUMPLIDO"





def test_relevamiento_cerrado_no_existe_local_procesados(app_ctx) -> None:

    rel, _ = _mk_relevamiento(estado_iniciador="CERRADO_NO_EXISTE_LOCAL")

    row = _rel_procesados_by_id()[rel.id]

    assert row["resultado_label"] == "No existe local"

    assert row["resultado_codigo"] == "NO_EXISTE_LOCAL"





def test_relevamiento_reencolado_no_en_procesados(app_ctx) -> None:

    rel, ini = _mk_relevamiento(estado_iniciador="PENDIENTE")

    assert rel.id not in _rel_procesados_by_id()

    assert ini.estado_iniciador == "PENDIENTE"





def test_relevamiento_realizados_legacy_solo_cumplido(app_ctx) -> None:

    rel_ok, _ = _mk_relevamiento(estado_iniciador="CUMPLIDO")

    rel_ne, _ = _mk_relevamiento(estado_iniciador="CERRADO_NO_EXISTE_LOCAL")

    realizados = {

        int(r.id)

        for r in listar_relevamientos_realizados_actuacion_completada_con_filtros(_rel_filters())["items"]

    }

    assert rel_ok.id in realizados

    assert rel_ne.id not in realizados





def test_relevamiento_procesados_paginacion(app_ctx) -> None:

    for _ in range(3):

        _mk_relevamiento(estado_iniciador="CUMPLIDO")

    f = RelevamientosListFilters.model_validate(

        {"desde": "2026-01-01", "hasta": "2026-12-31", "page": 1, "page_size": 2}

    )

    r1 = listar_relevamientos_procesados_con_filtros(f)

    assert len(r1["items"]) == 2

    assert r1["meta"]["total"] >= 3





def test_denuncia_pendiente_solo_operativas(app_ctx) -> None:

    den_id, _ = _mk_denuncia(estado_iniciador="PENDIENTE")

    assert den_id not in _den_procesados_by_id()

    oper = {

        int(r["id"])

        for r in listar_denuncias_gestion_operativa(_den_filters())["items"]

    }

    assert den_id in oper





def test_denuncia_cumplido_procesados(app_ctx) -> None:

    den_id, _ = _mk_denuncia(estado_iniciador="CUMPLIDO")

    row = _den_procesados_by_id()[den_id]

    assert row["resultado_label"] == "Realizado"





def test_denuncia_cerrado_no_existe_local_procesados(app_ctx) -> None:

    den_id, _ = _mk_denuncia(estado_iniciador="CERRADO_NO_EXISTE_LOCAL")

    row = _den_procesados_by_id()[den_id]

    assert row["resultado_label"] == "No existe local"





def test_denuncia_reencolado_no_procesados(app_ctx) -> None:

    den_id, _ = _mk_denuncia(estado_iniciador="PENDIENTE")

    assert den_id not in _den_procesados_by_id()


