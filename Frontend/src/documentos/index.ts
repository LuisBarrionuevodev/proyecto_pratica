/**
 * Submódulo documental (PDFs e informes). Integración por dominio desde contenedores o hooks.
 *
 * Fase A (contrato): modelo canónico + registro de fuentes + descargas; consumidores pueden importar solo desde aquí.
 */

export { buildRutaPublicadaDocumentModel } from "./builders/buildRutaPublicadaDocumentModel";
export {
  PDF_FONT_ARCHIVO_BLACK,
  PDF_FONT_CARLITO,
  PDF_FONT_LIBRE_BASKERVILLE,
  registerDocumentosPdfFonts,
} from "./core/registerPdfFonts";
export {
  PDF_DESIGN_COLORS,
  PDF_DESIGN_FONT,
  pdfInformeBlockRule,
  pdfInformeMetaTable,
  pdfInformePage,
  pdfInformeSectionSeparator,
  pdfInformeTable,
  pdfInformeTypography,
  pdfPlanilla,
} from "./core/pdfDesignTokens";
export type {
  RutaDocumentoGrupo,
  RutaDocumentoInspector,
  RutaDocumentoInspectorSalida,
  RutaDocumentoItemFila,
  RutaDocumentoMapaPunto,
  RutaPublicadaDocumentModel,
} from "./types/rutaPublicadaDocument";
export { downloadOrdenesSalidaPdf, downloadRutaResumenPdf } from "./rutas/downloadRutaPublicadaPdfs";
export { buildOsmStaticMapUrl, computeStaticMapView, fetchStaticMapAsDataUrl } from "./rutas/osmStaticMapImage";
export type { FetchStaticMapOptions, StaticMapParams } from "./rutas/osmStaticMapImage";
export {
  INSTITUTIONAL_CITY_LINE,
  INSTITUTIONAL_DIRECTION_LINE,
  INSTITUTIONAL_SECRETARY_LINE,
} from "./core/institutionalCopy";
