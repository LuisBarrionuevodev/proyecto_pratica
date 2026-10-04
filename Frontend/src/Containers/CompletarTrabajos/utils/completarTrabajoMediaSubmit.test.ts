import { describe, expect, it, vi } from "vitest";
import {
  validateCompletarTrabajoSeguimientoFields,
  type SolicitaCarnetUiValue,
} from "./actaSeguimientoUi";
import { runCompletarTrabajoFinalizeFlow } from "./completarTrabajoFinalizeFlow";

const uiPolicyCarnet = {
  recurso_logico: "actuacion",
  ancla_operativa: "ruta_item",
  orden_trabajo_y_fecha_readonly: true,
  inspectores_readonly: true,
  previas_visible: false,
  post_cierre: "",
  mostrar_solicitud_carnet_manipulador: true,
  mostrar_subsanacion_notificacion: false,
};

const uiPolicySubs = {
  ...uiPolicyCarnet,
  mostrar_solicitud_carnet_manipulador: false,
  mostrar_subsanacion_notificacion: true,
};

const actaValida = "123456";

describe("validateCompletarTrabajoSeguimientoFields", () => {
  it("carnet obligatorio sin respuesta", () => {
    const errors = validateCompletarTrabajoSeguimientoFields({
      uiPolicy: uiPolicyCarnet,
      visitaRealizada: true,
      actaInspeccion: actaValida,
      solicitaCarnetManipulador: "",
      telefonoSolicitudCarnet: "",
      faltasNotificacionSubsanadas: "",
    });
    expect(errors.solicita_carnet_manipulador).toBeTruthy();
  });

  it("teléfono obligatorio si solicita carnet", () => {
    const errors = validateCompletarTrabajoSeguimientoFields({
      uiPolicy: uiPolicyCarnet,
      visitaRealizada: true,
      actaInspeccion: actaValida,
      solicitaCarnetManipulador: "si",
      telefonoSolicitudCarnet: "",
      faltasNotificacionSubsanadas: "",
    });
    expect(errors.telefono_contacto_solicitud_carnet).toBeTruthy();
  });

  it("subsanación obligatoria sin respuesta", () => {
    const errors = validateCompletarTrabajoSeguimientoFields({
      uiPolicy: uiPolicySubs,
      visitaRealizada: true,
      actaInspeccion: actaValida,
      solicitaCarnetManipulador: "",
      telefonoSolicitudCarnet: "",
      faltasNotificacionSubsanadas: "",
    });
    expect(errors.faltas_notificacion_subsanadas).toBeTruthy();
  });
});

describe("runCompletarTrabajoFinalizeFlow", () => {
  it("no sube ni cierra si la validación falla", async () => {
    const upload = vi.fn();
    const cierre = vi.fn();
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({
        canSubmit: false,
        fieldErrors: { solicita_carnet_manipulador: "falta" },
      }),
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(result).toBe("validation_failed");
    expect(upload).not.toHaveBeenCalled();
    expect(cierre).not.toHaveBeenCalled();
  });

  it("valida → sube → cierra cuando todo ok", async () => {
    const upload = vi.fn().mockResolvedValue(true);
    const cierre = vi.fn().mockResolvedValue(undefined);
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(result).toBe("success");
    expect(upload).toHaveBeenCalledTimes(1);
    expect(cierre).toHaveBeenCalledTimes(1);
  });

  it("sin archivos pendientes: upload ok y cierra directo", async () => {
    const upload = vi.fn().mockResolvedValue(true);
    const cierre = vi.fn().mockResolvedValue(undefined);
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(result).toBe("success");
    expect(cierre).toHaveBeenCalled();
  });

  it("error de subida: no cierra", async () => {
    const cierre = vi.fn();
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: vi.fn().mockResolvedValue(false),
      submitCierre: cierre,
    });
    expect(result).toBe("upload_failed");
    expect(cierre).not.toHaveBeenCalled();
  });

  it("error de cierre tras upload: no vuelve a subir", async () => {
    const upload = vi.fn().mockResolvedValue(true);
    const cierre = vi.fn().mockRejectedValue(new Error("422"));
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(result).toBe("cierre_failed");
    expect(upload).toHaveBeenCalledTimes(1);
    const retry = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: vi.fn().mockResolvedValue(true),
      submitCierre: vi.fn().mockResolvedValue(undefined),
    });
    expect(retry).toBe("success");
  });
});

describe("upload-intent contract", () => {
  it("validación de carnet bloquea antes de intent (integración de flujo)", async () => {
    const intent = vi.fn();
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => {
        const seg = validateCompletarTrabajoSeguimientoFields({
          uiPolicy: uiPolicyCarnet,
          visitaRealizada: true,
          actaInspeccion: actaValida,
          solicitaCarnetManipulador: "" as SolicitaCarnetUiValue,
          telefonoSolicitudCarnet: "",
          faltasNotificacionSubsanadas: "",
        });
        return {
          canSubmit: Object.keys(seg).length === 0,
          fieldErrors: seg,
        };
      },
      uploadPendingMedia: async () => {
        intent();
        return true;
      },
      submitCierre: vi.fn(),
    });
    expect(result).toBe("validation_failed");
    expect(intent).not.toHaveBeenCalled();
  });
});
