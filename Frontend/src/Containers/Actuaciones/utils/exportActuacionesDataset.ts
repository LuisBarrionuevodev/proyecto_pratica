import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllActuacionesForExport,
  type ActuacionesExportFilters,
} from "../../../api/actuacionesExportApi";
import { downloadActuacionesListadoPdf } from "../../../documentos/actuaciones/downloadActuacionesListadoPdf";
import { downloadActuacionesExcel } from "./downloadActuacionesExcel";

export type ExportActuacionesOptions = {
  format: ExportFormat;
  desde: string;
  hasta: string;
  tipo: string | null;
  contraproducencia: string | null;
  orden_trabajo: string | null;
  onProgress?: (loaded: number, total: number) => void;
};

function buildFiltrosResumen(filters: ActuacionesExportFilters): string[] {
  const out: string[] = [];
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
  const filters: ActuacionesExportFilters = {
    desde: options.desde,
    hasta: options.hasta,
    tipo: options.tipo,
    contraproducencia: options.contraproducencia,
    orden_trabajo: options.orden_trabajo,
  };

  const items = await fetchAllActuacionesForExport(filters, (p) =>
    options.onProgress?.(p.loaded, p.total)
  );

  if (items.length === 0) {
    throw new Error("No hay actuaciones para exportar con el rango y filtros seleccionados.");
  }

  const range = { desde: options.desde, hasta: options.hasta };

  if (options.format === "excel") {
    downloadActuacionesExcel(items, range);
    return;
  }

  await downloadActuacionesListadoPdf({
    items,
    desde: options.desde,
    hasta: options.hasta,
    filtrosResumen: buildFiltrosResumen(filters),
  });
}
