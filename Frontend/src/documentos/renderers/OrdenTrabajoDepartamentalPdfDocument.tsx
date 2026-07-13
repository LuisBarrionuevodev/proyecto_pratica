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

import logoOtDepartamentalUrl from "../assets/logo-ot-departamental-isotipo.png?url";

/** Máximo de órdenes departamentales por hoja A4 (formato institucional compacto). */
const ORDENES_POR_PAGINA = 4;

const INK = pdfPlanilla.ink;

const styles = StyleSheet.create({
  page: {
    paddingTop: 8,
    paddingBottom: 6,
    paddingHorizontal: 16,
    backgroundColor: "#ffffff",
    fontFamily: PDF_DESIGN_FONT.ui,
    color: INK,
  },
  ordenBlock: {
    marginBottom: 5,
  },
  ordenBlockAfter: {
    marginTop: 4,
    paddingTop: 5,
    borderTopWidth: 0.5,
    borderTopColor: "#cccccc",
  },
  headerZone: {
    position: "relative",
    alignItems: "center",
    marginBottom: 2,
    paddingTop: 2,
  },
  otNumWrap: {
    position: "absolute",
    top: 0,
    right: 0,
    alignItems: "flex-end",
  },
  otNumInline: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 12,
    fontWeight: 700,
    lineHeight: 1.1,
    textAlign: "right",
  },
  otNumRule: {
    marginTop: 2,
    width: "100%",
    minWidth: 64,
    borderBottomWidth: 1,
    borderBottomColor: INK,
    borderStyle: "dashed",
    minHeight: 1,
  },
  headerLine: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 6.5,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    letterSpacing: 0.2,
    marginTop: 1,
  },
  headerInstitutionLine: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.5,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    letterSpacing: 0.15,
    marginTop: 1,
  },
  headerLineSecondary: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.25,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    lineHeight: 1.15,
    marginTop: 0.75,
  },
  headerAddress: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.25,
    fontWeight: 700,
    textAlign: "center",
    marginTop: 0.75,
    lineHeight: 1.1,
  },
  logo: {
    width: 54,
    height: 54,
    marginTop: 0,
    marginBottom: 1,
    objectFit: "contain",
  },
  docTitle: {
    fontFamily: PDF_FONT_ARCHIVO_BLACK,
    fontSize: 8.5,
    fontWeight: 700,
    textAlign: "center",
    textTransform: "uppercase",
    textDecoration: "underline",
    marginBottom: 3,
    lineHeight: 1.1,
  },
  mainBox: {
    borderWidth: 1.5,
    borderColor: INK,
    paddingHorizontal: 6,
    paddingTop: 5,
    paddingBottom: 4,
    minHeight: 118,
  },
  fieldRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginBottom: 3,
    gap: 2,
  },
  fieldRowSplit: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginBottom: 3,
    gap: 6,
  },
  fieldHalf: {
    flex: 1,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 2,
  },
  fieldLabel: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 700,
    textTransform: "uppercase",
    lineHeight: 1.1,
  },
  dottedValueWrap: {
    flex: 1,
    borderBottomWidth: 1,
    borderBottomColor: INK,
    borderStyle: "dashed",
    minHeight: 11,
    justifyContent: "flex-end",
    paddingBottom: 1,
  },
  fieldValue: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    lineHeight: 1.1,
  },
  domicilioBlock: {
    marginTop: 2,
    marginBottom: 4,
  },
  instrucciones: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 6.5,
    fontWeight: 700,
    textTransform: "uppercase",
    textAlign: "center",
    lineHeight: 1.18,
    marginTop: 2,
    marginBottom: 2,
  },
  cierre: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7,
    fontWeight: 700,
    textTransform: "uppercase",
    textAlign: "center",
    lineHeight: 1.15,
    marginTop: 1,
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

function EncabezadoInstitucional({ numeroOt }: { numeroOt?: string }) {
  return (
    <View style={styles.headerZone}>
      {numeroOt ? (
        <View style={styles.otNumWrap}>
          <Text style={styles.otNumInline}>N° {numeroOt}</Text>
          <View style={styles.otNumRule} />
        </View>
      ) : null}

      <Image src={logoOtDepartamentalUrl} style={styles.logo} />
      <Text style={styles.headerLine}>{ORDEN_TRABAJO_DEPARTAMENTAL_MUNICIPALITY}</Text>
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

type CardProps = {
  orden: OrdenTrabajoDepartamentalFila;
  separarArriba?: boolean;
};

function OrdenTrabajoDepartamentalCard({ orden, separarArriba = false }: CardProps) {
  return (
    <View
      style={[styles.ordenBlock, ...(separarArriba ? [styles.ordenBlockAfter] : [])]}
      wrap={false}
    >
      <EncabezadoInstitucional numeroOt={orden.numeroOt} />

      <Text style={styles.docTitle}>ORDEN DE TRABAJO DEPARTAMENTAL</Text>

      <View style={styles.mainBox}>
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

        <Text style={styles.instrucciones}>{ORDEN_TRABAJO_DEPARTAMENTAL_INSTRUCCIONES}</Text>
        <Text style={styles.cierre}>{ORDEN_TRABAJO_DEPARTAMENTAL_CIERRE}</Text>
      </View>
    </View>
  );
}

type Props = {
  model: OrdenTrabajoDepartamentalDocumentModel;
  /** Conservado por compatibilidad; el logo institucional OT usa asset propio. */
  logoSrc: string;
};

/**
 * PDF de Órdenes de Trabajo Departamentales: formulario institucional; hasta 4 por hoja A4.
 */
export function OrdenTrabajoDepartamentalPdfDocument({ model }: Props) {
  const paginas = chunkOrdenes(model.ordenes, ORDENES_POR_PAGINA);

  if (model.ordenes.length === 0) {
    return (
      <Document
        title={`Órdenes de trabajo departamental ruta ${model.numeroRuta}`}
        author={INSTITUTIONAL_DIRECTION_LINE}
      >
        <Page size="A4" style={styles.page}>
          <EncabezadoInstitucional />
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
        <Page key={`ot-dep-${pageIdx}`} size="A4" style={styles.page}>
          {grupo.map((orden, idx) => (
            <OrdenTrabajoDepartamentalCard key={orden.itemId} orden={orden} separarArriba={idx > 0} />
          ))}
        </Page>
      ))}
    </Document>
  );
}
