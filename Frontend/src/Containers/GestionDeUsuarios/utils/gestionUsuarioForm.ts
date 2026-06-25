export type UsuarioRole = "admin" | "usuario" | "relevador";

export type GestionUsuarioFormValues = {
  username: string;
  email: string;
  password: string;
  role: UsuarioRole | "";
};

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const USUARIO_ROLE_OPTIONS: { value: UsuarioRole; label: string }[] = [
  { value: "admin", label: "Administrador" },
  { value: "usuario", label: "Usuario" },
  { value: "relevador", label: "Relevador" },
];

/** Label legible del rol (valor API sin cambiar). */
export function usuarioRoleLabel(role: string | null | undefined): string {
  const found = USUARIO_ROLE_OPTIONS.find((o) => o.value === role);
  return found?.label ?? String(role ?? "—");
}

export function emptyGestionUsuarioForm(): GestionUsuarioFormValues {
  return { username: "", email: "", password: "", role: "" };
}

export function gestionUsuarioFormFromUser(user: {
  username: string;
  email: string;
  role: UsuarioRole;
}): GestionUsuarioFormValues {
  return {
    username: user.username ?? "",
    email: user.email ?? "",
    password: "",
    role: user.role ?? "",
  };
}

/** Misma normalización de rol que el POST/PUT actual. */
export function normalizeUsuarioRoleForApi(role: string): UsuarioRole {
  if (role === "admin") return "admin";
  if (role === "relevador") return "relevador";
  return "usuario";
}

export function buildCreateUsuarioPayload(values: GestionUsuarioFormValues) {
  return {
    username: values.username.trim(),
    email: values.email.trim(),
    password: values.password,
    role: normalizeUsuarioRoleForApi(values.role),
  };
}

export function buildUpdateUsuarioPayload(values: GestionUsuarioFormValues) {
  const password = values.password.trim();
  return {
    username: values.username.trim(),
    email: values.email.trim(),
    password: password || undefined,
    role: normalizeUsuarioRoleForApi(values.role),
  };
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

  return errors;
}
