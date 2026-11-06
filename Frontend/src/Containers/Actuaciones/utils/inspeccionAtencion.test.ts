import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  buildInspeccionAtencionPutFields,
  hasActaInspeccionEnCurso,
  inspeccionAtencionLecturaVisible,
  labelCaracterPersonaAtendio,
  labelContratoResiduos,
  stripInspeccionAtencionResidualFromPut,
} from "./inspeccionAtencion";

const baseRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-06-10",
    rubro_nombre: "Bar",
    inspector1: "A",
    calle: "San Martín",
    numero: "100",
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    doc_nro: "30123456",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    acta_inspeccion_num: "000042",
    ...overrides,
  }) as IActuacionListItem;

describe("inspeccionAtencion helpers", () => {
  it("create: solo envía valores indicados", () => {
    expect(
      buildInspeccionAtencionPutFields(
        baseRow({
          caracter_persona_atendio: "ENCARGADO",
          posee_contrato_retiro_residuos_solidos_urbanos: true,
        })
      )
    ).toEqual({
      caracter_persona_atendio: "ENCARGADO",
      posee_contrato_retiro_residuos_solidos_urbanos: true,
    });
    expect(buildInspeccionAtencionPutFields(baseRow())).toEqual({});
  });

  it("edit: omite si no hubo toque ni cambio", () => {
    const original = baseRow({
      caracter_persona_atendio: "TITULAR",
      posee_contrato_retiro_residuos_solidos_urbanos: true,
    });
    expect(buildInspeccionAtencionPutFields(original, original)).toEqual({});
  });

  it("edit: incluye si el usuario tocó aunque el valor coincida", () => {
    const original = baseRow({
      caracter_persona_atendio: "ENCARGADO",
      posee_contrato_retiro_residuos_solidos_urbanos: false,
    });
    expect(
      buildInspeccionAtencionPutFields(original, original, { caracter: true, contrato: true })
    ).toEqual({
      caracter_persona_atendio: "ENCARGADO",
      posee_contrato_retiro_residuos_solidos_urbanos: false,
    });
  });

  it("edit: — envía null para limpiar", () => {
    const original = baseRow({
      caracter_persona_atendio: "EMPLEADO",
      posee_contrato_retiro_residuos_solidos_urbanos: true,
    });
    const draft = baseRow({
      caracter_persona_atendio: null,
      posee_contrato_retiro_residuos_solidos_urbanos: null,
    });
    expect(buildInspeccionAtencionPutFields(draft, original, { caracter: true, contrato: true })).toEqual({
      caracter_persona_atendio: null,
      posee_contrato_retiro_residuos_solidos_urbanos: null,
    });
  });

  it("strip elimina residuales del PUT", () => {
    const stripped = stripInspeccionAtencionResidualFromPut(
      baseRow({
        caracter_persona_atendio: "OTRO",
        posee_contrato_retiro_residuos_solidos_urbanos: false,
      })
    );
    expect(stripped.caracter_persona_atendio).toBeUndefined();
    expect(stripped.posee_contrato_retiro_residuos_solidos_urbanos).toBeUndefined();
  });

  it("lectura oculta el bloque si ambos están sin indicar", () => {
    expect(inspeccionAtencionLecturaVisible(baseRow())).toBe(false);
    expect(
      inspeccionAtencionLecturaVisible(
        baseRow({ caracter_persona_atendio: "TITULAR" })
      )
    ).toBe(true);
    expect(labelCaracterPersonaAtendio("ENCARGADO")).toBe("Encargado");
    expect(labelContratoResiduos(true)).toBe("Sí");
    expect(labelContratoResiduos(false)).toBe("No");
    expect(labelContratoResiduos(null)).toBe("");
    expect(hasActaInspeccionEnCurso(" 42 ")).toBe(true);
    expect(hasActaInspeccionEnCurso("")).toBe(false);
  });
});
