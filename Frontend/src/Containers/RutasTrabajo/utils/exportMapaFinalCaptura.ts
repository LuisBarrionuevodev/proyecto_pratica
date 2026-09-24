import { toBlob } from "html-to-image";
import { saveAs } from "file-saver";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";

/**
 * Genera un nombre de archivo estable para la captura PNG tras publicar una ruta.
 *
 * @param ruta — Ruta cuyo número, id, fecha y turno se usan en el nombre.
 * @returns Nombre sugerido, sin caracteres problemáticos en Windows.
 */
export function buildMapaFinalCapturaFilename(ruta: IRutaTrabajo): string {
  const fecha = ruta.fecha.replace(/[^\d-]/g, "") || "fecha";
  const turno =
    ruta.turno === "MANIANA"
      ? "manana"
      : ruta.turno === "TARDE"
        ? "tarde"
        : String(ruta.turno).toLowerCase().replace(/[^a-z0-9_-]/gi, "-");
  const num = ruta.numero;
  const id = ruta.id;
  return `ruta-${num}-id${id}-${fecha}-${turno}-publicada.png`;
}

/**
 * Exporta un nodo DOM a PNG y dispara la descarga.
 *
 * Usa `html-to-image` (canvas vía SVG foreignObject). Los tiles del mapa pueden
 * quedar en blanco si no cargan con CORS adecuado o si el navegador bloquea
 * la serialización; en ese caso conviene reintentar o capturar manualmente.
 *
 * @param el — Contenedor a rasterizar (mapa + panel lateral + bloque operativo).
 * @param filename — Nombre del archivo descargado.
 * @throws Error si no se obtiene blob.
 */
export async function downloadMapaFinalRegionPng(el: HTMLElement, filename: string): Promise<void> {
  if (typeof document !== "undefined" && document.fonts?.ready) {
    await document.fonts.ready.catch(() => undefined);
  }

  const blob = await toBlob(el, {
    pixelRatio: 2,
    cacheBust: true,
    backgroundColor: "#12151a",
    filter: (node) => {
      if (!(node instanceof Element)) return true;
      if (node.classList.contains("leaflet-control-container")) return false;
      if (node.classList.contains("leaflet-popup")) return false;
      if (node.classList.contains("leaflet-popup-pane")) return false;
      return true;
    },
  });

  if (!blob) {
    throw new Error("La captura no produjo imagen.");
  }

  saveAs(blob, filename);
}
