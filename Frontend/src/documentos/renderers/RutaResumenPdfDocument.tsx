import { Document, Page, StyleSheet, Text, View, Image } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import { PDF_FONT_CARLITO, PDF_FONT_LIBRE_BASKERVILLE } from "../core/registerPdfFonts";
import type { RutaPublicadaDocumentModel } from "../types/rutaPublicadaDocument";

const styles = StyleSheet.create({
  page: {
    paddingTop: 24,
    paddingBottom: 28,
    paddingHorizontal: 36,
    fontSize: 9,
    fontFamily: PDF_FONT_CARLITO,
    fontStyle: "normal",
    fontWeight: 400,
    color: "#111",
  },
  membreteImg: {
    width: "100%",
    height: 58,
    objectFit: "contain",
    marginBottom: 12,
  },
  title: {
    fontFamily: PDF_FONT_LIBRE_BASKERVILLE,
    fontSize: 13,
    fontWeight: 700,
    fontStyle: "normal",
    marginBottom: 10,
    color: "#1a237e",
  },
  metaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginBottom: 6,
  },
  metaBox: {
    minWidth: 120,
    marginRight: 14,
    marginBottom: 6,
  },
  metaLabel: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 7,
    fontWeight: 400,
    fontStyle: "normal",
    color: "#555",
    textTransform: "uppercase",
    marginBottom: 2,
  },
  metaValue: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 10,
    fontWeight: 700,
    fontStyle: "normal",
  },
  sectionTitle: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 10,
    fontWeight: 700,
    fontStyle: "normal",
    marginTop: 12,
    marginBottom: 6,
    borderBottomWidth: 0.5,
    borderBottomColor: "#ccc",
    paddingBottom: 3,
  },
  mapWrap: {
    marginTop: 8,
    marginBottom: 10,
    alignItems: "center",
    width: "100%",
  },
  /** Ancho fijo en pt: porcentajes en Image suelen fallar en react-pdf/yoga. */
  mapImg: {
    width: 518,
    height: 188,
    objectFit: "contain",
    borderWidth: 0.5,
    borderColor: "#999",
  },
  mapCaption: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 7,
    fontWeight: 400,
    fontStyle: "normal",
    color: "#666",
    marginTop: 4,
    textAlign: "center",
  },
  grupoBlock: {
    marginBottom: 10,
    padding: 8,
    borderWidth: 0.5,
    borderColor: "#ddd",
    backgroundColor: "#fafafa",
  },
  grupoTitle: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 10,
    fontWeight: 700,
    fontStyle: "normal",
    marginBottom: 4,
  },
  small: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 8,
    fontStyle: "normal",
    lineHeight: 1.35,
    marginBottom: 2,
  },
  tableHeader: {
    flexDirection: "row",
    borderBottomWidth: 0.5,
    borderBottomColor: "#333",
    paddingBottom: 3,
    marginTop: 4,
    fontFamily: PDF_FONT_CARLITO,
    fontWeight: 700,
    fontStyle: "normal",
    fontSize: 7,
  },
  tableRow: {
    flexDirection: "row",
    borderBottomWidth: 0.3,
    borderBottomColor: "#ddd",
    paddingVertical: 3,
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 7,
    fontStyle: "normal",
  },
  /** "OT" ancho fijo para que no se recorte (evitar "O.T." con glifos raros en PDF). */
  colOrd: { width: "7%" },
  colDom: { width: "36%" },
  colDist: { width: "16%" },
  colRub: { width: "16%" },
  colOt: { width: "25%" },
  obs: {
    marginTop: 8,
    fontSize: 8,
    lineHeight: 1.4,
  },
});

type Props = {
  model: RutaPublicadaDocumentModel;
  /** Membrete institucional (PNG) encabezado del documento. */
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

        <View style={styles.metaRow}>
          <View style={styles.metaBox}>
            <Text style={styles.metaLabel}>Número de ruta</Text>
            <Text style={styles.metaValue}>{model.numeroRuta}</Text>
          </View>
          <View style={styles.metaBox}>
            <Text style={styles.metaLabel}>Fecha operativa</Text>
            <Text style={styles.metaValue}>{model.fechaLegible}</Text>
          </View>
          <View style={styles.metaBox}>
            <Text style={styles.metaLabel}>Turno</Text>
            <Text style={styles.metaValue}>{model.turnoLegible}</Text>
          </View>
          <View style={styles.metaBox}>
            <Text style={styles.metaLabel}>Estado</Text>
            <Text style={styles.metaValue}>{model.estadoRuta}</Text>
          </View>
        </View>

        {model.displayName ? (
          <View style={{ marginBottom: 6 }}>
            <Text style={styles.metaLabel}>Denominación</Text>
            <Text style={styles.metaValue}>{model.displayName}</Text>
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
            <Text style={[styles.mapCaption, { color: "#888" }]}>
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
            <Text style={styles.small}>
              Inspectores:{" "}
              {g.inspectores.length
                ? g.inspectores.map((i) => `${i.nombreCompleto} (Af. ${i.numeroAfiliado})`).join(" · ")
                : "—"}
            </Text>
            <View style={styles.tableHeader}>
              <Text style={styles.colOrd}>Nº</Text>
              <Text style={styles.colDom}>Domicilio</Text>
              <Text style={styles.colDist}>Distrito</Text>
              <Text style={styles.colRub}>Rubro</Text>
              <Text style={styles.colOt}>OT</Text>
            </View>
            {g.items.length === 0 ? (
              <Text style={[styles.small, { marginTop: 4 }]}>Sin ítems asignados.</Text>
            ) : (
              g.items.map((it) => (
                <View key={it.itemId} style={styles.tableRow}>
                  <Text style={styles.colOrd}>{it.ordenVisita}</Text>
                  <Text style={styles.colDom}>{it.domicilioTexto}</Text>
                  <Text style={styles.colDist}>{it.distritoNombre ?? "—"}</Text>
                  <Text style={styles.colRub}>{it.rubroNombre ?? "—"}</Text>
                  <Text style={styles.colOt}>{it.ordenTrabajoLabel ?? "—"}</Text>
                </View>
              ))
            )}
          </View>
        ))}

        <Text style={styles.sectionTitle}>Observaciones</Text>
        <Text style={styles.obs}>{(model.observaciones ?? "").trim() || "—"}</Text>
      </Page>
    </Document>
  );
}
