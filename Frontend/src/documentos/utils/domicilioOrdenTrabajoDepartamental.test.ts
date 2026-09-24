import { describe, expect, it } from "vitest";
import { buildDomicilioOrdenTrabajoDepartamental } from "./domicilioOrdenTrabajoDepartamental";

describe("buildDomicilioOrdenTrabajoDepartamental", () => {
  it("intersección: dos calles con y minúscula", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Chacabuco Y Piedras")).toBe("Chacabuco y Piedras");
  });

  it("intersección con ángulo", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("San Martín Y Maipú", "NE")).toBe(
      "San Martín y Maipú\nÁngulo: NE"
    );
  });

  it("calle+número: rango n-5 a n+10", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("San Martín 1000")).toBe("San Martín 995 - 1010");
    expect(buildDomicilioOrdenTrabajoDepartamental("Mendoza 500")).toBe("Mendoza 495 - 510");
  });

  it("calle+número bajo: solo calle si desde < 0", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Mitre 3")).toBe("Mitre");
  });

  it("ignora ref. para calcular rango", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("San Martín 1200 ref. frente al hospital")).toBe(
      "San Martín 1195 - 1210"
    );
  });

  it("sin número parseable devuelve texto principal", () => {
    expect(buildDomicilioOrdenTrabajoDepartamental("Pasaje Los Olivos")).toBe("Pasaje Los Olivos");
  });
});
