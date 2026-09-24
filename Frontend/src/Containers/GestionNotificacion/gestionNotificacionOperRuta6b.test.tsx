import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("GestionNotificacion OPER-RUTA.6B", () => {
  const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");
  const prorroga = read("src/Containers/GestionNotificacion/components/ReinspeccionOperativaAccionCell.tsx");

  it("bloquea prórroga cuando está en pool/ruta", () => {
    expect(page).toContain("estaBloqueadoParaGestionDocumental");
    expect(page).toContain("MENSAJE_BLOQUEO_GESTION_POOL_RUTA");
    expect(prorroga).toContain("disabled");
  });

  it("muestra Sacar de ruta en acciones danger", () => {
    expect(cell).toContain("OPER_RUTA_LABELS.SACAR_DE_RUTA");
    expect(cell).toContain('dsVariant="danger"');
    expect(cell).toContain("oper-ruta-sacar-de-ruta");
    expect(cell).toContain("liberarRutaPoolDia");
    expect(cell).not.toContain("Sacar del pool");
  });

  it("modal permite solo ruta y grupo", () => {
    expect(dialog).toContain("oper-ruta-solo-pool");
    expect(dialog).toContain("OPER_RUTA_LABELS.AGREGAR_SOLO_A_LA_RUTA");
    expect(dialog).toContain("oper-ruta-modo-grupo");
    expect(dialog).toContain("OPER_RUTA_LABELS.CONFIRMAR_GRUPO");
  });
});
