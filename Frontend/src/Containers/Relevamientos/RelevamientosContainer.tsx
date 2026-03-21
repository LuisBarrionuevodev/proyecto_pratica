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
import {
  fetchCallesCatalogo,
  type CalleCatalogoItem,
} from "../../api/geolocalizacionApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import type { MRT_ColumnDef } from "material-react-table";
import type { IRelevamientoListItem } from "../../api/relevamientosListApi";

import {
  moduleContentColumnSx,
  titleStyles,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "../Actuaciones/styles/filtroStyles";

const RelevamientosContainer = (): JSX.Element => {
  const navigate = useNavigate();
  const [tab] = useState<"todos" | "pendientes">("todos");

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

  const pendingExtraColumns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => [], []);

  const pendingColumnVisibility = useMemo(() => ({
    fecha: true,
    calle: true,
    numero: true,
    calle_catalogo_id: false,
    inspector: false,
    rubro: false,
    contraproducencia: false,
  }), []);

  const handleBeforeSavePendiente = useCallback(async (_fullRow: IRelevamientoListItem) => {}, []);

  return (
    <Box sx={moduleContentColumnSx}>
        <Typography sx={titleStyles}>Relevamientos</Typography>

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
                numeroAllowFreeSolo
              />
            )}
        </>

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
                <Alert
                  severity="info"
                  sx={{ marginBottom: 2, display: "flex", alignItems: "center", gap: 2 }}
                >
                  La resolución de domicilios pendientes se centralizó en Gestionar domicilios.
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => navigate("/gestionarDomicilios")}
                    sx={{ marginLeft: 1 }}
                  >
                    Ir a Gestionar domicilios
                  </Button>
                </Alert>
                <TablaRelevamientos
                  data={pendingItems}
                  loading={pendingLoading}
                  onRefresh={handleFiltrarPendientes}
                  initialColumnVisibility={pendingColumnVisibility}
                  extraColumns={pendingExtraColumns}
                  hideRowActions
                  hideDeleteAction
                  skipValidation
                  skipUpdate
                  numeroHeader="Número/Esquina"
                  numeroEditorLabel="Número/Esquina"
                  onBeforeSave={handleBeforeSavePendiente}
                  readOnlyColumns={["fecha"]}
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

export default RelevamientosContainer;
