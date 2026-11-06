import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export const CARACTER_PERSONA_ATENDIO_VALORES = [
  "TITULAR",
  "ENCARGADO",
  "EMPLEADO",
  "OTRO",
] as const;

export type CaracterPersonaAtendio = (typeof CARACTER_PERSONA_ATENDIO_VALORES)[number];

export const INSPECCION_ATENCION_PUT_KEYS = [
  "caracter_persona_atendio",
  "posee_contrato_retiro_residuos_solidos_urbanos",
] as const;

export type InspeccionAtencionPutFields = {
  caracter_persona_atendio?: CaracterPersonaAtendio | null;
  posee_contrato_retiro_residuos_solidos_urbanos?: boolean | null;
};

export type InspeccionAtencionTouched = {
  caracter?: boolean;
  contrato?: boolean;
};

export const CARACTER_PERSONA_ATENDIO_LABELS: Record<CaracterPersonaAtendio, string> = {
  TITULAR: "Titular",
  ENCARGADO: "Encargado",
  EMPLEADO: "Empleado",
  OTRO: "Otro",
};

export function isCaracterPersonaAtendio(value: unknown): value is CaracterPersonaAtendio {
  return (
    typeof value === "string" &&
    (CARACTER_PERSONA_ATENDIO_VALORES as readonly string[]).includes(value)
  );
}

export function caracterPersonaAtendioFromRow(
  row: { caracter_persona_atendio?: unknown } | null | undefined
): CaracterPersonaAtendio | null {
  const raw = row?.caracter_persona_atendio;
  return isCaracterPersonaAtendio(raw) ? raw : null;
}

export function contratoResiduosFromRow(
  row: { posee_contrato_retiro_residuos_solidos_urbanos?: unknown } | null | undefined
): boolean | null {
  const v = row?.posee_contrato_retiro_residuos_solidos_urbanos;
  if (v === true || v === false) return v;
  return null;
}

export function labelCaracterPersonaAtendio(value: unknown): string {
  return isCaracterPersonaAtendio(value) ? CARACTER_PERSONA_ATENDIO_LABELS[value] : "";
}

export function labelContratoResiduos(value: boolean | null | undefined): string {
  if (value === true) return "Sí";
  if (value === false) return "No";
  return "";
}

export function inspeccionAtencionLecturaVisible(
  row: Pick<
    IActuacionListItem,
    "caracter_persona_atendio" | "posee_contrato_retiro_residuos_solidos_urbanos"
  >
): boolean {
  return caracterPersonaAtendioFromRow(row) != null || contratoResiduosFromRow(row) != null;
}

export function hasActaInspeccionEnCurso(actaNum: string | null | undefined): boolean {
  return Boolean(String(actaNum ?? "").trim());
}

export function stripInspeccionAtencionResidualFromPut(row: IActuacionListItem): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  for (const key of INSPECCION_ATENCION_PUT_KEYS) {
    delete copy[key];
  }
  return copy as unknown as IActuacionListItem;
}

export function buildInspeccionAtencionPutFields(
  row: IActuacionListItem,
  baseline?: IActuacionListItem | null,
  touched?: InspeccionAtencionTouched | null
): InspeccionAtencionPutFields {
  const currentCaracter = caracterPersonaAtendioFromRow(row);
  const currentContrato = contratoResiduosFromRow(row);
  if (!baseline) {
    const out: InspeccionAtencionPutFields = {};
    if (currentCaracter != null) out.caracter_persona_atendio = currentCaracter;
    if (currentContrato != null) out.posee_contrato_retiro_residuos_solidos_urbanos = currentContrato;
    return out;
  }

  const origCaracter = caracterPersonaAtendioFromRow(baseline);
  const origContrato = contratoResiduosFromRow(baseline);
  const caracterChanged = currentCaracter !== origCaracter;
  const contratoChanged = currentContrato !== origContrato;
  const includeCaracter = touched?.caracter === true || caracterChanged;
  const includeContrato = touched?.contrato === true || contratoChanged;
  if (!includeCaracter && !includeContrato) {
    return {};
  }

  const out: InspeccionAtencionPutFields = {};
  if (includeCaracter) out.caracter_persona_atendio = currentCaracter;
  if (includeContrato) out.posee_contrato_retiro_residuos_solidos_urbanos = currentContrato;
  return out;
}
