"""
Política edit-in-place vs nuevo vínculo para domicilios (STAB-7).
"""

from __future__ import annotations

from typing import Any

from app.database import db
from app.models import Domicilio, IniciadorRuta
from app.domains.domicilios.schemas.domicilio_edit_policy import EditDomicilioPolicy
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    iniciador_en_ruta_publicada_o_en_curso,
)

_CAMPOS_GEO = frozenset(
    {
        "calle",
        "numero",
        "barrio_id",
        "numero_tipo",
        "esquina_normalizada",
        "esquina_raw",
        "esquina_catalogo_id",
    }
)

_MODOS_EXPLICITOS_NUEVO = frozenset({"NUEVO", "CREAR_NUEVO", "CAMBIAR_DOMICILIO"})
_MODOS_EXPLICITOS_REASIGNAR = frozenset({"REASIGNAR", "REASIGNAR_EXISTENTE", "VINCULAR_EXISTENTE"})


def _norm_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _norm_numero_tipo(v: Any) -> str | None:
    s = _norm_str(v)
    return s.upper() if s else None


def domicilio_payload_cambia_texto_geografico(
    dom: Domicilio | None,
    cambios: dict[str, Any] | None,
) -> bool:
    """
    True si el payload trae calle/número/tipo distinto al domicilio persistido.

    Usado para evitar normalización/geocode en updates documentales que reenvían
    la misma dirección (p. ej. PUT Actuaciones al cargar actas).
    """
    c = dict(cambios or {})
    if dom is None:
        return bool(_norm_str(c.get("calle")) and _norm_str(c.get("numero")))
    for field, normalizer in (
        ("calle", _norm_str),
        ("numero", _norm_str),
        ("numero_tipo", _norm_numero_tipo),
    ):
        if field not in c:
            continue
        new_v = normalizer(c.get(field))
        old_raw = getattr(dom, field, None)
        old_v = normalizer(old_raw) if field == "numero_tipo" else _norm_str(old_raw)
        if new_v is not None and new_v != (old_v or ""):
            return True
    return False


def _valor_campo_geo_en_domicilio(dom: Domicilio, campo: str) -> Any:
    if campo == "esquina_normalizada":
        return dom.esquina_normalizada or dom.esquina_raw
    return getattr(dom, campo, None)


def _cambios_afectan_geocode(
    cambios: dict[str, Any],
    dom_actual: Domicilio | None = None,
) -> bool:
    """
    True si algún campo geográfico del payload difiere del domicilio actual.

    Si no hay domicilio actual, cualquier campo geo presente implica refresh.
    """
    for k in _CAMPOS_GEO:
        if k not in cambios or cambios[k] is None:
            continue
        if dom_actual is None:
            return True
        if k == "barrio_id":
            if cambios[k] != dom_actual.barrio_id:
                return True
            continue
        if k == "numero_tipo":
            nuevo = _norm_numero_tipo(cambios[k])
            actual = _norm_numero_tipo(dom_actual.numero_tipo)
            if nuevo != actual:
                return True
            continue
        nuevo = _norm_str(cambios[k])
        actual = _norm_str(_valor_campo_geo_en_domicilio(dom_actual, k))
        if nuevo != actual:
            return True
    return False


def _iniciadores_vinculados(contexto: str, origen_id: int) -> list[IniciadorRuta]:
    tipo = (contexto or "").strip().upper()
    q = IniciadorRuta.query.filter(IniciadorRuta.deleted_at.is_(None))
    if tipo in ("ACTUACION", "COMPLETAR_TRABAJO"):
        return q.filter(IniciadorRuta.actuacion_id == origen_id).all()
    if tipo == "RELEVAMIENTO":
        return q.filter(IniciadorRuta.relevamiento_id == origen_id).all()
    if tipo == "DENUNCIA":
        return q.filter(IniciadorRuta.denuncia_id == origen_id).all()
    return []


def _bloquea_cambio_vinculo(contexto: str, origen_id: int) -> tuple[bool, str]:
    """Bloquea cambio de ``domicilio_id`` si hay iniciador en ruta publicada/en curso."""
    iniciadores = _iniciadores_vinculados(contexto, origen_id)
    for ini in iniciadores:
        if iniciador_en_ruta_publicada_o_en_curso(int(ini.id)):
            return True, (
                "No se puede cambiar el vínculo de domicilio: el iniciador está en una ruta "
                "PUBLICADA, EN_CURSO o CERRADA. Corregí la dirección sobre el mismo domicilio."
            )
    return False, ""


def resolver_policy_edicion_domicilio(
    *,
    domicilio_id: int | None,
    contexto: str,
    origen_id: int,
    cambios: dict[str, Any] | None,
    modo_explicito: str | None = None,
    relevamiento_id: int | None = None,
) -> EditDomicilioPolicy:
    """
    Resuelve si una edición debe mutar la misma fila, reasignar o crear nuevo domicilio.

    Parámetros:
        domicilio_id: domicilio actual del origen (actuación, relevamiento, etc.).
        contexto: ACTUACION | RELEVAMIENTO | DENUNCIA | COMPLETAR_TRABAJO.
        origen_id: id del registro origen.
        cambios: dict con calle, numero, barrio_id, etc.
        modo_explicito: NUEVO | REASIGNAR si el frontend lo envía.
        relevamiento_id: si el origen proviene de relevamiento, fuerza copy-on-write ante cambio geo.

    Retorno:
        ``EditDomicilioPolicy`` con modo y flags.

    Errores:
        ValueError si modo BLOQUEAR (mensaje en policy, el caller puede lanzar).
    """
    cambios = dict(cambios or {})
    modo_exp = (modo_explicito or "").strip().upper()
    dom_actual = None
    if domicilio_id is not None:
        dom_actual = db.session.get(Domicilio, int(domicilio_id))
        if dom_actual is not None and dom_actual.deleted_at is not None:
            dom_actual = None
    afecta_geo = _cambios_afectan_geocode(cambios, dom_actual)

    calle_nueva = _norm_str(cambios.get("calle"))
    numero_nuevo = _norm_str(cambios.get("numero"))

    if modo_exp in _MODOS_EXPLICITOS_NUEVO:
        bloqueado, motivo = _bloquea_cambio_vinculo(contexto, origen_id)
        if bloqueado:
            return EditDomicilioPolicy(modo="BLOQUEAR", motivo=motivo)
        return EditDomicilioPolicy(
            modo="CREAR_NUEVO",
            motivo="modo_explicito_nuevo",
            propagar_a_iniciadores=True,
            requiere_geocode_refresh=afecta_geo,
        )

    if modo_exp in _MODOS_EXPLICITOS_REASIGNAR:
        bloqueado, motivo = _bloquea_cambio_vinculo(contexto, origen_id)
        if bloqueado:
            return EditDomicilioPolicy(modo="BLOQUEAR", motivo=motivo)
        return EditDomicilioPolicy(
            modo="REASIGNAR_EXISTENTE",
            motivo="modo_explicito_reasignar",
            propagar_a_iniciadores=True,
            requiere_geocode_refresh=afecta_geo,
        )

    if domicilio_id is None:
        return EditDomicilioPolicy(
            modo="CREAR_NUEVO",
            motivo="sin_domicilio_previo",
            propagar_a_iniciadores=True,
            requiere_geocode_refresh=afecta_geo,
        )

    dom_actual = db.session.get(Domicilio, int(domicilio_id))
    if dom_actual is None or dom_actual.deleted_at is not None:
        return EditDomicilioPolicy(
            modo="CREAR_NUEVO",
            motivo="domicilio_previo_invalido",
            propagar_a_iniciadores=True,
            requiere_geocode_refresh=afecta_geo,
        )

    calle_efectiva = calle_nueva if calle_nueva is not None else (dom_actual.calle or "").strip()
    numero_efectivo = numero_nuevo if numero_nuevo is not None else (dom_actual.numero or "").strip()

    if calle_efectiva and numero_efectivo:
        otro = (
            Domicilio.query.filter(
                Domicilio.calle == calle_efectiva,
                Domicilio.numero == numero_efectivo,
                Domicilio.deleted_at.is_(None),
                Domicilio.id != int(domicilio_id),
            )
            .limit(1)
            .first()
        )
        if otro is not None:
            bloqueado, motivo = _bloquea_cambio_vinculo(contexto, origen_id)
            if bloqueado:
                return EditDomicilioPolicy(modo="BLOQUEAR", motivo=motivo)
            return EditDomicilioPolicy(
                modo="REASIGNAR_EXISTENTE",
                motivo="domicilio_existente_misma_clave",
                propagar_a_iniciadores=True,
                requiere_geocode_refresh=afecta_geo,
                domicilio_id_objetivo=int(otro.id),
            )

    # Copy-on-write: relevamiento conserva domicilio histórico; la actuación recibe domicilio real nuevo.
    ctx = (contexto or "").strip().upper()
    if ctx in ("ACTUACION", "COMPLETAR_TRABAJO") and relevamiento_id:
        if domicilio_payload_cambia_texto_geografico(dom_actual, cambios):
            return EditDomicilioPolicy(
                modo="CREAR_NUEVO",
                motivo="copy_on_write_relevamiento",
                propagar_a_iniciadores=False,
                requiere_geocode_refresh=False,
            )

    # Corrección operativa por defecto: misma fila (sin invalidar geocode en canales documentales).
    requiere_geo = False if ctx in ("ACTUACION", "COMPLETAR_TRABAJO") else afecta_geo
    return EditDomicilioPolicy(
        modo="EDITAR_MISMA_FILA",
        motivo="correccion_operativa_misma_fila",
        propagar_a_iniciadores=False,
        requiere_geocode_refresh=requiere_geo,
        domicilio_id_objetivo=int(domicilio_id),
    )
