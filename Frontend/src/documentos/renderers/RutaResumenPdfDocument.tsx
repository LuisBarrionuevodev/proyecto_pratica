import { Document, Page, StyleSheet, Text, View, Image } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import {
  PDF_DESIGN_COLORS,
  pdfInformeMetaTable,
  pdfInformePage,
  pdfInformeTable,
  pdfInformeTypography,
} from "../core/pdfDesignTokens";
import type { RutaPublicadaDocumentModel } from "../types/rutaPublicadaDocument";

const styles = StyleSheet.create({
  page: {
    ...pdfInformePage,
    paddingTop: 24,
    paddingBottom: 28,
    paddingHorizontal: 36,
  },
  membreteImg: {
    width: "100%",
    height: 58,
    objectFit: "contain",
    marginBottom: 12,
  },
  title: {
    ...pdfInformeTypography.titleMain,
    marginBottom: 10,
  },
  metaTableHeaderRow: {
    ...pdfInformeMetaTable.headerRow,
  },
  metaTableValueRow: {
    ...pdfInformeMetaTable.valueRow,
  },
  metaTableCol: {
    ...pdfInformeMetaTable.col,
  },
  metaTableHeaderCell: {
    ...pdfInformeTypography.metaTableHeaderCell,
  },
  metaTableValueCell: {
    ...pdfInformeTypography.metaTableValueCell,
  },
  denomBlock: {
    marginTop: 6,
    marginBottom: 6,
  },
  denomLabel: {
    ...pdfInformeTypography.metaLabel,
    marginBottom: 2,
  },
  denomValue: {
    ...pdfInformeTypography.metaTableValueCell,
  },
  sectionTitle: {
    ...pdfInformeTypography.sectionTitle,
    marginTop: 12,
    marginBottom: 4,
  },
  mapWrap: {
    marginTop: 8,
    marginBottom: 10,
    alignItems: "center",
    width: "100%",
  },
  mapImg: {
    width: 518,
    height: 188,
    objectFit: "contain",
    borderWidth: 0.5,
    borderColor: PDF_DESIGN_COLORS.borderNeutral,
  },
  mapCaption: {
    ...pdfInformeTypography.caption,
    marginTop: 4,
    textAlign: "center",
  },
  grupoBlock: {
    marginBottom: 10,
    padding: 8,
    borderWidth: 0.5,
    borderColor: PDF_DESIGN_COLORS.grupoCardBorder,
    backgroundColor: PDF_DESIGN_COLORS.grupoCardBg,
  },
  grupoTitle: {
    ...pdfInformeTypography.grupoTitle,
  },
  inspectorsLine: {
    marginBottom: 4,
  },
  inspectorsPrefix: {
    ...pdfInformeTypography.inspectorsPrefix,
  },
  inspectorsNames: {
    ...pdfInformeTypography.inspectorsLead,
  },
  tableHeader: {
    ...pdfInformeTable.headerRow,
    marginTop: 4,
  },
  tableRow: {
    ...pdfInformeTable.bodyRow,
  },
  tableHeaderCell: {
    ...pdfInformeTypography.tableHeaderCell,
  },
  tableBodyCell: {
    ...pdfInformeTypography.tableBodyCell,
  },
  tableBodyCellSecondary: {
    ...pdfInformeTypography.tableBodyCell,
    fontSize: 7,
    color: PDF_DESIGN_COLORS.textMuted,
    marginTop: 1,
    lineHeight: 1.2,
  },
  colOrd: { width: "7%" },
  colDom: { width: "36%" },
  colDist: { width: "16%" },
  colRub: { width: "16%" },
  colOt: { width: "25%" },
  obsSectionTitle: {
    ...pdfInformeTypography.sectionTitle,
    color: PDF_DESIGN_COLORS.titleBlue,
    marginTop: 14,
    marginBottom: 4,
  },
  obs: {
    ...pdfInformeTypography.obsBody,
    marginTop: 4,
  },
  emptyGrupoNote: {
    ...pdfInformeTypography.inspectorsLead,
    fontSize: 8,
    marginTop: 4,
  },
});

type Props = {
  model: RutaPublicadaDocumentModel;
  membreteSrc: string;
  mapImageDataUrl: string | null;
};

/**
 * PDF «Resumen de ruta»: membrete gráfico, datos, grupos/ítems y mini-mapa embebido.
 */
export function RutaResumenPdfDocument({ model, membreteSrc, mapImageDataUrl }: Props) {
  return (
    <Document
      title={`Resumen ruta ${model.numeroRuta}`}
      author={INSTITUTIONAL_DIRECTION_LINE}
      subject={`Ruta ${model.numeroRuta} — ${model.fechaLegible}`}
    >
      <Page size="A4" style={styles.page}>
        <Image src={membreteSrc} style={styles.membreteImg} />
        <Text style={styles.title}>Resumen de ruta de trabajo</Text>

        <View style={styles.metaTableHeaderRow}>
          <Text style={[styles.metaTableCol, styles.metaTableHeaderCell]}>Número de ruta</Text>
          <Text style={[styles.metaTableCol, styles.metaTableHeaderCell]}>Fecha operativa</Text>
          <Text style={[styles.metaTableCol, styles.metaTableHeaderCell]}>Turno</Text>
          <Text style={[styles.metaTableCol, styles.metaTableHeaderCell]}>Estado</Text>
        </View>
        <View style={styles.metaTableValueRow}>
          <Text style={[styles.metaTableCol, styles.metaTableValueCell]}>{model.numeroRuta}</Text>
          <Text style={[styles.metaTableCol, styles.metaTableValueCell]}>{model.fechaLegible}</Text>
          <Text style={[styles.metaTableCol, styles.metaTableValueCell]}>{model.turnoLegible}</Text>
          <Text style={[styles.metaTableCol, styles.metaTableValueCell]}>{model.estadoRuta}</Text>
        </View>

        {model.displayName ? (
          <View style={styles.denomBlock}>
            <Text style={styles.denomLabel}>Denominación</Text>
            <Text style={styles.denomValue}>{model.displayName}</Text>
          </View>
        ) : null}

        {mapImageDataUrl ? (
          <View style={styles.mapWrap}>
            <Image src={mapImageDataUrl} style={styles.mapImg} />
            <Text style={styles.mapCaption}>
              Ubicación aproximada de los domicilios de la ruta (mapa de referencia, OpenStreetMap).
            </Text>
          </View>
        ) : (
          <View style={styles.mapWrap}>
            <Text style={[styles.mapCaption, { color: PDF_DESIGN_COLORS.textMuted }]}>
              {model.puntosMapa.length === 0
                ? "Mini-mapa no disponible: no hay coordenadas geográficas en los ítems de la ruta."
                : "Mini-mapa no disponible en este momento (servicio de mapa estático no respondió)."}
            </Text>
          </View>
        )}

        <Text style={styles.sectionTitle}>Grupos, inspectores y domicilios</Text>
        {model.grupos.map((g) => (
          <View key={g.grupoId} style={styles.grupoBlock}>
            <Text style={styles.grupoTitle}>{g.nombreGrupo}</Text>
            <Text style={styles.inspectorsLine}>
              <Text style={styles.inspectorsPrefix}>Inspectores: </Text>
              <Text style={styles.inspectorsNames}>
                {g.inspectores.length
                  ? g.inspectores.map((i) => `${i.nombreCompleto} (Af. ${i.numeroAfiliado})`).join(" · ")
                  : "—"}
              </Text>
            </Text>
            <View style={styles.tableHeader}>
              <Text style={[styles.colOrd, styles.tableHeaderCell]}>Nº</Text>
              <Text style={[styles.colDom, styles.tableHeaderCell]}>Domicilio</Text>
              <Text style={[styles.colDist, styles.tableHeaderCell]}>Distrito</Text>
              <Text style={[styles.colRub, styles.tableHeaderCell]}>Rubro</Text>
              <Text style={[styles.colOt, styles.tableHeaderCell]}>OT</Text>
            </View>
            {g.items.length === 0 ? (
              <Text style={styles.emptyGrupoNote}>Sin ítems asignados.</Text>
            ) : (
              g.items.map((it) => (
                <View key={it.itemId} style={styles.tableRow}>
                  <Text style={[styles.colOrd, styles.tableBodyCell]}>{it.ordenVisita}</Text>
                  <Text style={[styles.colDom, styles.tableBodyCell]}>{it.domicilioTexto}</Text>
                  <Text style={[styles.colDist, styles.tableBodyCell]}>{it.distritoNombre ?? "—"}</Text>
                  <View style={styles.colRub}>
                    <Text style={styles.tableBodyCell}>{it.rubroNombre ?? "—"}</Text>
                    {it.establecimientoSecundario ? (
                      <Text style={styles.tableBodyCellSecondary}>{it.establecimientoSecundario}</Text>
                    ) : null}
                  </View>
                  <Text style={[styles.colOt, styles.tableBodyCell]}>{it.ordenTrabajoLabel ?? "—"}</Text>
                </View>
              ))
            )}
          </View>
        ))}

        <Text style={styles.obsSectionTitle}>Observaciones</Text>
        <Text style={styles.obs}>{(model.observaciones ?? "").trim() || "—"}</Text>
      </Page>
    </Document>
  );
}
