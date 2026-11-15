import { describe, expect, it } from "vitest";

import {
  CORRECCION_CONTRIBUYENTE_HINT,
  CORRECCION_DOCUMENTO_CONFIRMACION_DETALLE,
  CORRECCION_DOCUMENTO_CONFIRMACION_TITULO,
  CORRECCION_DOCUMENTO_MISMA_PERSONA,
  CORRECCION_DOMICILIO_HINT,
  CORRECCION_LOCAL_HINT,
  CORRECCION_SIN_CAMBIOS_HINT,
  VINCULACION_ACCION,
  VINCULACION_ANTECEDENTES_JUNTOS,
  VINCULACION_ASOCIAR,
  VINCULACION_CONFLICTO_INSEGURO,
  VINCULACION_DOCUMENTO_AJENO_CTA,
  VINCULACION_DATOS_DESTINO_CONSERVAN,
  VINCULACION_DOCUMENTOS_CONSERVAN,
  VINCULACION_DOCUMENTOS_EMITIDOS,
  VINCULACION_HINT,
  VINCULACION_OCULTAR_DETALLE,
  VINCULACION_PREGUNTA_ASOCIAR,
  VINCULACION_REGISTRADO_TITULO,
  etiquetaCantidad,
  inferTitularCorreccionModo,
  mensajeConflictoVinculacionInseguro,
  ofreceVinculacionDesdeConflicto,
  preguntaAsociarEstablecimiento,
  resumenHistorialAsociar,
  titularVinculacionTexto,
} from "./correccionEstablecimientoCopy";

describe("correccionEstablecimientoCopy", () => {
  it("no promete recálculo de coordenadas ni cambio de titular", () => {
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("misma persona");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("cuit/dni");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("solo este establecimiento");
    expect(CORRECCION_DOCUMENTO_CONFIRMACION_TITULO.toLowerCase()).toContain(
      "todos los establecimientos asociados"
    );
    expect(CORRECCION_DOCUMENTO_CONFIRMACION_DETALLE.toLowerCase()).toContain(
      "el cuit/dni anterior estaba mal cargado"
    );
    expect(CORRECCION_DOCUMENTO_MISMA_PERSONA.toLowerCase()).toContain("misma persona");
    expect(CORRECCION_DOMICILIO_HINT.toLowerCase()).toContain("no se recalculan coordenadas");
    expect(CORRECCION_SIN_CAMBIOS_HINT.toLowerCase()).toContain("no se desvincula");
    expect(CORRECCION_LOCAL_HINT.toLowerCase()).toContain("este establecimiento");
    expect(CORRECCION_LOCAL_HINT.toLowerCase()).toContain("no modifica otros locales");
  });

  it("infiere persona, razón social o ambos sin perder datos", () => {
    expect(
      inferTitularCorreccionModo({ apellido: "Pérez", nombre: "Ana", razonSocial: "" })
    ).toBe("persona");
    expect(
      inferTitularCorreccionModo({ apellido: "", nombre: "", razonSocial: "Panadería SRL" })
    ).toBe("razon_social");
    expect(
      inferTitularCorreccionModo({
        apellido: "Pérez",
        nombre: "Ana",
        razonSocial: "Panadería SRL",
      })
    ).toBe("ambos");
    expect(inferTitularCorreccionModo({ apellido: "", nombre: "", razonSocial: "" })).toBe(
      "persona"
    );
  });

  it("vinculación no promete editar datos personales ni fusionar", () => {
    expect(VINCULACION_HINT.toLowerCase()).toContain("vínculo");
    expect(VINCULACION_HINT.toLowerCase()).toContain("no edita");
    expect(VINCULACION_ACCION).toBe("Vincular este establecimiento");
    expect(VINCULACION_DOCUMENTO_AJENO_CTA.toLowerCase()).toContain("no cambia el titular");
    expect(VINCULACION_REGISTRADO_TITULO.toLowerCase()).toContain("ya está registrado");
    expect(VINCULACION_PREGUNTA_ASOCIAR.toLowerCase()).toContain("asociar");
    expect(VINCULACION_ASOCIAR).toBe("Sí, asociar");
    expect(VINCULACION_ANTECEDENTES_JUNTOS.toLowerCase()).toContain("juntas");
    expect(VINCULACION_DOCUMENTOS_EMITIDOS.toLowerCase()).toContain("no se modifican");
    expect(VINCULACION_DOCUMENTOS_EMITIDOS.toLowerCase()).not.toContain("snapshot");
    expect(VINCULACION_DOCUMENTOS_CONSERVAN.toLowerCase()).toContain("conservarán sus datos");
    expect(VINCULACION_DATOS_DESTINO_CONSERVAN.toLowerCase()).toContain(
      "datos personales del contribuyente encontrado se conservan"
    );
    expect(VINCULACION_DATOS_DESTINO_CONSERVAN.toLowerCase()).not.toContain("fusion");
    expect(VINCULACION_DOCUMENTOS_CONSERVAN.toLowerCase()).not.toContain("snapshot");
    expect(VINCULACION_OCULTAR_DETALLE).toBe("Ocultar detalle del alcance");
    expect(VINCULACION_CONFLICTO_INSEGURO.toLowerCase()).toContain("seguridad");
  });

  it("ofrece vinculación solo con codigo estructurado, no por texto de error", () => {
    expect(
      ofreceVinculacionDesdeConflicto({
        codigo: "DOCUMENTO_AJENO",
        ofrece_vinculacion: true,
        detail: "El documento propuesto ya pertenece a otro contribuyente.",
      })
    ).toBe(true);
    expect(
      ofreceVinculacionDesdeConflicto({
        codigo: "DOCUMENTO_AJENO",
        ofrece_vinculacion: false,
        detail: "El documento propuesto ya pertenece a otro contribuyente.",
      })
    ).toBe(false);
    expect(
      ofreceVinculacionDesdeConflicto({
        codigo: "DOCUMENTO_AJENO",
        detail: "El documento propuesto ya pertenece a otro contribuyente.",
      })
    ).toBe(false);
    expect(
      ofreceVinculacionDesdeConflicto({
        codigo: "AMBIGUEDAD_DOMICILIO",
        ofrece_vinculacion: true,
        detail: "otro contribuyente",
      })
    ).toBe(false);
    expect(mensajeConflictoVinculacionInseguro("Hay más de un contribuyente activo.")).toContain(
      VINCULACION_CONFLICTO_INSEGURO
    );
    expect(mensajeConflictoVinculacionInseguro("Hay más de un contribuyente activo.")).toContain(
      "Hay más de un contribuyente activo."
    );
    expect(titularVinculacionTexto({ nombre: "Ana", apellido: "Pérez" })).toBe("Ana Pérez");
    expect(titularVinculacionTexto({ razon_social: "Panadería SRL" })).toBe("Panadería SRL");
    expect(titularVinculacionTexto({ nombre: "", apellido: "", razon_social: "" })).toBe("");
  });

  it("pregunta genérica si falta el nombre y cantidades usan singular/plural", () => {
    expect(preguntaAsociarEstablecimiento("Carlos Ocampo")).toBe(
      "¿Querés asociar este establecimiento a Carlos Ocampo?"
    );
    expect(preguntaAsociarEstablecimiento("")).toBe(VINCULACION_PREGUNTA_ASOCIAR);
    expect(preguntaAsociarEstablecimiento("   ")).toBe(VINCULACION_PREGUNTA_ASOCIAR);
    expect(etiquetaCantidad(1, "actuación", "actuaciones")).toBe("1 actuación");
    expect(etiquetaCantidad(2, "actuación", "actuaciones")).toBe("2 actuaciones");
    expect(etiquetaCantidad(0, "notificación", "notificaciones")).toBe("0 notificaciones");
    expect(etiquetaCantidad(1, "comprobación", "comprobaciones")).toBe("1 comprobación");
    expect(
      resumenHistorialAsociar({ actuaciones: 4, notificaciones: 1, comprobaciones: 0 })
    ).toEqual(["4 actuaciones", "1 notificación", "0 comprobaciones"]);
    expect(resumenHistorialAsociar({ actuaciones: 1 })).toEqual(["1 actuación"]);
  });
});
