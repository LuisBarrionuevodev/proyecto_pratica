import { Alert, Box, Tab, Tabs, Typography } from "@mui/material";
import { useCallback, useMemo, useState } from "react";
import { containerStyles, wrapperStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { alertBaseStyles } from "../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { getCurrentMonthRange } from "../../utils/dateRange";
import DomiciliosFiltersBar from "./components/DomiciliosFiltersBar";
import DomiciliosQueueToggle from "./components/DomiciliosQueueToggle";
import type { DomiciliosQueueFocus } from "./components/DomiciliosQueueToggle";
import ManualMapPanel from "./components/ManualMapPanel";
import TabGeolocalizacionTable from "./components/TabGeolocalizacionTable";
import TabNomenclaturaTable from "./components/TabNomenclaturaTable";
import { useDomicilioGeolocalizacionActions } from "./hooks/useDomicilioGeolocalizacionActions";
import { useDomicilioNormalizationActions } from "./hooks/useDomicilioNormalizationActions";
import { useDomiciliosPendientes } from "./hooks/useDomiciliosPendientes";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosTab } from "./types";

const GestionarDomiciliosContainer = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [activeTab, setActiveTab] = useState<DomiciliosTab>("nomenclatura");
  const [queueFocus, setQueueFocus] = useState<DomiciliosQueueFocus>("all");
  const [filters, setFilters] = useState<DomiciliosFilters>({
    desde: defaultRange.desde,
    hasta: defaultRange.hasta,
    scope: "all",
  });
  /** Hasta presionar Filtrar no se cargan pendientes ni las pestañas operativas. */
  const [queryEnabled, setQueryEnabled] = useState(false);
  const [selectedForManual, setSelectedForManual] = useState<DomicilioPendienteItem | null>(null);

  const { nomenclaturaItems, geolocalizacionItems, loading, error, refetch } =
    useDomiciliosPendientes(filters, { enabled: queryEnabled });

  const { guardarNormalizacion } = useDomicilioNormalizationActions();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();

  const onFiltrar = useCallback(async () => {
    if (queryEnabled) {
      await refetch();
    } else {
      setQueryEnabled(true);
    }
  }, [queryEnabled, refetch]);

  const onLimpiar = async () => {
    const range = getCurrentMonthRange();
    const reset = { desde: range.desde, hasta: range.hasta, scope: "all" as const };
    setFilters(reset);
    setQueryEnabled(false);
    setSelectedForManual(null);
    setQueueFocus("all");
  };

  const handleQueueFocus = useCallback((next: DomiciliosQueueFocus) => {
    setQueueFocus(next);
    if (next === "nomenclatura") setActiveTab("nomenclatura");
    if (next === "geolocalizacion") setActiveTab("geolocalizacion");
  }, []);

  const onGuardarNormalizacion = async (payload: {
    domicilio_id: number;
    calle_catalogo_id?: number | null;
    esquina_catalogo_id?: number | null;
    numero?: string | null;
    numero_tipo?: string | null;
  }) => {
    await guardarNormalizacion(payload);
    if (queryEnabled) await refetch();
  };

  const onGuardarPuntoManual = async (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
  }) => {
    await guardarPuntoManual({ ...payload, do_reverse: true });
    setSelectedForManual(null);
    if (queryEnabled) await refetch();
  };

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
        <DomiciliosQueueToggle
          value={queueFocus}
          onChange={handleQueueFocus}
          nomenclaturaCount={nomenclaturaItems.length}
          geolocalizacionCount={geolocalizacionItems.length}
          pendingQuery={!queryEnabled}
        />

        <DomiciliosFiltersBar
          filters={filters}
          onChange={setFilters}
          onFiltrar={onFiltrar}
          onLimpiar={onLimpiar}
        />

        {!queryEnabled && (
          <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 2, px: 0.5 }}>
            Definí el rango de fechas y el alcance, luego presioná <strong>Filtrar</strong> para cargar
            pendientes y trabajar en nomenclatura o geolocalización.
          </Typography>
        )}

        {error && (
          <Alert severity="error" sx={{ ...alertBaseStyles, mb: 2 }}>
            {error}
          </Alert>
        )}

        {queryEnabled && (
          <>
            {queueFocus === "all" && (
              <Box
                sx={{
                  borderRadius: "12px",
                  border: `1px solid ${GLASS_COLORS.borderLight}`,
                  backgroundColor: GLASS_COLORS.cardBg,
                  backdropFilter: "blur(10px)",
                  WebkitBackdropFilter: "blur(10px)",
                  px: 1,
                  overflow: "hidden",
                }}
              >
                <Tabs
                  value={activeTab}
                  onChange={(_, v: DomiciliosTab) => {
                    setActiveTab(v);
                    if (v !== "geolocalizacion") {
                      setSelectedForManual(null);
                    }
                  }}
                  sx={{
                    minHeight: 44,
                    "& .MuiTab-root": { color: GLASS_COLORS.textSecondary, fontFamily: '"Tactic Sans", sans-serif' },
                    "& .Mui-selected": { color: GLASS_COLORS.primary },
                    "& .MuiTabs-indicator": { backgroundColor: GLASS_COLORS.primary },
                  }}
                >
                  <Tab label="Nomenclatura" value="nomenclatura" />
                  <Tab label="Geolocalización" value="geolocalizacion" />
                </Tabs>
              </Box>
            )}

            <Box sx={{ mt: 1.5 }}>
              {(queueFocus === "all" && activeTab === "nomenclatura") || queueFocus === "nomenclatura" ? (
                <TabNomenclaturaTable
                  items={nomenclaturaItems}
                  loading={loading}
                  onGuardar={onGuardarNormalizacion}
                />
              ) : (
                <>
                  <TabGeolocalizacionTable
                    items={geolocalizacionItems}
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
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
};

export default GestionarDomiciliosContainer;
