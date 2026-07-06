import { Alert, Box, Paper, Tab, Tabs } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import { alertBaseStyles, moduleContentColumnSx } from "../Actuaciones/styles/filtroStyles";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import type { GuardarNomenclaturaBody } from "../../api/geolocalizacionApi";
import ManualMapPanel from "./components/ManualMapPanel";
import { GestionarDomiciliosPageHeader } from "./components/GestionarDomiciliosPageHeader";
import TabDomiciliosOverviewTable from "./components/TabDomiciliosOverviewTable";
import TabMapaOperativoView from "./components/TabMapaOperativoView";
import TabNomenclaturaTable from "./components/TabNomenclaturaTable";
import TabParaRevisarTable from "./components/TabParaRevisarTable";
import { DomicilioSliceFilterChips } from "./components/DomicilioSliceFilterChips";
import {
  getDomicilioSliceEmptyMessage,
  getDomicilioViewEmptyMessage,
} from "./domicilioSliceEmptyStates";
import {
  DOMICILIOS_VIEW_TABS,
  type DomiciliosViewTab,
} from "./domicilioViewTabs";
import { useDomicilioGeolocalizacionActions } from "./hooks/useDomicilioGeolocalizacionActions";
import { useDomicilioNormalizationActions } from "./hooks/useDomicilioNormalizationActions";
import { useDomiciliosPendientes } from "./hooks/useDomiciliosPendientes";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosSlice } from "./types";

/**
 * Gestión Domicilios — 4 tabs visibles PR6B; slices internos vía filtros secundarios.
 */
const GestionarDomiciliosContainer = () => {
  const filters = useMemo<DomiciliosFilters>(
    () => ({
      desde: "",
      hasta: "",
      scope: "all",
    }),
    []
  );

  const [activeView, setActiveView] = useState<DomiciliosViewTab>("para_revisar");
  const [secondaryFilter, setSecondaryFilter] = useState<DomiciliosSlice | "all">("all");
  const [selectedForManual, setSelectedForManual] = useState<DomicilioPendienteItem | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  const selection = useMemo(
    () => ({
      mode: "view" as const,
      view: activeView,
      filterSlice: secondaryFilter,
    }),
    [activeView, secondaryFilter]
  );

  const { activeItems, loading, error, refreshActiveSlice, getViewCount } = useDomiciliosPendientes(
    filters,
    selection,
    { enabled: true }
  );

  const { guardarNormalizacion } = useDomicilioNormalizationActions();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();

  useEffect(() => {
    if (!loading && !error) {
      setLastUpdatedAt(new Date());
    }
  }, [loading, error, activeView, activeItems.length]);

  const onGuardarNormalizacion = async (payload: GuardarNomenclaturaBody & { domicilio_id: number }) => {
    await guardarNormalizacion(payload);
    await refreshActiveSlice();
  };

  const onGuardarPuntoManual = async (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
  }) => {
    await guardarPuntoManual({ ...payload, do_reverse: true });
    setSelectedForManual(null);
    await refreshActiveSlice();
  };

  const handleViewChange = useCallback((_: unknown, view: DomiciliosViewTab) => {
    setActiveView(view);
    setSecondaryFilter("all");
    setSelectedForManual(null);
  }, []);

  const handleEditNomenclatura = useCallback((item: DomicilioPendienteItem) => {
    setActiveView("para_revisar");
    setSecondaryFilter("nomenclatura_pendiente");
    setSelectedForManual(null);
  }, []);

  const emptyMessage =
    secondaryFilter === "all"
      ? getDomicilioViewEmptyMessage(activeView)
      : getDomicilioSliceEmptyMessage(secondaryFilter);

  const showNomenclaturaEditor =
    activeView === "para_revisar" && secondaryFilter === "nomenclatura_pendiente";

  const lastUpdatedLabel = lastUpdatedAt
    ? `Última actualización ${lastUpdatedAt.toLocaleTimeString("es-AR", {
        hour: "2-digit",
        minute: "2-digit",
      })}`
    : null;

  const tabLabel = useCallback(
    (view: DomiciliosViewTab, label: string) => {
      const count = getViewCount(view);
      if (loading && view === activeView) return `${label} · …`;
      if (count == null) return label;
      return `${label} · ${count}`;
    },
    [activeView, getViewCount, loading]
  );

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx }}>
      <GestionarDomiciliosPageHeader
        onRefresh={refreshActiveSlice}
        loading={loading}
        lastUpdatedLabel={lastUpdatedLabel}
      />

      <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
        <Tabs
          value={activeView}
          onChange={handleViewChange}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={moduleSlicesTabsSx}
        >
          {DOMICILIOS_VIEW_TABS.map(({ view, label, hint }) => (
            <Tab key={view} label={tabLabel(view, label)} value={view} title={hint} />
          ))}
        </Tabs>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ ...alertBaseStyles, mb: 0 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, minHeight: 0 }}>
        {activeView === "para_revisar" && (
          <>
            <DomicilioSliceFilterChips
              view="para_revisar"
              value={secondaryFilter}
              onChange={setSecondaryFilter}
            />
            {showNomenclaturaEditor ? (
              <TabNomenclaturaTable
                items={activeItems}
                loading={loading}
                emptyMessage={emptyMessage}
                onGuardar={onGuardarNormalizacion}
              />
            ) : (
              <TabParaRevisarTable
                items={activeItems}
                loading={loading}
                emptyMessage={emptyMessage}
                onGeolocalizar={(item) => setSelectedForManual(item)}
                onEditNomenclatura={handleEditNomenclatura}
              />
            )}
            {selectedForManual ? (
              <ManualMapPanel
                selected={selectedForManual}
                onClose={() => setSelectedForManual(null)}
                onSave={onGuardarPuntoManual}
              />
            ) : null}
          </>
        )}

        {activeView === "mapa" && (
          <TabMapaOperativoView
            items={activeItems}
            loading={loading}
            emptyMessage={emptyMessage}
            filterSlice={secondaryFilter}
            onFilterSliceChange={setSecondaryFilter}
            onRefresh={refreshActiveSlice}
            onEditNomenclatura={handleEditNomenclatura}
            onSaveManualPoint={onGuardarPuntoManual}
          />
        )}

        {activeView === "validados" && (
          <>
            <DomicilioSliceFilterChips
              view="validados"
              value={secondaryFilter}
              onChange={setSecondaryFilter}
            />
            <TabDomiciliosOverviewTable
              items={activeItems}
              loading={loading}
              emptyMessage={emptyMessage}
            />
          </>
        )}

        {activeView === "todos" && (
          <>
            <TabDomiciliosOverviewTable
              items={activeItems}
              loading={loading}
              emptyMessage={emptyMessage}
              showGeoAction
              onGeolocalizar={(item) => setSelectedForManual(item)}
            />
            {selectedForManual ? (
              <ManualMapPanel
                selected={selectedForManual}
                onClose={() => setSelectedForManual(null)}
                onSave={onGuardarPuntoManual}
              />
            ) : null}
          </>
        )}
      </Box>
    </Box>
  );
};

export default GestionarDomiciliosContainer;
