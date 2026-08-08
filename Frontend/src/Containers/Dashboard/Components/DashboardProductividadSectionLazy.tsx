import { lazy, memo, Suspense, type ComponentProps } from "react";

import { DashboardSectionBlock } from "./DashboardSectionBlock";
import { DashboardSectionLoader } from "./DashboardSectionLoader";

const DashboardProductividadSection = lazy(() =>
  import("./DashboardProductividadSection").then((m) => ({
    default: m.DashboardProductividadSection,
  }))
);

type Props = ComponentProps<typeof DashboardProductividadSection>;

/**
 * Montaje diferido de Productividad (3 tablas MRT) vía code-split + Suspense.
 */
export const DashboardProductividadSectionLazy = memo(function DashboardProductividadSectionLazy(
  props: Props
) {
  return (
    <Suspense
      fallback={
        <DashboardSectionBlock title="Productividad">
          <DashboardSectionLoader message="Cargando productividad..." />
        </DashboardSectionBlock>
      }
    >
      <DashboardProductividadSection {...props} />
    </Suspense>
  );
});
