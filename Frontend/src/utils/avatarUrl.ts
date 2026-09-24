/** URL de avatar Dicebear (mismo estilo en perfil y TopBar). */
export function getAvatarUrl(seed: string): string {
  return `https://api.dicebear.com/9.x/lorelei-neutral/svg?seed=${encodeURIComponent(seed)}`;
}

export type AvatarKey = "avatar1" | "avatar2" | "avatar3" | "avatar4" | "avatar5";

export const AVATAR_KEYS: AvatarKey[] = ["avatar1", "avatar2", "avatar3", "avatar4", "avatar5"];
