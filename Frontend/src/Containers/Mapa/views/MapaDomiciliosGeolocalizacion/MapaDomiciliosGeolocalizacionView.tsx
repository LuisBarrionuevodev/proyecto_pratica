import { Alert, Box, Divider, Paper } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { MRT_PaginationState } from "material-react-table";
import type { GestionDomiciliosMapPoint, GestionDomiciliosRow } from "../../../../api/gestionDomiciliosApi";
import { useAppFeedback } from "../../../../components/feedback";
import { alertBaseStyles, moduleContentColumnSx } from "../../../Actuaciones/styles/filtroStyles";
import { moduleContentPanelPaperSx } from "../../../../styles/GlassStyles";
import { MapaDomicilioDetalleOperativo } from "./components/MapaDomicilioDetalleOperativo";
import { MapaDomiciliosGeolocalizacionFiltro } from "./components/MapaDomiciliosGeolocalizacionFiltro";
import { MapaDomiciliosGeolocalizacionLista } from "./components/MapaDomiciliosGeolocalizacionLista";
import {
  GESTION_MAP_DEFAULT_CENTER,
  MapaDomiciliosGeolocalizacionMapPanel,
} from "./components/MapaDomiciliosGeolocalizacionMapPanel";
import { MapaDomiciliosGeolocalizacionPageHeader } from "./components/MapaDomiciliosGeolocalizacionPageHeader";
import { useDomicilioGeolocalizacionActions } from "./hooks/useDomicilioGeolocalizacionActions";
import { useGestionDomicilios } from "./hooks/useGestionDomicilios";
import {
  MAP_GEO_PANEL_HEIGHT,
  mapGeoListaScrollContainerSx,
  mapGeoPanelPaperSx,
} from "./mapaGeolocalizacionLayout";
import type { MapaDomiciliosGeolocalizacionViewProps } from "./types";

const DEFAULT_TITLE = "Gestión de Domicilios";
const DEFAULT_SUBTITLE = "Cola operativa de geolocalización";

/**
 * Vista compartida PR6C.10: geolocalización/reubicación de domicilios (mapa + lista).
 * Usada por Gestión Domicilios hoy; Mapa en PR6C.11.
 */
export function MapaDomiciliosGeolocalizacionView({
  title = DEFAULT_TITLE,
  subtitle = DEFAULT_SUBTITLE,
  showHeader = true,
  filterVariant = "dropdown",
  actionVariant = "button",
  showDetailPanel = true,
  defaultStatus = "requiere_accion",
}: MapaDomiciliosGeolocalizacionViewProps = {}) {
  const feedback = useAppFeedback();
  const { guardarPuntoManual } = useDomicilioGeolocalizacionActions();
  const {
    data,
    loading,
    error,
    statusOperativo,
    setStatusOperativo,
    page,
    setPage,
    searchQ,
    setSearchQ,
    applySearch,
    clearSearch,
    refetch,
    pageSize,
  } = useGestionDomicilios(defaultStatus);

  const [selectedRow, setSelectedRow] = useState<GestionDomiciliosRow | null>(null);
  const [manualEditRow, setManualEditRow] = useState<GestionDomiciliosRow | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [focusCenter, setFocusCenter] = useState<[number, number] | null>(null);

  useEffect(() => {
    if (!loading && !error) {
      setLastUpdatedAt(new Date());
    }
  }, [loading, error, data?.rows.length, data?.pagination.page]);

  const rows = data?.rows ?? [];
  const mapPoints = data?.map_points ?? [];
  const summary = data?.summary ?? null;
  const totalRows = data?.pagination.total ?? 0;

  const pagination: MRT_PaginationState = useMemo(
    () => ({ pageIndex: Math.max(0, page - 1), pageSize }),
    [page, pageSize]
  );

  const handlePaginationChange = useCallback(
    (next: MRT_PaginationState) => {
      setPage(next.pageIndex + 1);
    },
    [setPage]
  );

  const selectRow = useCallback((row: GestionDomiciliosRow) => {
    setSelectedRow(row);
    setManualEditRow(null);
    if (row.geo_chip === "EN_MAPA" && row.lat != null && row.lng != null) {
      setFocusCenter([row.lat, row.lng]);
    } else {
      setFocusCenter(GESTION_MAP_DEFAULT_CENTER);
    }
  }, []);

  const startGeolocalizar = useCallback((row: GestionDomiciliosRow) => {
    setSelectedRow(row);
    setManualEditRow(row);
    setFocusCenter(GESTION_MAP_DEFAULT_CENTER);
  }, []);

  const startReubicar = useCallback((row: GestionDomiciliosRow) => {
    setSelectedRow(row);
    setManualEditRow(row);
    if (row.lat != null && row.lng != null) {
      setFocusCenter([row.lat, row.lng]);
    }
  }, []);

  const handleMapPointSelect = useCallback(
    (point: GestionDomiciliosMapPoint) => {
      const row =
        rows.find((r) => r.domicilio_id === point.domicilio_id) ??
        ({
          domicilio_id: point.domicilio_id,
          domicilio_linea: point.label,
          status_operativo: point.status_operativo,
          status_operativo_label: point.status_operativo_label,
          geo_chip: point.geo_chip,
          has_coordinates: true,
          lat: point.lat,
          lng: point.lng,
          requiere_accion: point.requiere_accion,
        } satisfies GestionDomiciliosRow);
      startReubicar(row);
    },
    [rows, startReubicar]
  );

  const onGuardarPuntoManual = useCallback(
    async (payload: { domicilio_id: number; lat: number; lng: number }) => {
      await guardarPuntoManual({ ...payload, do_reverse: true });
      feedback.success("Ubicación guardada correctamente.");
      setManualEditRow(null);
      setFocusCenter(null);
      await refetch();
    },
    [feedback, guardarPuntoManual, refetch]
  );

  const lastUpdatedLabel = lastUpdatedAt
    ? `Última actualización ${lastUpdatedAt.toLocaleTimeString("es-AR", {
        hour: "2-digit",
        minute: "2-digit",
      })}`
    : null;

  const emptyMessage =
    statusOperativo === "requiere_accion"
      ? "No hay domicilios que requieran acción con este filtro."
      : "No hay domicilios para mostrar.";

  const isMapaLayout = filterVariant === "mapa";
  const mapPanelHeight = isMapaLayout ? "100%" : "min(72vh, 640px)";

  return (
    <Box sx={moduleContentColumnSx}>
      {showHeader ? (
        <MapaDomiciliosGeolocalizacionPageHeader
          title={title}
          subtitle={subtitle}
          onRefresh={refetch}
          loading={loading}
          lastUpdatedLabel={lastUpdatedLabel}
        />
      ) : null}

      <MapaDomiciliosGeolocalizacionFiltro
        statusOperativo={statusOperativo}
        onStatusChange={setStatusOperativo}
        searchQ={searchQ}
        onSearchChange={setSearchQ}
        onFiltrar={applySearch}
        onLimpiar={clearSearch}
        summary={summary}
        loading={loading}
        filterVariant={filterVariant}
      />

      {error ? (
        <Alert severity="error" sx={{ ...alertBaseStyles, mb: 0 }}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", lg: "row" },
          gap: 2,
          width: "100%",
          maxWidth: "100%",
          alignItems: "stretch",
          ...(isMapaLayout
            ? { flexShrink: 0 }
            : { minHeight: 0, flex: 1, overflow: "hidden" }),
        }}
      >
        <Paper
          elevation={0}
          sx={{
            ...(isMapaLayout ? { ...moduleContentPanelPaperSx, ...mapGeoPanelPaperSx } : {}),
            flex: { xs: "1 1 auto", lg: "0 0 65%" },
            maxWidth: { lg: "65%" },
            minWidth: 0,
            p: isMapaLayout ? 0 : 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <MapaDomiciliosGeolocalizacionMapPanel
            mapPoints={mapPoints}
            selectedId={selectedRow?.domicilio_id ?? null}
            focusCenter={manualEditRow ? null : focusCenter}
            onSelectPoint={handleMapPointSelect}
            height={mapPanelHeight}
            editRow={manualEditRow}
            onCloseEdit={() => setManualEditRow(null)}
            onSavePoint={onGuardarPuntoManual}
          />
        </Paper>

        <Paper
          elevation={0}
          sx={{
            ...(isMapaLayout ? { ...moduleContentPanelPaperSx, ...mapGeoPanelPaperSx } : {}),
            flex: { xs: "1 1 auto", lg: "0 0 35%" },
            maxWidth: { lg: "35%" },
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            minHeight: isMapaLayout ? MAP_GEO_PANEL_HEIGHT : 360,
            overflow: "hidden",
          }}
        >
          {isMapaLayout ? (
            <Box sx={mapGeoListaScrollContainerSx}>
              <MapaDomiciliosGeolocalizacionLista
                rows={rows}
                loading={loading}
                emptyMessage={emptyMessage}
                selectedId={selectedRow?.domicilio_id ?? null}
                totalRows={totalRows}
                pagination={pagination}
                onPaginationChange={handlePaginationChange}
                onSelectRow={selectRow}
                onGeolocalizar={startGeolocalizar}
                onReubicar={startReubicar}
                actionVariant={actionVariant}
                layoutVariant="mapa"
              />
            </Box>
          ) : (
            <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", overflowX: "hidden" }}>
              <MapaDomiciliosGeolocalizacionLista
                rows={rows}
                loading={loading}
                emptyMessage={emptyMessage}
                selectedId={selectedRow?.domicilio_id ?? null}
                totalRows={totalRows}
                pagination={pagination}
                onPaginationChange={handlePaginationChange}
                onSelectRow={selectRow}
                onGeolocalizar={startGeolocalizar}
                onReubicar={startReubicar}
                actionVariant={actionVariant}
              />
            </Box>
          )}
          {showDetailPanel ? (
            <>
              <Divider />
              <MapaDomicilioDetalleOperativo
                row={selectedRow}
                onClose={() => {
                  setSelectedRow(null);
                  setFocusCenter(null);
                }}
                onGeolocalizar={startGeolocalizar}
                onReubicar={startReubicar}
              />
            </>
          ) : null}
        </Paper>
      </Box>
    </Box>
  );
}

export default MapaDomiciliosGeolocalizacionView;
