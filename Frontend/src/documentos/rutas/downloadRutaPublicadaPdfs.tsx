import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import { apiClient } from "../../api/apiClient";
import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "../builders/buildRutaPublicadaDocumentModel";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { OrdenesSalidaPdfDocument } from "../renderers/OrdenesSalidaPdfDocument";
import { RutaResumenPdfDocument } from "../renderers/RutaResumenPdfDocument";
import { buildOsmStaticMapUrl, computeStaticMapView, fetchStaticMapAsDataUrl } from "./osmStaticMapImage";

import logoPngUrl from "../assets/logo-smt.png?url";
import membretePngUrl from "../assets/membrete-smt.png?url";

function buildRutaPdfBasename(ruta: IRutaTrabajo): string {
  const fecha = ruta.fecha.replace(/[^\d-]/g, "") || "fecha";
  const turno =
    ruta.turno === "MANIANA"
      ? "manana"
      : ruta.turno === "TARDE"
        ? "tarde"
        : String(ruta.turno).toLowerCase().replace(/[^a-z0-9_-]/gi, "-");
  return `ruta-${ruta.numero}-id${ruta.id}-${fecha}-${turno}`;
}

/**
 * Descarga el PDF «Resumen de ruta» (membrete + datos + mini-mapa estático OSM cuando aplique).
 */
export async function downloadRutaResumenPdf(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<void> {
  registerDocumentosPdfFonts();
  const model = buildRutaPublicadaDocumentModel(ruta, grupos, itemsActivos);
  const view = computeStaticMapView(model.puntosMapa);
  let mapImageDataUrl: string | null = null;
  if (view) {
    const size = { width: 520, height: 280 };
    const n = Math.min(view.markers.length, model.puntosMapa.length);
    const pinGrupo1Based =
      n > 0 ? model.puntosMapa.slice(0, n).map((p) => p.grupoIx + 1) : undefined;
    const pinOrden = n > 0 ? model.puntosMapa.slice(0, n).map((p) => p.ordenEnGrupo) : undefined;
    const apiBase = (apiClient.defaults.baseURL ?? "").replace(/\/+$/, "");
    const osmFull = buildOsmStaticMapUrl({ ...view, ...size, pinGrupo1Based, pinOrden });
    const search = new URL(osmFull).search;
    const proxyAbsoluteUrl = apiBase ? `${apiBase}/map/osm-static${search}` : null;
    const token = typeof localStorage !== "undefined" ? localStorage.getItem("access_token") : null;
    const proxyFetchInit: RequestInit | undefined = token
      ? { headers: { Authorization: `Bearer ${token}` } }
      : undefined;
    mapImageDataUrl = await fetchStaticMapAsDataUrl(view, size, {
      proxyAbsoluteUrl,
      proxyFetchInit,
      pinGrupo1Based,
      pinOrden,
    });
  }

  const blob = await pdf(
    <RutaResumenPdfDocument model={model} membreteSrc={membretePngUrl} mapImageDataUrl={mapImageDataUrl} />
  ).toBlob();

  saveAs(blob, `${buildRutaPdfBasename(ruta)}-resumen.pdf`);
}

/**
 * Descarga el PDF «Órdenes de salida del personal» (hasta 3 inspectores por hoja A4).
 */
export async function downloadOrdenesSalidaPdf(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<void> {
  registerDocumentosPdfFonts();
  const model = buildRutaPublicadaDocumentModel(ruta, grupos, itemsActivos);

  const blob = await pdf(<OrdenesSalidaPdfDocument model={model} logoSrc={logoPngUrl} />).toBlob();

  saveAs(blob, `${buildRutaPdfBasename(ruta)}-ordenes-salida.pdf`);
}
