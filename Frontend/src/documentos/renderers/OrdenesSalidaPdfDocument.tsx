import { Document, Image, Line, Page, StyleSheet, Svg, Text, View } from "@react-pdf/renderer";

import { INSTITUTIONAL_DIRECTION_LINE } from "../core/institutionalCopy";
import { PDF_DESIGN_COLORS, PDF_DESIGN_FONT, pdfInformePage, pdfPlanilla } from "../core/pdfDesignTokens";
import { PDF_FONT_ARCHIVO_BLACK, PDF_FONT_LIBRE_BASKERVILLE } from "../core/registerPdfFonts";
import type { RutaDocumentoInspectorSalida, RutaPublicadaDocumentModel } from "../types/rutaPublicadaDocument";
import { fechaOrdenSalidaLegible } from "../utils/fechaOrdenSalida";

/** Máximo de órdenes distintas (inspectores) por hoja A4. */
const ORDENES_POR_PAGINA = 3;

const styles = StyleSheet.create({
  page: {
    ...pdfInformePage,
    paddingTop: 10,
    paddingBottom: 4,
    paddingHorizontal: 22,
  },
  bloqueInspector: {
    width: "100%",
  },
  /** Línea suave + aire antes del logo cuando hay otra orden arriba en la misma hoja. */
  bloqueTrasOtra: {
    marginTop: 4,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: PDF_DESIGN_COLORS.separatorBlue,
  },
  /** Solo entre dos órdenes consecutivas (no bajo la última de la página: evita hueco al pie). */
  bloqueMargenAntesDeSiguiente: {
    marginBottom: 12,
  },
  headerTop: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 3,
  },
  logo: {
    width: 34,
    height: 34,
    marginRight: 8,
    objectFit: "contain",
  },
  municipalTitle: {
    flex: 1,
    fontFamily: PDF_FONT_LIBRE_BASKERVILLE,
    fontSize: 10,
    fontWeight: 700,
    textAlign: "center",
    color: PDF_DESIGN_COLORS.sectionDarkBlue,
  },
  titleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginBottom: 4,
  },
  ordenTitulo: {
    fontFamily: PDF_FONT_ARCHIVO_BLACK,
    fontSize: 9,
    textTransform: "uppercase",
    maxWidth: "52%",
    lineHeight: 1.12,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  fechaLine: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10.5,
    fontWeight: 700,
    maxWidth: "48%",
    textAlign: "right",
    lineHeight: 1.2,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  tableOuter: {
    borderWidth: 1.5,
    borderColor: pdfPlanilla.ink,
  },
  headerCellsRow: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: pdfPlanilla.ink,
    minHeight: 28,
  },
  dataCellsRow: {
    flexDirection: "row",
    alignItems: "stretch",
    minHeight: 66,
  },
  thCell: {
    borderRightWidth: 1,
    borderRightColor: pdfPlanilla.ink,
    padding: 3,
    justifyContent: "center",
  },
  thText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 700,
    textAlign: "center",
    lineHeight: 1.1,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  tdCell: {
    borderRightWidth: 1,
    borderRightColor: pdfPlanilla.ink,
    padding: 4,
    justifyContent: "flex-start",
  },
  tdText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8.5,
    lineHeight: 1.2,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  tdTextAfiliado: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10.5,
    fontWeight: 700,
    lineHeight: 1.15,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  /** Inspector: sin negrita, tamaño moderado para que entren 3 órdenes por hoja. */
  tdTextNombreInspector: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 10.5,
    fontWeight: 400,
    lineHeight: 1.15,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  colAfiliado: { width: "11%" },
  colNombre: { width: "23%" },
  colMotivo: { width: "43%", flexDirection: "column", borderRightWidth: 1, borderRightColor: pdfPlanilla.ink },
  colHoraSal: { width: "11.5%" },
  colHoraReg: { width: "11.5%" },
  motivoGridRow: {
    flexDirection: "row",
    alignItems: "stretch",
    borderBottomWidth: 1,
    borderBottomColor: pdfPlanilla.ink,
    minHeight: 18,
  },
  /** Fila Oficial: direcciones compactas para 3 órdenes por hoja. */
  motivoGridRowOficial: {
    flexDirection: "row",
    alignItems: "stretch",
    borderBottomWidth: 1,
    borderBottomColor: pdfPlanilla.ink,
    minHeight: 27,
  },
  motivoGridRowLast: {
    flexDirection: "row",
    alignItems: "stretch",
    minHeight: 18,
  },
  motivoLabelCol: {
    width: "38%",
    padding: 3,
    justifyContent: "center",
  },
  motivoLabelText: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 8,
    lineHeight: 1.2,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  motivoCheckCol: {
    width: "12%",
    justifyContent: "center",
    alignItems: "center",
    borderLeftWidth: 1,
    borderLeftColor: pdfPlanilla.ink,
  },
  motivoValueCol: {
    flex: 1,
    borderLeftWidth: 1,
    borderLeftColor: pdfPlanilla.ink,
    padding: 4,
    justifyContent: "flex-start",
  },
  textoDirecciones: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.25,
    fontWeight: 400,
    lineHeight: 1.28,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  checkBox: {
    width: 10,
    height: 10,
    borderWidth: 1,
    borderColor: pdfPlanilla.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  horaTh: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    fontWeight: 700,
    textAlign: "center",
    lineHeight: 1.05,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  horaBody: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 9,
    textAlign: "center",
    marginTop: 6,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  firmasWrap: {
    marginTop: 28,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingHorizontal: 10,
    width: "100%",
  },
  /** Columnas algo más angostas: `space-between` deja más aire entre una firma y la otra. */
  firmaCol: {
    width: "27%",
    alignItems: "center",
  },
  /** Franja en blanco encima de la raya para que quepa la firma manuscrita. */
  firmaSpacer: {
    minHeight: 16,
    width: "100%",
  },
  firmaLine: {
    borderTopWidth: 1,
    borderTopColor: pdfPlanilla.ink,
    width: "100%",
    marginTop: 2,
    paddingTop: 5,
  },
  firmaLabel: {
    fontFamily: PDF_DESIGN_FONT.ui,
    fontSize: 7.5,
    fontWeight: 700,
    textAlign: "center",
    marginTop: 4,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
  emptyInspectoresText: {
    marginTop: 12,
    fontSize: 10,
    fontFamily: PDF_DESIGN_FONT.ui,
    color: PDF_DESIGN_COLORS.textMuted,
  },
});

function chunkInspectores<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    out.push(items.slice(i, i + size));
  }
  return out;
}

/**
 * Casilla tipo formulario. La marca «X» se dibuja con SVG: el texto en cuadros
 * muy chicos suele no renderizarse en @react-pdf/renderer.
 */
function CheckCuadrado({ marcado }: { marcado: boolean }) {
  if (!marcado) {
    return <View style={styles.checkBox} />;
  }
  const stroke = pdfPlanilla.ink;
  return (
    <View style={styles.checkBox}>
      <Svg width={8} height={8} viewBox="0 0 10 10">
        <Line x1="1.5" y1="1.5" x2="8.5" y2="8.5" stroke={stroke} strokeWidth={1.2} />
        <Line x1="8.5" y1="1.5" x2="1.5" y2="8.5" stroke={stroke} strokeWidth={1.2} />
      </Svg>
    </View>
  );
}

type OrdenUnInspectorProps = {
  logoSrc: string;
  fechaCuerpo: string;
  inspector: RutaDocumentoInspectorSalida;
  /** 2.ª y 3.ª orden en la hoja: división clara antes del membrete/logo. */
  separarArriba?: boolean;
  /** Aire debajo de esta orden antes de la siguiente (no en la última del bloque). */
  margenAntesDeSiguiente?: boolean;
};

/**
 * Una orden de salida completa (un inspector), plantilla municipal.
 */
function OrdenUnInspector({
  logoSrc,
  fechaCuerpo,
  inspector,
  separarArriba = false,
  margenAntesDeSiguiente = false,
}: OrdenUnInspectorProps) {
  const distritosTexto = inspector.distritosTexto?.trim() || "—";

  return (
    <View
      style={[
        styles.bloqueInspector,
        ...(separarArriba ? [styles.bloqueTrasOtra] : []),
        ...(margenAntesDeSiguiente ? [styles.bloqueMargenAntesDeSiguiente] : []),
      ]}
      wrap={false}
    >
      <View style={styles.headerTop}>
        <Image src={logoSrc} style={styles.logo} />
        <Text style={styles.municipalTitle}>Municipalidad de San Miguel de Tucumán</Text>
      </View>

      <View style={styles.titleRow}>
        <Text style={styles.ordenTitulo}>ORDEN DE SALIDA DEL PERSONAL</Text>
        <Text style={styles.fechaLine}>FECHA: {fechaCuerpo}</Text>
      </View>

      <View style={styles.tableOuter}>
        <View style={styles.headerCellsRow}>
          <View style={[styles.thCell, styles.colAfiliado]}>
            <Text style={styles.thText}>
              N° de{"\n"}Afiliado
            </Text>
          </View>
          <View style={[styles.thCell, styles.colNombre]}>
            <Text style={styles.thText}>Apellido y Nombre</Text>
          </View>
          <View style={[styles.thCell, styles.colMotivo]}>
            <Text style={styles.thText}>Motivo de salida</Text>
          </View>
          <View style={[styles.thCell, styles.colHoraSal]}>
            <Text style={styles.horaTh}>
              Hora de{"\n"}Salida
            </Text>
          </View>
          <View style={[styles.thCell, styles.colHoraReg, { borderRightWidth: 0 }]}>
            <Text style={styles.horaTh}>
              Hora de{"\n"}Regreso
            </Text>
          </View>
        </View>

        <View style={styles.dataCellsRow}>
          <View style={[styles.tdCell, styles.colAfiliado]}>
            <Text style={styles.tdTextAfiliado}>{inspector.numeroAfiliado}</Text>
          </View>
          <View style={[styles.tdCell, styles.colNombre]}>
            <Text style={styles.tdTextNombreInspector}>{inspector.nombreCompleto}</Text>
          </View>

          <View style={styles.colMotivo}>
            <View style={styles.motivoGridRow}>
              <View style={styles.motivoLabelCol}>
                <Text style={styles.motivoLabelText}>Particular{"\n"}(Dto. 1020)</Text>
              </View>
              <View style={styles.motivoCheckCol}>
                <CheckCuadrado marcado={false} />
              </View>
              <View style={styles.motivoValueCol}>
                <Text style={styles.motivoLabelText}> </Text>
              </View>
            </View>
            <View style={styles.motivoGridRowOficial}>
              <View style={styles.motivoLabelCol}>
                <Text style={styles.motivoLabelText}>Oficial{"\n"}(Dto. 1020)</Text>
              </View>
              <View style={styles.motivoCheckCol}>
                <CheckCuadrado marcado />
              </View>
              <View style={styles.motivoValueCol}>
                <Text style={styles.textoDirecciones}>{distritosTexto}</Text>
              </View>
            </View>
            <View style={styles.motivoGridRowLast}>
              <View style={styles.motivoLabelCol}>
                <Text style={styles.motivoLabelText}>Crédito Horario Gremial{"\n"}(Dto. 1330)</Text>
              </View>
              <View style={styles.motivoCheckCol}>
                <CheckCuadrado marcado={false} />
              </View>
              <View style={styles.motivoValueCol}>
                <Text style={styles.motivoLabelText}> </Text>
              </View>
            </View>
          </View>

          <View style={[styles.tdCell, styles.colHoraSal, { justifyContent: "flex-start", alignItems: "center" }]}>
            <Text style={styles.horaBody}> </Text>
          </View>
          <View
            style={[
              styles.tdCell,
              styles.colHoraReg,
              { borderRightWidth: 0, justifyContent: "flex-start", alignItems: "center" },
            ]}
          >
            <Text style={styles.horaBody}>s/r</Text>
          </View>
        </View>
      </View>

      <View style={styles.firmasWrap}>
        <View style={styles.firmaCol}>
          <View style={styles.firmaSpacer} />
          <View style={styles.firmaLine} />
          <Text style={styles.firmaLabel}>Agente</Text>
        </View>
        <View style={styles.firmaCol}>
          <View style={styles.firmaSpacer} />
          <View style={styles.firmaLine} />
          <Text style={styles.firmaLabel}>Jefe de Personal</Text>
        </View>
        <View style={styles.firmaCol}>
          <View style={styles.firmaSpacer} />
          <View style={styles.firmaLine} />
          <Text style={styles.firmaLabel}>Director/Subdirector</Text>
        </View>
      </View>
    </View>
  );
}

type Props = {
  model: RutaPublicadaDocumentModel;
  logoSrc: string;
};

/**
 * PDF de órdenes de salida: una orden por inspector; hasta {ORDENES_POR_PAGINA} órdenes por hoja A4.
 * Fuentes: Libre Baskerville, Archivo Black, Carlito (registradas antes de renderizar).
 */
export function OrdenesSalidaPdfDocument({ model, logoSrc }: Props) {
  const fechaCuerpo = fechaOrdenSalidaLegible(model.fechaIso);
  const paginas = chunkInspectores(model.inspectoresSalida, ORDENES_POR_PAGINA);

  if (model.inspectoresSalida.length === 0) {
    return (
      <Document title={`Órdenes de salida ruta ${model.numeroRuta}`} author={INSTITUTIONAL_DIRECTION_LINE}>
        <Page size="A4" style={styles.page}>
          <View style={styles.headerTop}>
            <Image src={logoSrc} style={styles.logo} />
            <Text style={styles.municipalTitle}>Municipalidad de San Miguel de Tucumán</Text>
          </View>
          <Text style={styles.emptyInspectoresText}>No hay inspectores asignados a grupos en esta ruta.</Text>
        </Page>
      </Document>
    );
  }

  return (
    <Document
      title={`Órdenes de salida ruta ${model.numeroRuta}`}
      author={INSTITUTIONAL_DIRECTION_LINE}
      subject={`Ruta ${model.numeroRuta} — personal`}
    >
      {paginas.map((grupo, pageIdx) => (
        <Page key={`p-${pageIdx}`} size="A4" style={styles.page}>
          {grupo.map((insp, idxEnPagina) => (
            <OrdenUnInspector
              key={insp.inspectorId}
              logoSrc={logoSrc}
              fechaCuerpo={fechaCuerpo}
              inspector={insp}
              separarArriba={idxEnPagina > 0}
              margenAntesDeSiguiente={idxEnPagina < grupo.length - 1}
            />
          ))}
        </Page>
      ))}
    </Document>
  );
}
