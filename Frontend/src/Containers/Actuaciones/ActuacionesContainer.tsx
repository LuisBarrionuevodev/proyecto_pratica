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
import TablaActuaciones from "./Components/TableActuaciones";
import FiltroFechas from "./Components/FiltroFechas";
import FiltroPendientes from "./Components/FiltroPendientes";
import { useActuacionesFiltradas } from "./hooks/useActuacionesFiltradas";
import {
  getActuacionesPendientes,
  getActuacionesPendientesSummary,
  type ActuacionesPendientesTipo,
  type IActuacionesPendientesItem,
  type IActuacionesPendientesSummary,
} from "../../api/actuacionesPendientesApi";
import {
  fetchCallesCatalogo,
  setCalleCanon,
  setNumeroEsquina,
  type CalleCatalogoItem,
} from "../../api/geolocalizacionApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import type { MRT_ColumnDef } from "material-react-table";
import type { IActuacionListItem } from "../../api/actuacionesListApi";

import {
  wrapperStyles,
  titleStyles,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "./styles/filtroStyles";

const ActuacionesContainer = (): JSX.Element => {
  const [tab, setTab] = useState<"todos" | "pendientes">("todos");

  const { actuaciones, meta, loading, error, hasSearched, buscar } = useActuacionesFiltradas();

  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [pendientesDesde, setPendientesDesde] = useState<string>(defaultRange.desde);
  const [pendientesHasta, setPendientesHasta] = useState<string>(defaultRange.hasta);
  const [pendingType, setPendingType] = useState<ActuacionesPendientesTipo>("domicilios");
  const [pendingSummary, setPendingSummary] = useState<IActuacionesPendientesSummary | null>(null);
  const [pendingItems, setPendingItems] = useState<IActuacionesPendientesItem[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);

  const [callesCatalogo, setCallesCatalogo] = useState<CalleCatalogoItem[]>([]);
  const [callesLoading, setCallesLoading] = useState(false);


  const handleFiltrarTodos = (filtros: {
    desde: string | null;
    hasta: string | null;
    tipo: string | null;
    contraproducencia: string | null;
    orden_trabajo: string | null;
  }) => {
    buscar(filtros);
  };

  useEffect(() => {
    getActuacionesPendientesSummary(pendientesDesde, pendientesHasta)
      .then(setPendingSummary)
      .catch(() => undefined);
  }, [pendientesDesde, pendientesHasta]);

  const refreshPendientes = useCallback(async (desde: string, hasta: string, tipo: ActuacionesPendientesTipo) => {
    setPendingLoading(true);
    setPendingError(null);
    try {
      const [summary, items] = await Promise.all([
        getActuacionesPendientesSummary(desde, hasta),
        getActuacionesPendientes({ tipo, desde, hasta }),
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
    await refreshPendientes(pendientesDesde, pendientesHasta, pendingType);
  }, [refreshPendientes, pendientesDesde, pendientesHasta, pendingType]);

  const handleLimpiarPendientes = () => {
    const range = getCurrentMonthRange();
    setPendientesDesde(range.desde);
    setPendientesHasta(range.hasta);
    refreshPendientes(range.desde, range.hasta, pendingType);
  };

  useEffect(() => {
    if (tab === "pendientes") {
      handleFiltrarPendientes();
    }
  }, [tab, handleFiltrarPendientes]);

  const handleCardClick = (tipo: ActuacionesPendientesTipo) => {
    setPendingType(tipo);
    refreshPendientes(pendientesDesde, pendientesHasta, tipo);
  };

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
    if (tab === "pendientes" && pendingType === "domicilios") {
      handleSearchCalles("");
    }
  }, [tab, pendingType, handleSearchCalles]);

  const pendingExtraColumns = useMemo<MRT_ColumnDef<IActuacionListItem>[]>(() => [
    {
      accessorKey: "calle_ingresada",
      header: "Calle ingresada",
      size: 200,
      enableEditing: false,
    },
    {
      accessorKey: "calle_catalogo_id",
      header: "Calle catálogo",
      size: 240,
      enableEditing: pendingType === "domicilios",
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
                calle: newValue?.nombre ?? row.original.calle ?? "",
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
  ], [pendingType, callesCatalogo, callesLoading, handleSearchCalles]);

  const pendingColumnVisibility = useMemo(() => ({
    calle: true,
    numero: true,
    calle_ingresada: true,
    calle_catalogo_id: pendingType === "domicilios",
  }), [pendingType]);

  const handleBeforeSavePendiente = useCallback(async (fullRow: IActuacionListItem) => {
    if (pendingType !== "domicilios") return;
    const domicilioId = fullRow.domicilio_id;
    const calleCatalogoId = fullRow.calle_catalogo_id;
    const numero = fullRow.numero;
    const numeroTipo = (fullRow as any).numero_tipo;
    if (!domicilioId) return;
    if (numero) {
      await setNumeroEsquina(domicilioId, String(numero), numeroTipo || null);
    }
    if (calleCatalogoId) {
      await setCalleCanon(domicilioId, Number(calleCatalogoId));
    }
  }, [pendingType]);

  const totalPendientes = pendingSummary?.total ?? 0;

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={wrapperStyles}>
        <Typography sx={titleStyles}>Actuaciones</Typography>

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
            <FiltroFechas onFiltrar={handleFiltrarTodos} />

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
                  <strong>Mostrando:</strong> {actuaciones.length} de {meta.total}
                </Typography>
                <Typography sx={metaItemStyles}>
                  <strong>Página:</strong> {meta.page}
                </Typography>
                {meta.desde && meta.hasta && (
                  <Typography sx={metaItemStyles}>
                    <strong>Rango:</strong> {meta.desde} - {meta.hasta}
                  </Typography>
                )}
                {meta.tipo && (
                  <Typography sx={metaItemStyles}>
                    <strong>Tipo:</strong> {meta.tipo}
                  </Typography>
                )}
                {meta.contraproducencia && (
                  <Typography sx={metaItemStyles}>
                    <strong>Contraproducencia:</strong> {meta.contraproducencia}
                  </Typography>
                )}
                {meta.orden_trabajo && (
                  <Typography sx={metaItemStyles}>
                    <strong>OT:</strong> {meta.orden_trabajo}
                  </Typography>
                )}
              </Box>
            )}

            {hasSearched && !loading && (
              <TablaActuaciones
                data={actuaciones}
                loading={loading}
                onRefresh={() =>
                  handleFiltrarTodos({
                    desde: meta?.desde || null,
                    hasta: meta?.hasta || null,
                    tipo: meta?.tipo || null,
                    contraproducencia: meta?.contraproducencia || null,
                    orden_trabajo: meta?.orden_trabajo || null,
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
                <CardActionArea onClick={() => handleCardClick("domicilios")}>
                  <CardContent>
                    <Typography variant="subtitle2">Domicilios pendientes</Typography>
                    <Typography variant="h5">{pendingSummary?.domicilios ?? 0}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
              <Card sx={{ minWidth: 220 }}>
                <CardActionArea onClick={() => handleCardClick("sin_expediente")}>
                  <CardContent>
                    <Typography variant="subtitle2">Actas sin expediente</Typography>
                    <Typography variant="h5">{pendingSummary?.sin_expediente ?? 0}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
              <Card sx={{ minWidth: 220 }}>
                <CardActionArea onClick={() => handleCardClick("notificaciones")}>
                  <CardContent>
                    <Typography variant="subtitle2">Notificaciones pendientes</Typography>
                    <Typography variant="h5">{pendingSummary?.notificaciones ?? 0}</Typography>
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
                    <strong>Mostrando:</strong>{" "}
                    {pendingType === "domicilios"
                      ? "Domicilios pendientes"
                      : pendingType === "sin_expediente"
                      ? "Actas sin expediente"
                      : "Notificaciones pendientes"}{" "}
                    ({pendingItems.length})
                  </Typography>
                </Box>
                <TablaActuaciones
                  data={pendingItems}
                  loading={pendingLoading}
                  onRefresh={handleFiltrarPendientes}
                  initialColumnVisibility={pendingColumnVisibility}
                  extraColumns={pendingExtraColumns}
                  enableEditing={pendingType !== "notificaciones"}
                  hideRowActions={false}
                  hideDeleteAction
                  skipValidation
                  skipUpdate
                  numeroHeader="Número/Esquina"
                  numeroEditorLabel="Número/Esquina"
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

export default ActuacionesContainer;
