/** @jsxImportSource react */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
const exists = (rel: string) => existsSync(resolve(process.cwd(), rel));

function walkTsFiles(dir: string): string[] {
  const abs = resolve(process.cwd(), dir);
  const entries = readdirSync(abs, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const rel = `${dir}/${entry.name}`;
    if (entry.isDirectory()) {
      files.push(...walkTsFiles(rel));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".test.ts") && !entry.name.endsWith(".test.tsx")) {
      files.push(rel);
    }
  }
  return files;
}

describe("PR6C.15 elimina wrapper temporal GestionarDomicilios", () => {
  it("GestionarDomiciliosContainer.tsx no existe", () => {
    expect(exists("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx")).toBe(
      false
    );
  });

  it("index.tsx solo redirige a /mapa", () => {
    const index = read("src/Containers/GestionarDomicilios/index.tsx");
    expect(index).toContain('<Navigate to="/mapa" replace />');
    expect(index).not.toContain("GestionarDomiciliosContainer");
    expect(index).not.toContain("MapaDomiciliosGeolocalizacionView");
  });

  it("App.tsx redirige sin importar el módulo ni el container", () => {
    const app = read("src/App.tsx");
    expect(app).toContain('path="/gestionarDomicilios"');
    expect(app).toContain('<Navigate to="/mapa" replace />');
    expect(app).not.toContain("GestionarDomiciliosContainer");
    expect(app).not.toContain('from "./Containers/GestionarDomicilios"');
    expect(app).not.toContain("GestionarDomicilios");
  });

  it("ningún archivo src importa GestionarDomiciliosContainer", () => {
    const srcFiles = walkTsFiles("src");
    const offenders = srcFiles.filter((path) => {
      const content = read(path);
      return content.includes("GestionarDomiciliosContainer");
    });
    expect(offenders).toEqual([]);
  });

  it("módulo compartido de geolocalización intacto en /mapa", () => {
    expect(exists(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`)).toBe(true);
    expect(exists(`${SHARED}/hooks/useGestionDomicilios.ts`)).toBe(true);
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).not.toContain("GestionarDomiciliosContainer");
  });
});
