import { apiClient } from "../api/apiClient";

export type ProfileMeResponse = {
  user: {
    id?: number;
    username: string;
    email?: string;
    role: string;
    inspector_id?: number | null;
    inspector_nombre?: string | null;
  };
  profile: {
    nickname: string | null;
    avatar_key: "avatar1" | "avatar2" | "avatar3" | "avatar4" | "avatar5";
  };
};

let memoryCache: ProfileMeResponse | null = null;
let inflight: Promise<ProfileMeResponse> | null = null;

type FetchProfileMeOptions = {
  /** Ignora cache en memoria (login, logout previo, edición de perfil). */
  force?: boolean;
};

/**
 * Perfil autenticado: deduplica requests simultáneos de bootstrap (`/api/profile/me`).
 */
export async function fetchProfileMe(options?: FetchProfileMeOptions): Promise<ProfileMeResponse> {
  const force = options?.force === true;
  if (force) {
    memoryCache = null;
  }
  if (!force && memoryCache) {
    return memoryCache;
  }
  if (inflight) {
    return inflight;
  }
  inflight = apiClient
    .get<ProfileMeResponse>("/api/profile/me")
    .then((res) => {
      memoryCache = res.data;
      inflight = null;
      return res.data;
    })
    .catch((err) => {
      inflight = null;
      throw err;
    });
  return inflight;
}

/** Limpia cache de perfil (logout / 401). */
export function clearProfileMeSessionCache(): void {
  memoryCache = null;
  inflight = null;
}
