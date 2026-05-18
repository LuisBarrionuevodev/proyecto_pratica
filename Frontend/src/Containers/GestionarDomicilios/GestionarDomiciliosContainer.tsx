import { Alert, Box, Paper, Tab, Tabs } from "@mui/material";
import { useCallback, useMemo, useState } from "react";
import { alertBaseStyles, moduleContentColumnSx } from "../Actuaciones/styles/filtroStyles";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import type { GuardarNomenclaturaBody } from "../../api/geolocalizacionApi";
import ManualMapPanel from "./components/ManualMapPanel";
import TabGeolocalizacionTable from "./components/TabGeolocalizacionTable";
import TabNomenclaturaTable from "./components/TabNomenclaturaTable";
import { useDomicilioGeolocalizacionActions } from "./hooks/useDomicilioGeolocalizacionActions";
import { useDomicilioNormalizationActions } from "./hooks/useDomicilioNormalizationActions";
import { useDomiciliosPendientes } from "./hooks/useDomiciliosPendientes";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosTab } from "./types";

/**
 * Pendientes de normalización / geocodificación: sin filtro por fechas en UI;
 * listado completo según backend (`/map/pendientes`). Sub-vistas Nomenclatura | Geolocalización con el mismo patrón de tabs que Relevamientos / Actas.
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

  const [activeTab, setActiveTab] = useState<DomiciliosTab>("nomenclatura");
  const [selectedForManual, setSelectedForManual] = useState<DomicilioPendienteItem | null>(null);

  const { nomenclaturaItems, geolocalizacionItems, loading, error, refetch } = useDomiciliosPendientes(filters, {
    enabled: true,
  });

  const { guardarNormalizacion } = useDomicilioNormalizationActions();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();

  const onGuardarNormalizacion = async (payload: GuardarNomenclaturaBody & { domicilio_id: number }) => {
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

  const handleTabChange = useCallback((_: unknown, v: DomiciliosTab) => {
    setActiveTab(v);
    if (v !== "geolocalizacion") {
      setSelectedForManual(null);
    }
  }, []);

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx }}>
          <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              variant="scrollable"
              allowScrollButtonsMobile
              sx={moduleSlicesTabsSx}
            >
              <Tab
                label={`Nomenclatura · ${loading ? "…" : nomenclaturaItems.length}`}
                value="nomenclatura"
              />
              <Tab
                label={`Geolocalización · ${loading ? "…" : geolocalizacionItems.length}`}
                value="geolocalizacion"
              />
            </Tabs>
          </Paper>

          {error && (
            <Alert severity="error" sx={{ ...alertBaseStyles, mb: 0 }}>
              {error}
            </Alert>
          )}

          {activeTab === "nomenclatura" && (
            <TabNomenclaturaTable items={nomenclaturaItems} loading={loading} onGuardar={onGuardarNormalizacion} />
          )}

          {activeTab === "geolocalizacion" && (
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
  );
};

export default GestionarDomiciliosContainer;
