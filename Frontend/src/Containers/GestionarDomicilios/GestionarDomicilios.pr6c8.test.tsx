/** @jsxImportSource react */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";



const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

const exists = (rel: string) => existsSync(resolve(process.cwd(), rel));



const LEGACY_PATHS = [

  "src/Containers/GestionarDomicilios/components/TabMapaOperativoView.tsx",

  "src/Containers/GestionarDomicilios/components/TabParaRevisarTable.tsx",

  "src/Containers/GestionarDomicilios/components/TabGeolocalizacionTable.tsx",

  "src/Containers/GestionarDomicilios/components/TabDomiciliosOverviewTable.tsx",

  "src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx",

  "src/Containers/GestionarDomicilios/components/DomicilioSliceFilterChips.tsx",

  "src/Containers/GestionarDomicilios/components/ManualMapPanel.tsx",

  "src/Containers/GestionarDomicilios/components/DomicilioDetallePanel.tsx",

  "src/Containers/GestionarDomicilios/components/DomicilioOperativoMap.tsx",

  "src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts",

  "src/Containers/GestionarDomicilios/domicilioViewTabs.ts",

  "src/Containers/GestionarDomicilios/domicilioSliceTabs.ts",

  "src/Containers/GestionarDomicilios/domicilioItemsMerge.ts",

  "src/Containers/GestionarDomicilios/GestionarDomicilios.pr3.test.tsx",

  "src/Containers/GestionarDomicilios/components/GestionDomiciliosVistaUnica.tsx",

  "src/Containers/GestionarDomicilios/hooks/useGestionDomicilios.ts",

  "src/Containers/GestionarDomicilios/components/GestionDomiciliosMapaPanel.tsx",

  "src/Containers/GestionarDomicilios/hooks/useMapaEdicionManual.ts",

];



const ACTIVE_PATHS = [

  "src/Containers/GestionarDomicilios/index.tsx",

  `${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`,

  `${SHARED}/hooks/useGestionDomicilios.ts`,

  `${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`,

  `${SHARED}/hooks/useMapaEdicionManual.ts`,

];



describe("PR6C.8 limpieza legacy Gestión Domicilios", () => {

  it("elimina componentes y módulos PR6B no usados", () => {

    for (const path of LEGACY_PATHS) {

      expect(exists(path), `legacy aún presente: ${path}`).toBe(false);

    }

  });



  it("conserva vista operativa PR6C vía módulo compartido", () => {

    for (const path of ACTIVE_PATHS) {

      expect(exists(path), `activo faltante: ${path}`).toBe(true);

    }

    const index = read("src/Containers/GestionarDomicilios/index.tsx");

    expect(index).toContain('<Navigate to="/mapa" replace />');

  });



  it("Gestión Domicilios no importa getMapPendientes ni useDomiciliosPendientes", () => {

    const index = read("src/Containers/GestionarDomicilios/index.tsx");

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);

    const combined = `${index}\n${vista}\n${hook}`;

    expect(combined).not.toContain("getMapPendientes");

    expect(combined).not.toContain("useDomiciliosPendientes");

    expect(combined).not.toContain("/map/pendientes");

    expect(combined).not.toContain("slice=");

  });



  it("usa solo getGestionDomicilios en el hook activo", () => {

    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);

    expect(hook).toContain("getGestionDomicilios");

    expect(hook).not.toContain("getMapPendientes");

  });



  it("no quedan tabs ni slices visibles en módulo activo", () => {

    const index = read("src/Containers/GestionarDomicilios/index.tsx");

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    const combined = `${index}\n${vista}`;

    expect(combined).not.toContain("DOMICILIOS_VIEW_TABS");

    expect(combined).not.toContain("domicilioViewTabs");

    expect(combined).not.toContain("domicilioSliceTabs");

    expect(combined).not.toContain("DomicilioSliceFilterChips");

  });

});



describe("PR6C.8 módulo activo sin pendientes legacy", () => {

  it("mapa integrado usa overlay de edición, no ManualMapPanel", () => {

    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);

    expect(mapa).toContain("useMapaEdicionManual");

    expect(mapa).toContain("ConfirmarUbicacionDialog");

    expect(mapa).not.toContain("ManualMapPanel");

  });



  it("header operativo disponible vía props de la vista compartida", () => {

    const header = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionPageHeader.tsx`);

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    expect(header).toContain("title");

    expect(header).toContain("subtitle");

    expect(vista).toContain("showHeader");

  });

});

