import { Font } from "@react-pdf/renderer";

import archivoBlackSrc from "../assets/fonts/ArchivoBlack-Regular.ttf?url";
import carlitoBoldItalicSrc from "../assets/fonts/Carlito-BoldItalic.ttf?url";
import carlitoBoldSrc from "../assets/fonts/Carlito-Bold.ttf?url";
import carlitoItalicSrc from "../assets/fonts/Carlito-Italic.ttf?url";
import carlitoRegularSrc from "../assets/fonts/Carlito-Regular.ttf?url";
import libreBaskervilleBoldSrc from "../assets/fonts/LibreBaskerville-Bold.ttf?url";
import libreBaskervilleRegularSrc from "../assets/fonts/LibreBaskerville-Regular.ttf?url";

/** Nombres de familia alineados a `StyleSheet` (espacios permitidos). */
export const PDF_FONT_LIBRE_BASKERVILLE = "Libre Baskerville";
export const PDF_FONT_ARCHIVO_BLACK = "Archivo Black";
export const PDF_FONT_CARLITO = "Carlito";

let registered = false;

/**
 * Registra fuentes empaquetadas en `documentos/assets/fonts/` para PDFs.
 * Idempotente: seguro llamar antes de cada `pdf().toBlob()`.
 */
export function registerDocumentosPdfFonts(): void {
  if (registered) return;
  registered = true;

  Font.register({
    family: PDF_FONT_LIBRE_BASKERVILLE,
    fonts: [
      { src: libreBaskervilleRegularSrc, fontWeight: 400, fontStyle: "normal" },
      { src: libreBaskervilleBoldSrc, fontWeight: 700, fontStyle: "normal" },
    ],
  });

  Font.register({
    family: PDF_FONT_ARCHIVO_BLACK,
    src: archivoBlackSrc,
  });

  Font.register({
    family: PDF_FONT_CARLITO,
    fonts: [
      { src: carlitoRegularSrc, fontWeight: 400, fontStyle: "normal" },
      { src: carlitoItalicSrc, fontWeight: 400, fontStyle: "italic" },
      { src: carlitoBoldSrc, fontWeight: 700, fontStyle: "normal" },
      { src: carlitoBoldItalicSrc, fontWeight: 700, fontStyle: "italic" },
    ],
  });
}
