/**
 * Tokens visuales unificados para informes PDF (resumen de ruta, futuros informes de trabajo).
 *
 * **Calibri en documentación municipal:** en el bundle usamos **Carlito** (SIL OFL), métrica
 * compatible con Calibri. Registrar siempre `registerDocumentosPdfFonts()` antes de `pdf().toBlob()`.
 *
 * Convención tablas informe: cabecera negra / texto blanco bold; filas blancas / texto normal.
 */

import { PDF_FONT_CARLITO } from "./registerPdfFonts";

/** Paleta y grises para impresión (incluye B/N). */
export const PDF_DESIGN_COLORS = {
  titleBlue: "#0d47a1",
  sectionDarkBlue: "#0d3d82",
  separatorBlue: "#1565c0",
  textPrimary: "#111111",
  textSecondary: "#555555",
  textMuted: "#666666",
  tableHeaderBg: "#000000",
  tableHeaderText: "#ffffff",
  tableRowBg: "#ffffff",
  tableRowBorder: "#dddddd",
  grupoCardBorder: "#dddddd",
  grupoCardBg: "#fafafa",
  borderNeutral: "#999999",
} as const;

/** Rejilla tipo formulario papel (cuadros B/N; tinta = misma que cabeceras de tabla informe). */
export const pdfPlanilla = {
  ink: PDF_DESIGN_COLORS.tableHeaderBg,
  borderSoft: PDF_DESIGN_COLORS.borderNeutral,
} as const;

/** Familia UI de informes (Carlito ≈ Calibri). */
export const PDF_DESIGN_FONT = {
  ui: PDF_FONT_CARLITO,
} as const;

/** Tipografía reutilizable (fragmentos para `StyleSheet.create`). */
export const pdfInformeTypography = {
  titleMain: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 16,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.titleBlue,
  },
  /** Título de sección; combinar con `pdfInformeSectionSeparator` para línea azul bajo el título. */
  sectionTitle: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 11,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.sectionDarkBlue,
  },
  grupoTitle: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10.5,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.sectionDarkBlue,
  },
  metaLabel: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textSecondary,
    textTransform: "uppercase" as const,
  },
  metaValue: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  tableHeaderCell: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.tableHeaderText,
  },
  tableBodyCell: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  caption: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textMuted,
  },
  inspectorsLead: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
    lineHeight: 1.35,
  },
  obsBody: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
    lineHeight: 1.4,
  },
  /** Cabecera tabla meta datos (fila negra): texto blanco mayúsculas. */
  metaTableHeaderCell: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 700,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.tableHeaderText,
    textTransform: "uppercase" as const,
  },
  /** Valores tabla meta (fila blanca). */
  metaTableValueCell: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  /** Prefijo «Inspectores:» un poco más grande que la lista. */
  inspectorsPrefix: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10.5,
    fontWeight: 400,
    fontStyle: "normal" as const,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
} as const;

/** Filas de tabla tipo informe (cabecera negra / cuerpo blanco). */
export const pdfInformeTable = {
  headerRow: {
    flexDirection: "row" as const,
    backgroundColor: PDF_DESIGN_COLORS.tableHeaderBg,
    paddingVertical: 5,
    paddingHorizontal: 4,
    alignItems: "center" as const,
  },
  bodyRow: {
    flexDirection: "row" as const,
    backgroundColor: PDF_DESIGN_COLORS.tableRowBg,
    borderBottomWidth: 0.5,
    borderBottomColor: PDF_DESIGN_COLORS.tableRowBorder,
    paddingVertical: 4,
    paddingHorizontal: 4,
  },
} as const;

/** Cuerpo de página por defecto para informes de ruta. */
export const pdfInformePage = {
  fontFamily: PDF_DESIGN_FONT.ui,
  fontSize: 9,
  fontStyle: "normal" as const,
  fontWeight: 400,
  color: PDF_DESIGN_COLORS.textPrimary,
} as const;

/** Separación visual entre secciones (línea azul). */
export const pdfInformeSectionSeparator = {
  borderBottomWidth: 1,
  borderBottomColor: PDF_DESIGN_COLORS.separatorBlue,
  paddingBottom: 4,
  marginBottom: 6,
} as const;

/** Regla horizontal entre bloques (meta / mapa / grupos). */
export const pdfInformeBlockRule = {
  width: "100%" as const,
  height: 1.5,
  backgroundColor: PDF_DESIGN_COLORS.separatorBlue,
  marginVertical: 8,
} as const;

/** Tabla 2 filas (cabecera negra + valores) para datos de cabecera del informe. */
export const pdfInformeMetaTable = {
  headerRow: {
    flexDirection: "row" as const,
    backgroundColor: PDF_DESIGN_COLORS.tableHeaderBg,
    paddingVertical: 5,
    paddingHorizontal: 4,
    alignItems: "center" as const,
  },
  valueRow: {
    flexDirection: "row" as const,
    backgroundColor: PDF_DESIGN_COLORS.tableRowBg,
    borderBottomWidth: 0.5,
    borderBottomColor: PDF_DESIGN_COLORS.tableRowBorder,
    paddingVertical: 6,
    paddingHorizontal: 4,
    alignItems: "center" as const,
  },
  col: { width: "25%" as const },
} as const;
