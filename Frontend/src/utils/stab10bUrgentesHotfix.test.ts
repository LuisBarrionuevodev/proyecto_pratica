import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";

import { resolve } from "node:path";



import { buildUrgentesQueryParams } from "../Containers/RutasTrabajo/planificacion/utils/buildUrgentesQueryParams";



describe("STAB-10b-HOTFIX buildUrgentesQueryParams", () => {

  it("sin filtros solo envía paginación", () => {

    expect(buildUrgentesQueryParams({ page: 1, per_page: 25 })).toEqual({

      page: 1,

      per_page: 25,

    });

  });



  it("tipo Todos no envía tipo_urgente", () => {

    const q = buildUrgentesQueryParams({

      page: 1,

      per_page: 25,

      filtros: { tipo_urgente: "", rubro_id: null, q_identificador: "", q_domicilio: "" },

    });

    expect(q).not.toHaveProperty("tipo_urgente");

    expect(q).not.toHaveProperty("q_identificador");

    expect(q).not.toHaveProperty("q_domicilio");

    expect(q).not.toHaveProperty("rubro_id");

  });



  it("tipo OFICIO envía tipo_urgente", () => {

    const q = buildUrgentesQueryParams({

      filtros: {

        tipo_urgente: "OFICIO",

        rubro_id: null,

        q_identificador: "",

        q_domicilio: "",

      },

    });

    expect(q.tipo_urgente).toBe("OFICIO");

  });



  it("campos vacíos no se envían", () => {

    const q = buildUrgentesQueryParams({

      filtros: {

        tipo_urgente: "",

        rubro_id: null,

        q_identificador: "  ",

        q_domicilio: "  ",

      },

    });

    expect(Object.keys(q)).toEqual(["page", "per_page"]);

  });



  it("q_identificador y rubro_id válidos se envían", () => {

    const q = buildUrgentesQueryParams({

      filtros: {

        tipo_urgente: "",

        rubro_id: 3,

        q_identificador: " 99 ",

        q_domicilio: "mitre",

      },

    });

    expect(q.rubro_id).toBe(3);

    expect(q.q_identificador).toBe("99");

    expect(q.q_domicilio).toBe("mitre");

  });



  it("distrito_id solo si está definido", () => {

    expect(buildUrgentesQueryParams({ distrito_id: 15 }).distrito_id).toBe(15);

    expect(buildUrgentesQueryParams({ distrito_id: null })).not.toHaveProperty("distrito_id");

  });

});



describe("STAB-10b-HOTFIX urgentes controller", () => {

  it("API usa buildUrgentesQueryParams", () => {

    const src = readFileSync(

      resolve(process.cwd(), "src/Containers/RutasTrabajo/planificacion/api/planificacionApi.ts"),

      "utf8"

    );

    expect(src).toContain("buildUrgentesQueryParams");

  });



  it("loadUrgentes pasa filtros al API sin armar params inline", () => {

    const src = readFileSync(

      resolve(

        process.cwd(),

        "src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts"

      ),

      "utf8"

    );

    expect(src).toContain("filtros: f");

    expect(src).not.toContain("tipo_urgente: f.tipo_urgente");

  });



  it("urgentes no refetch por tecla", () => {

    const src = readFileSync(

      resolve(process.cwd(), "src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx"),

      "utf8"

    );

    expect(src).toContain("onClick={handleFiltrar}");

    expect(src).not.toContain("useDebouncedValue");

  });



  it("backend urgentes usa iniciador_pendiente_present full", () => {

    const src = readFileSync(

      resolve(

        process.cwd(),

        "../Backend/app/domains/rutas_trabajo/routes/planificacion.py"

      ),

      "utf8"

    );

    expect(src).toContain('iniciador_pendiente_present(row, fields="full")');

    expect(src).not.toContain("iniciador_pendiente_to_row(row)");

  });

});

