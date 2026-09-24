import { Document, Image, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

import type { NotificacionPdfResumenPair } from "../../Containers/GestionNotificacion/utils/notificacionesExportPdfResumen";
import type { NotificacionVisualPdfRow } from "../../Containers/GestionNotificacion/utils/notificacionesExportVisualRows";
import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import {
  PDF_DESIGN_COLORS,
  PDF_DESIGN_FONT,
  pdfInformePage,
  pdfInformeTable,
  pdfInformeTypography,
  pdfTableCellBorder,
} from "../core/pdfDesignTokens";

export type NotificacionesListadoPdfModel = {
  desde: string;
  hasta: string;
  periodoExportadoLine: string;
  generadoEl: string;
  totalRegistros: number;
  filtrosResumen: string[];
  resumen: NotificacionPdfResumenPair[];
  rows: NotificacionVisualPdfRow[];
};

const COL_FLEX = {
  fechaOt: 1.05,
  notificacion: 0.95,
  domicilio: 1.35,
  contribuyente: 1.15,
  motivos: 1.25,
  plazo: 1.05,
  estado: 0.75,
} as const;

const DETAIL_ROWS_PER_PAGE = 12;

export function paginateNotificacionesDetalleRows(rows: NotificacionVisualPdfRow[]): NotificacionVisualPdfRow[][] {
  if (rows.length === 0) return [];
  const out: NotificacionVisualPdfRow[][] = [];
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

function BodyCell({ flex, value }: { flex: number; value: string }) {
  return (
    <View style={[styles.tableCellBody, { flex }]}>
      <Text style={styles.bodyCell}>{value || "—"}</Text>
    </View>
  );
}

function TableHeaderRow() {
  return (
    <View style={styles.tableHeader}>
      <HeaderCell flex={COL_FLEX.fechaOt} label="Fecha · OT" />
      <HeaderCell flex={COL_FLEX.notificacion} label="Notificación" />
      <HeaderCell flex={COL_FLEX.domicilio} label="Domicilio / rubro" />
      <HeaderCell flex={COL_FLEX.contribuyente} label="Contribuyente" />
      <HeaderCell flex={COL_FLEX.motivos} label="Motivos" />
      <HeaderCell flex={COL_FLEX.plazo} label="Plazo / venc." />
      <HeaderCell flex={COL_FLEX.estado} label="Estado" />
    </View>
  );
}

function DataRow({ row }: { row: NotificacionVisualPdfRow }) {
  return (
    <View style={styles.tableRow} wrap={false}>
      <BodyCell flex={COL_FLEX.fechaOt} value={row.fechaOt} />
      <BodyCell flex={COL_FLEX.notificacion} value={row.notificacion} />
      <BodyCell flex={COL_FLEX.domicilio} value={row.domicilioRubro} />
      <BodyCell flex={COL_FLEX.contribuyente} value={row.contribuyente} />
      <BodyCell flex={COL_FLEX.motivos} value={row.motivos} />
      <BodyCell flex={COL_FLEX.plazo} value={row.plazoVencimiento} />
      <BodyCell flex={COL_FLEX.estado} value={row.estado} />
    </View>
  );
}

function ResumenTabla({ rows }: { rows: NotificacionPdfResumenPair[] }) {
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
  model: NotificacionesListadoPdfModel;
  sheetIndex: number;
  totalSheets: number;
}) {
  return (
    <Text style={styles.footer} fixed>
      {INSTITUTIONAL_DIRECTION_LINE} · Notificaciones · {model.desde} — {model.hasta} · Hoja {sheetIndex}/
      {totalSheets}
    </Text>
  );
}

export type NotificacionesListadoPdfDocumentProps = {
  model: NotificacionesListadoPdfModel;
  membreteSrc: string;
};

/**
 * PDF administrativo de notificaciones: hoja 1 = indicadores; hojas 2+ = detalle.
 */
export function NotificacionesListadoPdfDocument({ model, membreteSrc }: NotificacionesListadoPdfDocumentProps) {
  const filtros =
    model.filtrosResumen.length > 0 ? model.filtrosResumen.join(" · ") : "Sin filtros adicionales";
  const detailChunks = paginateNotificacionesDetalleRows(model.rows);
  const totalSheets = 1 + detailChunks.length;

  return (
    <Document title={`Notificaciones ${model.desde} — ${model.hasta}`}>
      <Page size="A4" orientation="landscape" style={styles.page}>
        <Image src={membreteSrc} style={styles.membreteImg} />
        <Text style={styles.mainTitle}>LISTADO DE NOTIFICACIONES</Text>
        <Text style={styles.periodExported}>Período exportado: {model.periodoExportadoLine}</Text>
        <Text style={styles.metaMuted}>Generado: {model.generadoEl}</Text>
        <Text style={styles.metaMuted}>
          Total registros: {model.totalRegistros} · {filtros}
        </Text>
        <Text style={styles.resumenTitle}>Notificaciones bromatológicas</Text>
        <ResumenTabla rows={model.resumen} />
        <PageFooter model={model} sheetIndex={1} totalSheets={totalSheets} />
      </Page>

      {detailChunks.map((slice, detailIdx) => {
        const sheetIndex = detailIdx + 2;
        const detailTitle =
          detailIdx === 0
            ? "LISTADO DE NOTIFICACIONES · DETALLE"
            : "DETALLE DE NOTIFICACIONES · CONTINUACIÓN";

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
