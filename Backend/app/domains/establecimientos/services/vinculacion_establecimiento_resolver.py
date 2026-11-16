"""
Resolución del contribuyente destino para vinculación de ficha.

No usa ``resolve_contribuyente`` (ese helper actualiza nombre/apellido/razón).
"""

from __future__ import annotations

from app.database import db
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    business_key_tuple,
    identidad_logica_completa,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.models import Contribuyente, Domicilio, EstablecimientoOperativo

MSG_SIN_DESTINO = (
    "No encontramos este contribuyente. "
    "¿Querés cargar sus datos para corregir este establecimiento?"
)
MSG_DESTINO_APARECIO = (
    "El contribuyente apareció desde la vista previa. "
    "Volvé a consultar antes de confirmar. No se creó un duplicado."
)
MSG_ALTA_REQUERIDA = (
    "Indicá nombre y apellido, o razón social, para cargar el contribuyente."
)
MSG_MISMO_CONTRIB = (
    "El documento corresponde al contribuyente actual de esta ficha. "
    "No hay un cambio de vínculo."
)
MSG_DOC_AMBIGUO = (
    "Hay más de un contribuyente activo con ese documento. "
    "No se vincula automáticamente; hace falta revisión."
)
MSG_IDENTIDAD_INCOMPLETA = (
    "La identidad del domicilio de esta ficha no se puede resolver con seguridad. "
    "No se vincula automáticamente."
)
MSG_PREVIEW_STALE = (
    "El alcance cambió desde la vista previa. Volvé a consultar antes de confirmar."
)
MSG_SIN_FINGERPRINT = "Debe consultar el alcance antes de confirmar la vinculación."
MSG_CONFIRMAR = "Debe confirmar explícitamente la vinculación antes de guardar."


def resolver_contribuyente_destino(
    documento: str,
    origen: Contribuyente,
    *,
    for_update: bool = False,
) -> Contribuyente:
    """
    Encuentra el contribuyente destino por documento normalizado.

    Parámetros:
        documento: CUIT/DNI ingresado (se normaliza en el lookup).
        origen: contribuyente actual de la ficha.
        for_update: locking de lectura (apply, con GET_LOCK tomado).

    Retorno:
        Instancia activa distinta de ``origen``.

    Errores:
        400 SIN_DESTINO / MISMO_CONTRIBUYENTE / documento vacío.
        409 DOCUMENTO_AMBIGUO si hay más de un id activo.
    """
    doc = (documento or "").strip()
    if not doc:
        raise CorreccionEstablecimientoError("El documento del contribuyente destino es obligatorio.")
    if len(doc) > 11:
        raise CorreccionEstablecimientoError("El documento no puede superar 11 caracteres.")

    ids = contribuyente_ids_por_documento(doc, for_update=for_update)
    if not ids:
        raise CorreccionEstablecimientoError(MSG_SIN_DESTINO, codigo="SIN_DESTINO")
    unique = sorted(set(int(i) for i in ids))
    if len(unique) > 1:
        raise CorreccionEstablecimientoConflictError(MSG_DOC_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")

    dest_id = unique[0]
    if dest_id == int(origen.id):
        raise CorreccionEstablecimientoError(MSG_MISMO_CONTRIB, codigo="MISMO_CONTRIBUYENTE")

    dest = (
        Contribuyente.query.filter(
            Contribuyente.id == dest_id,
            Contribuyente.deleted_at.is_(None),
        ).first()
    )
    if dest is None:
        raise CorreccionEstablecimientoError(MSG_SIN_DESTINO, codigo="SIN_DESTINO")
    return dest


def eo_ids_contribuyente(contrib_id: int, *, exclude_eo_id: int | None = None) -> list[int]:
    """EO activos cuyo domicilio pertenece al contribuyente (otros locales)."""
    q = (
        db.session.query(EstablecimientoOperativo.id)
        .join(Domicilio, EstablecimientoOperativo.domicilio_id == Domicilio.id)
        .filter(
            Domicilio.contribuyente_id == int(contrib_id),
            Domicilio.deleted_at.is_(None),
        )
    )
    rows = q.all()
    ids = sorted({int(r[0]) for r in rows})
    if exclude_eo_id is not None:
        ids = [i for i in ids if i != int(exclude_eo_id)]
    return ids


def eo_canonico_destino_misma_direccion(
    dom: Domicilio,
    dest: Contribuyente,
    *,
    exclude_domicilio_ids: list[int],
) -> int | None:
    """
    Si el destino ya tiene un EO con la misma identidad lógica (calle+número),
    devuelve el id canónico (MIN) de esos EO. No modifica filas.

    Parámetros:
        dom: domicilio ancla de la ficha origen.
        dest: contribuyente destino.
        exclude_domicilio_ids: domicilios de la ficha origen (aún no reasignados).

    Retorno:
        EO id o None (situación A).
    """
    if not identidad_logica_completa(dom, dest):
        return None
    target = business_key_tuple(dom, dest)
    excl = {int(i) for i in exclude_domicilio_ids}
    candidatos = Domicilio.query.filter(
        Domicilio.deleted_at.is_(None),
        Domicilio.contribuyente_id == int(dest.id),
        ~Domicilio.id.in_(excl) if excl else True,
    ).all()
    matching_ids = [
        int(d.id) for d in candidatos if business_key_tuple(d, dest) == target
    ]
    if not matching_ids:
        return None
    rows = (
        EstablecimientoOperativo.query.filter(
            EstablecimientoOperativo.domicilio_id.in_(matching_ids)
        )
        .with_entities(EstablecimientoOperativo.id)
        .all()
    )
    eo_ids = [int(r[0]) for r in rows]
    return min(eo_ids) if eo_ids else None


def lookalike_ids_destino(
    dom: Domicilio,
    dest: Contribuyente,
    *,
    exclude_domicilio_ids: list[int],
) -> list[int]:
    """
    Domicilios del destino con la misma calle/número en texto, fuera de la identidad lógica.

    Parámetros:
        dom: domicilio ancla de la ficha origen.
        dest: contribuyente destino.
        exclude_domicilio_ids: domicilios de la ficha origen.

    Retorno:
        Ids ambiguos (vacío si la coincidencia es identidad completa / situación B).
    """
    calle_k = slug_key(dom.calle or "")
    num_k = slug_key(str(dom.numero or ""))
    if not calle_k or not num_k:
        return []
    excl = {int(i) for i in exclude_domicilio_ids} | {int(dom.id)}
    target = business_key_tuple(dom, dest)
    rows = Domicilio.query.filter(
        Domicilio.deleted_at.is_(None),
        Domicilio.contribuyente_id == int(dest.id),
    ).all()
    out: list[int] = []
    for other in rows:
        if int(other.id) in excl:
            continue
        if business_key_tuple(other, dest) == target:
            continue
        if slug_key(other.calle or "") == calle_k and slug_key(str(other.numero or "")) == num_k:
            out.append(int(other.id))
    return sorted(set(out))
