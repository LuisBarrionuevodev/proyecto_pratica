import { Document, Image, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

import {
  INSTITUTIONAL_DIRECTION_LINE,
  INSTITUTIONAL_SECRETARY_LINE,
  ORDEN_TRABAJO_DEPARTAMENTAL_ADDRESS_LINE,
  ORDEN_TRABAJO_DEPARTAMENTAL_CIERRE,
  ORDEN_TRABAJO_DEPARTAMENTAL_INSTRUCCIONES,
  ORDEN_TRABAJO_DEPARTAMENTAL_MUNICIPALITY,
} from "../core/institutionalCopy";
import { PDF_DESIGN_FONT, pdfPlanilla } from "../core/pdfDesignTokens";
import { PDF_FONT_ARCHIVO_BLACK } from "../core/registerPdfFonts";
import type {
  OrdenTrabajoDepartamentalDocumentModel,
  OrdenTrabajoDepartamentalFila,
} from "../types/ordenTrabajoDepartamentalDocument";

/** Órdenes por hoja A4 (media hoja c/u). */
const ORDENES_POR_PAGINA = 2;

/** Zona de corte entre órdenes consecutivas en la misma hoja: 5 mm. */
const CORTE_ENTRE_ORDENES_PT = (5 / 25.4) * 72;

/** Desplazamiento vertical del N° de OT respecto al encabezado. */
const OT_NUM_TOP_OFFSET_PT = (3 / 25.4) * 72;

/** Márgenes de página (pt). */
const PAGE_PAD_TOP = 6;
const PAGE_PAD_BOTTOM = 6;
const PAGE_PAD_H = 18;

/** Alto A4 en puntos (react-pdf). */
const A4_HEIGHT_PT = 842;

/**
 * Altura fija de cada bloque de orden (~media hoja A4 con 2 por página).
 */
const ORDEN_ALTURA_PT = 408;

/** Espacio vacío al pie de la hoja para que una sola orden no se estire. */
function pageBottomSpacerHeight(ordenesEnPagina: number): number {
  const ordersHeight = ordenesEnPagina * ORDEN_ALTURA_PT;
  const cutHeight = ordenesEnPagina > 1 ? CORTE_ENTRE_ORDENES_PT : 0;
  const used = PAGE_PAD_TOP + PAGE_PAD_BOTTOM + ordersHeight + cutHeight;
  return Math.max(1, A4_HEIGHT_PT - used);
}

const INK = pdfPlanilla.ink;

const styles = StyleSheet.create({
  page: {
    paddingTop: PAGE_PAD_TOP,
    paddingBottom: PAGE_PAD_BOTTOM,
    paddingHorizontal: PAGE_PAD_H,
    backgroundColor: "#ffffff",
    fontFamily: PDF_DESIGN_FONT.ui,
    color: INK,
  },
  ordenSlot: {
    height: ORDEN_ALTURA_PT,
    maxHeight: ORDEN_ALTURA_PT,
    flexGrow: 0,
    flexShrink: 0,
  },
  cutLineWrap: {
    height: CORTE_ENTRE_ORDENES_PT,
    flexGrow: 0,
    flexShrink: 0,
    justifyContent: "center",
  },
  ordenBlock: {
    height: ORDEN_ALTURA_PT,
    maxHeight: ORDEN_ALTURA_PT,
    flexGrow: 0,
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
  },
  cutLine: {
    borderTopWidth: 1,
    borderTopColor: "#888888",
    borderStyle: "dashed",
  },
  headerZone: {
    position: "relative",
    alignItems: "center",
    marginBottom: 4,
    paddingTop: 0,
  },
  otNumWrap: {
    position: "absolute",
    top: OT_NUM_TOP_OFFSET_PT,
    right: 0,
    alignItems: "flex-end",
  },
  otNumInline: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 15,
    fontWeight: 700,
    lineHeight: 1.1,
    textAlign: "right",
  },
  otNumRule: {
    marginTop: 2,
    width: "100%",
    minWidth: 72,
    borderBottomWidth: 1,
    borderBottomColor: INK,
    borderStyle: "dashed",
    minHeight: 1,
  },
  headerMunicipality: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    letterSpacing: 0.2,
    marginTop: 0,
  },
  headerInstitutionLine: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9.5,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    letterSpacing: 0.15,
    marginTop: 2,
  },
  headerLineSecondary: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    marginTop: 1,
  },
  headerAddress: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 700,
    textAlign: "center",
    marginTop: 1,
    lineHeight: 1.1,
  },
  logo: {
    width: 44,
    height: 44,
    marginTop: 2,
    marginBottom: 3,
    objectFit: "contain",
  },
  docTitle: {
    fontFamily: PDF_FONT_ARCHIVO_BLACK,
    fontSize: 11.5,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    textDecoration: "underline",
    marginBottom: 5,
    lineHeight: 1.1,
  },
  mainBox: {
    flexGrow: 0,
    flexShrink: 0,
    height: 296,
    borderWidth: 1.5,
    borderColor: INK,
    paddingHorizontal: 10,
    paddingTop: 9,
    paddingBottom: 8,
    display: "flex",
    flexDirection: "column",
  },
  mainBoxTop: {
    flexShrink: 0,
  },
  fieldRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginBottom: 5,
    gap: 4,
  },
  fieldRowSplit: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginBottom: 5,
    gap: 10,
  },
  fieldHalf: {
    flex: 1,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 3,
  },
  fieldLabel: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 11,
    fontWeight: 700,
    textTransform: "uppercase",
    lineHeight: 1.15,
  },
  dottedValueWrap: {
    flex: 1,
    borderBottomWidth: 1,
    borderBottomColor: INK,
    borderStyle: "dashed",
    minHeight: 18,
    justifyContent: "flex-end",
    paddingBottom: 1,
  },
  fieldValue: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 11,
    lineHeight: 1.3,
  },
  domicilioBlock: {
    marginTop: 2,
    marginBottom: 2,
  },
  /** ~3 filas punteadas vacías bajo domicilio (anotaciones manuales). */
  anotacionBlock: {
    marginTop: 3,
    marginBottom: 4,
  },
  anotacionLine: {
    borderBottomWidth: 1,
    borderBottomColor: INK,
    borderStyle: "dashed",
    minHeight: 15,
    marginBottom: 6,
  },
  /** Espacio libre bajo la leyenda (firma/anotaciones). */
  signatureSpace: {
    flexGrow: 0,
    flexShrink: 0,
    height: 28,
  },
  instrucciones: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8.75,
    fontWeight: 700,
    textTransform: "uppercase",
    textAlign: "center",
    lineHeight: 1.25,
    marginTop: 2,
    marginBottom: 0,
  },
  cierre: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9.25,
    fontWeight: 700,
    textTransform: "uppercase",
    textAlign: "center",
    lineHeight: 1.2,
    flexShrink: 0,
  },
  emptyText: {
    marginTop: 24,
    fontSize: 10,
    fontFamily: PDF_DESIGN_FONT.ui,
    color: "#666666",
    textAlign: "center",
  },
});

function chunkOrdenes<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    out.push(items.slice(i, i + size));
  }
  return out;
}

function EncabezadoInstitucional({
  numeroOt,
  logoSrc,
}: {
  numeroOt?: string;
  logoSrc: string;
}) {
  return (
    <View style={styles.headerZone}>
      {numeroOt ? (
        <View style={styles.otNumWrap}>
          <Text style={styles.otNumInline}>N° {numeroOt}</Text>
          <View style={styles.otNumRule} />
        </View>
      ) : null}

      <Text style={styles.headerMunicipality}>{ORDEN_TRABAJO_DEPARTAMENTAL_MUNICIPALITY}</Text>
      <Image src={logoSrc} style={styles.logo} />
      <Text style={styles.headerInstitutionLine}>{INSTITUTIONAL_DIRECTION_LINE.toUpperCase()}</Text>
      <Text style={styles.headerLineSecondary}>{INSTITUTIONAL_SECRETARY_LINE.toUpperCase()}</Text>
      <Text style={styles.headerAddress}>{ORDEN_TRABAJO_DEPARTAMENTAL_ADDRESS_LINE}</Text>
    </View>
  );
}

function CampoPunteado({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fieldRow}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.dottedValueWrap}>
        <Text style={styles.fieldValue}>{value}</Text>
      </View>
    </View>
  );
}

function LineaCorte() {
  return (
    <View style={styles.cutLineWrap}>
      <View style={styles.cutLine} />
    </View>
  );
}

const FILAS_ANOTACION = 3;

function LineasAnotacionVacias() {
  return (
    <View style={styles.anotacionBlock}>
      {Array.from({ length: FILAS_ANOTACION }, (_, i) => (
        <View key={`anot-${i}`} style={styles.anotacionLine} />
      ))}
    </View>
  );
}

type CardProps = {
  orden: OrdenTrabajoDepartamentalFila;
  logoSrc: string;
};

function OrdenTrabajoDepartamentalCard({ orden, logoSrc }: CardProps) {
  return (
    <View style={styles.ordenBlock} wrap={false}>
      <EncabezadoInstitucional numeroOt={orden.numeroOt} logoSrc={logoSrc} />

      <Text style={styles.docTitle}>ORDEN DE TRABAJO DEPARTAMENTAL</Text>

      <View style={styles.mainBox}>
        <View style={styles.mainBoxTop}>
          <CampoPunteado label="INSPECTORES:" value={orden.inspectoresTexto} />

          <View style={styles.fieldRowSplit}>
            <View style={styles.fieldHalf}>
              <Text style={styles.fieldLabel}>TURNO:</Text>
              <View style={styles.dottedValueWrap}>
                <Text style={styles.fieldValue}>{orden.turnoLegible}</Text>
              </View>
            </View>
            <View style={styles.fieldHalf}>
              <Text style={styles.fieldLabel}>FECHA:</Text>
              <View style={styles.dottedValueWrap}>
                <Text style={styles.fieldValue}>{orden.fechaLegible}</Text>
              </View>
            </View>
          </View>

          <View style={styles.domicilioBlock}>
            <CampoPunteado label="DOMICILIO:" value={orden.domicilioLinea} />
          </View>

          <LineasAnotacionVacias />
        </View>

        <Text style={styles.instrucciones}>{ORDEN_TRABAJO_DEPARTAMENTAL_INSTRUCCIONES}</Text>

        <View style={styles.signatureSpace} />
        <Text style={styles.cierre}>{ORDEN_TRABAJO_DEPARTAMENTAL_CIERRE}</Text>
      </View>
    </View>
  );
}

type Props = {
  model: OrdenTrabajoDepartamentalDocumentModel;
  /** Mismo logo institucional que Orden de Salida (`logo-smt.png`). */
  logoSrc: string;
};

/**
 * PDF de Órdenes de Trabajo Departamentales: formulario institucional; 2 por hoja A4.
 */
export function OrdenTrabajoDepartamentalPdfDocument({ model, logoSrc }: Props) {
  const paginas = chunkOrdenes(model.ordenes, ORDENES_POR_PAGINA);

  if (model.ordenes.length === 0) {
    return (
      <Document
        title={`Órdenes de trabajo departamental ruta ${model.numeroRuta}`}
        author={INSTITUTIONAL_DIRECTION_LINE}
      >
        <Page size="A4" style={styles.page}>
          <EncabezadoInstitucional logoSrc={logoSrc} />
          <Text style={styles.emptyText}>
            No hay ítems con orden de trabajo asignada en esta ruta.
          </Text>
        </Page>
      </Document>
    );
  }

  return (
    <Document
      title={`Órdenes de trabajo departamental ruta ${model.numeroRuta}`}
      author={INSTITUTIONAL_DIRECTION_LINE}
      subject={`Ruta ${model.numeroRuta} — OT departamental`}
    >
      {paginas.map((grupo, pageIdx) => (
        <Page key={`ot-dep-${pageIdx}`} size="A4" style={styles.page} wrap={false}>
          {grupo.map((orden, idx) => (
            <View key={orden.itemId} wrap={false}>
              {idx > 0 ? <LineaCorte /> : null}
              <View style={styles.ordenSlot}>
                <OrdenTrabajoDepartamentalCard orden={orden} logoSrc={logoSrc} />
              </View>
            </View>
          ))}
          <View style={{ height: pageBottomSpacerHeight(grupo.length) }} />
        </Page>
      ))}
    </Document>
  );
}
