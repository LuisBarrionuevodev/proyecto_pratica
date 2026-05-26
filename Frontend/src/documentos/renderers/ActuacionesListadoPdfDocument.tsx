import { Document, Image, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import {
  PDF_DESIGN_COLORS,
  pdfInformePage,
  pdfInformeTable,
  pdfInformeTypography,
} from "../core/pdfDesignTokens";
import type { ActuacionVisualPdfRow } from "../../Containers/Actuaciones/utils/actuacionesExportVisualRows";

export type ActuacionesListadoPdfModel = {
  desde: string;
  hasta: string;
  generadoEl: string;
  totalRegistros: number;
  filtrosResumen: string[];
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

const styles = StyleSheet.create({
  page: {
    ...pdfInformePage,
    paddingTop: 22,
    paddingBottom: 24,
    paddingHorizontal: 28,
  },
  membreteImg: {
    width: "100%",
    height: 52,
    objectFit: "contain",
    marginBottom: 10,
  },
  title: {
    ...pdfInformeTypography.titleMain,
    marginBottom: 6,
  },
  subtitle: {
    ...pdfInformeTypography.metaLabel,
    marginBottom: 8,
  },
  metaLine: {
    ...pdfInformeTypography.caption,
    marginBottom: 2,
  },
  tableHeader: {
    ...pdfInformeTable.headerRow,
    flexDirection: "row",
    marginTop: 8,
  },
  tableRow: {
    ...pdfInformeTable.bodyRow,
    flexDirection: "row",
    alignItems: "flex-start",
  },
  headerCell: {
    ...pdfInformeTypography.tableHeaderCell,
    paddingRight: 4,
    paddingVertical: 4,
  },
  bodyCell: {
    ...pdfInformeTypography.tableBodyCell,
    paddingRight: 4,
    paddingVertical: 3,
    fontSize: 7,
    lineHeight: 1.25,
  },
  footer: {
    position: "absolute",
    bottom: 14,
    left: 28,
    right: 28,
    ...pdfInformeTypography.caption,
    textAlign: "center",
    color: PDF_DESIGN_COLORS.textMuted,
  },
});

function HeaderCell({ flex, label }: { flex: number; label: string }) {
  return (
    <View style={{ flex }}>
      <Text style={styles.headerCell}>{label}</Text>
    </View>
  );
}

function BodyCell({ flex, value }: { flex: number; value: string }) {
  return (
    <View style={{ flex }}>
      <Text style={styles.bodyCell}>{value || "—"}</Text>
    </View>
  );
}

function TableHeaderRow() {
  return (
    <View style={styles.tableHeader} fixed>
      <HeaderCell flex={COL_FLEX.fechaOt} label="Fecha · OT" />
      <HeaderCell flex={COL_FLEX.tipo} label="Tipo / contraproducencia" />
      <HeaderCell flex={COL_FLEX.domicilio} label="Domicilio / rubro" />
      <HeaderCell flex={COL_FLEX.inspectores} label="Inspectores" />
      <HeaderCell flex={COL_FLEX.actas} label="Actas y trámite" />
      <HeaderCell flex={COL_FLEX.motivos} label="Motivos" />
    </View>
  );
}

function DataRow({ row }: { row: ActuacionVisualPdfRow }) {
  return (
    <View style={styles.tableRow}>
      <BodyCell flex={COL_FLEX.fechaOt} value={row.fechaOt} />
      <BodyCell flex={COL_FLEX.tipo} value={row.tipoContraproducencia} />
      <BodyCell flex={COL_FLEX.domicilio} value={row.domicilioRubro} />
      <BodyCell flex={COL_FLEX.inspectores} value={row.inspectores} />
      <BodyCell flex={COL_FLEX.actas} value={row.actasTramite} />
      <BodyCell flex={COL_FLEX.motivos} value={row.motivos} />
    </View>
  );
}

export type ActuacionesListadoPdfDocumentProps = {
  model: ActuacionesListadoPdfModel;
  membreteSrc: string;
};

/**
 * PDF administrativo del listado de actuaciones (columnas compuestas, estilo informe institucional).
 */
export function ActuacionesListadoPdfDocument({ model, membreteSrc }: ActuacionesListadoPdfDocumentProps) {
  const filtros =
    model.filtrosResumen.length > 0 ? model.filtrosResumen.join(" · ") : "Sin filtros adicionales";

  return (
    <Document title={`Actuaciones ${model.desde} — ${model.hasta}`}>
      <Page size="A4" orientation="landscape" style={styles.page}>
        <Image src={membreteSrc} style={styles.membreteImg} />
        <Text style={styles.title}>Listado de actuaciones</Text>
        <Text style={styles.subtitle}>{INSTITUTIONAL_DIRECTION_LINE}</Text>
        <Text style={styles.metaLine}>Período exportado: {model.desde} — {model.hasta}</Text>
        <Text style={styles.metaLine}>Generado: {model.generadoEl}</Text>
        <Text style={styles.metaLine}>Total registros: {model.totalRegistros}</Text>
        <Text style={styles.metaLine}>Filtros: {filtros}</Text>

        <TableHeaderRow />
        {model.rows.map((row, idx) => (
          <DataRow key={`act-${idx}`} row={row} />
        ))}

        <Text style={styles.footer} fixed>
          {INSTITUTIONAL_DIRECTION_LINE} · Actuaciones · {model.desde} — {model.hasta}
        </Text>
      </Page>
    </Document>
  );
}
