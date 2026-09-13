import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AppFeedback } from "../../components/feedback/GlobalFeedbackProvider";
import {
  ACTUACION_NETWORK_ERROR_MESSAGE,
} from "../Actuaciones/validations/normalizeActuacionApiError";
import { itemsActaInspeccionWriteFromEstados } from "../Actuaciones/utils/inspeccionChecklistSubmit";
import {
  CARGAR_ACTUACION_SUCCESS_MESSAGE,
  getCargarActuacionChecklistV2ResetState,
  runCargarActuacionPostSaveCleanup,
} from "./utils/cargarActuacionModalLifecycle";
import { submitCargarActuacionNuevaRow } from "./utils/cargarActuacionNuevaSubmit";

vi.mock("../../api/gridApi", () => ({
  validateRow: vi.fn(),
  commitBatch: vi.fn(),
}));

import { validateRow, commitBatch } from "../../api/gridApi";

const mockedValidateRow = vi.mocked(validateRow);
const mockedCommitBatch = vi.mocked(commitBatch);

const baseDir = dirname(fileURLToPath(import.meta.url));
const modalPath = join(baseDir, "Components", "CargarActuacionNuevaModal.tsx");
const frontendSrcRoot = join(baseDir, "..");

const V1_SETTERS = ["setInspeccionItemIds", "setCantidadCarnets", "setChecklistCarnetsTouched"] as const;

function mockFeedback(): AppFeedback {
  return {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  };
}

function walkTsFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules") continue;
      walkTsFiles(full, acc);
      continue;
    }
    if (/\.(ts|tsx)$/.test(entry) && !/\.test\.(ts|tsx)$/.test(entry)) {
      acc.push(full);
    }
  }
  return acc;
}

describe("CargarActuacionNuevaModal reset V2", () => {
  it("getCargarActuacionChecklistV2ResetState limpia checklist, personas y touched", () => {
    const dirty = {
      checklistEstados: { 1: "BIEN" as const, 3: "OBSERVADO" as const },
      personasSinCarnet: "3",
      checklistItemsTouched: true,
      personasSinCarnetTouched: true,
    };
    expect(dirty.checklistEstados[1]).toBe("BIEN");

    const reset = getCargarActuacionChecklistV2ResetState();
    expect(reset.checklistEstados).toEqual({});
    expect(itemsActaInspeccionWriteFromEstados(reset.checklistEstados)).toEqual([]);
    expect(reset.personasSinCarnet).toBe("0");
    expect(reset.checklistItemsTouched).toBe(false);
    expect(reset.personasSinCarnetTouched).toBe(false);
  });

  it("resetForm en modal usa helper V2 y no setters V1", () => {
    const src = readFileSync(modalPath, "utf8");
    expect(src).toContain("getCargarActuacionChecklistV2ResetState");
    expect(src).toContain("setChecklistEstados(checklistV2Reset.checklistEstados)");
    expect(src).toContain("setPersonasSinCarnet(checklistV2Reset.personasSinCarnet)");
    expect(src).toContain("setChecklistItemsTouched(checklistV2Reset.checklistItemsTouched)");
    expect(src).toContain("setPersonasSinCarnetTouched(checklistV2Reset.personasSinCarnetTouched)");
    for (const setter of V1_SETTERS) {
      expect(src).not.toContain(setter);
    }
  });

  it("no quedan referencias V1 en Frontend/src", () => {
    const files = walkTsFiles(frontendSrcRoot);
    const offenders: string[] = [];
    for (const file of files) {
      const src = readFileSync(file, "utf8");
      for (const setter of V1_SETTERS) {
        if (src.includes(setter)) offenders.push(`${file}: ${setter}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("runCargarActuacionPostSaveCleanup", () => {
  it("éxito: feedback.success, reset y cierre sin error", () => {
    const success = vi.fn();
    const resetForm = vi.fn();
    const closeModal = vi.fn();

    runCargarActuacionPostSaveCleanup({ success, resetForm, closeModal });

    expect(success).toHaveBeenCalledOnce();
    expect(success).toHaveBeenCalledWith(CARGAR_ACTUACION_SUCCESS_MESSAGE);
    expect(resetForm).toHaveBeenCalledOnce();
    expect(closeModal).toHaveBeenCalledOnce();
  });

  it("error en resetForm no propaga ni llama feedback.error", () => {
    const success = vi.fn();
    const error = vi.fn();
    const logError = vi.fn();

    runCargarActuacionPostSaveCleanup({
      success,
      resetForm: () => {
        throw new ReferenceError("setInspeccionItemIds is not defined");
      },
      closeModal: vi.fn(),
      logError,
    });

    expect(success).toHaveBeenCalledOnce();
    expect(logError).toHaveBeenCalledOnce();
    expect(error).not.toHaveBeenCalled();
  });
});

describe("submitCargarActuacionNuevaRow", () => {
  const rowId = "row-test-1";
  const batchId = "batch-test-1";
  let feedback: AppFeedback;
  let resetForm: ReturnType<typeof vi.fn>;
  let closeModal: ReturnType<typeof vi.fn>;
  let setFieldErrors: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    feedback = mockFeedback();
    resetForm = vi.fn();
    closeModal = vi.fn();
    setFieldErrors = vi.fn();
  });

  it("guardado exitoso: success una vez, reset, cierre, sin error API", async () => {
    mockedValidateRow.mockResolvedValue({
      batch_id: batchId,
      row_id: rowId,
      ok: true,
      normalized: { _rowId: rowId } as never,
    });
    mockedCommitBatch.mockResolvedValue({
      batch_id: batchId,
      results: [{ batch_id: batchId, row_id: rowId, ok: true }],
    });

    await submitCargarActuacionNuevaRow({
      batchId,
      rowId,
      payload: {},
      feedback,
      resetForm,
      closeModal,
      setFieldErrors,
    });

    expect(feedback.success).toHaveBeenCalledOnce();
    expect(feedback.success).toHaveBeenCalledWith(CARGAR_ACTUACION_SUCCESS_MESSAGE);
    expect(feedback.error).not.toHaveBeenCalled();
    expect(resetForm).toHaveBeenCalledOnce();
    expect(closeModal).toHaveBeenCalledOnce();
  });

  it("mine.ok=false: warning funcional, sin success ni reset ni cierre", async () => {
    mockedValidateRow.mockResolvedValue({
      batch_id: batchId,
      row_id: rowId,
      ok: true,
      normalized: { _rowId: rowId } as never,
    });
    mockedCommitBatch.mockResolvedValue({
      batch_id: batchId,
      results: [
        {
          batch_id: batchId,
          row_id: rowId,
          ok: false,
          errors: { rubro_nombre: "Rubro obligatorio" },
        },
      ],
    });

    await submitCargarActuacionNuevaRow({
      batchId,
      rowId,
      payload: {},
      feedback,
      resetForm,
      closeModal,
      setFieldErrors,
    });

    expect(feedback.success).not.toHaveBeenCalled();
    expect(feedback.warning).toHaveBeenCalled();
    expect(resetForm).not.toHaveBeenCalled();
    expect(closeModal).not.toHaveBeenCalled();
    expect(setFieldErrors).toHaveBeenCalledWith({ Rubro: "Rubro obligatorio" });
  });

  it("error de red real: feedback.error de conexión", async () => {
    const networkErr = Object.assign(new Error("Network Error"), {
      isAxiosError: true,
      response: undefined,
    });
    mockedValidateRow.mockRejectedValue(networkErr);

    await submitCargarActuacionNuevaRow({
      batchId,
      rowId,
      payload: {},
      feedback,
      resetForm,
      closeModal,
      setFieldErrors,
    });

    expect(feedback.error).toHaveBeenCalledWith(ACTUACION_NETWORK_ERROR_MESSAGE);
    expect(feedback.success).not.toHaveBeenCalled();
    expect(resetForm).not.toHaveBeenCalled();
    expect(closeModal).not.toHaveBeenCalled();
  });

  it("reset fallido post-éxito no dispara error de conexión", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    mockedValidateRow.mockResolvedValue({
      batch_id: batchId,
      row_id: rowId,
      ok: true,
      normalized: { _rowId: rowId } as never,
    });
    mockedCommitBatch.mockResolvedValue({
      batch_id: batchId,
      results: [{ batch_id: batchId, row_id: rowId, ok: true }],
    });
    resetForm.mockImplementation(() => {
      throw new ReferenceError("setInspeccionItemIds is not defined");
    });

    await submitCargarActuacionNuevaRow({
      batchId,
      rowId,
      payload: {},
      feedback,
      resetForm,
      closeModal,
      setFieldErrors,
    });

    expect(feedback.success).toHaveBeenCalledOnce();
    expect(feedback.error).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
