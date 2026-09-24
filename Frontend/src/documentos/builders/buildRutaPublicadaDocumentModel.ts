import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { parseCoord } from "../../utils/mapCoords";
import { tipoIniciadorDesdeCodigoApi } from "../../Containers/RutasTrabajo/planificacion/utils/iniciadorDisplay";
import { detalleOperativoTexto } from "../../Containers/RutasTrabajo/utils/iniciadorDetalleOperativo";
import { buildDetalleOperativoResumenRutaExport } from "../utils/detalleOperativoResumenRutaExport";
import { formatDistritosRutaExport } from "../utils/formatDistritosRutaExport";
import { buildEstablecimientoSecundarioText } from "../utils/establecimientoSecundario";
import type {
  RutaDocumentoGrupo,
  RutaDocumentoInspector,
  RutaDocumentoInspectorSalida,
  RutaDocumentoItemFila,
  RutaDocumentoMapaPunto,
  RutaPublicadaDocumentModel,
} from "../types/rutaPublicadaDocument";
import { fechaRutaLegiblePdf } from "../utils/fechaArg";

function turnoLegible(turno: string): string {
  return turno === "MANIANA" ? "Mañana" : turno === "TARDE" ? "Tarde" : turno;
}

function otLabel(item: IRutaItemMin): string | null {
  const ot = item.orden_trabajo;
  if (!ot) return null;
  const num = (ot.numero_acta ?? "").toString().trim();
  if (!num) return null;
  return `${num}/${ot.mes ?? "—"}/${ot.anio ?? "—"}`;
}

/**
 * Arma el modelo documental único para PDFs de ruta (resumen + órdenes de salida).
 *
 * @param ruta — Cabecera de ruta (fecha, turno, número, observaciones).
 * @param grupos — Grupos con ítems embebidos como devuelve `GET /rutas-trabajo/:id`.
 * @param itemsActivos — Ítems no borrados (misma fuente que la vista mapa).
 * @returns Payload estable para renderers PDF.
 */
export function buildRutaPublicadaDocumentModel(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): RutaPublicadaDocumentModel {
  const itemsByGrupo = new Map<number, IRutaItemMin[]>();
  for (const it of itemsActivos) {
    const gid = it.ruta_grupo_id;
    if (!itemsByGrupo.has(gid)) itemsByGrupo.set(gid, []);
    itemsByGrupo.get(gid)!.push(it);
  }

  for (const [, list] of itemsByGrupo) {
    list.sort((a, b) => a.id - b.id);
  }

  const gruposDoc: RutaDocumentoGrupo[] = grupos.map((g) => {
    const list = itemsByGrupo.get(g.id) ?? [];
    const inspectores: RutaDocumentoInspector[] = g.inspectores.map((row) => ({
      inspectorId: row.inspector_id,
      nombreCompleto: (row.inspector_nombre ?? "").trim() || "—",
      numeroAfiliado: (row.inspector_legajo ?? "").trim() || "—",
    }));

    const items: RutaDocumentoItemFila[] = list.map((it, idx) => ({
      itemId: it.id,
      ordenVisita: idx + 1,
      domicilioTexto: (it.domicilio_texto ?? "").trim() || "—",
      distritoNombre: it.distrito_nombre ?? null,
      rubroNombre: it.rubro_nombre ?? null,
      nombreFantasia: (it.nombre_fantasia ?? "").trim() || null,
      anguloEsquina: (it.angulo_esquina ?? "").trim() || null,
      establecimientoSecundario: buildEstablecimientoSecundarioText(it),
      ordenTrabajoLabel: otLabel(it),
      tipoIniciador: it.tipo_iniciador ?? null,
      tipoIniciadorLabel:
        it.tipo_iniciador_label?.trim() ||
        tipoIniciadorDesdeCodigoApi(it.tipo_iniciador ?? null) ||
        null,
      prioridadLabel: it.prioridad_label ?? null,
      detalleOperativoSegmentos: buildDetalleOperativoResumenRutaExport(it),
      detalleOperativo: detalleOperativoTexto(it),
      lat: parseCoord(it.lat),
      lng: parseCoord(it.lng),
    }));

    return {
      grupoId: g.id,
      nombreGrupo: (g.nombre ?? "").trim() || `Grupo ${g.id}`,
      inspectores,
      items,
    };
  });

  const distritosPorInspector = new Map<number, Set<string>>();
  const metaInspector = new Map<number, { nombre: string; legajo: string }>();

  for (const g of grupos) {
    for (const row of g.inspectores) {
      if (!metaInspector.has(row.inspector_id)) {
        metaInspector.set(row.inspector_id, {
          nombre: (row.inspector_nombre ?? "").trim() || "—",
          legajo: (row.inspector_legajo ?? "").trim() || "—",
        });
      }
    }
  }

  const grupoIxPorId = new Map<number, number>();
  grupos.forEach((g, ix) => grupoIxPorId.set(g.id, ix));

  for (const it of itemsActivos) {
    const distrito = it.distrito_nombre?.trim();
    const grupo = grupos.find((x) => x.id === it.ruta_grupo_id);
    if (!grupo) continue;
    for (const row of grupo.inspectores) {
      if (!distritosPorInspector.has(row.inspector_id)) {
        distritosPorInspector.set(row.inspector_id, new Set());
      }
      if (distrito) distritosPorInspector.get(row.inspector_id)!.add(distrito);
    }
  }

  const inspectoresSalida: RutaDocumentoInspectorSalida[] = Array.from(metaInspector.entries())
    .map(([inspectorId, m]) => ({
      inspectorId,
      nombreCompleto: m.nombre,
      numeroAfiliado: m.legajo,
      distritosTexto: formatDistritosRutaExport(distritosPorInspector.get(inspectorId) ?? []),
    }))
    .sort((a, b) => a.nombreCompleto.localeCompare(b.nombreCompleto, "es"));

  const puntosMapa: RutaDocumentoMapaPunto[] = [];
  for (const it of itemsActivos) {
    const la = parseCoord(it.lat);
    const ln = parseCoord(it.lng);
    if (la == null || ln == null) continue;
    const list = itemsByGrupo.get(it.ruta_grupo_id) ?? [];
    const idxEnGrupo = list.findIndex((x) => x.id === it.id);
    const ordenEnGrupo = idxEnGrupo >= 0 ? idxEnGrupo + 1 : 1;
    const grupoIx = grupoIxPorId.get(it.ruta_grupo_id) ?? 0;
    puntosMapa.push({ lat: la, lng: ln, grupoIx, ordenEnGrupo });
  }

  puntosMapa.sort((a, b) => {
    if (a.grupoIx !== b.grupoIx) return a.grupoIx - b.grupoIx;
    return a.ordenEnGrupo - b.ordenEnGrupo;
  });

  const fechaLegible = fechaRutaLegiblePdf(ruta.fecha);

  return {
    rutaId: ruta.id,
    numeroRuta: ruta.numero,
    fechaIso: ruta.fecha,
    fechaLegible,
    turnoCodigo: ruta.turno,
    turnoLegible: turnoLegible(ruta.turno),
    estadoRuta: ruta.estado_ruta,
    observaciones: ruta.observaciones,
    displayName: ruta.display_name ?? null,
    grupos: gruposDoc,
    inspectoresSalida,
    puntosMapa,
  };
}
