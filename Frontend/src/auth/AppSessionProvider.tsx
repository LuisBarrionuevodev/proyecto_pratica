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

export type AppSessionStatus = "loading" | "ready" | "error";

export type AppSessionValue = {
  status: AppSessionStatus;
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

/**
 * Sesión única: un solo fetch de `/api/profile/me` para TopBar, Nav, Inicio y guards.
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
        setRole(null);
        setUsername(null);
        setNickname(null);
        setAvatarKey(DEFAULT_AVATAR);
        setStatus("error");
      }
    };

    void load();
    return () => {
      cancel = true;
    };
  }, [tick]);

  useEffect(() => {
    const onProfileUpdated = () => refresh();
    window.addEventListener("profile:updated", onProfileUpdated);
    return () => window.removeEventListener("profile:updated", onProfileUpdated);
  }, [refresh]);

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
    [status, role, username, nickname, avatarKey, displayName, toolbar, refresh]
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
