import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllActuacionesForExport,
  type ActuacionesExportFilters,
} from "../../../api/actuacionesExportApi";
import { downloadActuacionesListadoPdf } from "../../../documentos/actuaciones/downloadActuacionesListadoPdf";
import { downloadActuacionesExcel } from "./downloadActuacionesExcel";

export type ExportActuacionesOptions = {
  format: ExportFormat;
  filters: ActuacionesExportFilters;
  onProgress?: (loaded: number, total: number) => void;
};

function buildFiltrosResumen(filters: ActuacionesExportFilters): string[] {
  const out: string[] = [];
  if (filters.q) out.push(`Búsqueda: ${filters.q}`);
  if (filters.tipo) out.push(`Tipo: ${filters.tipo}`);
  if (filters.contraproducencia) out.push(`Contraproducencia: ${filters.contraproducencia}`);
  if (filters.orden_trabajo) out.push(`OT: ${filters.orden_trabajo}`);
  return out;
}

/**
 * Exporta actuaciones del rango indicado (fetch paginado completo + Excel/PDF).
 * No usa filas visibles ni paginación de la grilla.
 */
export async function exportActuacionesDataset(options: ExportActuacionesOptions): Promise<void> {
  const { filters } = options;

  const items = await fetchAllActuacionesForExport(filters, (p) =>
    options.onProgress?.(p.loaded, p.total)
  );

  if (items.length === 0) {
    throw new Error("No hay actuaciones para exportar con el rango y filtros seleccionados.");
  }

  const range = { desde: filters.desde ?? "", hasta: filters.hasta ?? "" };

  if (options.format === "excel") {
    downloadActuacionesExcel(items, range);
    return;
  }

  await downloadActuacionesListadoPdf({
    items,
    desde: range.desde,
    hasta: range.hasta,
    filtrosResumen: buildFiltrosResumen(filters),
  });
}
