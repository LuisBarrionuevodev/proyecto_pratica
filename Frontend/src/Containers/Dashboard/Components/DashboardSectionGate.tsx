import type { ReactNode } from "react";

import { DashboardSectionBlock } from "./DashboardSectionBlock";
import { DashboardSectionLoader } from "./DashboardSectionLoader";

type Props = {
  title: string;
  subtitle?: string;
  first?: boolean;
  /** Bloque aún sin datos ni error y fetch en curso. */
  loading: boolean;
  /** Bloque listo para mostrar contenido (`data` o `error`). */
  ready: boolean;
  loadingMessage?: string;
  children: ReactNode;
};

/**
 * Envuelve una sección del dashboard: loader propio mientras carga, contenido cuando está lista.
 */
export function DashboardSectionGate({
  title,
  subtitle,
  first = false,
  loading,
  ready,
  loadingMessage,
  children,
}: Props) {
  if (!ready && loading) {
    return (
      <DashboardSectionBlock title={title} subtitle={subtitle} first={first}>
        <DashboardSectionLoader message={loadingMessage} />
      </DashboardSectionBlock>
    );
  }

  if (!ready) {
    return null;
  }

  return <>{children}</>;
}
