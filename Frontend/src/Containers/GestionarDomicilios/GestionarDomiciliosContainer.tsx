import { Alert, Box, Tab, Tabs, ThemeProvider, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import { darkTheme } from "../../configs/theme";
import { getCurrentMonthRange } from "../../utils/dateRange";
import DomiciliosFiltersBar from "./components/DomiciliosFiltersBar";
import DomiciliosSummaryCards from "./components/DomiciliosSummaryCards";
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
  const [filters, setFilters] = useState<DomiciliosFilters>({
    desde: defaultRange.desde,
    hasta: defaultRange.hasta,
    scope: "all",
  });
  const [selectedForManual, setSelectedForManual] = useState<DomicilioPendienteItem | null>(null);

  const { nomenclaturaItems, geolocalizacionItems, loading, error, refetch } =
    useDomiciliosPendientes(filters);

  const { guardarNormalizacion } = useDomicilioNormalizationActions();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();

  const onFiltrar = async () => {
    await refetch();
  };

  const onLimpiar = async () => {
    const range = getCurrentMonthRange();
    const reset = { desde: range.desde, hasta: range.hasta, scope: "all" as const };
    setFilters(reset);
  };

  const onGuardarNormalizacion = async (payload: {
    domicilio_id: number;
    calle_catalogo_id?: number | null;
    esquina_catalogo_id?: number | null;
    numero?: string | null;
    numero_tipo?: string | null;
  }) => {
    await guardarNormalizacion(payload);
    await refetch();
  };

  const onGuardarPuntoManual = async (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
  }) => {
    await guardarPuntoManual({ ...payload, do_reverse: true });
    setSelectedForManual(null);
    await refetch();
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={{ width: "100%", p: 2 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Gestionar domicilios
        </Typography>

        <DomiciliosSummaryCards
          nomenclaturaCount={nomenclaturaItems.length}
          geolocalizacionCount={geolocalizacionItems.length}
        />

        <DomiciliosFiltersBar
          filters={filters}
          onChange={setFilters}
          onFiltrar={onFiltrar}
          onLimpiar={onLimpiar}
        />

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ bgcolor: "#2B2E34", px: 1 }}>
          <Tabs
            value={activeTab}
            onChange={(_, v: DomiciliosTab) => {
              setActiveTab(v);
              if (v !== "geolocalizacion") {
                setSelectedForManual(null);
              }
            }}
          >
            <Tab sx={{ color: "white" }} label="Nomenclatura" value="nomenclatura" />
            <Tab sx={{ color: "white" }} label="Geolocalización" value="geolocalizacion" />
          </Tabs>
        </Box>

        <Box sx={{ mt: 1 }}>
          {activeTab === "nomenclatura" ? (
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
      </Box>
    </ThemeProvider>
  );
};

export default GestionarDomiciliosContainer;
