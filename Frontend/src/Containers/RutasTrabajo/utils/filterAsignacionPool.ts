import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import type { AsignacionPoolFilters } from "../Components/TablaIniciadoresPendientes";

/**
 * Filtra filas del pool del día en cliente (tipo, prioridad, distrito, texto).
 */
export function filterAsignacionPoolRows(
  rows: IRutaIniciadorPendienteRow[],
  f: AsignacionPoolFilters
): IRutaIniciadorPendienteRow[] {
  let out = rows;
  if (f.tipo) {
    out = out.filter((r) => r.tipo_iniciador === f.tipo);
  }
  if (f.prioridad_categoria) {
    const cat = f.prioridad_categoria;
    out = out.filter((r) => {
      const p = r.prioridad ?? 0;
      if (cat === "ALTA") return p >= 3;
      if (cat === "MEDIA") return p === 2;
      if (cat === "BAJA") return p <= 1;
      return true;
    });
  }
  if (f.distrito) {
    const did = Number(f.distrito);
    out = out.filter((r) => (r.distrito_id ?? r.domicilio?.distrito_id) === did);
  }
  if (f.q?.trim()) {
    const q = f.q.toLowerCase().trim();
    out = out.filter((r) => {
      const dom =
        r.domicilio_texto ?? `${r.domicilio?.calle ?? "-"} ${r.domicilio?.numero ?? ""}`.trim();
      const hay = [
        r.tipo_iniciador,
        r.tipo_iniciador_label,
        r.badges?.tipo_label,
        r.detalle_operativo_texto,
        ...(r.detalle_operativo_items ?? []).flatMap((it) => [it.label, it.value]),
        r.motivo_denuncia,
        r.causa,
        r.prorroga_texto,
        String(r.prioridad ?? ""),
        dom,
        r.distrito_nombre,
        r.domicilio?.distrito_nombre,
        r.rubro_nombre,
        r.domicilio?.rubro,
        r.observaciones,
        r.fecha_origen,
        String(r.id),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }
  return out;
}

/** Opciones de distrito derivadas únicamente de los iniciadores del pool. */
export function buildDistritoOptionsFromPool(rows: IRutaIniciadorPendienteRow[]) {
  const map = new Map<number, string>();
  for (const r of rows) {
    const id = r.distrito_id ?? r.domicilio?.distrito_id;
    if (id == null) continue;
    const name = r.distrito_nombre ?? r.domicilio?.distrito_nombre ?? `Distrito ${id}`;
    if (!map.has(id)) map.set(id, name);
  }
  return [
    { value: "", label: "Todos" },
    ...Array.from(map.entries())
      .sort((a, b) => a[1].localeCompare(b[1], "es"))
      .map(([id, nombre]) => ({ value: String(id), label: nombre })),
  ];
}
