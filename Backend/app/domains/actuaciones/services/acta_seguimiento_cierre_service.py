from __future__ import annotations

import re
from datetime import date

from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import ContrapBucket
from app.domains.actuaciones.utils.acta_seguimiento_policy import (
    contexto_solicitud_carnet_relevamiento,
    contexto_subsanacion_reinspeccion_notificacion,
    labra_acta_inspeccion_en_cierre,
)
from app.models import Actuaciones, IniciadorRuta, Inspeccion, NotificacionResultadoReinspeccion
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador

_TELEFONO_MAX_LEN = 32
_TELEFONO_ALLOWED_RE = re.compile(r"^[\d\s+\-()./]+$")


def _field_error(loc: tuple[str, ...], message: str) -> None:
    raise ValidationError.from_exception_data(
        "CompletarTrabajoCierreCompletoIn",
        [
            {
                "type": "value_error",
                "loc": loc,
                "msg": "Value error",
                "input": None,
                "ctx": {"error": message},
            }
        ],
    )


def normalizar_telefono_solicitud_carnet(raw: str | None) -> str | None:
    """
    Trim y valida longitud/formato humano del teléfono de solicitud de carnet.

    Retorno:
        Teléfono normalizado o None si vacío.

    Errores:
        ValidationError: formato o longitud inválidos.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) > _TELEFONO_MAX_LEN:
        _field_error(
            ("telefono_contacto_solicitud_carnet",),
            f"El teléfono no puede superar {_TELEFONO_MAX_LEN} caracteres.",
        )
    if not _TELEFONO_ALLOWED_RE.match(s):
        _field_error(
            ("telefono_contacto_solicitud_carnet",),
            "El teléfono contiene caracteres no permitidos.",
        )
    return s


def validar_payload_acta_seguimiento_cierre(
    *,
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
    bucket: ContrapBucket,
) -> None:
    """
    Valida campos de seguimiento de acta según tipo de iniciador (antes de persistir actuación).

    Parámetros:
        ini: iniciador del ítem de ruta.
        payload: body de cierre Completar trabajo.
        bucket: contraproducencia normalizada.

    Errores:
        ValidationError (422): campos fuera de contexto o reglas de obligatoriedad.
    """
    labra = labra_acta_inspeccion_en_cierre(payload.acta_inspeccion_num)
    ctx_carnet = contexto_solicitud_carnet_relevamiento(ini, bucket=bucket, labra_inspeccion=labra)
    ctx_subs = contexto_subsanacion_reinspeccion_notificacion(
        ini, bucket=bucket, labra_inspeccion=labra
    )

    envia_carnet = payload.solicita_carnet_manipulador is not None
    envia_tel = payload.telefono_contacto_solicitud_carnet is not None
    envia_subs = payload.faltas_notificacion_subsanadas is not None

    if (envia_carnet or envia_tel) and not ctx_carnet:
        _field_error(
            ("solicita_carnet_manipulador",),
            "La solicitud de carnet solo aplica a Relevamiento con acta de inspección.",
        )
    if envia_subs and not ctx_subs:
        _field_error(
            ("faltas_notificacion_subsanadas",),
            "La subsanación de notificación solo aplica a Reinspección por Notificación con acta de inspección.",
        )

    if ctx_carnet:
        if payload.solicita_carnet_manipulador is None:
            _field_error(
                ("solicita_carnet_manipulador",),
                "Indicá si el personal solicita carnet de manipulador.",
            )
        if payload.solicita_carnet_manipulador is True:
            tel = normalizar_telefono_solicitud_carnet(payload.telefono_contacto_solicitud_carnet)
            if not tel:
                _field_error(
                    ("telefono_contacto_solicitud_carnet",),
                    "Si solicita carnet, el teléfono de contacto es obligatorio.",
                )
        elif payload.solicita_carnet_manipulador is False and envia_tel:
            tel_norm = normalizar_telefono_solicitud_carnet(payload.telefono_contacto_solicitud_carnet)
            if tel_norm:
                _field_error(
                    ("telefono_contacto_solicitud_carnet",),
                    "Si no solicita carnet, no envíe teléfono de contacto.",
                )

    if ctx_subs and payload.faltas_notificacion_subsanadas is None:
        _field_error(
            ("faltas_notificacion_subsanadas",),
            "Indicá si se subsanaron las faltas de la notificación de origen.",
        )


def persistir_acta_seguimiento_tras_cierre(
    *,
    act: Actuaciones,
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
    bucket: ContrapBucket,
    ejecutado_por_user_id: int,
) -> None:
    """
    Crea registros de seguimiento (carnet / subsanación) tras aplicar actas en la misma transacción.

    Parámetros:
        act: actuación cerrada (con inspección si correspondía).
        ini: iniciador origen.
        payload: body validado.
        bucket: visita realizada u otra.
        ejecutado_por_user_id: usuario de sesión.

    Errores:
        ValidationError: falta inspección, contribuyente o datos inconsistentes.
    """
    labra = labra_acta_inspeccion_en_cierre(payload.acta_inspeccion_num)
    ctx_carnet = contexto_solicitud_carnet_relevamiento(ini, bucket=bucket, labra_inspeccion=labra)
    ctx_subs = contexto_subsanacion_reinspeccion_notificacion(
        ini, bucket=bucket, labra_inspeccion=labra
    )
    if not ctx_carnet and not ctx_subs:
        return

    db.session.flush()
    inspeccion: Inspeccion | None = getattr(act, "inspeccion", None)
    if inspeccion is None and act.id:
        inspeccion = Inspeccion.query.filter(Inspeccion.actuacion_id == int(act.id)).first()
    if inspeccion is None:
        _field_error(
            ("acta_inspeccion_num",),
            "No se pudo vincular el seguimiento: falta acta de inspección persistida.",
        )

    fecha_ref: date = act.fecha if act.fecha else date.today()

    if ctx_carnet:
        assert payload.solicita_carnet_manipulador is not None
        dom = act.domicilio
        contrib_id = getattr(dom, "contribuyente_id", None) if dom else None
        if contrib_id is None:
            _field_error(
                ("doc_nro",),
                "Para registrar solicitud de carnet se requiere contribuyente en el domicilio de la actuación.",
            )
        tel: str | None = None
        if payload.solicita_carnet_manipulador:
            tel = normalizar_telefono_solicitud_carnet(payload.telefono_contacto_solicitud_carnet)
        row = SolicitudCarnetManipulador(
            contribuyente_id=int(contrib_id),
            inspeccion_id=int(inspeccion.id),
            solicita_carnet=bool(payload.solicita_carnet_manipulador),
            telefono_contacto=tel,
            fecha_solicitud=fecha_ref,
            created_by_user_id=int(ejecutado_por_user_id),
        )
        db.session.add(row)

    if ctx_subs:
        assert payload.faltas_notificacion_subsanadas is not None
        assert ini.notificacion_id is not None
        row_r = NotificacionResultadoReinspeccion(
            notificacion_id=int(ini.notificacion_id),
            actuacion_id=int(act.id),
            inspeccion_id=int(inspeccion.id),
            faltas_subsanadas=bool(payload.faltas_notificacion_subsanadas),
            fecha_verificacion=fecha_ref,
            created_by_user_id=int(ejecutado_por_user_id),
        )
        db.session.add(row_r)
