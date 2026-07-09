import { Alert, Box, Divider, Paper } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { MRT_PaginationState } from "material-react-table";
import type { GestionDomiciliosMapPoint, GestionDomiciliosRow } from "../../../api/gestionDomiciliosApi";
import { useAppFeedback } from "../../../components/feedback";
import { alertBaseStyles, moduleContentColumnSx } from "../../Actuaciones/styles/filtroStyles";
import { functionalPageShellSx } from "../../../styles/functionalPageShell";
import { GestionDomicilioDetalleOperativo } from "./GestionDomicilioDetalleOperativo";
import { GestionDomiciliosFiltro } from "./GestionDomiciliosFiltro";
import { GestionDomiciliosLista } from "./GestionDomiciliosLista";
import {
  GESTION_MAP_DEFAULT_CENTER,
  GestionDomiciliosMapaPanel,
} from "./GestionDomiciliosMapaPanel";
import { GestionarDomiciliosPageHeader } from "./GestionarDomiciliosPageHeader";
import ManualMapPanel from "./ManualMapPanel";
import { useDomicilioGeolocalizacionActions } from "../hooks/useDomicilioGeolocalizacionActions";
import { useGestionDomicilios } from "../hooks/useGestionDomicilios";
import { rowToManualMapItem } from "../utils/rowToManualMapItem";

/** Vista única PR6C.6: mapa izquierda + lista/d detalle derecha. */
export function GestionDomiciliosVistaUnica() {
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
    refetch,
    pageSize,
  } = useGestionDomicilios("requiere_accion");

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
      selectRow(row);
    },
    [rows, selectRow]
  );

  const onGuardarPuntoManual = useCallback(
    async (payload: { domicilio_id: number; lat: number; lng: number }) => {
      await guardarPuntoManual({ ...payload, do_reverse: true });
      feedback.success("Punto guardado correctamente.");
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

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx }}>
      <GestionarDomiciliosPageHeader
        onRefresh={refetch}
        loading={loading}
        lastUpdatedLabel={lastUpdatedLabel}
      />

      <GestionDomiciliosFiltro
        statusOperativo={statusOperativo}
        onStatusChange={setStatusOperativo}
        searchQ={searchQ}
        onSearchChange={setSearchQ}
        summary={summary}
        loading={loading}
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
          minHeight: 0,
          flex: 1,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            flex: { xs: "1 1 auto", lg: "0 0 65%" },
            p: 1,
            minHeight: 360,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {manualEditRow ? (
            <ManualMapPanel
              selected={rowToManualMapItem(manualEditRow)}
              onClose={() => setManualEditRow(null)}
              onSave={onGuardarPuntoManual}
            />
          ) : (
            <GestionDomiciliosMapaPanel
              mapPoints={mapPoints}
              selectedId={selectedRow?.domicilio_id ?? null}
              focusCenter={focusCenter}
              onSelectPoint={handleMapPointSelect}
              height="min(72vh, 640px)"
            />
          )}
        </Paper>

        <Paper
          elevation={0}
          sx={{
            flex: { xs: "1 1 auto", lg: "0 0 35%" },
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            minHeight: 360,
          }}
        >
          <Box sx={{ flex: 1, minHeight: 0, overflow: "auto" }}>
            <GestionDomiciliosLista
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
            />
          </Box>
          <Divider />
          <GestionDomicilioDetalleOperativo
            row={selectedRow}
            onClose={() => {
              setSelectedRow(null);
              setFocusCenter(null);
            }}
            onGeolocalizar={startGeolocalizar}
            onReubicar={startReubicar}
          />
        </Paper>
      </Box>
    </Box>
  );
}

export default GestionDomiciliosVistaUnica;
