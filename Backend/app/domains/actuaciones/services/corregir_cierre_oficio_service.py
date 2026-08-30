"""
Corrección de cierre operativo de reinspección por oficio desde Actuaciones (GESTIÓN-FIX.2C).

Orquesta Actuaciones, RutaItem e IniciadorRuta con paridad a Completar Trabajo.
"""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    es_subtipo_ratificacion_oficio,
    es_subtipo_verificar_informar,
    sincronizar_tipo_iniciador_con_tipo_actuacion_oficio,
)
from app.domains.actuaciones.schemas.list_filters import _coerce_catalog_value
from app.domains.actuaciones.services.oficio_circuito_service import (
    MSG_SI_A_NO_CON_ACTAS,
    actuacion_tiene_actas_inspeccion_normal,
    resolver_item_iniciador_por_actuacion,
)
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    ContrapBucket,
    motivo_no_realizado_para_ruta_item,
    normalize_contraproducencia,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    reencolar_iniciador_si_oficio_no_cumple,
)
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    aplicar_reencolado_iniciador,
    aplicar_sincronizacion_tras_establecer_contraproducencia,
)
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import (
    quitar_actas_de_actuacion_en_sesion,
)
from app.domains.actuaciones.services.actuacion_corregir_cierre_operativo_service import (
    aplicar_sincronizacion_tras_limpiar_contraproducencia,
)
from app.domains.actuaciones.utils.contraproducencia_por_tipo_iniciador import (
    contraproducencia_permitida_en_completar_trabajo,
)
from app.models import Actuaciones, CatalogTipoActuacion, IniciadorRuta, RutaItem


def _normalizar_tipo_actuacion(s: str | None) -> str:
    return " ".join((s or "").strip().upper().replace("_", " ").split())


MSG_CAMBIO_SUBTIPO_CON_ACTAS = (
    "Para cambiar el tipo de actuación, primero debe quitar las actas incompatibles "
    "con el nuevo resultado."
)


def _validar_subtipo_oficio_destino(tipo_actuacion: str) -> str:
    """
    Valida que el subtipo destino sea uno de los tres permitidos para oficio.

    Errores:
        ValueError: subtipo vacío o no reconocido.
    """
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        es_subtipo_actuacion_oficio,
    )

    tipo = (tipo_actuacion or "").strip()
    if not tipo or not es_subtipo_actuacion_oficio(tipo):
        raise ValueError(
            "El tipo de actuación debe ser Ratificación de clausura, "
            "Ratificación de decomiso o Verificar e informar."
        )
    return tipo


def _limpiar_residuos_subtipo_anterior(act: Actuaciones, *, subtipo_destino: str) -> None:
    """
    Limpia campos operativos exclusivos del subtipo anterior antes de aplicar el destino.

    Parámetros:
        act: actuación en sesión.
        subtipo_destino: subtipo elegido en la corrección.
    """
    if es_subtipo_verificar_informar(subtipo_destino):
        act.resultado_cumplimiento_oficio = None
    if es_subtipo_ratificacion_oficio(subtipo_destino):
        act.realizo_nueva_inspeccion = None


def _validar_actas_compatibles_subtipo_destino(
    act: Actuaciones,
    *,
    subtipo_destino: str,
    payload: CorregirCierreOficioIn,
) -> None:
    """
    Rechaza cambio de subtipo si quedan actas incompatibles con el destino.

    Errores:
        ValueError: actas de inspección normal presentes hacia ratificación o Verificar sin Sí.
    """
    if not actuacion_tiene_actas_inspeccion_normal(act):
        return
    if es_subtipo_ratificacion_oficio(subtipo_destino):
        raise ValueError(MSG_CAMBIO_SUBTIPO_CON_ACTAS)
    if es_subtipo_verificar_informar(subtipo_destino):
        realizo = payload.realizo_nueva_inspeccion
        contra_set = "contraproducencia" in payload.model_fields_set
        contra = (payload.contraproducencia or "").strip() if contra_set else ""
        if realizo is not True and not contra:
            raise ValueError(MSG_CAMBIO_SUBTIPO_CON_ACTAS)


def _aplicar_tipo_actuacion_oficio(act: Actuaciones, tipo_destino: str) -> None:
    """Persiste ``act.tipo`` con valor de catálogo normalizado."""
    act.tipo = _coerce_catalog_value(
        tipo_destino,
        CatalogTipoActuacion,
        "tipo_actuacion",
        strip_prefix="TIPO.",
    )


def _aplicar_visita_realizada_ratificacion(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    now: datetime,
) -> None:
    """Marca visita realizada (CUMPLE) y desreencola iniciador si correspondía."""
    act.contraproducencia = None
    item.estado_ejecucion = "REALIZADO"
    item.estado_ruta_item = "FINALIZADO"
    item.motivo_no_realizado = None
    aplicar_sincronizacion_tras_limpiar_contraproducencia(act, item=item, ini=ini, now=now)


def _aplicar_no_cumple_sin_contra(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    now: datetime,
) -> None:
    """NO_CUMPLE sin contraproducencia: visita realizada + reencolado OFICIO_NO_CUMPLE."""
    act.contraproducencia = None
    act.resultado_cumplimiento_oficio = "NO_CUMPLE"
    act.realizo_nueva_inspeccion = None
    item.estado_ejecucion = "REALIZADO"
    item.estado_ruta_item = "FINALIZADO"
    item.motivo_no_realizado = None
    ini.estado_iniciador = "CUMPLIDO"
    ini.cerrado_at = None
    ini.cerrado_motivo = None
    reencolar_iniciador_si_oficio_no_cumple(ini=ini, act=act, item=item, now=now)


def _aplicar_contraproducencia_ratificacion(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    stored_contra: str,
    bucket: ContrapBucket,
    now: datetime,
) -> None:
    """NO_CUMPLE vía contraproducencia específica (visita no realizada operativa)."""
    act.contraproducencia = stored_contra
    act.resultado_cumplimiento_oficio = None
    act.realizo_nueva_inspeccion = None
    item.estado_ejecucion = "NO_REALIZADO"
    item.estado_ruta_item = "FINALIZADO"
    item.motivo_no_realizado = motivo_no_realizado_para_ruta_item(stored_contra, bucket)
    aplicar_reencolado_iniciador(ini, now, act=act, cerrado_motivo=None)


def _corregir_ratificacion(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    payload: CorregirCierreOficioIn,
    now: datetime,
) -> None:
    """
    Corrige cumplimiento/contraproducencia en ratificación clausura/decomiso.

    Errores:
        ValueError: combinación inválida o contraproducencia no permitida.
    """
    if payload.realizo_nueva_inspeccion is not None:
        raise ValueError("realizo_nueva_inspeccion no aplica a ratificación de oficio.")

    contra_raw = (payload.contraproducencia or "").strip()
    resultado = payload.resultado_cumplimiento_oficio

    if resultado == "CUMPLE":
        act.resultado_cumplimiento_oficio = "CUMPLE"
        act.realizo_nueva_inspeccion = None
        _aplicar_visita_realizada_ratificacion(act=act, item=item, ini=ini, now=now)
        return

    if contra_raw:
        stored_contra, bucket = normalize_contraproducencia(contra_raw)
        if bucket == ContrapBucket.NONE or not stored_contra:
            raise ValueError("Contraproducencia inválida para el subtipo de ratificación.")
        if not contraproducencia_permitida_en_completar_trabajo(
            ini.tipo_iniciador,
            stored_contra,
            tipo_actuacion=payload.tipo_actuacion,
        ):
            raise ValueError("La contraproducencia no aplica al tipo de actuación elegido.")
        _aplicar_contraproducencia_ratificacion(
            act=act,
            item=item,
            ini=ini,
            stored_contra=stored_contra,
            bucket=bucket,
            now=now,
        )
        return

    if resultado == "NO_CUMPLE":
        _aplicar_no_cumple_sin_contra(act=act, item=item, ini=ini, now=now)
        return

    raise ValueError("Resultado de cumplimiento: seleccione una opción.")


MSG_VERIFICAR_HIBRIDO = (
    "Resultado de Verificar e Informar: contraproducencia y nueva inspección "
    "no pueden informarse simultáneamente."
)
MSG_VERIFICAR_SI_A_CONTRA_CON_ACTAS = (
    "Para registrar una contraproducencia, primero debe quitar las actas labradas "
    "de la nueva inspección."
)
MSG_VERIFICAR_ESTADO_REQUERIDO = "Resultado de Verificar e Informar: seleccione una opción."


def _corregir_verificar_informar(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    payload: CorregirCierreOficioIn,
) -> None:
    """
    Corrige resultado operativo en verificar e informar (tres estados mutuamente excluyentes).

    Errores:
        ValueError: híbrido, actas incompatibles, contraproducencia inválida o estado faltante.
    """
    if payload.resultado_cumplimiento_oficio is not None:
        raise ValueError("El resultado de cumplimiento no aplica a verificar e informar.")

    contra_was_set = "contraproducencia" in payload.model_fields_set
    realizo_was_set = "realizo_nueva_inspeccion" in payload.model_fields_set

    contra_raw = (payload.contraproducencia or "").strip() if contra_was_set else ""
    nuevo = payload.realizo_nueva_inspeccion if realizo_was_set else None

    has_contra = bool(contra_raw)
    has_realizo_bool = realizo_was_set and nuevo is not None

    if has_contra and has_realizo_bool:
        raise ValueError(MSG_VERIFICAR_HIBRIDO)

    if has_contra:
        if actuacion_tiene_actas_inspeccion_normal(act):
            raise ValueError(MSG_VERIFICAR_SI_A_CONTRA_CON_ACTAS)
        stored_contra, bucket = normalize_contraproducencia(contra_raw)
        if bucket == ContrapBucket.NONE or not stored_contra:
            raise ValueError("Contraproducencia inválida para verificar e informar.")
        if not contraproducencia_permitida_en_completar_trabajo(
            ini.tipo_iniciador,
            stored_contra,
            tipo_actuacion=payload.tipo_actuacion,
        ):
            raise ValueError("La contraproducencia no aplica al tipo de actuación elegido.")
        act.contraproducencia = stored_contra
        act.realizo_nueva_inspeccion = None
        act.resultado_cumplimiento_oficio = None
        aplicar_sincronizacion_tras_establecer_contraproducencia(
            act,
            stored_contra=stored_contra,
            bucket=bucket,
            item=item,
            ini=ini,
            reencolar=ini.estado_iniciador != "PENDIENTE",
        )
        return

    if nuevo is False:
        if actuacion_tiene_actas_inspeccion_normal(act):
            raise ValueError(MSG_SI_A_NO_CON_ACTAS)
        act.realizo_nueva_inspeccion = False
        act.contraproducencia = None
        act.resultado_cumplimiento_oficio = None
        return

    if nuevo is True:
        act.realizo_nueva_inspeccion = True
        act.contraproducencia = None
        act.resultado_cumplimiento_oficio = None
        return

    raise ValueError(MSG_VERIFICAR_ESTADO_REQUERIDO)


def corregir_cierre_oficio(
    actuacion_id: int,
    payload: CorregirCierreOficioIn,
) -> Actuaciones:
    """
    Corrige el resultado operativo de una actuación de reinspección por oficio.

    Parámetros:
        actuacion_id: PK de la actuación.
        payload: datos de corrección validados.

    Retorno:
        Actuación actualizada (commit realizado).

    Errores:
        LookupError, ValueError: ver mensajes en helpers y validaciones.
    """
    act, item, ini = resolver_item_iniciador_por_actuacion(actuacion_id)
    tipo_destino = _validar_subtipo_oficio_destino(payload.tipo_actuacion)
    subtipo_anterior = getattr(act, "tipo", None)
    subtipo_cambio = _normalizar_tipo_actuacion(subtipo_anterior) != _normalizar_tipo_actuacion(
        tipo_destino
    )

    now = datetime.utcnow()

    try:
        if payload.actas_a_quitar:
            quitar_actas_de_actuacion_en_sesion(act, list(payload.actas_a_quitar))
            db.session.refresh(act)

        if subtipo_cambio:
            _validar_actas_compatibles_subtipo_destino(
                act, subtipo_destino=tipo_destino, payload=payload
            )
            _limpiar_residuos_subtipo_anterior(act, subtipo_destino=tipo_destino)
            _aplicar_tipo_actuacion_oficio(act, tipo_destino)
            sincronizar_tipo_iniciador_con_tipo_actuacion_oficio(ini, tipo_destino)

        if es_subtipo_verificar_informar(tipo_destino):
            _corregir_verificar_informar(act=act, item=item, ini=ini, payload=payload)
        elif es_subtipo_ratificacion_oficio(tipo_destino):
            _corregir_ratificacion(act=act, item=item, ini=ini, payload=payload, now=now)
        else:
            raise ValueError("El subtipo de actuación no admite corrección de cierre por oficio.")

        ini.updated_at = now
        db.session.add(act)
        db.session.add(item)
        db.session.add(ini)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    db.session.refresh(act)
    return act
