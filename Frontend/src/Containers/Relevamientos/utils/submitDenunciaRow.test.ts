import { describe, expect, it } from "vitest";

import type { IDenunciaGestionItem } from "../../../api/denunciasApi";
import { denunciaRowParaEdicion } from "./denunciaCamposForm";
import { applyDenunciaDomicilioSubmitGuard } from "./submitDenunciaRow";

describe("submitDenunciaRow — payload domicilio", () => {
  const baseRow: IDenunciaGestionItem = {
    id: 3,
    fecha: "2026-06-10",
    calle: "Maipú",
    calle_normalizada: "Maipú",
    numero: "34",
    numero_tipo: "NUMERO",
    motivo: "Ruidos molestos",
    estado: "ABIERTA",
  };

  it("submit guard usa calle normalizada si draft no editó", () => {
    const baseline = {
      ...baseRow,
      calle: "San Martín",
      calle_estado: "OK",
      calle_normalizada: "Av. San Martín",
    };
    const hydrated = denunciaRowParaEdicion(baseline);
    const payload = applyDenunciaDomicilioSubmitGuard(hydrated, baseline);
    expect(payload.calle).toBe("Av. San Martín");
    expect(payload.numero).toBe("34");
    expect((payload as IDenunciaGestionItem).calle_normalizada).toBeUndefined();
  });

  it("submit guard envía calle editada", () => {
    const baseline = { ...baseRow };
    const draft = { ...denunciaRowParaEdicion(baseline), calle: "Mendoza" };
    const payload = applyDenunciaDomicilioSubmitGuard(draft, baseline);
    expect(payload.calle).toBe("Mendoza");
  });

  it("ESQUINA → NUMERO envía numero_tipo NUMERO", () => {
    const baseline: IDenunciaGestionItem = {
      ...baseRow,
      numero_tipo: "ESQUINA",
      numero: "San Martín y Maipú",
      esquina_normalizada: "San Martín y Maipú",
    };
    const draft: IDenunciaGestionItem = {
      ...denunciaRowParaEdicion(baseline),
      numero_tipo: "NUMERO",
      numero: "500",
    };
    const payload = applyDenunciaDomicilioSubmitGuard(draft, baseline);
    expect(payload.numero_tipo).toBe("NUMERO");
    expect(payload.numero).toBe("500");
  });
});
