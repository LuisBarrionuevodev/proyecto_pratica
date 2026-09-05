"""
Identidad lógica de ficha ``establecimiento_operativo`` (GESTIÓN-FIX.7).

Business key: contribuyente lógico + domicilio lógico (sin rubro).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_

from app.database import db
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.models import Actuaciones, Contribuyente, Domicilio, EstablecimientoOperativo

if TYPE_CHECKING:
    from collections.abc import Iterable


BusinessKey = tuple[str, str, str]


def _calle_logica_key(dom: Domicilio) -> str:
    raw = (dom.calle_key or dom.calle_normalizada or dom.calle or "").strip()
    return slug_key(raw) if raw else ""


def _numero_logica_key(dom: Domicilio) -> str:
    nt = (dom.numero_tipo or "").strip().upper()
    if nt == "ESQUINA":
        ref = (dom.esquina_normalizada or dom.numero or "").strip()
        return f"ESQ:{slug_key(ref)}" if ref else ""
    num = str(dom.numero or "").strip()
    return slug_key(num) if num else ""


def contribuyente_logico_key(dom: Domicilio, contrib: Contribuyente | None = None) -> str:
    """
    Clave de contribuyente lógico: documento normalizado o fallback a contribuyente_id.
    """
    c = contrib if contrib is not None else getattr(dom, "contribuyente", None)
    doc = normalizar_documento(getattr(c, "documento", None) if c is not None else None)
    if doc:
        return f"doc:{doc}"
    if dom.contribuyente_id is not None:
        return f"cid:{int(dom.contribuyente_id)}"
    return ""


def business_key_tuple(dom: Domicilio, contrib: Contribuyente | None = None) -> BusinessKey:
    """Tupla (contrib_logico, calle_logica, numero_logica). Rubro excluido."""
    return (
        contribuyente_logico_key(dom, contrib),
        _calle_logica_key(dom),
        _numero_logica_key(dom),
    )


def business_key_str(dom: Domicilio, contrib: Contribuyente | None = None) -> str:
    """Representación serializable de la business key."""
    ck, calle_k, num_k = business_key_tuple(dom, contrib)
    return f"{ck}|{calle_k}|{num_k}"


def identidad_logica_completa(dom: Domicilio, contrib: Contribuyente | None = None) -> bool:
    """True si hay datos mínimos para resolver identidad lógica de ficha."""
    ck, calle_k, num_k = business_key_tuple(dom, contrib)
    return bool(ck and calle_k and num_k)


def domicilio_puede_resolver_establecimiento_operativo(
    dom: Domicilio | None,
    contrib: Contribuyente | None = None,
) -> bool:
    """
    Gate FIX.10B.1.2: True si el domicilio tiene identidad lógica completa (FIX.7).

    Parámetros:
        dom: domicilio ancla del cierre/edición.
        contrib: contribuyente opcional si no está cargado en ``dom``.

    Retorno:
        False si el domicilio es None, está eliminado o la identidad lógica es incompleta.

    Errores:
        Ninguno.
    """
    if dom is None or getattr(dom, "deleted_at", None) is not None:
        return False
    return identidad_logica_completa(dom, contrib)


def contribuyente_ids_logicos(dom: Domicilio, contrib: Contribuyente | None = None) -> list[int]:
    """
    IDs de contribuyente equivalentes lógicamente (mismo documento normalizado).

    Sin documento válido: solo el ``contribuyente_id`` del domicilio.
    """
    c = contrib if contrib is not None else getattr(dom, "contribuyente", None)
    doc = getattr(c, "documento", None) if c is not None else None
    ids = contribuyente_ids_por_documento(doc or "")
    if ids:
        return ids
    if dom.contribuyente_id is not None:
        return [int(dom.contribuyente_id)]
    return []


def domicilio_coincide_identidad_logica(dom_a: Domicilio, dom_b: Domicilio) -> bool:
    """True si dos domicilios comparten business key lógica."""
    return business_key_tuple(dom_a) == business_key_tuple(dom_b)


def domicilio_ids_misma_identidad_logica(
    dom: Domicilio,
    *,
    contrib: Contribuyente | None = None,
) -> list[int]:
    """
    IDs de domicilio (no eliminados) con la misma identidad lógica que ``dom``.

    Parámetros:
        dom: domicilio semilla.
        contrib: contribuyente opcional si no está cargado en ``dom``.

    Retorno:
        Lista de ids (incluye al menos ``dom.id`` si la identidad es completa).
    """
    if dom is None or getattr(dom, "deleted_at", None) is not None:
        return []

    target = business_key_tuple(dom, contrib)
    if not target[0] or not target[1] or not target[2]:
        return [int(dom.id)]

    contrib_ids = contribuyente_ids_logicos(dom, contrib)
    if not contrib_ids:
        return [int(dom.id)]

    candidatos = (
        Domicilio.query.filter(
            Domicilio.deleted_at.is_(None),
            Domicilio.contribuyente_id.in_(contrib_ids),
        )
        .all()
    )
    out = [int(d.id) for d in candidatos if business_key_tuple(d) == target]
    if int(dom.id) not in out:
        out.append(int(dom.id))
    return sorted(set(out))


def eo_ids_misma_identidad_logica(dom: Domicilio) -> list[int]:
    """IDs de ``establecimiento_operativo`` anclados a domicilios de la misma identidad lógica."""
    dom_ids = domicilio_ids_misma_identidad_logica(dom)
    if not dom_ids:
        return []
    rows = (
        EstablecimientoOperativo.query.filter(EstablecimientoOperativo.domicilio_id.in_(dom_ids))
        .with_entities(EstablecimientoOperativo.id)
        .all()
    )
    return sorted({int(r[0]) for r in rows})


def eo_canonico_id_para_domicilio(dom: Domicilio) -> int | None:
    """
    ID canónico de ficha (MIN id) para la identidad lógica del domicilio.

    Retorno:
        ``None`` si no existe ninguna ficha para esa identidad.
    """
    eo_ids = eo_ids_misma_identidad_logica(dom)
    return min(eo_ids) if eo_ids else None


def eo_canonico_para_domicilio(dom: Domicilio) -> EstablecimientoOperativo | None:
    """Instancia EO canónica (MIN id) para la identidad lógica."""
    eid = eo_canonico_id_para_domicilio(dom)
    if eid is None:
        return None
    return db.session.get(EstablecimientoOperativo, eid)


def actuaciones_filter_identidad_logica_desde_domicilio(dom: Domicilio):
    """Cláusula SQLAlchemy: actuaciones cuyo domicilio comparte identidad lógica."""
    dom_ids = domicilio_ids_misma_identidad_logica(dom)
    if not dom_ids:
        return Actuaciones.domicilio_id == -1
    return Actuaciones.domicilio_id.in_(dom_ids)


def grupo_eo_sostenido_por_actuaciones(eos: Iterable[EstablecimientoOperativo]) -> bool:
    """
    True si hay actuaciones en la identidad lógica del grupo (FIX.7 / forks COW).

    No limita a ``act.establecimiento_operativo_id``; cuenta por domicilios de la business key.
    """
    for eo in eos:
        dom = eo.domicilio
        if dom is None:
            continue
        if count_actuaciones_identidad_logica(dom) > 0:
            return True
    return False


def eo_tiene_actuacion_vinculada(eo_id: int) -> bool:
    """True si alguna actuación apunta a esta ficha por ``establecimiento_operativo_id``."""
    return (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.establecimiento_operativo_id == int(eo_id))
        .limit(1)
        .first()
        is not None
    )


def grupo_eo_tiene_actuacion_vinculada(eos: Iterable[EstablecimientoOperativo]) -> bool:
    """True si alguna ficha del grupo conserva actuaciones vinculadas por FK."""
    return any(eo_tiene_actuacion_vinculada(int(eo.id)) for eo in eos)


def count_actuaciones_identidad_logica(dom: Domicilio) -> int:
    """Cuenta actuaciones de la identidad lógica (todos los forks de domicilio)."""
    dom_ids = domicilio_ids_misma_identidad_logica(dom)
    if not dom_ids:
        return 0
    return (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.domicilio_id.in_(dom_ids))
        .count()
    )


def ultima_actuacion_identidad_logica(dom: Domicilio) -> Actuaciones | None:
    """Actuación más reciente de la identidad lógica (para rubro vigente, etc.)."""
    dom_ids = domicilio_ids_misma_identidad_logica(dom)
    if not dom_ids:
        return None
    return (
        Actuaciones.query.filter(Actuaciones.domicilio_id.in_(dom_ids))
        .order_by(Actuaciones.fecha.desc(), Actuaciones.id.desc())
        .first()
    )


def rubro_vigente_identidad_logica(dom: Domicilio) -> str | None:
    """Rubro de la actuación/domicilio más reciente de la identidad lógica."""
    ultima = ultima_actuacion_identidad_logica(dom)
    if ultima is not None and ultima.domicilio is not None:
        rub = getattr(ultima.domicilio, "rubro", None)
        if rub is not None:
            nombre = getattr(rub, "nombre", None)
            if nombre:
                return str(nombre).strip() or None
    rub_dom = getattr(dom, "rubro", None)
    if rub_dom is not None:
        nombre = getattr(rub_dom, "nombre", None)
        return str(nombre).strip() or None if nombre else None
    return None


def agrupar_eo_por_identidad_logica(
    eos: Iterable[EstablecimientoOperativo],
) -> dict[BusinessKey, list[EstablecimientoOperativo]]:
    """Agrupa fichas por business key; fichas sin identidad completa quedan aisladas por domicilio_id."""
    from collections import defaultdict

    groups: dict[BusinessKey, list[EstablecimientoOperativo]] = defaultdict(list)
    for eo in eos:
        dom = eo.domicilio
        if dom is None or getattr(dom, "deleted_at", None) is not None:
            continue
        key = business_key_tuple(dom)
        if not identidad_logica_completa(dom):
            key = (f"dom:{eo.domicilio_id}", "", "")
        groups[key].append(eo)
    return dict(groups)


def seleccionar_eo_canonico_del_grupo(eos: list[EstablecimientoOperativo]) -> EstablecimientoOperativo:
    """EO canónico determinístico: MIN(id)."""
    return min(eos, key=lambda e: int(e.id))
