"""
Alcance comprobado de una corrección desde la ficha (sin escribir).

No fusiona entidades ni resuelve por coincidencia de texto de dirección.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
    CorreccionEstablecimientoNotFoundError,
    CorreccionEstablecimientoPermisoError,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.domains.establecimientos.utils.domicilio_display import domicilio_texto_visible
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    business_key_tuple,
    domicilio_ids_misma_identidad_logica,
    identidad_logica_completa,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    EstablecimientoOperativo,
    IniciadorRuta,
    Oficio,
    RutaItem,
    User,
)

_ROLES_PERMITIDOS = frozenset({"admin", "usuario"})

MSG_DOC_AJENO = (
    "El documento propuesto ya pertenece a otro contribuyente. "
    "No se fusionan registros ni se reasigna el titular."
)
MSG_DOC_AMBIGUO = (
    "Hay más de un contribuyente activo con ese documento. "
    "No se corrige ni se asocia automáticamente; hace falta revisión."
)
MSG_PREVIEW_STALE = (
    "El alcance cambió desde la vista previa. Volvé a consultar antes de confirmar."
)
MSG_SIN_FINGERPRINT = (
    "Debe consultar el alcance antes de confirmar la corrección del documento."
)
MSG_CONFIRMACION_DOCUMENTO = (
    "Esta corrección se aplicará a todos los establecimientos asociados. "
    "Confirmá que se trata del mismo contribuyente y que el CUIT/DNI anterior estaba mal cargado."
)
MSG_AMBIGUEDAD = (
    "Hay otras filas físicas de domicilio con la misma dirección de este contribuyente "
    "que no están vinculadas de forma segura a esta ficha. "
    "No se actualiza por coincidencia de texto."
)
MSG_FUSION = (
    "La dirección propuesta coincidiría con otro establecimiento ya existente del mismo "
    "contribuyente. No se fusionan fichas automáticamente."
)
MSG_SIN_CONTRIB = (
    "La ficha no tiene contribuyente vinculado; no se puede corregir el titular."
)


@dataclass
class CorreccionScope:
    """Alcance verificado a partir de FK e identidad lógica (no por texto)."""

    eo: EstablecimientoOperativo
    domicilio: Domicilio
    contribuyente: Contribuyente | None
    identity_completa: bool
    domicilio_ids_ficha: list[int]
    lookalike_ids: list[int]
    conflicto: str | None = None
    conflicto_codigo: str | None = None
    establecimiento_ids_contribuyente: list[int] = field(default_factory=list)
    actuacion_ids_contribuyente: list[int] = field(default_factory=list)
    actuacion_ids_domicilio: list[int] = field(default_factory=list)
    notificacion_ids: list[int] = field(default_factory=list)
    comprobacion_ids: list[int] = field(default_factory=list)
    oficio_ids: list[int] = field(default_factory=list)
    iniciador_ids: list[int] = field(default_factory=list)
    ruta_item_ids: list[int] = field(default_factory=list)
    ruta_estados: list[dict[str, Any]] = field(default_factory=list)
    establecimientos_contribuyente: list[dict[str, Any]] = field(default_factory=list)


def assert_rol_puede_corregir(user: User) -> None:
    """
    Restringe el canal a roles que ya operan Establecimientos (admin/usuario).

    Errores:
        CorreccionEstablecimientoPermisoError si el rol no corresponde.
    """
    role = getattr(user, "role", None)
    if role not in _ROLES_PERMITIDOS:
        raise CorreccionEstablecimientoPermisoError(
            "No tiene permisos para corregir datos desde Establecimientos."
        )


def cargar_ficha_para_correccion(establecimiento_id: int, *, for_update: bool = False) -> CorreccionScope:
    """
    Carga la ficha ancla y calcula el alcance comprobado.

    Parámetros:
        establecimiento_id: id de ``establecimiento_operativo``.
        for_update: bloquea domicilio y contribuyente (aplicación).

    Retorno:
        CorreccionScope con ids comprobados.

    Errores:
        CorreccionEstablecimientoNotFoundError si la ficha no existe.
    """
    eo = EstablecimientoOperativo.query.filter_by(id=int(establecimiento_id)).first()
    if eo is None:
        raise CorreccionEstablecimientoNotFoundError("Establecimiento operativo no encontrado.")

    q_dom = Domicilio.query.options(joinedload(Domicilio.geocode), joinedload(Domicilio.distrito))
    if for_update:
        q_dom = q_dom.with_for_update()
    dom = q_dom.filter(Domicilio.id == eo.domicilio_id).first()
    if dom is None or getattr(dom, "deleted_at", None) is not None:
        raise CorreccionEstablecimientoNotFoundError("Domicilio de origen de la ficha no encontrado.")

    contrib: Contribuyente | None = None
    if dom.contribuyente_id is not None:
        q_c = Contribuyente.query.filter(
            Contribuyente.id == int(dom.contribuyente_id),
            Contribuyente.deleted_at.is_(None),
        )
        if for_update:
            q_c = q_c.with_for_update()
        contrib = q_c.first()

    identity_ok = identidad_logica_completa(dom, contrib)
    ficha_ids = domicilio_ids_misma_identidad_logica(dom, contrib=contrib)
    if int(dom.id) not in ficha_ids:
        ficha_ids = sorted(set(ficha_ids) | {int(dom.id)})

    lookalikes = _lookalike_domicilio_ids(dom, exclude_ids=ficha_ids)
    conflicto = None
    codigo = None
    if lookalikes:
        conflicto = MSG_AMBIGUEDAD
        codigo = "AMBIGUEDAD_DOMICILIO"

    scope = CorreccionScope(
        eo=eo,
        domicilio=dom,
        contribuyente=contrib,
        identity_completa=identity_ok,
        domicilio_ids_ficha=ficha_ids,
        lookalike_ids=lookalikes,
        conflicto=conflicto,
        conflicto_codigo=codigo,
    )
    _llenar_conteos(scope)
    return scope


def validar_documento_propuesto(contrib: Contribuyente, documento: str) -> None:
    """
    Protege la identidad compartida del contribuyente en el canal de corrección.

    Permite el mismo documento normalizado (cambio de formato). Si el normalizado
    cambia y no pertenece a otro contribuyente activo, permite la corrección A2
    de la misma fila. Si pertenece a otro id único, expone DOCUMENTO_AJENO para
    asociar solo esta ficha. Si hay varios ids activos, DOCUMENTO_AMBIGUO.

    Extra de conflicto:
        ofrece_vinculacion: True solo si hay exactamente un contribuyente activo ajeno.

    Errores:
        CorreccionEstablecimientoConflictError (409).
        CorreccionEstablecimientoError si el documento queda vacío.
    """
    doc = (documento or "").strip()
    if not doc:
        raise CorreccionEstablecimientoError("El documento del contribuyente no puede quedar vacío.")
    if len(doc) > 11:
        raise CorreccionEstablecimientoError("El documento no puede superar 11 caracteres.")
    propuesto_norm = normalizar_documento(doc)
    actual_norm = normalizar_documento(getattr(contrib, "documento", None))
    if actual_norm == propuesto_norm:
        return
    ids = contribuyente_ids_por_documento(doc)
    ajenos = sorted({int(i) for i in ids if int(i) != int(contrib.id)})
    if len(ajenos) > 1:
        raise CorreccionEstablecimientoConflictError(
            MSG_DOC_AMBIGUO,
            codigo="DOCUMENTO_AMBIGUO",
            extra={"ofrece_vinculacion": False},
        )
    if ajenos:
        # ``ofrece_vinculacion`` es contrato estructurado: True solo si hay un único id ajeno.
        raise CorreccionEstablecimientoConflictError(
            MSG_DOC_AJENO,
            codigo="DOCUMENTO_AJENO",
            extra={"ofrece_vinculacion": True},
        )


def validar_no_fusion_identidad(
    dom: Domicilio,
    contrib: Contribuyente | None,
    *,
    calle: str,
    numero: str,
    numero_tipo: str | None,
    esquina: str | None,
    scope_ids: list[int],
) -> None:
    """
    Evita que la dirección nueva colisione con otra ficha del mismo contribuyente.

    Errores:
        CorreccionEstablecimientoConflictError si fusionaría fichas.
    """
    if contrib is None or contrib.id is None:
        return
    new_key = _clave_propuesta(contrib, calle, numero, numero_tipo, esquina)
    if not new_key[0] or not new_key[1] or not new_key[2]:
        return
    scope_set = set(int(i) for i in scope_ids)
    candidatos = Domicilio.query.filter(
        Domicilio.deleted_at.is_(None),
        Domicilio.contribuyente_id == int(contrib.id),
        ~Domicilio.id.in_(scope_set) if scope_set else True,
    ).all()
    for other in candidatos:
        if business_key_tuple(other, contrib) == new_key:
            raise CorreccionEstablecimientoConflictError(MSG_FUSION, codigo="FUSION_FICHA")


def _clave_propuesta(
    contrib: Contribuyente,
    calle: str,
    numero: str,
    numero_tipo: str | None,
    esquina: str | None,
) -> tuple[str, str, str]:
    doc = normalizar_documento(contrib.documento)
    ck = f"doc:{doc}" if doc else f"cid:{int(contrib.id)}"
    calle_k = slug_key(calle or "")
    nt = (numero_tipo or "").strip().upper()
    if nt == "ESQUINA":
        ref = (esquina or numero or "").strip()
        num_k = f"ESQ:{slug_key(ref)}" if ref else ""
    else:
        num_k = slug_key(str(numero or "").strip()) if numero else ""
    return (ck, calle_k, num_k)


def _lookalike_domicilio_ids(dom: Domicilio, *, exclude_ids: list[int]) -> list[int]:
    """
    Otras filas del mismo contribuyente con la misma calle/número en texto,
    fuera de la identidad lógica comprobada.
    """
    if dom.contribuyente_id is None:
        return []
    calle_k = slug_key(dom.calle or "")
    num_k = slug_key(str(dom.numero or ""))
    if not calle_k or not num_k:
        return []
    excl = set(int(i) for i in exclude_ids) | {int(dom.id)}
    rows = Domicilio.query.filter(
        Domicilio.deleted_at.is_(None),
        Domicilio.contribuyente_id == int(dom.contribuyente_id),
    ).all()
    out: list[int] = []
    for d in rows:
        if int(d.id) in excl:
            continue
        if slug_key(d.calle or "") == calle_k and slug_key(str(d.numero or "")) == num_k:
            out.append(int(d.id))
    return sorted(set(out))


def _llenar_conteos(scope: CorreccionScope) -> None:
    contrib = scope.contribuyente
    if contrib is not None:
        est_rows = (
            db.session.query(EstablecimientoOperativo.id)
            .join(Domicilio, EstablecimientoOperativo.domicilio_id == Domicilio.id)
            .filter(
                Domicilio.contribuyente_id == int(contrib.id),
                Domicilio.deleted_at.is_(None),
            )
            .all()
        )
        scope.establecimiento_ids_contribuyente = sorted({int(r[0]) for r in est_rows})
        act_c = (
            db.session.query(Actuaciones.id)
            .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
            .filter(Domicilio.contribuyente_id == int(contrib.id))
            .all()
        )
        scope.actuacion_ids_contribuyente = sorted({int(r[0]) for r in act_c})
        scope.establecimientos_contribuyente = _establecimientos_contribuyente_preview(int(contrib.id))

    dom_ids = scope.domicilio_ids_ficha or [int(scope.domicilio.id)]
    acts = (
        Actuaciones.query.filter(Actuaciones.domicilio_id.in_(dom_ids))
        .with_entities(
            Actuaciones.id,
            Actuaciones.notificacion_id,
            Actuaciones.comprobacion_id,
        )
        .all()
    )
    scope.actuacion_ids_domicilio = sorted({int(a[0]) for a in acts})
    notif = {int(a[1]) for a in acts if a[1] is not None}
    comps = {int(a[2]) for a in acts if a[2] is not None}
    scope.notificacion_ids = sorted(notif)
    scope.comprobacion_ids = sorted(comps)
    if comps:
        of_rows = (
            Oficio.query.filter(Oficio.comprobacion_id.in_(comps), Oficio.deleted_at.is_(None))
            .with_entities(Oficio.id)
            .all()
        )
        scope.oficio_ids = sorted({int(r[0]) for r in of_rows})
    inis = (
        IniciadorRuta.query.filter(IniciadorRuta.domicilio_id.in_(dom_ids))
        .with_entities(IniciadorRuta.id)
        .all()
    )
    scope.iniciador_ids = sorted({int(r[0]) for r in inis})
    if scope.iniciador_ids:
        items = (
            RutaItem.query.filter(
                RutaItem.iniciador_ruta_id.in_(scope.iniciador_ids),
                RutaItem.deleted_at.is_(None),
            )
            .options(joinedload(RutaItem.ruta_trabajo))
            .all()
        )
        scope.ruta_item_ids = sorted({int(i.id) for i in items})
        estados = []
        for it in items:
            ruta = getattr(it, "ruta_trabajo", None)
            estados.append(
                {
                    "ruta_item_id": int(it.id),
                    "estado_ruta_item": it.estado_ruta_item,
                    "estado_ejecucion": it.estado_ejecucion,
                    "ruta_id": int(it.ruta_trabajo_id) if it.ruta_trabajo_id else None,
                    "estado_ruta": getattr(ruta, "estado_ruta", None) if ruta is not None else None,
                }
            )
        scope.ruta_estados = estados


def _establecimientos_contribuyente_preview(contribuyente_id: int) -> list[dict[str, Any]]:
    """
    Locales del contribuyente para la preview (domicilio visible + actuaciones por FK).

    No expone IDs como dato de negocio; el presenter puede incluirlos para alcance.
    """
    rows = (
        db.session.query(EstablecimientoOperativo, Domicilio)
        .join(Domicilio, EstablecimientoOperativo.domicilio_id == Domicilio.id)
        .filter(
            Domicilio.contribuyente_id == int(contribuyente_id),
            Domicilio.deleted_at.is_(None),
        )
        .order_by(EstablecimientoOperativo.id.asc())
        .all()
    )
    if not rows:
        return []
    dom_ids = [int(dom.id) for _eo, dom in rows]
    count_rows = (
        db.session.query(Actuaciones.domicilio_id, func.count(Actuaciones.id))
        .filter(Actuaciones.domicilio_id.in_(dom_ids))
        .group_by(Actuaciones.domicilio_id)
        .all()
    )
    por_dom = {int(did): int(n) for did, n in count_rows}
    out: list[dict[str, Any]] = []
    for eo, dom in rows:
        nombre = (str(eo.nombre_local).strip() or None) if getattr(eo, "nombre_local", None) else None
        out.append(
            {
                "establecimiento_operativo_id": int(eo.id),
                "nombre_local": nombre,
                "domicilio_texto": domicilio_texto_visible(dom),
                "actuaciones_cantidad": por_dom.get(int(dom.id), 0),
            }
        )
    return out
