import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  ACTUACION_ROW_ERROR_KEY_MAP,
  normalizeActuacionRowErrors,
  sanitizeActuacionRowForCanalActasPut,
  submitActuacionRow,
} from "./submitActuacionRow";
import {
  buildActuacionFormGlobalError,
  finalizeActuacionFormErrors,
  splitActuacionFormErrors,
} from "./actuacionFormErrors";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";

vi.mock("../../../api/gridApi", () => ({
  validateRow: vi.fn(),
}));

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: vi.fn(),
}));

vi.mock("../../../api/actuacionesListApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/actuacionesListApi")>();
  return {
    ...mod,
    postQuitarActaCanalActas: vi.fn(),
  };
});

import { validateRow } from "../../../api/gridApi";
import { updateActuacion } from "../../../api/actuacionesApi";
import { postQuitarActaCanalActas } from "../../../api/actuacionesListApi";

const mockedValidateRow = vi.mocked(validateRow);
const mockedUpdateActuacion = vi.mocked(updateActuacion);
const mockedPostQuitarActa = vi.mocked(postQuitarActaCanalActas);

const baseRow: IActuacionListItem = {
  id: 1,
  orden_trabajo_numero: "123456",
  fecha_actuacion: "2026-05-10",
  tipo_actuacion: "INSPECCION",
  rubro_nombre: "Bar",
  inspector1: "García",
  inspector2: "López",
  calle: "San Martín",
  numero: "100",
  doc_nro: "20345678901",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
  contraproducencia: "NO_HUBO",
  acta_inspeccion_num: "42",
};

describe("submitActuacionRow error map", () => {
  it("mapea claves Glide españolas a snake_case del modal", () => {
    const mapped = normalizeActuacionRowErrors({
      Contraproducencia: "Requerida",
      "Acta inspección": "Inválida",
    });
    expect(mapped.contraproducencia).toBe("Requerida");
    expect(mapped.acta_inspeccion_num).toBe("Inválida");
  });

  it("pasa claves pydantic snake_case sin cambio", () => {
    const mapped = normalizeActuacionRowErrors({
      rubro_nombre: "Rubro obligatorio",
      acta_comprobacion_num: "Número inválido",
    });
    expect(mapped.rubro_nombre).toBe("Rubro obligatorio");
    expect(mapped.acta_comprobacion_num).toBe("Número inválido");
  });

  it("mapea actas anidadas a celda de inspección", () => {
    const mapped = normalizeActuacionRowErrors({
      "actas.0.numero": "Revisá las actas cargadas",
    });
    expect(mapped.acta_inspeccion_num).toBe("Revisá las actas cargadas");
  });

  it("incluye alias nro_acta en el mapa", () => {
    expect(ACTUACION_ROW_ERROR_KEY_MAP.nro_acta_notificacion).toBe("acta_notificacion_num");
  });
});

describe("actuacionFormErrors", () => {
  it("resume campos visibles con nombres humanos", () => {
    const msg = buildActuacionFormGlobalError({
      calle: "Calle obligatoria",
      rubro_nombre: "Rubro obligatorio",
    });
    expect(msg).toContain("Revisá:");
    expect(msg).toContain("Calle");
    expect(msg).toContain("Rubro");
  });

  it("filtra error de actas previas obsoletas en CRUD", () => {
    const { fieldErrors, rowMessages } = finalizeActuacionFormErrors(
      {
        notificacion_previa_num: "Obligatorio para REINSPECCIÓN.",
        calle: "Calle obligatoria",
      },
      { ignoreCrudObsoleteFields: true }
    );
    expect(fieldErrors.notificacion_previa_num).toBeUndefined();
    expect(fieldErrors.calle).toBe("Calle obligatoria");
    expect(rowMessages).toHaveLength(0);
  });

  it("campo oculto incluye detalle en resumen global cuando no se ignora", () => {
    const { fieldErrors, rowMessages } = splitActuacionFormErrors({
      notificacion_previa_num: "Obligatorio para REINSPECCIÓN.",
    });
    const msg = buildActuacionFormGlobalError(fieldErrors, rowMessages);
    expect(msg).toContain("Acta notificación previa");
  });

  it("_row queda como mensaje global sin fieldErrors", () => {
    const { fieldErrors, rowMessages } = splitActuacionFormErrors({
      _row: "Duplicado en el lote",
    });
    expect(Object.keys(fieldErrors)).toHaveLength(0);
    expect(rowMessages).toContain("Duplicado en el lote");
    expect(buildActuacionFormGlobalError(fieldErrors, rowMessages)).toBe("Duplicado en el lote");
  });

  it("filtra error de oficio del canal actas como mensaje informativo", () => {
    const { fieldErrors, rowMessages } = finalizeActuacionFormErrors({
      oficio_numero: "El canal de carga de actas no admite oficio. Use el flujo específico de oficio (Esperando oficio).",
    });
    expect(Object.keys(fieldErrors)).toHaveLength(0);
    expect(rowMessages.join(" ")).toContain("Esperando oficio");
  });

  it("numero_oficio obligatorio no bloquea como campo editable del modal", () => {
    const { fieldErrors, rowMessages } = finalizeActuacionFormErrors({
      numero_oficio: "numero_oficio es obligatorio",
    });
    expect(fieldErrors.oficio_numero).toBeUndefined();
    expect(rowMessages.join(" ")).toContain("Número de oficio");
  });
});

describe("submitActuacionRow pipeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("guardado válido no devuelve error", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const result = await submitActuacionRow({
      id: 1,
      fullRow: baseRow,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(true);
    expect(mockedUpdateActuacion).toHaveBeenCalledOnce();
  });

  it("validación cliente fallida no llama validateRow del backend", async () => {
    const result = await submitActuacionRow({
      id: 1,
      fullRow: { ...baseRow, fecha_actuacion: "" },
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.kind).toBe("validation");
    expect(result.fieldErrors.fecha_actuacion).toBeTruthy();
    expect(mockedValidateRow).not.toHaveBeenCalled();
    expect(mockedUpdateActuacion).not.toHaveBeenCalled();
  });

  it("validación fallida devuelve resumen con nombres de campo", async () => {
    mockedValidateRow.mockResolvedValue({
      ok: false,
      errors: { contraproducencia: "Debés elegir una contraproducencia." },
    } as any);

    const result = await submitActuacionRow({
      id: 1,
      fullRow: baseRow,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.kind).toBe("validation");
    expect(result.fieldErrors.contraproducencia).toBe("Debés elegir una contraproducencia.");
    expect(result.globalMessage).toContain("Contraproducencia");
  });

  it("sanitize omite oficio/expediente y metadatos de lectura del PUT", () => {
    const sanitized = sanitizeActuacionRowForCanalActasPut({
      ...baseRow,
      oficio_numero: "88",
      oficio_anio: 2024,
      oficio_causa: "Causa X",
      expediente_numero: "99",
      documentacion_contexto: { circuito: "COMUN_COMPROBACION", propia: {} },
      origen_reinspeccion_oficio: { oficio_numero: "12" },
    } as any);
    expect(sanitized.calle).toBe("San Martín");
    expect(sanitized.oficio_numero).toBeNull();
    expect(sanitized.oficio_anio).toBeNull();
    expect(sanitized.oficio_causa).toBeNull();
    expect(sanitized.expediente_numero).toBeNull();
    expect((sanitized as any).documentacion_contexto).toBeUndefined();
    expect((sanitized as any).origen_reinspeccion_oficio).toBeUndefined();
  });

  it("normaliza actas antes del PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: baseRow,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.acta_inspeccion_num).toBe("000042");
  });

  it("borrar acta de inspección la omite del payload", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: { ...baseRow, acta_inspeccion_num: "" },
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.acta_inspeccion_num).toBeNull();
  });

  it("acta existente borrada llama POST quitar-acta antes del PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedPostQuitarActa.mockResolvedValue({ ...baseRow, acta_inspeccion_num: null } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const original = { ...baseRow, acta_inspeccion_num: "000123" };
    await submitActuacionRow({
      id: 1,
      fullRow: { ...original, acta_inspeccion_num: "" },
      originalRow: original,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(mockedPostQuitarActa).toHaveBeenCalledWith(1, "INSPECCION");
    expect(mockedPostQuitarActa.mock.invocationCallOrder[0]).toBeLessThan(
      mockedUpdateActuacion.mock.invocationCallOrder[0]!
    );
    expect(mockedUpdateActuacion).toHaveBeenCalledOnce();
  });

  it("acta existente borrada no usa fallback al original en PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedPostQuitarActa.mockResolvedValue({ ...baseRow, acta_inspeccion_num: null } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const original = { ...baseRow, acta_inspeccion_num: "000123" };
    await submitActuacionRow({
      id: 1,
      fullRow: { ...original, acta_inspeccion_num: "" },
      originalRow: original,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.acta_inspeccion_num).toBeNull();
  });

  it("acta bloqueada por expediente no llama quitar-acta y bloquea guardado", async () => {
    const original = {
      ...baseRow,
      notificacion_editable: false,
      acta_notificacion_num: "000100",
      notificacion_motivo_1: "Motivo",
    };
    const result = await submitActuacionRow({
      id: 1,
      fullRow: {
        ...original,
        acta_notificacion_num: "",
        notificacion_motivo_1: null,
        notificacion_motivo_2: null,
        notificacion_motivo_3: null,
      },
      originalRow: original,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.globalMessage).toContain("modificarse desde la sección correspondiente");
    expect(mockedPostQuitarActa).not.toHaveBeenCalled();
    expect(mockedUpdateActuacion).not.toHaveBeenCalled();
  });

  it("borrar comprobación limpia número y motivo en payload y llama quitar-acta", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedPostQuitarActa.mockResolvedValue({ ...baseRow } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const original = {
      ...baseRow,
      acta_comprobacion_num: "000200",
      comprobacion_motivo: "Incumplimiento",
    };
    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...original,
        acta_comprobacion_num: "",
        comprobacion_motivo: "",
      },
      originalRow: original,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(mockedPostQuitarActa).toHaveBeenCalledWith(1, "COMPROBACION");
    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.acta_comprobacion_num).toBeNull();
    expect(putBody.comprobacion_motivo).toBeNull();
  });

  it("borrar acta de comprobación sin motivo la omite del payload", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...baseRow,
        acta_comprobacion_num: "",
        comprobacion_motivo: "",
      },
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.acta_comprobacion_num).toBeNull();
    expect(putBody.comprobacion_motivo).toBeNull();
  });

  it("backend error de acta previa no bloquea CRUD", async () => {
    mockedValidateRow.mockResolvedValue({
      ok: false,
      errors: { notificacion_previa_num: "Obligatorio para REINSPECCIÓN." },
    } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const result = await submitActuacionRow({
      id: 1,
      fullRow: baseRow,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(true);
    expect(mockedUpdateActuacion).toHaveBeenCalledOnce();
  });

  it("guardado válido con oficio en lectura no envía oficio al PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...baseRow,
        oficio_numero: "204",
        oficio_anio: 2026,
        oficio_causa: "Test",
      },
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.oficio_numero).toBeNull();
    expect(putBody.oficio_anio).toBeNull();
    expect(putBody.oficio_causa).toBeNull();
  });

  it("can_edit_domicilio envía calle y número explícitos al cambiar calle", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const originalRow: IActuacionListItem = {
      ...baseRow,
      can_edit_domicilio: true,
      calle: "Mendoza",
      calle_normalizada: "Mendoza",
      numero: "500",
    };
    const fullRow: IActuacionListItem = {
      ...originalRow,
      calle: "Catamarca",
      numero: "500",
    };

    await submitActuacionRow({
      id: 1,
      fullRow,
      originalRow,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.calle).toBe("Catamarca");
    expect(putBody.numero).toBe("500");
  });

  it("can_edit_domicilio sin cambio domicilio omite calle y numero del PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const originalRow: IActuacionListItem = {
      ...baseRow,
      can_edit_domicilio: true,
      calle: "monteagudo",
      calle_normalizada: "Mendoza",
      numero: "500",
    };
    const fullRow: IActuacionListItem = {
      ...originalRow,
      calle: "Mendoza",
      numero: "500",
      inspector1: "Otro",
    };

    await submitActuacionRow({
      id: 1,
      fullRow,
      originalRow,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.calle).toBeUndefined();
    expect(putBody.numero).toBeUndefined();
    expect(putBody.inspector1).toBe("Otro");
  });

  it("PR7.15d: domicilio bloqueado omite calle y número del PUT y valida sin error domicilio", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const originalRow: IActuacionListItem = {
      ...baseRow,
      can_edit_domicilio: false,
      domicilio_edit_blocked_reason:
        "El domicilio no puede modificarse porque el acta ya fue utilizada en un circuito posterior.",
      calle: "Mendoza",
      calle_normalizada: "Mendoza",
      numero: "500",
      acta_notificacion_num: "200",
    };
    const fullRow: IActuacionListItem = {
      ...originalRow,
      nombre_local: "Solo nombre local",
    };

    const result = await submitActuacionRow({
      id: 1,
      fullRow,
      originalRow,
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(true);
    const validatePayload = mockedValidateRow.mock.calls[0][0] as { row: Record<string, unknown> };
    expect(validatePayload.row.calle).toBeUndefined();
    expect(validatePayload.row.numero).toBeUndefined();
    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.calle).toBeUndefined();
    expect(putBody.numero).toBeUndefined();
    expect(putBody.nombre_local).toBe("Solo nombre local");
  });

  it("circuito REINSPECCION_OFICIO omite campos operativos del PUT sin flag (Fix 2C.3)", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...baseRow,
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        contraproducencia: "LOCAL CERRADO",
        resultado_cumplimiento_oficio: "CUMPLE",
        realizo_nueva_inspeccion: false,
        limpiar_contraproducencia: true,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      } as IActuacionListItem,
      oficioCorrectionApplied: false,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.contraproducencia).toBeUndefined();
    expect(putBody.realizo_nueva_inspeccion).toBeUndefined();
    expect(putBody.limpiar_contraproducencia).toBeUndefined();
    expect(putBody.resultado_cumplimiento_oficio).toBeUndefined();
  });

  it("omite contraproducencia del PUT tras corrección oficio (Fix 2C.2)", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...baseRow,
        tipo_actuacion: "VERIFICAR E INFORMAR",
        contraproducencia: "LOCAL CERRADO",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      } as IActuacionListItem,
      oficioCorrectionApplied: true,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.contraproducencia).toBeUndefined();
    expect(putBody.realizo_nueva_inspeccion).toBeUndefined();
  });

  it("Reinspección Notificación sigue enviando contraproducencia en PUT", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    await submitActuacionRow({
      id: 1,
      fullRow: {
        ...baseRow,
        contraproducencia: "LOCAL CERRADO",
        documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      } as IActuacionListItem,
      oficioCorrectionApplied: false,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.contraproducencia).toBe("LOCAL CERRADO");
  });

  it("GESTIÓN-FIX.3: no llama quitar-acta si ya fue procesada por corregir-cierre-oficio", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const original = {
      ...baseRow,
      tipo_actuacion: "VERIFICAR E INFORMAR",
      acta_inspeccion_num: "000123",
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    } as IActuacionListItem;

    await submitActuacionRow({
      id: 1,
      fullRow: { ...original, acta_inspeccion_num: "" },
      originalRow: original,
      actasClearedByOficioCorrection: ["INSPECCION"],
      skipValidation: false,
      skipUpdate: false,
    });

    expect(mockedPostQuitarActa).not.toHaveBeenCalled();
    expect(mockedUpdateActuacion).toHaveBeenCalledOnce();
  });

  it("GESTIÓN-FIX.3: sin corrección oficio sigue llamando quitar-acta al borrar acta", async () => {
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedPostQuitarActa.mockResolvedValue({ ...baseRow, acta_inspeccion_num: null } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);

    const original = { ...baseRow, acta_inspeccion_num: "000123" };
    await submitActuacionRow({
      id: 1,
      fullRow: { ...original, acta_inspeccion_num: "" },
      originalRow: original,
      actasClearedByOficioCorrection: [],
      skipValidation: false,
      skipUpdate: false,
    });

    expect(mockedPostQuitarActa).toHaveBeenCalledWith(1, "INSPECCION");
    expect(mockedUpdateActuacion).toHaveBeenCalledOnce();
  });
});
