import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiClient } from "../api/apiClient";
import { normalizeAppRole, type AppRole } from "./roles";
import { formatToolbarUserDisplay, resolveRealDisplayName } from "./userDisplay";

type MeResponse = {
  user: {
    username: string;
    role: string;
  };
  profile: {
    nickname: string | null;
    avatar_key: "avatar1" | "avatar2" | "avatar3" | "avatar4" | "avatar5";
  };
};

/** loading = bootstrap en curso; unauthenticated = sin token (no es error). */
export type AppSessionStatus = "loading" | "ready" | "unauthenticated" | "error";

export type AppSessionValue = {
  status: AppSessionStatus;
  /** True cuando el bootstrap terminó (listo, sin sesión o error de perfil). */
  authReady: boolean;
  role: AppRole | null;
  username: string | null;
  nickname: string | null;
  avatarKey: string;
  displayName: string | null;
  toolbarPrimary: string;
  toolbarRoleLabel: string;
  toolbarShowRoleBadge: boolean;
  refresh: () => void;
};

const AppSessionContext = createContext<AppSessionValue | null>(null);

const DEFAULT_AVATAR = "avatar1";

/** Eventos de ciclo de vida de sesión (login/logout/401). */
export const AUTH_SESSION_REFRESH_EVENT = "auth:session-refresh";

export function notifyAuthSessionRefresh(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_SESSION_REFRESH_EVENT));
  }
}

function resetSessionFields(
  setRole: (v: AppRole | null) => void,
  setUsername: (v: string | null) => void,
  setNickname: (v: string | null) => void,
  setAvatarKey: (v: string) => void
): void {
  setRole(null);
  setUsername(null);
  setNickname(null);
  setAvatarKey(DEFAULT_AVATAR);
}

/**
 * Sesión única: un solo fetch de `/api/profile/me` para TopBar, Nav, Inicio y guards.
 * No consulta perfil sin token (evita 401 en /login y estado error pegado post-login).
 */
export function AppSessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AppSessionStatus>("loading");
  const [role, setRole] = useState<AppRole | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [nickname, setNickname] = useState<string | null>(null);
  const [avatarKey, setAvatarKey] = useState(DEFAULT_AVATAR);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => {
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    let cancel = false;

    const load = async () => {
      setStatus("loading");
      const token = localStorage.getItem("access_token");
      if (!token) {
        if (cancel) return;
        resetSessionFields(setRole, setUsername, setNickname, setAvatarKey);
        setStatus("unauthenticated");
        return;
      }

      try {
        const res = await apiClient.get<MeResponse>("/api/profile/me");
        if (cancel) return;
        const u = res.data.user;
        const p = res.data.profile;
        setRole(normalizeAppRole(u.role));
        setUsername(u.username ?? null);
        setNickname(p.nickname ?? null);
        setAvatarKey(p.avatar_key || DEFAULT_AVATAR);
        setStatus("ready");
      } catch {
        if (cancel) return;
        resetSessionFields(setRole, setUsername, setNickname, setAvatarKey);
        setStatus("error");
      }
    };

    void load();
    return () => {
      cancel = true;
    };
  }, [tick]);

  useEffect(() => {
    const onRefresh = () => refresh();
    window.addEventListener("profile:updated", onRefresh);
    window.addEventListener(AUTH_SESSION_REFRESH_EVENT, onRefresh);
    return () => {
      window.removeEventListener("profile:updated", onRefresh);
      window.removeEventListener(AUTH_SESSION_REFRESH_EVENT, onRefresh);
    };
  }, [refresh]);

  const authReady = status !== "loading";

  const toolbar = useMemo(
    () => formatToolbarUserDisplay(nickname, username, role ?? undefined),
    [nickname, username, role]
  );

  const displayName = useMemo(
    () => resolveRealDisplayName(nickname, username),
    [nickname, username]
  );

  const value = useMemo<AppSessionValue>(
    () => ({
      status,
      authReady,
      role,
      username,
      nickname,
      avatarKey,
      displayName,
      toolbarPrimary: status === "loading" ? "…" : toolbar.primary,
      toolbarRoleLabel: toolbar.roleLabel,
      toolbarShowRoleBadge: status === "ready" && toolbar.showRoleBadge,
      refresh,
    }),
    [status, authReady, role, username, nickname, avatarKey, displayName, toolbar, refresh]
  );

  return <AppSessionContext.Provider value={value}>{children}</AppSessionContext.Provider>;
}

export function useAppSession(): AppSessionValue {
  const ctx = useContext(AppSessionContext);
  if (!ctx) {
    throw new Error("useAppSession debe usarse dentro de AppSessionProvider");
  }
  return ctx;
}
