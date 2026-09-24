/**
 * MF7 — Exportación imprimible de grupos y direcciones (HTML + diálogo de impresión del navegador).
 *
 * La lógica vive en `utils/exportMapaFinalGruposPrint.ts` (iframe oculto + print; sin `window.open`).
 */
export {
  buildMapaFinalGruposPrintDocumentTitle,
  buildMapaFinalGruposPrintHtml,
  printMapaFinalGruposOperativo,
} from "../utils/exportMapaFinalGruposPrint";
export type { MapaFinalGruposPrintPayload } from "../utils/exportMapaFinalGruposPrint";
