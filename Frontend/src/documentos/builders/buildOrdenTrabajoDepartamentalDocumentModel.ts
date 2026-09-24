import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import type {
  OrdenTrabajoDepartamentalDocumentModel,
  OrdenTrabajoDepartamentalFila,
} from "../types/ordenTrabajoDepartamentalDocument";
import { buildDomicilioOrdenTrabajoDepartamental } from "../utils/domicilioOrdenTrabajoDepartamental";
import { fechaOrdenSalidaLegible } from "../utils/fechaOrdenSalida";

function turnoLegible(turno: string): string {
  return turno === "MANIANA" ? "Mañana" : turno === "TARDE" ? "Tarde" : turno;
}

function numeroOtDesdeItem(item: IRutaItemMin): string | null {
  const num = (item.orden_trabajo?.numero_acta ?? "").trim();
  return num || null;
}

/** Ítems activos de ruta sin número de OT asignado (omitidos en el PDF departamental). */
export function listRutaItemsSinOtAsignada(
  itemsActivos: IRutaItemMin[]
): Array<{ itemId: number; domicilioTexto: string }> {
  return itemsActivos
    .filter((it) => !it.deleted_at && !numeroOtDesdeItem(it))
    .sort((a, b) => a.id - b.id)
    .map((it) => ({
      itemId: it.id,
      domicilioTexto: (it.domicilio_texto ?? "").trim() || "—",
    }));
}

/**
 * Arma el modelo PDF de Órdenes de Trabajo Departamentales (una por ítem con OT asignada).
 */
export function buildOrdenTrabajoDepartamentalDocumentModel(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): OrdenTrabajoDepartamentalDocumentModel {
  const fechaLegible = fechaOrdenSalidaLegible(ruta.fecha);
  const turno = turnoLegible(ruta.turno);
  const grupoById = new Map(grupos.map((g) => [g.id, g]));

  const ordenes: OrdenTrabajoDepartamentalFila[] = itemsActivos
    .filter((it) => !it.deleted_at && numeroOtDesdeItem(it))
    .sort((a, b) => a.id - b.id)
    .map((it) => {
      const grupo = grupoById.get(it.ruta_grupo_id);
      const inspectoresTexto =
        (grupo?.inspectores ?? [])
          .map((row) => (row.inspector_nombre ?? "").trim())
          .filter(Boolean)
          .join(", ") || "—";

      return {
        itemId: it.id,
        numeroOt: numeroOtDesdeItem(it)!,
        domicilioLinea: buildDomicilioOrdenTrabajoDepartamental(
          (it.domicilio_texto ?? "").trim() || "—",
          it.angulo_esquina
        ),
        inspectoresTexto,
        fechaLegible,
        turnoLegible: turno,
      };
    });

  return {
    rutaId: ruta.id,
    numeroRuta: ruta.numero,
    fechaLegible,
    turnoLegible: turno,
    ordenes,
  };
}
