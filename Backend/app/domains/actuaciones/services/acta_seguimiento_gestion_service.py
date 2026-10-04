from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.database import db
from app.domains.actuaciones.services.acta_seguimiento_cierre_service import (
    _field_error,
    normalizar_telefono_solicitud_carnet,
)
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    resolve_iniciador_operativo_actuacion,
)
from app.domains.actuaciones.utils.acta_seguimiento_policy import (
    contexto_solicitud_carnet_gestion,
    contexto_subsanacion_gestion,
)
from app.models import Actuaciones, Inspeccion, Notificacion, NotificacionResultadoReinspeccion
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador

_SEGUIMIENTO_PAYLOAD_KEYS = frozenset(
    {
        "solicita_carnet_manipulador",
        "telefono_contacto_solicitud_carnet",
        "faltas_notificacion_subsanadas",
    }
)


def extraer_fragmento_seguimiento_gestion(payload: dict[str, Any]) -> dict[str, Any]:
    """Extrae y elimina del payload canónico las claves de seguimiento de acta."""
    out: dict[str, Any] = {}
    for key in _SEGUIMIENTO_PAYLOAD_KEYS:
        if key in payload:
            out[key] = payload.pop(key)
    return out


def validar_y_aplicar_seguimiento_gestion_put(
    act: Actuaciones,
    seguimiento: dict[str, Any],
    *,
    actor_user_id: int,
) -> None:
    """
    Valida y persiste seguimiento de acta desde PUT de Gestión de Actuaciones.

    Parámetros:
        act: actuación existente (con relaciones de inspección si están cargadas).
        seguimiento: subconjunto con claves de carnet/subsanación enviadas por el cliente.
        actor_user_id: usuario de sesión.

    Errores:
        ValidationError (422): campos fuera de contexto o reglas de obligatoriedad.
        ValueError: falta inspección o contribuyente al crear carnet.
    """
    if not seguimiento:
        return

    assert act.id is not None
    ini = resolve_iniciador_operativo_actuacion(int(act.id))
    ctx_carnet = contexto_solicitud_carnet_gestion(ini, act)
    ctx_subs = contexto_subsanacion_gestion(ini, act)

    envia_carnet = "solicita_carnet_manipulador" in seguimiento
    envia_tel = "telefono_contacto_solicitud_carnet" in seguimiento
    envia_subs = "faltas_notificacion_subsanadas" in seguimiento

    if (envia_carnet or envia_tel) and not ctx_carnet:
        _field_error(
            ("solicita_carnet_manipulador",),
            "La solicitud de carnet solo aplica a Relevamiento o Denuncia con acta de inspección.",
        )
    if envia_subs and not ctx_subs:
        _field_error(
            ("faltas_notificacion_subsanadas",),
            "La subsanación de notificación solo aplica a Reinspección por Notificación con acta de inspección.",
        )

    solicita = seguimiento.get("solicita_carnet_manipulador")
    telefono_raw = seguimiento.get("telefono_contacto_solicitud_carnet")
    subsanadas = seguimiento.get("faltas_notificacion_subsanadas")

    if ctx_carnet and (envia_carnet or envia_tel):
        if envia_carnet and solicita is None:
            _field_error(
                ("solicita_carnet_manipulador",),
                "Indicá si el personal solicita carnet de manipulador.",
            )
        if solicita is True:
            tel = normalizar_telefono_solicitud_carnet(telefono_raw)
            if not tel:
                _field_error(
                    ("telefono_contacto_solicitud_carnet",),
                    "Si solicita carnet, el teléfono de contacto es obligatorio.",
                )
        elif solicita is False:
            if envia_tel and telefono_raw is not None:
                tel_norm = normalizar_telefono_solicitud_carnet(telefono_raw)
                if tel_norm:
                    _field_error(
                        ("telefono_contacto_solicitud_carnet",),
                        "Si no solicita carnet, no envíe teléfono de contacto.",
                    )

    if ctx_carnet and envia_carnet:
        _upsert_solicitud_carnet_gestion(
            act,
            solicita=bool(solicita),
            telefono_raw=telefono_raw if solicita is True else None,
            actor_user_id=actor_user_id,
        )

    if ctx_subs and envia_subs:
        if subsanadas is None:
            _field_error(
                ("faltas_notificacion_subsanadas",),
                "Indicá si se subsanaron las faltas de la notificación de origen.",
            )
        assert ini is not None and ini.notificacion_id is not None
        _upsert_resultado_reinspeccion_gestion(
            act,
            notificacion_id=int(ini.notificacion_id),
            faltas_subsanadas=bool(subsanadas),
            actor_user_id=actor_user_id,
        )


def _resolve_inspeccion(act: Actuaciones) -> Inspeccion:
    insp: Inspeccion | None = getattr(act, "inspeccion", None)
    if insp is None and act.id:
        insp = Inspeccion.query.filter(Inspeccion.actuacion_id == int(act.id)).first()
    if insp is None:
        _field_error(
            ("acta_inspeccion_num",),
            "No se pudo vincular el seguimiento: falta acta de inspección persistida.",
        )
    return insp


def _upsert_solicitud_carnet_gestion(
    act: Actuaciones,
    *,
    solicita: bool,
    telefono_raw: str | None,
    actor_user_id: int,
) -> None:
    insp = _resolve_inspeccion(act)
    dom = act.domicilio
    contrib_id = getattr(dom, "contribuyente_id", None) if dom else None
    if contrib_id is None:
        _field_error(
            ("doc_nro",),
            "Para registrar solicitud de carnet se requiere contribuyente en el domicilio de la actuación.",
        )
    tel: str | None = None
    if solicita:
        tel = normalizar_telefono_solicitud_carnet(telefono_raw)

    existing = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=int(insp.id)).first()
    now = datetime.utcnow()
    fecha_ref: date = act.fecha if act.fecha else date.today()

    if existing is None:
        row = SolicitudCarnetManipulador(
            contribuyente_id=int(contrib_id),
            inspeccion_id=int(insp.id),
            solicita_carnet=bool(solicita),
            telefono_contacto=tel,
            fecha_solicitud=fecha_ref,
            created_by_user_id=int(actor_user_id),
            updated_at=None,
            updated_by_user_id=None,
        )
        db.session.add(row)
        return

    existing.solicita_carnet = bool(solicita)
    existing.telefono_contacto = tel
    existing.updated_at = now
    existing.updated_by_user_id = int(actor_user_id)
    db.session.add(existing)


def _upsert_resultado_reinspeccion_gestion(
    act: Actuaciones,
    *,
    notificacion_id: int,
    faltas_subsanadas: bool,
    actor_user_id: int,
) -> None:
    assert act.id is not None
    insp = _resolve_inspeccion(act)
    existing = NotificacionResultadoReinspeccion.query.filter_by(
        actuacion_id=int(act.id)
    ).first()
    now = datetime.utcnow()
    fecha_ref: date = act.fecha if act.fecha else date.today()

    if existing is None:
        row = NotificacionResultadoReinspeccion(
            notificacion_id=int(notificacion_id),
            actuacion_id=int(act.id),
            inspeccion_id=int(insp.id),
            faltas_subsanadas=bool(faltas_subsanadas),
            fecha_verificacion=fecha_ref,
            created_by_user_id=int(actor_user_id),
        )
        db.session.add(row)
        return

    existing.faltas_subsanadas = bool(faltas_subsanadas)
    existing.inspeccion_id = int(insp.id)
    existing.updated_at = now
    existing.updated_by_user_id = int(actor_user_id)
    db.session.add(existing)


def notificacion_origen_numero_desde_iniciador(
    ini: Any,
    batch_notificacion_by_id: dict[int, Notificacion] | None = None,
) -> str | None:
    """Número de acta de la notificación origen (iniciador REINSPECCION_NOTIFICACION)."""
    if ini is None or getattr(ini, "notificacion_id", None) is None:
        return None
    nid = int(ini.notificacion_id)
    noti: Notificacion | None = None
    if batch_notificacion_by_id is not None:
        noti = batch_notificacion_by_id.get(nid)
    if noti is None:
        noti = Notificacion.query.get(nid)
    if noti is None:
        return None
    num = getattr(noti, "numero_acta", None)
    return str(num).strip() if num else None
