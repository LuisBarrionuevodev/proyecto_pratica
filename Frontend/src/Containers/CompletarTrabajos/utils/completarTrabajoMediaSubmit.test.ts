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

  it("valida → cierra → sube cuando todo ok", async () => {
    const upload = vi.fn().mockResolvedValue(true);
    const cierre = vi.fn().mockResolvedValue(undefined);
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      hasPendingUpload: () => true,
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(result).toBe("success");
    expect(upload).toHaveBeenCalledTimes(1);
    expect(cierre).toHaveBeenCalledTimes(1);
    expect(cierre.mock.invocationCallOrder[0]).toBeLessThan(upload.mock.invocationCallOrder[0]);
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

  it("cierre ok y falla subida: trabajo guardado con evidencias pendientes", async () => {
    const cierre = vi.fn().mockResolvedValue(undefined);
    const result = await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      hasPendingUpload: () => true,
      uploadPendingMedia: vi.fn().mockResolvedValue(false),
      submitCierre: cierre,
    });
    expect(result).toBe("success_evidencias_pendientes");
    expect(cierre).toHaveBeenCalledTimes(1);
  });

  it("error de cierre: no sube", async () => {
    const upload = vi.fn();
    const cierre = vi.fn().mockRejectedValue(new Error("422"));
    await expect(
      runCompletarTrabajoFinalizeFlow({
        validate: () => ({ canSubmit: true, fieldErrors: {} }),
        hasPendingUpload: () => true,
        uploadPendingMedia: upload,
        submitCierre: cierre,
      })
    ).rejects.toThrow("422");
    expect(upload).not.toHaveBeenCalled();
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
