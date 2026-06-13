import { ROLE_LABELS, normalizeAppRole, type AppRole } from "./roles";

const PLACEHOLDER_USERNAMES = new Set(["usuario", "user", ""]);

/**
 * Nombre real del usuario (nickname o username), excluyendo placeholders genéricos.
 */
export function resolveRealDisplayName(
  nickname: string | null | undefined,
  username: string | null | undefined
): string | null {
  const nick = nickname?.trim();
  if (nick && !PLACEHOLDER_USERNAMES.has(nick.toLowerCase())) {
    return nick;
  }
  const user = username?.trim();
  if (user && !PLACEHOLDER_USERNAMES.has(user.toLowerCase())) {
    return user;
  }
  return null;
}

export type ToolbarUserDisplay = {
  primary: string;
  roleLabel: string;
  showRoleBadge: boolean;
};

/**
 * Texto del toolbar: «Relevador» o «Nombre Apellido» + badge de rol si hay nombre real.
 */
export function formatToolbarUserDisplay(
  nickname: string | null | undefined,
  username: string | null | undefined,
  rawRole: string | null | undefined
): ToolbarUserDisplay {
  const role = normalizeAppRole(rawRole);
  const roleLabel = ROLE_LABELS[role];
  const realName = resolveRealDisplayName(nickname, username);

  if (realName) {
    return {
      primary: realName,
      roleLabel,
      showRoleBadge: true,
    };
  }

  return {
    primary: roleLabel,
    roleLabel,
    showRoleBadge: false,
  };
}
