import type { IRutaGrupoMin, IRutaItemMin } from "../../../api/rutasTrabajoApi";

/** Mínimo de inspectores por grupo exigido por el backend al publicar. */
export const MIN_INSPECTORES_POR_GRUPO_PUBLICAR = 2;

export type RutaPublicarReadiness = {
  puedePublicar: boolean;
  blockers: string[];
};

/**
 * Evalúa en cliente las mismas condiciones principales que `publicar_ruta_trabajo`
 * (inspectores, ítems activos, OT guardada) para anticipar el 409 y mostrar mensajes claros.
 */
export function evaluarPublicacionRuta(
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): RutaPublicarReadiness {
  const blockers: string[] = [];

  if (grupos.length === 0) {
    blockers.push("La ruta no tiene grupos activos. Creá al menos un grupo en Asignación.");
  }

  for (const grupo of grupos) {
    const nInsp = grupo.inspectores?.length ?? 0;
    if (nInsp < MIN_INSPECTORES_POR_GRUPO_PUBLICAR) {
      blockers.push(
        `El grupo «${grupo.nombre}» necesita al menos ${MIN_INSPECTORES_POR_GRUPO_PUBLICAR} inspectores (tiene ${nInsp}).`
      );
    }
    const itemsGrupo = itemsActivos.filter((it) => it.ruta_grupo_id === grupo.id);
    if (itemsGrupo.length === 0) {
      blockers.push(`El grupo «${grupo.nombre}» no tiene trabajos asignados.`);
    }
  }

  if (itemsActivos.length === 0) {
    blockers.push("No hay trabajos activos en la ruta. Asigná iniciadores desde el pool.");
  }

  for (const item of itemsActivos) {
    if (item.orden_trabajo_id == null) {
      const dom = (item.domicilio_texto ?? "").trim() || `ítem #${item.id}`;
      blockers.push(`Falta guardar la OT de ${dom} (Asignación → «Guardar OT»).`);
    } else if (item.estado_ruta_item != null && item.estado_ruta_item !== "ASIGNADO") {
      blockers.push(
        `El ítem #${item.id} no está listo para publicar (estado: ${item.estado_ruta_item}).`
      );
    }
  }

  return { puedePublicar: blockers.length === 0, blockers };
}

/** Texto corto para tooltip del botón Publicar. */
export function resumenBloqueoPublicacion(blockers: string[]): string {
  if (blockers.length === 0) {
    return "Publica la ruta. Luego podrás descargar el resumen y las órdenes en PDF.";
  }
  if (blockers.length === 1) return blockers[0];
  return `${blockers[0]} (+${blockers.length - 1} condición${blockers.length > 2 ? "es" : ""} más)`;
}
