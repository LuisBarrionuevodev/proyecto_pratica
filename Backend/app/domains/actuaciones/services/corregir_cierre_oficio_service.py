"""
Corrección de cierre operativo de reinspección por oficio desde Actuaciones (GESTIÓN-FIX.2C).

Orquesta Actuaciones, RutaItem e IniciadorRuta con paridad a Completar Trabajo.
"""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    es_flujo_cumplimiento_oficio,
    es_flujo_verificar_informar,
    validar_tipo_actuacion_para_iniciador,
)
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
    _aplicar_reencolado_iniciador,
    _reencolar_iniciador_si_oficio_no_cumple,
)
from app.domains.actuaciones.services.actuacion_corregir_cierre_operativo_service import (
    aplicar_sincronizacion_tras_limpiar_contraproducencia,
)
from app.domains.actuaciones.utils.contraproducencia_por_tipo_iniciador import (
    contraproducencia_permitida_en_completar_trabajo,
)
from app.models import Actuaciones, IniciadorRuta, RutaItem


def _normalizar_tipo_actuacion(s: str | None) -> str:
    return " ".join((s or "").strip().upper().replace("_", " ").split())


def _assert_subtipo_sin_cambio(act: Actuaciones, tipo_enviado: str) -> None:
    actual = _normalizar_tipo_actuacion(getattr(act, "tipo", None))
    enviado = _normalizar_tipo_actuacion(tipo_enviado)
    if actual != enviado:
        raise ValueError(
            "No se permite cambiar el subtipo de la actuación desde esta corrección. "
            f"Subtipo actual: {act.tipo!r}; recibido: {tipo_enviado!r}."
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
    _reencolar_iniciador_si_oficio_no_cumple(ini=ini, act=act, item=item, now=now)


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
    _aplicar_reencolado_iniciador(ini, now, act=act, cerrado_motivo=None)


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


def _corregir_verificar_informar(
    *,
    act: Actuaciones,
    item: RutaItem,
    ini: IniciadorRuta,
    payload: CorregirCierreOficioIn,
) -> None:
    """
    Corrige ``realizo_nueva_inspeccion`` en verificar e informar.

    Errores:
        ValueError: valor faltante, actas incompatibles o resultado de cumplimiento enviado.
    """
    if payload.resultado_cumplimiento_oficio is not None:
        raise ValueError("El resultado de cumplimiento no aplica a verificar e informar.")

    nuevo = payload.realizo_nueva_inspeccion
    if nuevo is None and act.realizo_nueva_inspeccion is None:
        raise ValueError("Nueva inspección: indique si realizó una nueva inspección.")

    if nuevo is None:
        return

    if nuevo is False and actuacion_tiene_actas_inspeccion_normal(act):
        raise ValueError(MSG_SI_A_NO_CON_ACTAS)

    act.realizo_nueva_inspeccion = nuevo

    contra_raw = (payload.contraproducencia or "").strip()
    if contra_raw:
        stored_contra, bucket = normalize_contraproducencia(contra_raw)
        if bucket != ContrapBucket.NONE and stored_contra:
            if not contraproducencia_permitida_en_completar_trabajo(
                ini.tipo_iniciador,
                stored_contra,
                tipo_actuacion=payload.tipo_actuacion,
            ):
                raise ValueError("La contraproducencia no aplica al tipo de actuación elegido.")
            act.contraproducencia = stored_contra
        else:
            act.contraproducencia = None
    elif nuevo is False:
        act.contraproducencia = None


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
    _assert_subtipo_sin_cambio(act, payload.tipo_actuacion)
    validar_tipo_actuacion_para_iniciador(
        tipo_iniciador=ini.tipo_iniciador,
        tipo_actuacion=payload.tipo_actuacion,
    )

    now = datetime.utcnow()
    tipo_ini = ini.tipo_iniciador

    if es_flujo_verificar_informar(tipo_ini, payload.tipo_actuacion):
        _corregir_verificar_informar(act=act, item=item, ini=ini, payload=payload)
    elif es_flujo_cumplimiento_oficio(tipo_ini) or _normalizar_tipo_actuacion(
        payload.tipo_actuacion
    ).startswith("RATIFICACION"):
        _corregir_ratificacion(act=act, item=item, ini=ini, payload=payload, now=now)
    else:
        raise ValueError("El subtipo de actuación no admite corrección de cierre por oficio.")

    ini.updated_at = now
    db.session.add(act)
    db.session.add(item)
    db.session.add(ini)
    db.session.commit()
    return act
