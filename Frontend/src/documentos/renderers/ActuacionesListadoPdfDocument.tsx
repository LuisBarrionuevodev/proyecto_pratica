import { Document, Image, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

import type { ActuacionPdfResumenPair } from "../../Containers/Actuaciones/utils/actuacionesExportPdfResumen";
import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import {
  PDF_DESIGN_COLORS,
  PDF_DESIGN_FONT,
  pdfInformePage,
  pdfInformeTable,
  pdfInformeTypography,
  pdfTableCellBorder,
} from "../core/pdfDesignTokens";
import type { ActuacionVisualPdfRow } from "../../Containers/Actuaciones/utils/actuacionesExportVisualRows";

export type ActuacionesListadoPdfModel = {
  desde: string;
  hasta: string;
  /** Texto ya formateado p. ej. `01/05/2026 al 31/05/2026`. */
  periodoExportadoLine: string;
  generadoEl: string;
  totalRegistros: number;
  filtrosResumen: string[];
  resumen: ActuacionPdfResumenPair[];
  rows: ActuacionVisualPdfRow[];
};

const COL_FLEX = {
  fechaOt: 1.1,
  tipo: 1.35,
  domicilio: 1.5,
  inspectores: 1.2,
  actas: 1.8,
  motivos: 1.4,
} as const;

/** Filas de detalle por página (solo páginas de detalle, sin resumen). */
const DETAIL_ROWS_PER_PAGE = 14;

/** Particiona filas de detalle para páginas 2+ del PDF (página 1 = solo resumen). */
export function paginateActuacionesDetalleRows(rows: ActuacionVisualPdfRow[]): ActuacionVisualPdfRow[][] {
  if (rows.length === 0) return [];
  const out: ActuacionVisualPdfRow[][] = [];
  for (let i = 0; i < rows.length; i += DETAIL_ROWS_PER_PAGE) {
    out.push(rows.slice(i, i + DETAIL_ROWS_PER_PAGE));
  }
  return out;
}

const styles = StyleSheet.create({
  page: {
    ...pdfInformePage,
    paddingTop: 22,
    paddingBottom: 28,
    paddingHorizontal: 28,
  },
  membreteImg: {
    width: "100%",
    height: 48,
    objectFit: "contain",
    marginBottom: 6,
  },
  mainTitle: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 17,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.titleBlue,
    textAlign: "center",
    textTransform: "uppercase",
    marginBottom: 8,
    letterSpacing: 0.3,
  },
  detailTitle: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 13,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.titleBlue,
    textAlign: "center",
    textTransform: "uppercase",
    marginBottom: 6,
    letterSpacing: 0.25,
  },
  periodExported: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 11.5,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.textPrimary,
    textAlign: "center",
    marginBottom: 6,
  },
  metaMuted: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.5,
    fontWeight: 400,
    color: PDF_DESIGN_COLORS.textSecondary,
    textAlign: "center",
    marginBottom: 2,
  },
  resumenTitle: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 11,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.sectionDarkBlue,
    textAlign: "center",
    textTransform: "uppercase",
    marginTop: 6,
    marginBottom: 6,
    letterSpacing: 0.2,
  },
  tableRowBase: {
    flexDirection: "row",
    alignItems: "stretch",
  },
  tableCellHeader: {
    ...pdfTableCellBorder,
    backgroundColor: PDF_DESIGN_COLORS.tableHeaderBg,
    paddingVertical: 4,
    paddingHorizontal: 4,
    justifyContent: "center",
  },
  tableCellBody: {
    ...pdfTableCellBorder,
    backgroundColor: PDF_DESIGN_COLORS.tableRowBg,
    paddingVertical: 3,
    paddingHorizontal: 4,
    justifyContent: "flex-start",
  },
  resumenHeadText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.tableHeaderText,
    textTransform: "uppercase",
  },
  resumenBodyIndText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8,
    fontWeight: 500,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  resumenBodyValText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  tableHeader: {
    ...pdfInformeTable.headerRow,
    flexDirection: "row",
    marginTop: 4,
    marginBottom: 0,
    paddingVertical: 0,
    paddingHorizontal: 0,
    backgroundColor: "transparent",
  },
  tableRow: {
    flexDirection: "row",
    alignItems: "stretch",
    backgroundColor: "transparent",
    borderBottomWidth: 0,
    paddingVertical: 0,
    paddingHorizontal: 0,
  },
  headerCell: {
    ...pdfInformeTypography.tableHeaderCell,
    paddingRight: 4,
    paddingVertical: 3,
    fontSize: 6.5,
  },
  bodyCell: {
    ...pdfInformeTypography.tableBodyCell,
    paddingRight: 4,
    paddingVertical: 2,
    fontSize: 6.75,
    lineHeight: 1.22,
  },
  bodyCellTipo: {
    ...pdfInformeTypography.tableBodyCell,
    paddingRight: 4,
    paddingVertical: 2,
    fontSize: 6.35,
    lineHeight: 1.18,
  },
  footer: {
    position: "absolute",
    bottom: 12,
    left: 28,
    right: 28,
    ...pdfInformeTypography.caption,
    textAlign: "center",
    color: PDF_DESIGN_COLORS.textMuted,
  },
});

function HeaderCell({ flex, label }: { flex: number; label: string }) {
  return (
    <View style={[styles.tableCellHeader, { flex }]}>
      <Text style={styles.headerCell}>{label}</Text>
    </View>
  );
}

function BodyCell({ flex, value, compact }: { flex: number; value: string; compact?: boolean }) {
  return (
    <View style={[styles.tableCellBody, { flex }]}>
      <Text style={compact ? styles.bodyCellTipo : styles.bodyCell}>{value || "—"}</Text>
    </View>
  );
}

function TableHeaderRow() {
  return (
    <View style={styles.tableHeader}>
      <HeaderCell flex={COL_FLEX.fechaOt} label="Fecha · OT" />
      <HeaderCell flex={COL_FLEX.tipo} label="Tipo / contraproducencia / origen" />
      <HeaderCell flex={COL_FLEX.domicilio} label="Domicilio / rubro" />
      <HeaderCell flex={COL_FLEX.inspectores} label="Inspectores" />
      <HeaderCell flex={COL_FLEX.actas} label="Actas y trámite (propios)" />
      <HeaderCell flex={COL_FLEX.motivos} label="Motivos (propios)" />
    </View>
  );
}

function DataRow({ row }: { row: ActuacionVisualPdfRow }) {
  return (
    <View style={styles.tableRow} wrap={false}>
      <BodyCell flex={COL_FLEX.fechaOt} value={row.fechaOt} />
      <BodyCell flex={COL_FLEX.tipo} value={row.tipoContraproducencia} compact />
      <BodyCell flex={COL_FLEX.domicilio} value={row.domicilioRubro} />
      <BodyCell flex={COL_FLEX.inspectores} value={row.inspectores} />
      <BodyCell flex={COL_FLEX.actas} value={row.actasTramite} />
      <BodyCell flex={COL_FLEX.motivos} value={row.motivos} />
    </View>
  );
}

function ResumenTabla({ rows }: { rows: ActuacionPdfResumenPair[] }) {
  return (
    <View>
      <View style={styles.tableRowBase}>
        <View style={[styles.tableCellHeader, { flex: 2.6 }]}>
          <Text style={styles.resumenHeadText}>Indicador</Text>
        </View>
        <View style={[styles.tableCellHeader, { flex: 0.85 }]}>
          <Text style={styles.resumenHeadText}>Valor</Text>
        </View>
      </View>
      {rows.map((r) => (
        <View key={r.indicator} style={styles.tableRowBase} wrap={false}>
          <View style={[styles.tableCellBody, { flex: 2.6 }]}>
            <Text style={styles.resumenBodyIndText}>{r.indicator}</Text>
          </View>
          <View style={[styles.tableCellBody, { flex: 0.85 }]}>
            <Text style={styles.resumenBodyValText}>{r.value}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function PageFooter({
  model,
  sheetIndex,
  totalSheets,
}: {
  model: ActuacionesListadoPdfModel;
  sheetIndex: number;
  totalSheets: number;
}) {
  return (
    <Text style={styles.footer} fixed>
      {INSTITUTIONAL_DIRECTION_LINE} · Actuaciones · {model.desde} — {model.hasta} · Hoja {sheetIndex}/
      {totalSheets}
    </Text>
  );
}

export type ActuacionesListadoPdfDocumentProps = {
  model: ActuacionesListadoPdfModel;
  membreteSrc: string;
};

/**
 * PDF administrativo: hoja 1 = resumen; hojas 2+ = detalle con encabezado repetido por página.
 */
export function ActuacionesListadoPdfDocument({ model, membreteSrc }: ActuacionesListadoPdfDocumentProps) {
  const filtros =
    model.filtrosResumen.length > 0 ? model.filtrosResumen.join(" · ") : "Sin filtros adicionales";
  const detailChunks = paginateActuacionesDetalleRows(model.rows);
  const totalSheets = 1 + detailChunks.length;

  return (
    <Document title={`Actuaciones ${model.desde} — ${model.hasta}`}>
      <Page size="A4" orientation="landscape" style={styles.page}>
        <Image src={membreteSrc} style={styles.membreteImg} />
        <Text style={styles.mainTitle}>LISTADO DE ACTUACIONES</Text>
        <Text style={styles.periodExported}>Período exportado: {model.periodoExportadoLine}</Text>
        <Text style={styles.metaMuted}>Generado: {model.generadoEl}</Text>
        <Text style={styles.metaMuted}>
          Total registros: {model.totalRegistros} · {filtros}
        </Text>
        <Text style={styles.resumenTitle}>Inspecciones bromatológicas</Text>
        <ResumenTabla rows={model.resumen} />
        <PageFooter model={model} sheetIndex={1} totalSheets={totalSheets} />
      </Page>

      {detailChunks.map((slice, detailIdx) => {
        const sheetIndex = detailIdx + 2;
        const detailTitle =
          detailIdx === 0
            ? "LISTADO DE ACTUACIONES · DETALLE"
            : "DETALLE DE ACTUACIONES · CONTINUACIÓN";

        return (
          <Page key={`det-${detailIdx}`} size="A4" orientation="landscape" style={styles.page}>
            <Image src={membreteSrc} style={styles.membreteImg} />
            <Text style={styles.detailTitle}>{detailTitle}</Text>
            <Text style={styles.periodExported}>Período exportado: {model.periodoExportadoLine}</Text>
            <Text style={styles.metaMuted}>
              Detalle · hoja {detailIdx + 1} de {detailChunks.length} · {slice.length} registro
              {slice.length === 1 ? "" : "s"}
            </Text>
            <TableHeaderRow />
            {slice.map((row, idx) => (
              <DataRow key={`${detailIdx}-${idx}`} row={row} />
            ))}
            <PageFooter model={model} sheetIndex={sheetIndex} totalSheets={totalSheets} />
          </Page>
        );
      })}
    </Document>
  );
}
