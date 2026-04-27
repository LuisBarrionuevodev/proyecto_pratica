/**
 * Submódulo documental (PDFs e informes). Integración por dominio desde contenedores o hooks.
 */

export { buildRutaPublicadaDocumentModel } from "./builders/buildRutaPublicadaDocumentModel";
export { registerDocumentosPdfFonts } from "./core/registerPdfFonts";
export type { RutaPublicadaDocumentModel } from "./types/rutaPublicadaDocument";
export { downloadOrdenesSalidaPdf, downloadRutaResumenPdf } from "./rutas/downloadRutaPublicadaPdfs";
export {
  INSTITUTIONAL_CITY_LINE,
  INSTITUTIONAL_DIRECTION_LINE,
  INSTITUTIONAL_SECRETARY_LINE,
} from "./core/institutionalCopy";
