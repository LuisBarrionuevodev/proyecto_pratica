import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Badge,
  Box,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Tab,
  Tabs,
  TextField,
  ThemeProvider,
  Typography,
} from "@mui/material";

import { darkTheme } from "../../configs/theme";
import TablaRelevamientos from "./Components/TableRelevamientos";
import FiltroRelevamientos from "./Components/FiltroRelevamientos";
import FiltroPendientes from "../Actuaciones/Components/FiltroPendientes";
import { useRelevamientosFiltradas } from "./hooks/useRelevamientosFiltradas";
import {
  getRelevamientosPendientes,
  getRelevamientosPendientesSummary,
  type IRelevamientosPendientesItem,
  type IRelevamientosPendientesSummary,
} from "../../api/relevamientosPendientesApi";
import { fetchCallesCatalogo, setCalleCanon, type CalleCatalogoItem } from "../../api/geolocalizacionApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import type { MRT_ColumnDef } from "material-react-table";
import type { IRelevamientoListItem } from "../../api/relevamientosListApi";

import {
  wrapperStyles,
  titleStyles,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "../Actuaciones/styles/filtroStyles";

const RelevamientosContainer = (): JSX.Element => {
  const [tab, setTab] = useState<"todos" | "pendientes">("todos");

  const { relevamientos, meta, loading, error, hasSearched, buscar } = useRelevamientosFiltradas();

  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [pendientesDesde, setPendientesDesde] = useState<string>(defaultRange.desde);
  const [pendientesHasta, setPendientesHasta] = useState<string>(defaultRange.hasta);
  const [pendingSummary, setPendingSummary] = useState<IRelevamientosPendientesSummary | null>(null);
  const [pendingItems, setPendingItems] = useState<IRelevamientosPendientesItem[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);

  const [callesCatalogo, setCallesCatalogo] = useState<CalleCatalogoItem[]>([]);
  const [callesLoading, setCallesLoading] = useState(false);

  const handleFiltrarTodos = (filtros: {
    desde: string | null;
    hasta: string | null;
    inspector: string | null;
    calle: string | null;
    numero: string | null;
  }) => {
    buscar(filtros);
  };

  useEffect(() => {
    getRelevamientosPendientesSummary(pendientesDesde, pendientesHasta)
      .then(setPendingSummary)
      .catch(() => undefined);
  }, [pendientesDesde, pendientesHasta]);

  const refreshPendientes = useCallback(async (desde: string, hasta: string) => {
    setPendingLoading(true);
    setPendingError(null);
    try {
      const [summary, items] = await Promise.all([
        getRelevamientosPendientesSummary(desde, hasta),
        getRelevamientosPendientes({ tipo: "domicilios", desde, hasta }),
      ]);
      setPendingSummary(summary);
      setPendingItems(items);
    } catch (err: any) {
      setPendingError(err?.response?.data?.detail || "Error al cargar pendientes");
      setPendingItems([]);
    } finally {
      setPendingLoading(false);
    }
  }, []);

  const handleFiltrarPendientes = useCallback(async () => {
    await refreshPendientes(pendientesDesde, pendientesHasta);
  }, [refreshPendientes, pendientesDesde, pendientesHasta]);

  const handleLimpiarPendientes = () => {
    const range = getCurrentMonthRange();
    setPendientesDesde(range.desde);
    setPendientesHasta(range.hasta);
    refreshPendientes(range.desde, range.hasta);
  };

  useEffect(() => {
    if (tab === "pendientes") {
      handleFiltrarPendientes();
    }
  }, [tab, handleFiltrarPendientes]);

  const handleSearchCalles = useCallback(async (value: string) => {
    setCallesLoading(true);
    try {
      const resp = await fetchCallesCatalogo(value, 25);
      setCallesCatalogo(resp.items);
    } finally {
      setCallesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "pendientes") {
      handleSearchCalles("");
    }
  }, [tab, handleSearchCalles]);

  const pendingExtraColumns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => [
    {
      accessorKey: "calle_mostrar",
      header: "Calle",
      size: 200,
      enableEditing: false,
    },
    {
      accessorKey: "calle_estado",
      header: "Estado Calle",
      size: 120,
      enableEditing: false,
    },
    {
      accessorKey: "calle_score",
      header: "Score Calle",
      size: 120,
      enableEditing: false,
    },
    {
      accessorKey: "calle_sugerida",
      header: "Calle sugerida",
      size: 200,
      enableEditing: false,
    },
    {
      accessorKey: "calle_catalogo_id",
      header: "Calle catálogo",
      size: 240,
      enableEditing: true,
      Cell: ({ cell }) => {
        const value = cell.getValue<number | null>();
        const match = callesCatalogo.find((opt) => opt.id === value);
        return match ? match.nombre : "";
      },
      Edit: ({ row }) => {
        const currentValue = (row as any)?._valuesCache?.calle_catalogo_id ?? row.original.calle_catalogo_id;
        const currentOption =
          callesCatalogo.find((opt) => opt.id === currentValue) || null;

        return (
          <Autocomplete
            options={callesCatalogo}
            getOptionLabel={(option) => option.nombre}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            loading={callesLoading}
            value={currentOption}
            onInputChange={(_, value) => handleSearchCalles(value)}
            onChange={(_, newValue) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                calle_catalogo_id: newValue?.id ?? null,
              };
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Calle catálogo"
                variant="outlined"
              />
            )}
          />
        );
      },
    },
  ], [callesCatalogo, callesLoading, handleSearchCalles]);

  const pendingColumnVisibility = useMemo(() => ({
    calle: false,
    calle_mostrar: true,
    calle_estado: true,
    calle_score: true,
    calle_sugerida: true,
    calle_catalogo_id: true,
  }), []);

  const handleBeforeSavePendiente = useCallback(async (fullRow: IRelevamientoListItem) => {
    const domicilioId = fullRow.domicilio_id;
    const calleCatalogoId = fullRow.calle_catalogo_id;
    if (!domicilioId || !calleCatalogoId) return;
    await setCalleCanon(domicilioId, Number(calleCatalogoId));
  }, []);

  const totalPendientes = pendingSummary?.total ?? 0;

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={wrapperStyles}>
        <Typography sx={titleStyles}>Relevamientos</Typography>

        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          sx={{ marginBottom: 2 }}
        >
          <Tab label="Todos" value="todos" />
          <Tab
            label={
              <Badge color="error" badgeContent={totalPendientes} showZero>
                Pendientes
              </Badge>
            }
            value="pendientes"
          />
        </Tabs>

        {tab === "todos" && (
          <>
            <FiltroRelevamientos onFiltrar={handleFiltrarTodos} />

            {error && hasSearched && (
              <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
                <strong>Error:</strong> {error}
              </Alert>
            )}

            {loading && (
              <Box sx={{ display: "flex", justifyContent: "center", padding: "40px" }}>
                <CircularProgress sx={{ color: "#0166FF" }} />
              </Box>
            )}

            {hasSearched && !loading && meta && (
              <Box sx={metaInfoStyles}>
                <Typography sx={metaItemStyles}>
                  <strong>Total:</strong> {meta.total}
                </Typography>
                <Typography sx={metaItemStyles}>
                  <strong>Mostrando:</strong> {relevamientos.length} de {meta.total}
                </Typography>
                <Typography sx={metaItemStyles}>
                  <strong>Página:</strong> {meta.page}
                </Typography>
                {meta.desde && meta.hasta && (
                  <Typography sx={metaItemStyles}>
                    <strong>Rango:</strong> {meta.desde} - {meta.hasta}
                  </Typography>
                )}
                {meta.inspector && (
                  <Typography sx={metaItemStyles}>
                    <strong>Inspector:</strong> {meta.inspector}
                  </Typography>
                )}
                {meta.calle && (
                  <Typography sx={metaItemStyles}>
                    <strong>Calle:</strong> {meta.calle}
                  </Typography>
                )}
                {meta.numero && (
                  <Typography sx={metaItemStyles}>
                    <strong>Número:</strong> {meta.numero}
                  </Typography>
                )}
              </Box>
            )}

            {hasSearched && !loading && (
              <TablaRelevamientos
                data={relevamientos}
                loading={loading}
                onRefresh={() =>
                  handleFiltrarTodos({
                    desde: meta?.desde || null,
                    hasta: meta?.hasta || null,
                    inspector: meta?.inspector || null,
                    calle: meta?.calle || null,
                    numero: meta?.numero || null,
                  })
                }
              />
            )}
          </>
        )}

        {tab === "pendientes" && (
          <>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", marginBottom: 2 }}>
              <Card sx={{ minWidth: 220 }}>
                <CardActionArea onClick={() => handleFiltrarPendientes()}>
                  <CardContent>
                    <Typography variant="subtitle2">Domicilios pendientes</Typography>
                    <Typography variant="h5">{pendingSummary?.domicilios ?? 0}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Box>

            <FiltroPendientes
              desde={pendientesDesde}
              hasta={pendientesHasta}
              onChangeDesde={setPendientesDesde}
              onChangeHasta={setPendientesHasta}
              onFiltrar={handleFiltrarPendientes}
              onLimpiar={handleLimpiarPendientes}
              title="Filtros de Pendientes"
            />

            {pendingError && (
              <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
                <strong>Error:</strong> {pendingError}
              </Alert>
            )}

            {pendingLoading && (
              <Box sx={{ display: "flex", justifyContent: "center", padding: "40px" }}>
                <CircularProgress sx={{ color: "#0166FF" }} />
              </Box>
            )}

            {!pendingLoading && (
              <>
                <Box sx={metaInfoStyles}>
                  <Typography sx={metaItemStyles}>
                    <strong>Mostrando:</strong> Domicilios pendientes ({pendingItems.length})
                  </Typography>
                </Box>
                <TablaRelevamientos
                  data={pendingItems}
                  loading={pendingLoading}
                  onRefresh={handleFiltrarPendientes}
                  initialColumnVisibility={pendingColumnVisibility}
                  extraColumns={pendingExtraColumns}
                  hideRowActions
                  onBeforeSave={handleBeforeSavePendiente}
                />
              </>
            )}
          </>
        )}
      </Box>
    </ThemeProvider>
  );
};

export default RelevamientosContainer;
