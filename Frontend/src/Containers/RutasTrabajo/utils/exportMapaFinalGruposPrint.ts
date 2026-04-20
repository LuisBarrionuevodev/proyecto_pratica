import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import type { RutaMapaGrupoVista, RutaMapaInspectorFila, RutaMapaItemVista } from "../types/rutasTrabajoMapa.types";
import { buildGrupoCodigoPorId } from "./mapaRutaGrupoTrazado";

export type MapaFinalGruposPrintPayload = {
  ruta: IRutaTrabajo;
  gruposVista: RutaMapaGrupoVista[];
  estadoEtiqueta: string;
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function dash(s: string | null | undefined): string {
  const t = (s ?? "").trim();
  return t ? escapeHtml(t) : "—";
}

function turnoHumano(t: string): string {
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return escapeHtml(t);
}

/**
 * Título del documento (suele usarse como nombre sugerido al guardar como PDF desde el navegador).
 */
export function buildMapaFinalGruposPrintDocumentTitle(ruta: IRutaTrabajo): string {
  const fecha = ruta.fecha.replace(/[^\d-]/g, "") || "fecha";
  const turno =
    ruta.turno === "MANIANA"
      ? "manana"
      : ruta.turno === "TARDE"
        ? "tarde"
        : String(ruta.turno)
            .toLowerCase()
            .replace(/[^a-z0-9_-]/gi, "-");
  return `ruta-${ruta.numero}-id${ruta.id}-${fecha}-${turno}-grupos`;
}

function distritosDelGrupo(gv: RutaMapaGrupoVista): string {
  const set = new Set<string>();
  for (const it of gv.items) {
    const d = it.distritoNombre?.trim();
    if (d) set.add(d);
  }
  if (set.size === 0) return "—";
  return Array.from(set)
    .sort((a, b) => a.localeCompare(b, "es"))
    .map((x) => escapeHtml(x))
    .join(", ");
}

function inspectoresHtml(filas: RutaMapaInspectorFila[]): string {
  if (!filas.length) {
    return `<p class="meta-line">—</p>`;
  }
  return filas
    .map((f) => {
      const nom = escapeHtml(f.nombre);
      const leg = f.legajo?.trim();
      if (leg) {
        return `<p class="meta-line">${nom} <span class="muted">— Afiliado ${escapeHtml(leg)}</span></p>`;
      }
      return `<p class="meta-line">${nom}</p>`;
    })
    .join("");
}

function filasDireccionesHtml(items: RutaMapaItemVista[]): string {
  if (!items.length) {
    return `<p class="muted">Sin direcciones en este grupo.</p>`;
  }
  const head = `<thead><tr>
<th style="width:3em">N.º</th>
<th>Domicilio</th>
<th>Rubro</th>
<th>Tipo de iniciador</th>
<th>Orden de trabajo</th>
<th>Distrito</th>
</tr></thead>`;
  const body = items
    .map(
      (it) => `<tr>
<td>${it.orden}</td>
<td>${dash(it.etiqueta)}</td>
<td>${dash(it.rubroNombre)}</td>
<td>${dash(it.tipoIniciadorLabel)}</td>
<td>${dash(it.ordenTrabajoLabel)}</td>
<td>${dash(it.distritoNombre)}</td>
</tr>`
    )
    .join("");
  return `<table>${head}<tbody>${body}</tbody></table>`;
}

/**
 * HTML completo para ventana de impresión (A4, alto contraste, sin estilos de dashboard).
 */
export function buildMapaFinalGruposPrintHtml(payload: MapaFinalGruposPrintPayload): string {
  const { ruta, gruposVista, estadoEtiqueta } = payload;
  const docTitle = buildMapaFinalGruposPrintDocumentTitle(ruta);
  const nombreRuta =
    ruta.display_name != null && String(ruta.display_name).trim() !== ""
      ? escapeHtml(String(ruta.display_name).trim())
      : "—";

  const grupoIdsSorted = [...gruposVista.map((g) => g.id)].sort((a, b) => a - b);
  const codigoPorGrupo = buildGrupoCodigoPorId(grupoIdsSorted);

  const bloquesGrupo = gruposVista
    .map((gv) => {
      const codigo = codigoPorGrupo.get(gv.id) ?? "";
      const tituloGrupo = `${escapeHtml(gv.nombre)}${codigo ? ` <span class="muted">(${escapeHtml(codigo)})</span>` : ""}`;
      return `
<section class="grupo">
<h2>${tituloGrupo}</h2>
<div class="meta-grupo"><strong>Distrito(s) del grupo:</strong> ${distritosDelGrupo(gv)}</div>
<div class="inspectores-block">
<strong>Inspectores</strong>
${inspectoresHtml(gv.inspectoresFilas)}
</div>
<h3 class="direcciones-title">Direcciones</h3>
${filasDireccionesHtml(gv.items)}
</section>`;
    })
    .join("\n");

  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>${escapeHtml(docTitle)}</title>
<style>
@page { size: A4; margin: 12mm; }
* { box-sizing: border-box; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #111;
  background: #fff;
  font-size: 11pt;
  line-height: 1.35;
  margin: 0;
  padding: 0;
}
h1 { font-size: 15pt; font-weight: 700; margin: 0 0 6px; }
h2 { font-size: 12pt; font-weight: 700; margin: 0 0 8px; padding-bottom: 4px; border-bottom: 1px solid #bbb; }
h3.direcciones-title { font-size: 10.5pt; font-weight: 600; margin: 12px 0 6px; }
.meta { font-size: 10pt; color: #222; margin-bottom: 4px; }
.meta-line { margin: 2px 0; font-size: 10pt; }
.subtitle { font-size: 10pt; color: #444; margin: 0 0 18px; }
.muted { color: #555; font-weight: 400; }
.grupo {
  margin-bottom: 18px;
  border: 1px solid #ccc;
  padding: 10px 12px;
  border-radius: 2px;
  break-inside: auto;
  page-break-inside: auto;
}
.meta-grupo { font-size: 9.5pt; margin-bottom: 8px; color: #333; }
.inspectores-block { margin-bottom: 10px; font-size: 9.5pt; }
.inspectores-block strong { display: block; margin-bottom: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
thead { display: table-header-group; }
tbody { display: table-row-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 5px 6px; text-align: left; vertical-align: top; }
th { background: #e8e8e8; font-weight: 600; color: #111; }
@media print {
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
</head>
<body>
<header class="doc-header">
<h1>Ruta de trabajo N.º ${escapeHtml(String(ruta.numero))}</h1>
<div class="meta"><strong>Identificador de ruta:</strong> ${escapeHtml(String(ruta.id))}</div>
<div class="meta"><strong>Fecha:</strong> ${escapeHtml(ruta.fecha)} &nbsp;|&nbsp; <strong>Turno:</strong> ${turnoHumano(ruta.turno)}</div>
<div class="meta"><strong>Estado:</strong> ${escapeHtml(estadoEtiqueta)}</div>
<div class="meta"><strong>Nombre:</strong> ${nombreRuta}</div>
<p class="subtitle">Resumen operativo por grupos</p>
</header>
${bloquesGrupo || '<p class="muted">Sin grupos en esta ruta.</p>'}
</body>
</html>`;
}

/**
 * Imprime la hoja de grupos usando un iframe oculto en el documento actual.
 * Evita `window.open` y el bloqueo de ventanas emergentes tras operaciones async.
 */
export function printMapaFinalGruposOperativo(payload: MapaFinalGruposPrintPayload): Promise<void> {
  return new Promise((resolve, reject) => {
    const html = buildMapaFinalGruposPrintHtml(payload);
    const iframe = document.createElement("iframe");
    iframe.setAttribute("title", "Impresión hoja de grupos");
    iframe.setAttribute("aria-hidden", "true");
    iframe.style.cssText =
      "position:fixed;right:0;bottom:0;width:0;height:0;border:0;margin:0;padding:0;opacity:0;pointer-events:none";

    let cleaned = false;
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      try {
        iframe.remove();
      } catch {
        /* ignore */
      }
    };

    try {
      document.body.appendChild(iframe);
    } catch (e) {
      reject(
        e instanceof Error
          ? e
          : new Error("No se pudo preparar la impresión de la hoja de grupos.")
      );
      return;
    }

    const idoc = iframe.contentDocument;
    const iwin = iframe.contentWindow;
    if (!idoc || !iwin) {
      cleanup();
      reject(new Error("El navegador no permitió crear el documento de impresión de grupos."));
      return;
    }

    try {
      idoc.open();
      idoc.write(html);
      idoc.close();
    } catch (e) {
      cleanup();
      reject(
        e instanceof Error
          ? e
          : new Error("No se pudo escribir el documento de impresión de grupos.")
      );
      return;
    }

    const triggerPrint = () => {
      try {
        iwin.focus();
        iwin.print();
      } catch (e) {
        cleanup();
        reject(
          e instanceof Error
            ? e
            : new Error("No se pudo abrir el cuadro de impresión de la hoja de grupos.")
        );
        return;
      }
      resolve();
      try {
        iwin.addEventListener("afterprint", cleanup, { once: true });
      } catch {
        /* IE / entornos viejos */
      }
      window.setTimeout(cleanup, 120_000);
    };

    window.setTimeout(triggerPrint, 300);
  });
}
