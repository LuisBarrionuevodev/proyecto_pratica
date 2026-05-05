import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
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
  type CalleCatalogoItem,
} from "../../api/geolocalizacionApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import type { MRT_ColumnDef } from "material-react-table";
import type { IActuacionListItem } from "../../api/actuacionesListApi";
import { ACTUACIONES_COMPOSITE_COLUMN_IDS } from "./Components/actuacionesCompositeColumns";

import {
  wrapperStyles,
  titleStyles,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "./styles/filtroStyles";

const ActuacionesContainer = (): JSX.Element => {
  const navigate = useNavigate();
  const [tab] = useState<"todos" | "pendientes">("todos");

  const { actuaciones, meta, loading, error, hasSearched, buscar, fusionarActuacionEnLista } =
    useActuacionesFiltradas();

  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [pendientesDesde, setPendientesDesde] = useState<string>(defaultRange.desde);
  const [pendientesHasta, setPendientesHasta] = useState<string>(defaultRange.hasta);
  const [pendingType, setPendingType] = useState<ActuacionesPendientesTipo>("domicilios");
  const [pendingSummary, setPendingSummary] = useState<IActuacionesPendientesSummary | null>(null);
  const [pendingItems, setPendingItems] = useState<IActuacionesPendientesItem[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);

  const [callesCatalogo, setCallesCatalogo] = useState<CalleCatalogoItem[]>([]);

  const handleFiltrarTodos = useCallback(
    (filtros: {
      desde: string | null;
      hasta: string | null;
      tipo: string | null;
      contraproducencia: string | null;
      orden_trabajo: string | null;
    }) => {
      void buscar(filtros);
    },
    [buscar]
  );

  const handleRefreshListaActuaciones = useCallback(() => {
    handleFiltrarTodos({
      desde: meta?.desde || null,
      hasta: meta?.hasta || null,
      tipo: meta?.tipo || null,
      contraproducencia: meta?.contraproducencia || null,
      orden_trabajo: meta?.orden_trabajo || null,
    });
  }, [handleFiltrarTodos, meta]);

  useEffect(() => {
    getActuacionesPendientesSummary(pendientesDesde, pendientesHasta)
      .then(setPendingSummary)
      .catch(() => undefined);
  }, [pendientesDesde, pendientesHasta]);

  const fusionarPendienteEnLista = useCallback((row: IActuacionListItem) => {
    const rid = Number(row.id);
    setPendingItems((prev) =>
      prev.map((item) => (Number(item.id) === rid ? { ...item, ...row } : item))
    );
  }, []);

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
    try {
      const resp = await fetchCallesCatalogo(value, 25);
      setCallesCatalogo(resp.items);
    } finally {
      // no-op
    }
  }, []);

  useEffect(() => {
    if (tab === "pendientes" && pendingType === "domicilios") {
      handleSearchCalles("");
    }
  }, [tab, pendingType, handleSearchCalles]);

  const pendingExtraColumns = useMemo<MRT_ColumnDef<IActuacionListItem>[]>(() => [], []);

  const pendingColumnVisibility = useMemo(() => {
    if (pendingType !== "domicilios") return {};
    const hideComposites = Object.fromEntries(
      ACTUACIONES_COMPOSITE_COLUMN_IDS.map((id) => [id, false])
    );
    return {
      ...hideComposites,
      orden_trabajo_numero: true,
      fecha_actuacion: true,
      calle: true,
      calle_catalogo_id: false,
      numero: true,
      tipo_actuacion: false,
      contraproducencia: false,
      rubro_nombre: false,
      inspector1: false,
      inspector2: false,
      inspector3: false,
      notificacion_motivo_1: false,
      notificacion_motivo_2: false,
      notificacion_motivo_3: false,
      acta_inspeccion_num: false,
      acta_notificacion_num: false,
      acta_comprobacion_num: false,
      acta_clausura_num: false,
      acta_decomiso_num: false,
      decomiso_kilos_total: false,
      expediente_numero: false,
      expediente_anio: false,
      oficio_numero: false,
      oficio_anio: false,
      oficio_causa: false,
    };
  }, [pendingType]);

  const handleBeforeSavePendiente = useCallback(async (_fullRow: IActuacionListItem) => {}, []);

  return (
    <Box sx={wrapperStyles}>
        <Typography sx={titleStyles}>Actuaciones</Typography>

        <>
            <FiltroFechas onFiltrar={handleFiltrarTodos} />

            {error && hasSearched && (
              <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
                <strong>Error:</strong> {error}
              </Alert>
            )}

            {loading && (
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  minHeight: 320,
                  width: "100%",
                }}
              >
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
                onRefresh={handleRefreshListaActuaciones}
                onActuacionListPatch={fusionarActuacionEnLista}
              />
            )}
        </>

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
                {pendingType === "domicilios" && (
                  <Alert
                    severity="info"
                    sx={{ marginBottom: 2, display: "flex", alignItems: "center", gap: 2 }}
                  >
                    La resolución de domicilios pendientes se gestiona ahora en el módulo central.
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => navigate("/gestionarDomicilios")}
                      sx={{ marginLeft: 1 }}
                    >
                      Ir a Gestionar domicilios
                    </Button>
                  </Alert>
                )}
                <TablaActuaciones
                  data={pendingItems}
                  loading={pendingLoading}
                  onRefresh={handleFiltrarPendientes}
                  onActuacionListPatch={fusionarPendienteEnLista}
                  initialColumnVisibility={pendingColumnVisibility}
                  extraColumns={pendingExtraColumns}
                  enableEditing={pendingType !== "notificaciones" && pendingType !== "domicilios"}
                  hideRowActions={false}
                  hideDeleteAction
                  skipValidation
                  skipUpdate
                  numeroHeader="Número/Esquina"
                  numeroEditorLabel="Número/Esquina"
                  onBeforeSave={handleBeforeSavePendiente}
                  readOnlyColumns={pendingType === "domicilios" ? ["orden_trabajo_numero", "fecha_actuacion"] : []}
                  numeroCallesOptions={callesCatalogo.map((c) => c.nombre)}
                  numeroAllowFreeSolo
                />
              </>
            )}
          </>
        )}
    </Box>
  );
};

export default ActuacionesContainer;
