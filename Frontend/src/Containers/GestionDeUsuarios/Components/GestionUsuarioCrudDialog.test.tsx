/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { GestionUsuarioCrudDialog } from "./GestionUsuarioCrudDialog";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("GestionUsuarioCrudDialog", () => {
  it("modo vista muestra Editar y datos en lectura", () => {
    const html = render(
      <GestionUsuarioCrudDialog
        open
        disablePortal
        mode="view"
        user={{
          id: 1,
          username: "relev1",
          email: "r@test.com",
          role: "relevador",
          is_active: true,
        }}
        saving={false}
        fieldErrors={{}}
        globalError={null}
        onClose={() => undefined}
        onModeChange={() => undefined}
        onSave={() => undefined}
        onClearFieldError={() => undefined}
      />
    );
    expect(html).toContain("Usuario");
    expect(html).toContain("relev1");
    expect(html).toContain("Relevador");
    expect(html).toContain("Editar");
    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("Guardar cambios");
  });

  it("modo edición muestra Guardar cambios", () => {
    const html = render(
      <GestionUsuarioCrudDialog
        open
        disablePortal
        mode="edit"
        user={{
          id: 1,
          username: "relev1",
          email: "r@test.com",
          role: "relevador",
          is_active: true,
        }}
        saving={false}
        fieldErrors={{}}
        globalError={null}
        onClose={() => undefined}
        onSave={() => undefined}
        onClearFieldError={() => undefined}
      />
    );
    expect(html).toContain("Editar usuario");
    expect(html).toContain("Guardar cambios");
    expect(html).not.toContain("Cancelar");
  });

  it("alta muestra Crear usuario", () => {
    const html = render(
      <GestionUsuarioCrudDialog
        open
        disablePortal
        mode="create"
        user={null}
        saving={false}
        fieldErrors={{}}
        globalError={null}
        onClose={() => undefined}
        onSave={() => undefined}
        onClearFieldError={() => undefined}
      />
    );
    expect(html).toContain("Nuevo usuario");
    expect(html).toContain("Crear usuario");
    expect(html).not.toContain("Cancelar");
  });

  it("muestra error global y error de email", () => {
    const html = render(
      <GestionUsuarioCrudDialog
        open
        disablePortal
        mode="create"
        user={null}
        saving={false}
        fieldErrors={{ email: "Email ya está en uso" }}
        globalError="No se pudo crear el usuario"
        onClose={() => undefined}
        onSave={() => undefined}
        onClearFieldError={() => undefined}
      />
    );
    expect(html).toContain("No se pudo crear el usuario");
    expect(html).toContain("Email ya está en uso");
  });
});
