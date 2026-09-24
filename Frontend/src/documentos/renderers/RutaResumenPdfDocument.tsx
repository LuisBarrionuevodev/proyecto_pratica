import { Document, Page, StyleSheet, Text, View, Image } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import {
  PDF_DESIGN_COLORS,
  pdfInformeMetaTable,
  pdfInformePage,
  pdfInformeTable,
  pdfInformeTypography,
} from "../core/pdfDesignTokens";
import type { RutaDocumentoGrupo, RutaDocumentoItemFila, RutaPublicadaDocumentModel } from "../types/rutaPublicadaDocument";

/** Grupos con hasta esta cantidad de filas se mantienen juntos en una página si entran. */
export const RUTA_PDF_GRUPO_KEEP_TOGETHER_MAX_ITEMS = 8;

/** Altura mínima estimada (pt) para evitar encabezado de tabla huérfano al final de página. */
const TABLE_HEADER_MIN_PRESENCE_AHEAD = 36;

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
  grupoIntro: {
    marginBottom: 2,
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
  detalleSegmentosRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "flex-start",
    marginTop: 1,
  },
  detalleSegmentoUnit: {
    flexDirection: "row",
    alignItems: "flex-start",
  },
  detalleSegmentoSep: {
    ...pdfInformeTypography.tableBodyCell,
    fontSize: 7,
    color: PDF_DESIGN_COLORS.textMuted,
    lineHeight: 1.2,
  },
  detalleSegmentoText: {
    ...pdfInformeTypography.tableBodyCell,
    fontSize: 7,
    color: PDF_DESIGN_COLORS.textMuted,
    lineHeight: 1.2,
  },
  colOrd: { width: "5%" },
  colDom: { width: "24%" },
  colDist: { width: "11%" },
  colRub: { width: "11%" },
  colTipo: { width: "12%" },
  colOt: { width: "10%" },
  colEntregado: { width: "9%", minHeight: 22 },
  colRecibido: { width: "9%", minHeight: 22 },
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

function DetalleOperativoPdfSegments({ segmentos }: { segmentos: string[] }) {
  if (!segmentos.length) return null;
  return (
    <View style={styles.detalleSegmentosRow}>
      {segmentos.map((seg, idx) => (
        <View key={`${idx}-${seg}`} style={styles.detalleSegmentoUnit} wrap={false}>
          {idx > 0 ? <Text style={styles.detalleSegmentoSep}> · </Text> : null}
          <Text style={styles.detalleSegmentoText}>{seg}</Text>
        </View>
      ))}
    </View>
  );
}

function GrupoTableHeader() {
  return (
    <View style={styles.tableHeader} wrap={false} minPresenceAhead={TABLE_HEADER_MIN_PRESENCE_AHEAD}>
      <Text style={[styles.colOrd, styles.tableHeaderCell]}>Nº</Text>
      <Text style={[styles.colDom, styles.tableHeaderCell]}>Domicilio</Text>
      <Text style={[styles.colDist, styles.tableHeaderCell]}>Distrito</Text>
      <Text style={[styles.colRub, styles.tableHeaderCell]}>Rubro</Text>
      <Text style={[styles.colTipo, styles.tableHeaderCell]}>Tipo / detalle</Text>
      <Text style={[styles.colOt, styles.tableHeaderCell]}>OT</Text>
      <Text style={[styles.colEntregado, styles.tableHeaderCell]}>Entregado</Text>
      <Text style={[styles.colRecibido, styles.tableHeaderCell]}>Recibido</Text>
    </View>
  );
}

function GrupoItemRow({ it }: { it: RutaDocumentoItemFila }) {
  return (
    <View style={styles.tableRow} wrap={false}>
      <Text style={[styles.colOrd, styles.tableBodyCell]}>{it.ordenVisita}</Text>
      <Text style={[styles.colDom, styles.tableBodyCell]}>{it.domicilioTexto}</Text>
      <Text style={[styles.colDist, styles.tableBodyCell]}>{it.distritoNombre ?? "—"}</Text>
      <View style={styles.colRub}>
        <Text style={styles.tableBodyCell}>{it.rubroNombre ?? "—"}</Text>
        {it.establecimientoSecundario ? (
          <Text style={styles.tableBodyCellSecondary}>{it.establecimientoSecundario}</Text>
        ) : null}
      </View>
      <View style={styles.colTipo}>
        <Text style={styles.tableBodyCell}>{it.tipoIniciadorLabel ?? it.tipoIniciador ?? "—"}</Text>
        <DetalleOperativoPdfSegments segmentos={it.detalleOperativoSegmentos} />
      </View>
      <Text style={[styles.colOt, styles.tableBodyCell]}>{it.ordenTrabajoLabel ?? "—"}</Text>
      <Text style={[styles.colEntregado, styles.tableBodyCell]}> </Text>
      <Text style={[styles.colRecibido, styles.tableBodyCell]}> </Text>
    </View>
  );
}

function GrupoResumenBlock({ g }: { g: RutaDocumentoGrupo }) {
  const keepTogether = g.items.length > 0 && g.items.length <= RUTA_PDF_GRUPO_KEEP_TOGETHER_MAX_ITEMS;

  const intro = (
    <View style={styles.grupoIntro} wrap={false}>
      <Text style={styles.grupoTitle}>{g.nombreGrupo}</Text>
      <Text style={styles.inspectorsLine}>
        <Text style={styles.inspectorsPrefix}>Inspectores: </Text>
        <Text style={styles.inspectorsNames}>
          {g.inspectores.length
            ? g.inspectores.map((i) => `${i.nombreCompleto} (Af. ${i.numeroAfiliado})`).join(" · ")
            : "—"}
        </Text>
      </Text>
    </View>
  );

  const tabla =
    g.items.length === 0 ? (
      <Text style={styles.emptyGrupoNote}>Sin ítems asignados.</Text>
    ) : (
      <View>
        <GrupoTableHeader />
        {g.items.map((it) => (
          <GrupoItemRow key={it.itemId} it={it} />
        ))}
      </View>
    );

  if (keepTogether) {
    return (
      <View style={styles.grupoBlock} wrap={false}>
        {intro}
        {tabla}
      </View>
    );
  }

  return (
    <View style={styles.grupoBlock}>
      {intro}
      {tabla}
    </View>
  );
}

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
          <GrupoResumenBlock key={g.grupoId} g={g} />
        ))}

        <Text style={styles.obsSectionTitle}>Observaciones</Text>
        <Text style={styles.obs}>{(model.observaciones ?? "").trim() || "—"}</Text>
      </Page>
    </Document>
  );
}

