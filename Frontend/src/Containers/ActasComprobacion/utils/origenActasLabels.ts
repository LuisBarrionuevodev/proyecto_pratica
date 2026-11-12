import type { IOrigenActas } from "../../../api/origenActas";
import { humanizarTipoVisitaRecorrido } from "./documentalLabelFormat";

export type OrigenActasKind = "rat_decomiso" | "rat_clausura" | "verificar_informar" | "pendiente";

export type OrigenActasFila = { etiqueta: string; valor: string };

export type OrigenActasOficioFuente = {
  tipo_iniciador?: string | null;
  ejecucion_reinspeccion?: Record<string, unknown> | null;
  origen_actas?: IOrigenActas | null;
};

export type OrigenActasExportCampos = {
  tipoFinal: string;
  actaDecomisoOrigen: string;
  kilosDecomisoOrigen: string;
  actaClausuraOrigen: string;
};

function normTipo(raw: unknown): string {
  return String(raw ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();
}

export function formatActaOrigenNum(num: string | null | undefined): string {
  const t = String(num ?? "").trim();
  return t;
}

export function formatKilosOrigen(kg: number | string | null | undefined): string {
  if (kg == null || kg === "") return "";
  const n = typeof kg === "number" ? kg : Number(String(kg).replace(",", "."));
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("es-AR", { maximumFractionDigits: 3, minimumFractionDigits: 0 });
}

export function origenActasTieneContenido(origen: IOrigenActas | null | undefined): boolean {
  if (!origen) return false;
  return Boolean(
    formatActaOrigenNum(origen.acta_decomiso_num) ||
      formatKilosOrigen(origen.decomiso_kilos_total) ||
      formatActaOrigenNum(origen.acta_clausura_num)
  );
}

export function origenActasKindFromTipo(tipoActuacion: string | null | undefined, tipoIniciador?: string | null): OrigenActasKind {
  const ini = normTipo(tipoIniciador);
  if (ini === "RATIFICACION DECOMISO OFICIO" || ini === "RATIFICACION DE DECOMISO") return "rat_decomiso";
  if (ini === "RATIFICACION CLAUSURA OFICIO" || ini === "RATIFICACION DE CLAUSURA") return "rat_clausura";
  if (ini === "VERIFICAR INFORMAR OFICIO" || ini === "VERIFICAR E INFORMAR") return "verificar_informar";
  const t = normTipo(tipoActuacion);
  if (t.includes("DECOMISO") && t.includes("RATIFICACION")) return "rat_decomiso";
  if (t.includes("CLAUSURA") && t.includes("RATIFICACION")) return "rat_clausura";
  if (t.includes("VERIFICAR") && t.includes("INFORMAR")) return "verificar_informar";
  return "pendiente";
}

export function origenActasKindFromOficio(item: OrigenActasOficioFuente): OrigenActasKind {
  const ejec = item.ejecucion_reinspeccion;
  const tipoLab =
    ejec && typeof ejec === "object" ? String(ejec.tipo_inspeccion_labrada ?? "").trim() : "";
  return origenActasKindFromTipo(tipoLab || null, item.tipo_iniciador);
}

export function esTipoVisitaOficioOrigen(tipoActuacion: string | null | undefined): boolean {
  const kind = origenActasKindFromTipo(tipoActuacion);
  return kind === "rat_decomiso" || kind === "rat_clausura" || kind === "verificar_informar";
}

function filasSegunKind(origen: IOrigenActas, kind: OrigenActasKind): OrigenActasFila[] {
  const actaDec = formatActaOrigenNum(origen.acta_decomiso_num);
  const kilos = formatKilosOrigen(origen.decomiso_kilos_total);
  const actaCla = formatActaOrigenNum(origen.acta_clausura_num);
  const filas: OrigenActasFila[] = [];
  if (kind === "rat_clausura") {
    if (actaCla) filas.push({ etiqueta: "N.º acta de clausura", valor: actaCla });
    return filas;
  }
  if (kind === "rat_decomiso") {
    if (actaDec) filas.push({ etiqueta: "N.º acta de decomiso", valor: actaDec });
    if (kilos) filas.push({ etiqueta: "Kilos ratificados", valor: `${kilos} kg` });
    return filas;
  }
  if (actaDec) filas.push({ etiqueta: "N.º acta de decomiso", valor: actaDec });
  if (kilos) {
    filas.push({
      etiqueta: kind === "verificar_informar" ? "Kilos decomisados de origen" : "Kilos decomisados",
      valor: `${kilos} kg`,
    });
  }
  if (actaCla) filas.push({ etiqueta: "N.º acta de clausura", valor: actaCla });
  return filas;
}

/** Detalle Recorrido: todos los antecedentes existentes de la ancla (sin afirmar ratificación). */
export function filasActasComprobacionOrigen(origen: IOrigenActas | null | undefined): OrigenActasFila[] {
  if (!origenActasTieneContenido(origen) || !origen) return [];
  const actaDec = formatActaOrigenNum(origen.acta_decomiso_num);
  const kilos = formatKilosOrigen(origen.decomiso_kilos_total);
  const actaCla = formatActaOrigenNum(origen.acta_clausura_num);
  const filas: OrigenActasFila[] = [];
  if (actaDec) filas.push({ etiqueta: "N.º acta de decomiso", valor: actaDec });
  if (kilos) filas.push({ etiqueta: "Kilos decomisados", valor: `${kilos} kg` });
  if (actaCla) filas.push({ etiqueta: "N.º acta de clausura", valor: actaCla });
  return filas;
}

/** Ver actuación: etiquetas según tipo de visita. */
export function filasOrigenActasVerActuacion(
  origen: IOrigenActas | null | undefined,
  tipoActuacion: string | null | undefined
): OrigenActasFila[] {
  if (!origenActasTieneContenido(origen) || !origen) return [];
  return filasSegunKind(origen, origenActasKindFromTipo(tipoActuacion));
}

/**
 * Filas del bloque «Resultado de la reinspección»: solo lo que ese oficio ratifica.
 * Verificar e informar y pendiente no muestran acta ni kilos ratificados.
 */
export function filasActasRatificadasOficio(item: OrigenActasOficioFuente): OrigenActasFila[] {
  const origen = item.origen_actas;
  if (!origenActasTieneContenido(origen) || !origen) return [];
  const kind = origenActasKindFromOficio(item);
  const actaDec = formatActaOrigenNum(origen.acta_decomiso_num);
  const kilos = formatKilosOrigen(origen.decomiso_kilos_total);
  const actaCla = formatActaOrigenNum(origen.acta_clausura_num);
  if (kind === "rat_clausura") {
    return actaCla ? [{ etiqueta: "Acta de clausura ratificada", valor: `N.º ${actaCla}` }] : [];
  }
  if (kind === "rat_decomiso") {
    const filas: OrigenActasFila[] = [];
    if (actaDec) filas.push({ etiqueta: "Acta de decomiso ratificada", valor: `N.º ${actaDec}` });
    if (kilos) filas.push({ etiqueta: "Kilos ratificados", valor: `${kilos} kg` });
    return filas;
  }
  return [];
}

/** Chips Recorrido: actas/kilos ratificados del oficio. Verificar e informar queda vacío. */
export function chipsOrigenActasOficio(item: OrigenActasOficioFuente): string[] {
  return filasActasRatificadasOficio(item).map((f) => `${f.etiqueta}: ${f.valor}`);
}

export function exportCamposOrigenActasOficio(item: OrigenActasOficioFuente): OrigenActasExportCampos {
  const origen = item.origen_actas;
  const kind = origenActasKindFromOficio(item);
  const ejec = item.ejecucion_reinspeccion;
  const tipoLab =
    ejec && typeof ejec === "object" ? String(ejec.tipo_inspeccion_labrada ?? "").trim() : "";
  const tipoHuman = humanizarTipoVisitaRecorrido(tipoLab || item.tipo_iniciador);
  const tipoFinal = tipoHuman !== "—" ? tipoHuman : "";
  const empty: OrigenActasExportCampos = {
    tipoFinal,
    actaDecomisoOrigen: "",
    kilosDecomisoOrigen: "",
    actaClausuraOrigen: "",
  };
  if (!origenActasTieneContenido(origen) || !origen) return empty;
  const actaDec = formatActaOrigenNum(origen.acta_decomiso_num);
  const kilos = formatKilosOrigen(origen.decomiso_kilos_total);
  const actaCla = formatActaOrigenNum(origen.acta_clausura_num);
  if (kind === "rat_clausura") {
    return { ...empty, actaClausuraOrigen: actaCla };
  }
  if (kind === "rat_decomiso") {
    return { ...empty, actaDecomisoOrigen: actaDec, kilosDecomisoOrigen: kilos };
  }
  return {
    ...empty,
    actaDecomisoOrigen: actaDec,
    kilosDecomisoOrigen: kilos,
    actaClausuraOrigen: actaCla,
  };
}

export function debeMostrarBloqueOrigenVerActuacion(params: {
  actuacionId: number | null | undefined;
  tipoActuacion: string | null | undefined;
  origenActas: IOrigenActas | null | undefined;
}): boolean {
  if (!esTipoVisitaOficioOrigen(params.tipoActuacion)) return false;
  if (!origenActasTieneContenido(params.origenActas)) return false;
  const origenId = params.origenActas?.actuacion_origen_id;
  if (origenId != null && params.actuacionId != null && Number(origenId) === Number(params.actuacionId)) {
    return false;
  }
  return true;
}
