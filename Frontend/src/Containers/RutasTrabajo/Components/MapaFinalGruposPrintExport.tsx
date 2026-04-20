/**
 * MF7 — Exportación imprimible de grupos y direcciones (HTML + diálogo de impresión del navegador).
 *
 * La lógica vive en `utils/exportMapaFinalGruposPrint.ts` para no acoplar a React ni al layout del dashboard.
 */
export {
  buildMapaFinalGruposPrintDocumentTitle,
  buildMapaFinalGruposPrintHtml,
  printMapaFinalGruposOperativo,
} from "../utils/exportMapaFinalGruposPrint";
export type { MapaFinalGruposPrintPayload } from "../utils/exportMapaFinalGruposPrint";
