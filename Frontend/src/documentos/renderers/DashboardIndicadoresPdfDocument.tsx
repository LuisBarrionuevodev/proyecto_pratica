import { Document, Image, Page, Text, View } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import type {
  DashboardPdfKpiRow,
  DashboardPdfModel,
  DashboardPdfTableSection,
} from "../../Containers/Dashboard/utils/dashboardPdfMappers";
import { DASHBOARD_PDF_EMPTY_MESSAGE } from "../../Containers/Dashboard/utils/dashboardPdfMappers";
import { dashboardPdfStyles as styles } from "../../Containers/Dashboard/utils/dashboardPdfStyles";

type Props = {
  model: DashboardPdfModel;
  membreteSrc: string;
};

function KpiGrid({ rows }: { rows: DashboardPdfKpiRow[] }) {
  if (rows.length === 0) {
    return <Text style={styles.emptyLine}>{DASHBOARD_PDF_EMPTY_MESSAGE}</Text>;
  }
  return (
    <View style={styles.kpiGrid}>
      {rows.map((row) => (
        <View key={row.label} style={styles.kpiCard}>
          <Text style={styles.kpiLabel}>{row.label}</Text>
          <Text style={styles.kpiValue}>{row.value}</Text>
        </View>
      ))}
    </View>
  );
}

function PdfTableSection({ section }: { section: DashboardPdfTableSection }) {
  const hasRows = section.rows.length > 0;
  const colCount = section.headers.length;
  const valueFlex = colCount > 2 ? 0.18 : 0.35;

  const rowCells = (row: DashboardPdfTableRow): string[] => {
    const cells = [row.value];
    if (row.value2 != null) cells.push(row.value2);
    if (row.extraValues?.length) cells.push(...row.extraValues);
    return cells;
  };

  return (
    <View wrap={false}>
      <Text style={styles.subSectionTitle}>{section.title}</Text>
      {hasRows ? (
        <>
          <View style={styles.tableHeader}>
            {section.headers.map((header, idx) => (
              <Text
                key={header}
                style={[
                  styles.tableHeaderCell,
                  {
                    flex: idx === 0 ? 1 : valueFlex,
                    textAlign: idx === 0 ? "left" : "right",
                  },
                ]}
              >
                {header}
              </Text>
            ))}
          </View>
          {section.rows.map((row, idx) => {
            const values = rowCells(row);
            return (
              <View key={`${row.label}-${idx}`} style={styles.tableRow}>
                <Text style={[styles.tableBodyCell, { flex: 1 }]}>{row.label}</Text>
                {values.map((cell, cellIdx) => (
                  <Text
                    key={`${row.label}-${cellIdx}`}
                    style={[styles.tableBodyCellRight, { flex: valueFlex }]}
                  >
                    {cell}
                  </Text>
                ))}
              </View>
            );
          })}
        </>
      ) : (
        <Text style={styles.emptyLine}>{DASHBOARD_PDF_EMPTY_MESSAGE}</Text>
      )}
    </View>
  );
}

function PageFooter({ model, pageNum, totalPages }: { model: DashboardPdfModel; pageNum: number; totalPages: number }) {
  return (
    <Text style={styles.footer} fixed>
      {INSTITUTIONAL_DIRECTION_LINE} · Indicadores operativos · {model.desde} — {model.hasta} · Hoja{" "}
      {pageNum}/{totalPages}
    </Text>
  );
}

function ReportHeader({ model, membreteSrc }: { model: DashboardPdfModel; membreteSrc: string }) {
  return (
    <>
      <Image src={membreteSrc} style={styles.membreteImg} />
      <Text style={styles.mainTitle}>{model.title}</Text>
      <Text style={styles.periodLine}>{model.periodoLine}</Text>
      <Text style={styles.metaLine}>Distrito: {model.distritoLabel}</Text>
      <Text style={styles.metaLine}>Inspector: {model.inspectorLabel}</Text>
      <Text style={styles.metaLine}>Emitido el: {model.generadoEl}</Text>
    </>
  );
}

/**
 * PDF institucional compacto del dashboard de indicadores (3 páginas A4 vertical).
 */
export function DashboardIndicadoresPdfDocument({ model, membreteSrc }: Props) {
  const totalPages = 3;

  return (
    <Document title={model.title}>
      <Page size="A4" style={styles.page}>
        <ReportHeader model={model} membreteSrc={membreteSrc} />
        <Text style={styles.sectionTitle}>Resumen ejecutivo</Text>
        <KpiGrid rows={model.ejecutivoKpis} />
        <Text style={styles.sectionTitle}>Pendientes operativos</Text>
        <Text style={[styles.metaLine, { textAlign: "left", marginBottom: 4 }]}>
          Pendientes actuales al momento de consulta.
        </Text>
        <KpiGrid rows={model.pendientesKpis} />
        <PageFooter model={model} pageNum={1} totalPages={totalPages} />
      </Page>

      <Page size="A4" style={styles.page}>
        <ReportHeader model={model} membreteSrc={membreteSrc} />
        <Text style={styles.sectionTitle}>Actas por tipo</Text>
        <PdfTableSection section={model.actasPorTipo} />
        <Text style={styles.sectionTitle}>Riesgo bromatológico</Text>
        <View style={styles.twoColRow}>
          <View style={styles.halfCol}>
            <PdfTableSection section={model.riesgoRubros} />
            <PdfTableSection section={model.riesgoMotivosNotificacion} />
          </View>
          <View style={styles.halfCol}>
            <PdfTableSection section={model.riesgoMotivosComprobacion} />
            <PdfTableSection section={model.riesgoDecomisoKg} />
          </View>
        </View>
        <PageFooter model={model} pageNum={2} totalPages={totalPages} />
      </Page>

      <Page size="A4" style={styles.page}>
        <ReportHeader model={model} membreteSrc={membreteSrc} />
        <Text style={styles.sectionTitle}>No realizadas</Text>
        {model.noRealizadasTotal != null ? (
          <Text style={styles.kpiValue}>No realizadas total: {model.noRealizadasTotal}</Text>
        ) : (
          <Text style={styles.emptyLine}>{DASHBOARD_PDF_EMPTY_MESSAGE}</Text>
        )}
        <PdfTableSection section={model.noRealizadasContraproducencias} />
        <PdfTableSection section={model.noRealizadasDistritos} />
        <Text style={styles.sectionTitle}>Productividad</Text>
        <PdfTableSection section={model.productividadRealizadas} />
        <PdfTableSection section={model.productividadNoRealizadas} />
        <PdfTableSection section={model.productividadActas} />
        {model.productividadTruncatedNote ? (
          <Text style={styles.note}>{model.productividadTruncatedNote}</Text>
        ) : null}
        <PageFooter model={model} pageNum={3} totalPages={totalPages} />
      </Page>
    </Document>
  );
}
