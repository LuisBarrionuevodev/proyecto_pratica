import { Alert, Box, Paper, Tab, Tabs } from "@mui/material";
import { useCallback, useMemo, useState } from "react";
import { alertBaseStyles, moduleContentColumnSx } from "../Actuaciones/styles/filtroStyles";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import type { GuardarNomenclaturaBody } from "../../api/geolocalizacionApi";
import ManualMapPanel from "./components/ManualMapPanel";
import TabDomiciliosOverviewTable from "./components/TabDomiciliosOverviewTable";
import TabGeolocalizacionTable from "./components/TabGeolocalizacionTable";
import TabNomenclaturaTable from "./components/TabNomenclaturaTable";
import {
  DOMICILIOS_GEO_MAP_SLICES,
  DOMICILIOS_SLICE_TABS,
  sliceSupportsGeoActions,
  sliceSupportsNomenclaturaEdit,
} from "./domicilioSliceTabs";
import { useDomicilioGeolocalizacionActions } from "./hooks/useDomicilioGeolocalizacionActions";
import { useDomicilioNormalizationActions } from "./hooks/useDomicilioNormalizationActions";
import { useDomiciliosPendientes } from "./hooks/useDomiciliosPendientes";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosSlice } from "./types";

/**
 * Gestión Domicilios — tabs unificados por ``slice=`` (PR3).
 * Cache por slice; mapa manual en slices geo-compatibles.
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

  const [activeSlice, setActiveSlice] = useState<DomiciliosSlice>("nomenclatura_pendiente");
  const [selectedForManual, setSelectedForManual] = useState<DomicilioPendienteItem | null>(null);

  const { activeItems, loading, error, refreshActiveSlice, getSliceCount } = useDomiciliosPendientes(
    filters,
    activeSlice,
    { enabled: true }
  );

  const { guardarNormalizacion } = useDomicilioNormalizationActions();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();

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

  const handleTabChange = useCallback((_: unknown, v: DomiciliosSlice) => {
    setActiveSlice(v);
    if (!DOMICILIOS_GEO_MAP_SLICES.has(v)) {
      setSelectedForManual(null);
    }
  }, []);

  const showGeoMap = sliceSupportsGeoActions(activeSlice);
  const showNomenclaturaEdit = sliceSupportsNomenclaturaEdit(activeSlice);
  const showGeoTable = activeSlice === "geo_pendiente";

  const tabLabel = useCallback(
    (slice: DomiciliosSlice, label: string) => {
      const count = getSliceCount(slice);
      if (loading && slice === activeSlice) return `${label} · …`;
      if (count == null) return label;
      return `${label} · ${count}`;
    },
    [activeSlice, getSliceCount, loading]
  );

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx }}>
      <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
        <Tabs
          value={activeSlice}
          onChange={handleTabChange}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={moduleSlicesTabsSx}
        >
          {DOMICILIOS_SLICE_TABS.map(({ slice, label }) => (
            <Tab key={slice} label={tabLabel(slice, label)} value={slice} />
          ))}
        </Tabs>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ ...alertBaseStyles, mb: 0 }}>
          {error}
        </Alert>
      )}

      {showNomenclaturaEdit && (
        <TabNomenclaturaTable items={activeItems} loading={loading} onGuardar={onGuardarNormalizacion} />
      )}

      {showGeoTable && (
        <>
          <TabGeolocalizacionTable
            items={activeItems}
            loading={loading}
            onGeolocalizar={(item) => setSelectedForManual(item)}
          />
          <ManualMapPanel
            selected={selectedForManual}
            onClose={() => setSelectedForManual(null)}
            onSave={onGuardarPuntoManual}
          />
        </>
      )}

      {!showNomenclaturaEdit && !showGeoTable && (
        <>
          <TabDomiciliosOverviewTable
            items={activeItems}
            loading={loading}
            showGeoAction={showGeoMap}
            onGeolocalizar={showGeoMap ? (item) => setSelectedForManual(item) : undefined}
          />
          {showGeoMap ? (
            <ManualMapPanel
              selected={selectedForManual}
              onClose={() => setSelectedForManual(null)}
              onSave={onGuardarPuntoManual}
            />
          ) : null}
        </>
      )}
    </Box>
  );
};

export default GestionarDomiciliosContainer;
