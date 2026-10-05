export type UsuarioRole = "admin" | "usuario" | "relevador" | "relevamiento";

export type GestionUsuarioFormValues = {
  username: string;
  email: string;
  password: string;
  role: UsuarioRole | "";
  inspector_id: number | "";
};

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const USUARIO_ROLE_OPTIONS: { value: UsuarioRole; label: string }[] = [
  { value: "admin", label: "Administrador" },
  { value: "usuario", label: "Usuario" },
  { value: "relevador", label: "Inspector" },
  { value: "relevamiento", label: "Relevamiento" },
];

/** Label legible del rol (valor API sin cambiar). */
export function usuarioRoleLabel(role: string | null | undefined): string {
  const found = USUARIO_ROLE_OPTIONS.find((o) => o.value === role);
  return found?.label ?? String(role ?? "—");
}

export function emptyGestionUsuarioForm(): GestionUsuarioFormValues {
  return { username: "", email: "", password: "", role: "", inspector_id: "" };
}

export function gestionUsuarioFormFromUser(user: {
  username: string;
  email: string;
  role: UsuarioRole;
  inspector_id?: number | null;
}): GestionUsuarioFormValues {
  return {
    username: user.username ?? "",
    email: user.email ?? "",
    password: "",
    role: user.role ?? "",
    inspector_id: user.inspector_id ?? "",
  };
}

/** Misma normalización de rol que el POST/PUT actual. */
export function normalizeUsuarioRoleForApi(role: string): UsuarioRole {
  if (role === "admin") return "admin";
  if (role === "relevador") return "relevador";
  if (role === "relevamiento") return "relevamiento";
  return "usuario";
}

export function buildCreateUsuarioPayload(values: GestionUsuarioFormValues) {
  const role = normalizeUsuarioRoleForApi(values.role);
  const payload: Record<string, unknown> = {
    username: values.username.trim(),
    email: values.email.trim(),
    password: values.password,
    role,
  };
  if (role === "relevador") {
    payload.inspector_id = values.inspector_id === "" ? null : Number(values.inspector_id);
  }
  return payload;
}

export function buildUpdateUsuarioPayload(values: GestionUsuarioFormValues) {
  const password = values.password.trim();
  const role = normalizeUsuarioRoleForApi(values.role);
  const payload: Record<string, unknown> = {
    username: values.username.trim(),
    email: values.email.trim(),
    password: password || undefined,
    role,
  };
  if (role === "relevador") {
    payload.inspector_id = values.inspector_id === "" ? null : Number(values.inspector_id);
  }
  return payload;
}

export function validateGestionUsuarioForm(
  values: GestionUsuarioFormValues,
  isCreate: boolean
): Record<string, string> {
  const errors: Record<string, string> = {};
  const username = values.username.trim();
  const email = values.email.trim();
  const password = values.password.trim();
  const role = values.role;

  if (!username) {
    errors.username = "Username is required";
  } else if (username.length < 3) {
    errors.username = "Username must be at least 3 characters";
  }

  if (!email) {
    errors.email = "Email is required";
  } else if (!EMAIL_REGEX.test(email)) {
    errors.email = "Incorrect Email Format";
  }

  if (isCreate && !password) {
    errors.password = "Password is required";
  }

  if (!role) {
    errors.role = "Role is required";
  }

  if (role === "relevador" && values.inspector_id === "") {
    errors.inspector_id = "Debe seleccionar un inspector";
  }

  return errors;
}
