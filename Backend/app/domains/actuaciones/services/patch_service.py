from __future__ import annotations

from typing import Any, Dict

from app.models import Actuaciones
from app.domains.actuaciones.schemas.actuacion_patch_in import ActuacionPatchIn


def actualizar_actuacion_parcial(actuacion_id: int, patch: ActuacionPatchIn) -> Actuaciones:
    """
    Actualiza campos específicos de una actuación (PATCH).
    
    Args:
        actuacion_id: ID de la actuación
        patch: Objeto con solo los campos a actualizar
    
    Returns:
        Actuación actualizada
    
    Raises:
        ValueError: Si la actuación no existe
    """
    from app.database import db
    from app.models import Domicilio, Oficio, Expediente
    from app.domains.actuaciones.cleanup.garbage_collector import (
        soft_delete_contribuyente_if_orphan,
        soft_delete_domicilio_if_orphan,
        soft_delete_orden_id_orphan,
        soft_delete_notificacion_if_orphan,
        soft_delete_comprobacion_if_orphan,
        soft_delete_oficio_if_orphan,
        soft_delete_expediente_if_orphan,
    )
    import traceback
    
    try:
        print(f"\n[PATCH] Actualizando actuación {actuacion_id}")
        print(f"[PATCH] Patch recibido: {patch.model_dump(exclude_unset=True, exclude_none=True)}")
        
        act = Actuaciones.query.get(actuacion_id)
        if not act:
            raise ValueError(f"Actuación {actuacion_id} no encontrada")
        
        print(f"[PATCH] Actuación encontrada: ID={act.id}, OT actual={act.orden_trabajo_id}")

        # Snapshot pre-update para cleanup post-commit.
        old_domicilio_id = act.domicilio_id
        old_notificacion_id = act.notificacion_id
        old_comprobacion_id = act.comprobacion_id
        old_orden_trabajo_id = act.orden_trabajo_id
        old_contribuyente_id = None
        old_oficios_ids = []
        old_expedientes_ids = []
        if old_domicilio_id:
            dom = db.session.get(Domicilio, old_domicilio_id)
            if dom:
                old_contribuyente_id = dom.contribuyente_id
        if old_comprobacion_id:
            old_oficios_ids = [o.id for o in Oficio.query.filter_by(comprobacion_id=old_comprobacion_id).all()]
            old_expedientes_ids = [e.id for e in Expediente.query.filter_by(comprobacion_id=old_comprobacion_id).all()]
        
        # Actualizar solo los campos que vienen en el patch (no None)
        patch_dict = patch.model_dump(exclude_unset=True, exclude_none=True)
        
        # Mapeo directo de campos simples
        simple_fields = {
            "tipo_actuacion": "tipo",
            "contraproducencia": "contraproducencia",
        }
        
        for patch_key, model_attr in simple_fields.items():
            if patch_key in patch_dict:
                print(f"[PATCH] Actualizando {model_attr} = {patch_dict[patch_key]}")
                setattr(act, model_attr, patch_dict[patch_key])
        
        # Fecha (si viene, actualizar mes/año también)
        if "fecha_actuacion" in patch_dict:
            from app.utils.fechas import parse_fecha_grid
            print(f"[PATCH] Actualizando fecha: {patch_dict['fecha_actuacion']}")
            mes, anio, fecha = parse_fecha_grid(patch_dict["fecha_actuacion"])
            act.fecha = fecha
            act.mes = mes
            act.anio = anio
        
        # Orden de Trabajo (solo buscar existente, NO crear nueva)
        if "orden_trabajo_numero" in patch_dict:
            from app.models import OrdenTrabajo
            from app.utils.actas import acta_6
            
            print(f"[PATCH] Procesando cambio de OT: {patch_dict['orden_trabajo_numero']}")
            
            # Normalizar número de OT
            ot_numero_normalizado = acta_6(patch_dict["orden_trabajo_numero"])
            print(f"[PATCH] OT normalizada: {ot_numero_normalizado}")
            
            # Buscar OT existente (NO crear nueva)
            ot = OrdenTrabajo.query.filter_by(numero=ot_numero_normalizado).first()
            
            if not ot:
                raise ValueError(
                    f"Orden de Trabajo '{patch_dict['orden_trabajo_numero']}' "
                    f"(normalizado: '{ot_numero_normalizado}') no existe. "
                    f"No se pueden crear nuevas OTs al editar. "
                    f"Usa el grid de carga para crear actuaciones con nuevas OTs."
                )
            
            print(f"[PATCH] OT encontrada: ID={ot.id}")
            
            # Validar regla: 1 actuación por OT
            if ot.id != act.orden_trabajo_id:
                print(f"[PATCH] Cambiando OT de {act.orden_trabajo_id} a {ot.id}")
                # Verificar que no haya otra actuación con esa OT
                otra_act = Actuaciones.query.filter(
                    Actuaciones.orden_trabajo_id == ot.id,
                    Actuaciones.id != actuacion_id  # Excluir la actuación actual
                ).first()
                
                if otra_act:
                    raise ValueError(
                        f"Ya existe otra actuación (ID: {otra_act.id}) "
                        f"asociada a la OT '{ot_numero_normalizado}'. "
                        f"Cada OT solo puede tener una actuación."
                    )
                
                # Asignar nueva OT
                print(f"[PATCH] Asignando nueva OT")
                act.orden_trabajo_id = ot.id
            else:
                print(f"[PATCH] OT es la misma, no hay cambio")
        
        # Inspectores (si viene alguno, armar lista)
        inspectores = []
        for i in [1, 2, 3]:
            key = f"inspector{i}"
            if key in patch_dict and patch_dict[key]:
                inspectores.append(patch_dict[key])
        
        if inspectores:
            from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
            print(f"[PATCH] Actualizando inspectores: {inspectores}")
            act.inspector = get_inspectores_o_falla(inspectores)
        
        # Domicilio/Rubro (si viene alguno de calle/numero/rubro)
        if any(
            k in patch_dict
            for k in ["calle", "numero", "rubro_nombre", "doc_nro", "contrib_apellido", "contrib_nombre"]
        ):
            # Construir payload para domicilio
            from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
            from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
            from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
            from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
                normalizar_domicilio_en_sesion,
            )

            print(f"[PATCH] Actualizando domicilio/rubro")

            # Rubro
            rubro = None
            if "rubro_nombre" in patch_dict:
                rubro = get_rubro_o_falla(patch_dict["rubro_nombre"])
            elif act.domicilio and act.domicilio.rubro:
                rubro = act.domicilio.rubro

            # Contribuyente (misma convención que `resolve_contribuyente`: clave `doc_nro`)
            contrib_payload: dict[str, Any] = {}
            if "doc_nro" in patch_dict:
                contrib_payload["doc_nro"] = patch_dict["doc_nro"]
            if "contrib_apellido" in patch_dict:
                contrib_payload["apellido"] = patch_dict["contrib_apellido"]
            if "contrib_nombre" in patch_dict:
                contrib_payload["nombre"] = patch_dict["contrib_nombre"]

            contrib = None
            if contrib_payload:
                contrib = resolve_contribuyente(contrib_payload)
            elif act.domicilio and act.domicilio.contribuyente:
                contrib = act.domicilio.contribuyente

            # Domicilio
            dom_payload: dict[str, Any] = {}
            if "calle" in patch_dict:
                dom_payload["calle"] = patch_dict["calle"]
            elif act.domicilio:
                dom_payload["calle"] = act.domicilio.calle

            if "numero" in patch_dict:
                dom_payload["numero"] = patch_dict["numero"]
            elif act.domicilio:
                dom_payload["numero"] = act.domicilio.numero

            if dom_payload:
                # Permitir domicilio sin rubro/contribuyente si no hay tipo y sí contraproducencia
                allow_missing_catalogs = (
                    (patch_dict.get("tipo_actuacion", act.tipo) is None)
                    and (patch_dict.get("contraproducencia", act.contraproducencia) is not None)
                )
                dom = get_or_create_domicilio(
                    dom_payload,
                    contrib,
                    rubro,
                    allow_missing_catalogs=allow_missing_catalogs,
                )
                act.domicilio_id = dom.id if dom else None
                if dom:
                    normalizar_domicilio_en_sesion(
                        dom, override_numero_tipo=dom_payload.get("numero_tipo")
                    )
                act.domicilio = dom
        
        # Actas (actualizaciones simples)
        if "acta_inspeccion_num" in patch_dict:
            from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
            print(f"[PATCH] Actualizando acta inspección: {patch_dict['acta_inspeccion_num']}")
            attach_inspeccion(act, patch_dict["acta_inspeccion_num"], crear=False)
        
        if "acta_notificacion_num" in patch_dict:
            noti_payload = {"numero_acta": patch_dict["acta_notificacion_num"]}
            motivos = []
            for i in [1, 2, 3]:
                key = f"notificacion_motivo_{i}"
                if key in patch_dict and patch_dict[key]:
                    motivos.append(patch_dict[key])
            if motivos:
                noti_payload["motivos"] = motivos
            
            print(f"[PATCH] Actualizando notificación: {noti_payload}")
            from app.domains.actuaciones.attach.notificacion import attach_notificacion
            attach_notificacion(act, noti_payload)
        
        if "acta_comprobacion_num" in patch_dict:
            comp_payload = {"numero_acta": patch_dict["acta_comprobacion_num"]}
            if "comprobacion_motivo" in patch_dict:
                comp_payload["motivo"] = patch_dict["comprobacion_motivo"]
            
            print(f"[PATCH] Actualizando comprobación: {comp_payload}")
            from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
            attach_comprobacion(act, comp_payload)
        
        if "acta_clausura_num" in patch_dict:
            from app.domains.actuaciones.attach.clausura import attach_clausura
            print(f"[PATCH] Actualizando clausura: {patch_dict['acta_clausura_num']}")
            attach_clausura(act, patch_dict["acta_clausura_num"], crear=False)
        
        if "acta_decomiso_num" in patch_dict:
            dec_payload = {"numero_acta": patch_dict["acta_decomiso_num"]}
            if "decomiso_kilos_total" in patch_dict:
                dec_payload["cantidad"] = patch_dict["decomiso_kilos_total"]
            
            print(f"[PATCH] Actualizando decomiso: {dec_payload}")
            from app.domains.actuaciones.attach.decomiso import attach_decomiso
            attach_decomiso(act, dec_payload, crear=False)
        
        print(f"[PATCH] Commit a DB...")
        db.session.add(act)
        db.session.commit()

        # Garbage collector post-update para huérfanos
        ran_cleanup = False
        if old_domicilio_id and old_domicilio_id != act.domicilio_id:
            soft_delete_domicilio_if_orphan(old_domicilio_id)
            ran_cleanup = True
        if old_contribuyente_id:
            soft_delete_contribuyente_if_orphan(old_contribuyente_id)
            ran_cleanup = True
        if old_orden_trabajo_id and old_orden_trabajo_id != act.orden_trabajo_id:
            soft_delete_orden_id_orphan(old_orden_trabajo_id)
            ran_cleanup = True
        if old_notificacion_id and old_notificacion_id != act.notificacion_id:
            soft_delete_notificacion_if_orphan(old_notificacion_id)
            ran_cleanup = True
        if old_comprobacion_id and old_comprobacion_id != act.comprobacion_id:
            soft_delete_comprobacion_if_orphan(old_comprobacion_id)
            for oid in old_oficios_ids:
                soft_delete_oficio_if_orphan(oid)
            for eid in old_expedientes_ids:
                soft_delete_expediente_if_orphan(eid)
            ran_cleanup = True
        if ran_cleanup:
            db.session.commit()

        try:
            from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
                on_domicilio_changed,
            )

            if act.domicilio_id:
                on_domicilio_changed(act.domicilio_id)
        except Exception:
            pass

        print(f"[PATCH] Actualización exitosa!")
        return act
        
    except Exception as e:
        print(f"\n[PATCH ERROR] Error al actualizar actuación {actuacion_id}")
        print(f"[PATCH ERROR] Tipo: {type(e).__name__}")
        print(f"[PATCH ERROR] Mensaje: {str(e)}")
        print(f"[PATCH ERROR] Traceback:")
        traceback.print_exc()
        db.session.rollback()
        raise
