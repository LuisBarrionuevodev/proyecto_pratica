import { Image, StyleSheet, Text, View } from "@react-pdf/renderer";

import {
  INSTITUTIONAL_CITY_LINE,
  INSTITUTIONAL_DIRECTION_LINE,
  INSTITUTIONAL_SECRETARY_LINE,
} from "./institutionalCopy";
import { PDF_DESIGN_COLORS } from "./pdfDesignTokens";
import { PDF_FONT_CARLITO, PDF_FONT_LIBRE_BASKERVILLE } from "./registerPdfFonts";

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: PDF_DESIGN_COLORS.separatorBlue,
    paddingBottom: 8,
  },
  logo: {
    width: 52,
    height: 52,
    marginRight: 12,
    objectFit: "contain",
  },
  textCol: {
    flex: 1,
    flexDirection: "column",
  },
  city: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 9,
    color: PDF_DESIGN_COLORS.textSecondary,
    marginBottom: 2,
  },
  secretary: {
    fontFamily: PDF_FONT_LIBRE_BASKERVILLE,
    fontSize: 10,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.sectionDarkBlue,
    marginBottom: 2,
  },
  direction: {
    fontFamily: PDF_FONT_CARLITO,
    fontSize: 10,
    fontWeight: 700,
    color: PDF_DESIGN_COLORS.textPrimary,
  },
});

type DocumentHeaderPdfProps = {
  /** URL del logo (PNG recomendado para embebido fiable en PDF). */
  logoSrc: string | null;
};

/**
 * Membrete reutilizable para PDFs de resumen (logo + líneas Secretaría / Dirección).
 * Requiere `registerDocumentosPdfFonts()` antes de renderizar.
 */
export function DocumentHeaderPdf({ logoSrc }: DocumentHeaderPdfProps) {
  return (
    <View style={styles.row} fixed>
      {logoSrc ? (
        <Image src={logoSrc} style={styles.logo} />
      ) : (
        <View style={[styles.logo, { backgroundColor: PDF_DESIGN_COLORS.grupoCardBg }]} />
      )}
      <View style={styles.textCol}>
        <Text style={styles.city}>{INSTITUTIONAL_CITY_LINE}</Text>
        <Text style={styles.secretary}>{INSTITUTIONAL_SECRETARY_LINE}</Text>
        <Text style={styles.direction}>{INSTITUTIONAL_DIRECTION_LINE}</Text>
      </View>
    </View>
  );
}
