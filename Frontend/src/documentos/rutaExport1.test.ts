import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "./builders/buildRutaPublicadaDocumentModel";
import {
  buildDetalleOperativoPdfSegments,
  splitDetalleOperativoTexto,
} from "./utils/detalleOperativoPdfSegments";
import { RUTA_PDF_GRUPO_KEEP_TOGETHER_MAX_ITEMS } from "./renderers/RutaResumenPdfDocument";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("RUTA-EXPORT.1 buildDetalleOperativoPdfSegments", () => {
  it("prioriza detalle_operativo_items con label y valor unidos", () => {
    const segs = buildDetalleOperativoPdfSegments({
      detalle_operativo_items: [
        { label: "Acta comp.", value: "008801/2026" },
        { label: "Exp.", value: "008805/2026" },
        { label: "Oficio", value: "9234/2026" },
        { label: "Causa", value: "123" },
        { label: "Juzgado", value: "Juz 167086" },
      ],
    });
    expect(segs).toEqual([
      "Acta comp.: 008801/2026",
      "Exp.: 008805/2026",
      "Oficio: 9234/2026",
      "Causa: 123",
      "Juzgado: Juz 167086",
    ]);
  });

  it("divide texto plano por separador · sin partir label del valor", () => {
    const texto =
      "Acta comp.: 008801/2026 · Exp.: 008805/2026 · Oficio: 9234/2026 · Causa: 123 · Juzgado: Juz 167086";
    expect(splitDetalleOperativoTexto(texto)).toEqual([
      "Acta comp.: 008801/2026",
      "Exp.: 008805/2026",
      "Oficio: 9234/2026",
      "Causa: 123",
      "Juzgado: Juz 167086",
    ]);
    expect(buildDetalleOperativoPdfSegments({ detalle_operativo_texto: texto })).toEqual(
      splitDetalleOperativoTexto(texto)
    );
  });

  it("cada segmento conserva Exp.: con su número", () => {
    const segs = buildDetalleOperativoPdfSegments({
      detalle_operativo_texto: "Acta comp.: 008801/2026 · Exp.: 008805/2026",
    });
    expect(segs[1]).toBe("Exp.: 008805/2026");
    expect(segs[1]).not.toBe("Exp.:");
  });
});

describe("RUTA-EXPORT.1 buildRutaPublicadaDocumentModel segmentos", () => {
  const ruta: IRutaTrabajo = {
    id: 1,
    fecha: "2026-08-01",
    turno: "MANIANA",
    estado_ruta: "PUBLICADA",
    numero: 1,
    observaciones: null,
    created_by_user_id: 1,
    created_at: null,
    updated_at: null,
  };

  const grupo: IRutaGrupoMin = {
    id: 10,
    ruta_trabajo_id: 1,
    nombre: "G1",
    estado: "ACTIVO",
    inspectores: [],
    created_by_user_id: 1,
    created_at: null,
    updated_at: null,
  };

  it("incluye detalleOperativoSegmentos en filas de grupo", () => {
    const item: IRutaItemMin = {
      id: 501,
      ruta_trabajo_id: 1,
      ruta_grupo_id: 10,
      iniciador_ruta_id: 200,
      tipo_iniciador: "REINSPECCION_OFICIO",
      estado_ruta_item: "ASIGNADO",
      deleted_at: null,
      detalle_operativo_texto: "Acta comp.: 008801/2026 · Exp.: 008805/2026 · Oficio: 9234/2026",
    };
    const model = buildRutaPublicadaDocumentModel(ruta, [grupo], [item]);
    const fila = model.grupos[0]?.items[0];
    expect(fila?.detalleOperativoSegmentos).toEqual([
      "Acta comp.: 008801/2026",
      "Exp.: 008805/2026",
      "Oficio: 9234/2026",
    ]);
    expect(fila?.detalleOperativo).toContain("008805/2026");
  });
});

describe("RUTA-EXPORT.1 RutaResumenPdfDocument renderer", () => {
  const src = read("src/documentos/renderers/RutaResumenPdfDocument.tsx");

  it("renderiza segmentos con wrap=false, no string plano único", () => {
    expect(src).toContain("DetalleOperativoPdfSegments");
    expect(src).toContain("detalleOperativoSegmentos");
    expect(src).not.toMatch(/detalleOperativo\}/);
    expect(src).toContain("wrap={false}");
  });

  it("grupo chico usa keep-together", () => {
    expect(src).toContain("RUTA_PDF_GRUPO_KEEP_TOGETHER_MAX_ITEMS");
    expect(src).toContain("keepTogether");
    expect(RUTA_PDF_GRUPO_KEEP_TOGETHER_MAX_ITEMS).toBeGreaterThan(0);
  });

  it("encabezado de tabla evita huérfanos con minPresenceAhead", () => {
    expect(src).toContain("minPresenceAhead");
    expect(src).toContain("GrupoTableHeader");
  });

  it("filas de grupo no se parten", () => {
    expect(src).toContain("GrupoItemRow");
  });

  it("columnas Entregado y Recibido a la derecha de OT", () => {
    const otIdx = src.indexOf('>OT</Text>');
    const entIdx = src.indexOf(">Entregado</Text>");
    const recIdx = src.indexOf(">Recibido</Text>");
    expect(otIdx).toBeGreaterThan(-1);
    expect(entIdx).toBeGreaterThan(otIdx);
    expect(recIdx).toBeGreaterThan(entIdx);
    expect(src).toContain("colEntregado");
    expect(src).toContain("colRecibido");
    expect(src).not.toContain("Prioridad:");
  });
});
