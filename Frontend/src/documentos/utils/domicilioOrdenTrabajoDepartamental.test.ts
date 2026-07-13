import { describe, expect, it } from "vitest";
import { buildDomicilioOrdenTrabajoDepartamental } from "./domicilioOrdenTrabajoDepartamental";

describe("buildDomicilioOrdenTrabajoDepartamental", () => {
  it("intersección: dos calles con y minúscula", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Chacabuco Y Piedras")).toBe("Chacabuco y Piedras");
  });

  it("calle+número: rango cuando n >= 20", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("San Martín 1000")).toBe("San Martín 980-1000");
  });

  it("calle+número bajo: solo calle", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Mitre 15")).toBe("Mitre");
  });

  it("ignora ref. para calcular rango", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("San Martín 1200 ref. frente al hospital")).toBe(
      "San Martín 1180-1200"
    );
  });

  it("sin número parseable devuelve texto principal", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Pasaje Los Olivos")).toBe("Pasaje Los Olivos");
  });
});
