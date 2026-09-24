import { describe, expect, it } from "vitest";

import type { IndicadoresNoRealizadasResponse } from "../../../api/indicadoresApi";
import {
  buildContraproducenciasResumen,
  calcTotalNoRealizadas,
  isNoHuboContraproducencia,
} from "./noRealizadasContraproducencias";

const base: IndicadoresNoRealizadasResponse = {
  por_tipo: {
    inspeccion: 2,
    reinspeccion_oficio: 3,
    reinspeccion_notificacion: 0,
    denuncia: 0,
  },
  top_contraproducencias: [],
  distritos_con_mas_no_realizadas: [],
  total: 5,
  contraproducencias_resumen: [
    { bucket: "local_cerrado", label: "Local cerrado", cantidad: 3 },
    { bucket: "clima", label: "Clima", cantidad: 1 },
    { bucket: "no_existe", label: "No existe", cantidad: 0 },
    { bucket: "no_se_ratifico", label: "No se ratificó", cantidad: 0 },
    { bucket: "otras", label: "Otras", cantidad: 1 },
  ],
};

describe("noRealizadasContraproducencias", () => {
  it("usa total del backend", () => {
    expect(calcTotalNoRealizadas(base)).toBe(5);
  });

  it("excluye NO_HUBO", () => {
    expect(isNoHuboContraproducencia("NO_HUBO")).toBe(true);
  });

  it("arma filas desde contraproducencias_resumen con porcentaje", () => {
    const resumen = buildContraproducenciasResumen(base);
    expect(resumen.total).toBe(5);
    expect(resumen.rows).toHaveLength(5);
    expect(resumen.rows[0]?.contraproducencia).toBe("Local cerrado");
    expect(resumen.rows[0]?.porcentaje).toBe(60);
  });

  it("con total 0 devuelve resumen vacío", () => {
    const resumen = buildContraproducenciasResumen({
      ...base,
      total: 0,
      contraproducencias_resumen: base.contraproducencias_resumen.map((r) => ({
        ...r,
        cantidad: 0,
      })),
    });
    expect(resumen.total).toBe(0);
    expect(resumen.rows).toHaveLength(0);
  });
});
