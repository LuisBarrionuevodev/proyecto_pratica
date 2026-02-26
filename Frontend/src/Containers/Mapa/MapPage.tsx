import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  CircleMarker,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";

import distritosGeo from "./distritos.json";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { fetchRubros, fetchTiposActuacion } from "../../api/gridApi";
import {
  getMapPointsV2,
  getMapHeatmap,
  getMapDistricts,
  type DistrictMetricItem,
  type HeatmapItem,
  type PendingItem,
} from "../../api/mapApi";
import { usePendientes } from "./hooks/usePendientes";
import { useCallesCatalogoOptions } from "./hooks/useCallesCatalogoOptions";
import { useUpdateDomicilio } from "./hooks/useUpdateDomicilio";
import { useSaveManualPoint } from "./hooks/useSaveManualPoint";
import { filtroItemStyles } from "../Actuaciones/styles/filtroStyles";
import { TablePendientesStyle } from "../../styles/MapStyles";

const defaultCenter: [number, number] = [-26.8241, -65.2226];

const createPin = (color: string) =>
  L.divIcon({
    className: "",
    html: `
      <div style="
        width:20px;
        height:20px;
        background:${color};
        border-radius:50% 50% 50% 0;
        transform: rotate(-45deg);
        border:2px solid white;
        box-shadow:0 4px 10px rgba(0,0,0,0.3);
      "></div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 18],
  });

  const getMarkerIcon = (f: any) => {
  const hasAct = f.properties?.has_act;
  const hasRel = f.properties?.has_rel;

  if (hasAct && hasRel) return createPin("#9C27B0"); // violeta
  if (hasAct) return createPin("#E53935"); // rojo
  if (hasRel) return createPin("#1976D2"); // azul

  return createPin("#9E9E9E"); // gris por si no tiene nada
};

const manualPinIcon = createPin("#FF9800");

const MapCenter = ({ center }: { center: [number, number] | null }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, 14);
    }
  }, [center, map]);
  return null;
};

const MapClickHandler = ({
  enabled,
  onClick,
}: {
  enabled: boolean;
  onClick: (lat: number, lng: number) => void;
}) => {
  useMapEvents({
    click: (e) => {
      if (!enabled) return;
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

const buildDireccion = (item: PendingItem) => {
  const numero = item.numero || item.numero_raw || "";
  if (item.numero_tipo === "ESQUINA" && item.esquina_normalizada) {
    return `${item.calle_normalizada || item.calle_raw || ""} y ${item.esquina_normalizada}`;
  }
  return `${item.calle_normalizada || item.calle_raw || ""} ${numero}`.trim();
};

const MapPage = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [activeTab, setActiveTab] = useState<"puntos" | "heatmap" | "distritos" | "pendientes">("puntos");
  const [pendientesView, setPendientesView] = useState<"norm" | "map" | "manual">("norm");

  const [desde, setDesde] = useState(defaultRange.desde);
  const [hasta, setHasta] = useState(defaultRange.hasta);
  const [scope, setScope] = useState<string>("all");
  const [origin, setOrigin] = useState<string>("all");
  const [tipo, setTipo] = useState<string>("");
  const [rubro, setRubro] = useState<string>("");
  const [distritoId, setDistritoId] = useState<string>("");

  const [tipos, setTipos] = useState<string[]>([]);
  const [rubros, setRubros] = useState<{ id: number; nombre: string }[]>([]);
  const [points, setPoints] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapItem[]>([]);
  const [districts, setDistricts] = useState<DistrictMetricItem[]>([]);
  const [center, setCenter] = useState<[number, number] | null>(null);

  const [selectedPending, setSelectedPending] = useState<PendingItem | null>(null);
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null);
  const [searchText, setSearchText] = useState("");
  const [searching, setSearching] = useState(false);

  const { items: pendientesNorm, loading: pendingNormLoading, refetch: refetchNorm } = usePendientes("norm", {
    desde,
    hasta,
    scope,
  });
  const { items: pendientesMap, loading: pendingMapLoading, refetch: refetchMap } = usePendientes("map", {
    desde,
    hasta,
    scope,
  });
  const { items: callesCatalogo } = useCallesCatalogoOptions();
  const { updateDomicilio } = useUpdateDomicilio();
  const { saveManualPoint } = useSaveManualPoint();

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [tiposResp, rubrosResp] = await Promise.all([fetchTiposActuacion(), fetchRubros()]);
        setTipos(tiposResp.items.map((t: any) => t.nombre));
        setRubros(rubrosResp.items.map((r: any) => ({ id: r.id, nombre: r.nombre })));
      } catch (err) {
        console.error(err);
      }
    };
    loadCatalogs();
  }, []);

  const loadMapData = useCallback(async () => {
    const rubroId = rubros.find((r) => r.nombre === rubro)?.id;
    const params: Record<string, any> = {
      from: desde || undefined,
      to: hasta || undefined,
      tipo: tipo || undefined,
      rubro_id: rubroId || undefined,
      distrito_id: distritoId || undefined,
      origin: origin || undefined,
    };
    if (activeTab === "puntos") {
      const fc = await getMapPointsV2(params);
      setPoints(fc.features);
    } else if (activeTab === "heatmap") {
      const items = await getMapHeatmap(params);
      setHeatmap(items);
    } else if (activeTab === "distritos") {
      const items = await getMapDistricts(params);
      setDistricts(items);
    }
  }, [activeTab, desde, hasta, tipo, rubro, rubros, distritoId, origin]);

  useEffect(() => {
    if (activeTab !== "pendientes") {
      loadMapData();
    }
  }, [loadMapData]);

  const districtValues = useMemo(() => {
    const map: Record<string, number> = {};
    districts.forEach((d) => {
      if (d.nombre) map[d.nombre] = d.value;
    });
    return map;
  }, [districts]);

  const maxDistrictValue = useMemo(() => Math.max(1, ...Object.values(districtValues)), [districtValues]);

  const onSaveManual = async () => {
    if (!selectedPending || !pin) return;
    await saveManualPoint({
      domicilio_id: selectedPending.domicilio_id,
      lat: pin.lat,
      lng: pin.lng,
      do_reverse: true,
    });
    setSelectedPending(null);
    setPin(null);
    await refetchMap();
    setPendientesView("map");
  };

  const onSearch = async () => {
    if (!searchText.trim()) return;
    setSearching(true);
    try {
      const q = encodeURIComponent(searchText.trim());
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${q}&limit=1`;
      const resp = await fetch(url, { headers: { "Accept-Language": "es" } });
      const data = await resp.json();
      if (Array.isArray(data) && data[0]) {
        const lat = parseFloat(data[0].lat);
        const lng = parseFloat(data[0].lon);
        if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
          setCenter([lat, lng]);
          setPin({ lat, lng });
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  const columnsNorm = useMemo<MRT_ColumnDef<PendingItem>[]>(() => [
    { accessorKey: "calle_raw", header: "Calle raw", size: 160 },
    { accessorKey: "numero_tipo", header: "Tipo", size: 80 },
    { accessorKey: "numero_raw", header: "Número raw", size: 110 },
    { accessorKey: "esquina_normalizada", header: "Esquina", size: 140 },
    {
      accessorKey: "calle_catalogo_id",
      header: "Calle catálogo",
      size: 180,
      Edit: ({ row }) => {
        const currentValue =
          (row as any)?._valuesCache?.calle_catalogo_id ?? row.original.calle_catalogo_id;
        return (
          <Select
            size="small"
            value={currentValue ?? ""}
            onChange={(e) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                calle_catalogo_id: e.target.value ? Number(e.target.value) : null,
              };
            }}
            fullWidth
          >
            <MenuItem value="">-</MenuItem>
            {callesCatalogo.map((c) => (
              <MenuItem key={c.id} value={c.id}>{c.nombre}</MenuItem>
            ))}
          </Select>
        );
      },
    },
    {
      accessorKey: "esquina_catalogo_id",
      header: "Esquina catálogo",
      size: 180,
      Edit: ({ row }) => {
        if (row.original.numero_tipo !== "ESQUINA") return null;
        const currentValue =
          (row as any)?._valuesCache?.esquina_catalogo_id ?? row.original.esquina_catalogo_id;
        return (
          <Select
            size="small"
            value={currentValue ?? ""}
            onChange={(e) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                esquina_catalogo_id: e.target.value ? Number(e.target.value) : null,
              };
            }}
            fullWidth
          >
            <MenuItem value="">-</MenuItem>
            {callesCatalogo.map((c) => (
              <MenuItem key={c.id} value={c.id}>{c.nombre}</MenuItem>
            ))}
          </Select>
        );
      },
    },
    {
      accessorKey: "numero",
      header: "Número",
      size: 120,
      muiEditTextFieldProps: ({ row }) => ({
        disabled: row.original.numero_tipo === "ESQUINA",
      }),
    },
  ], [callesCatalogo]);

  const tableNorm = useMaterialReactTable({
    ...TablePendientesStyle,
    columns: columnsNorm,
    data: pendientesNorm,
    enableEditing: true,
    editDisplayMode: "row",
    onEditingRowSave: async ({ row, values, exitEditingMode }) => {
      const payload = {
        domicilio_id: row.original.domicilio_id,
        calle_catalogo_id: values.calle_catalogo_id ?? row.original.calle_catalogo_id,
        esquina_catalogo_id: values.esquina_catalogo_id ?? row.original.esquina_catalogo_id,
        numero: values.numero ?? row.original.numero,
        numero_tipo: row.original.numero_tipo,
      };
      await updateDomicilio(payload);
      exitEditingMode();
      await refetchNorm();
      await refetchMap();
    },
    state: { isLoading: pendingNormLoading },
  });

  const columnsMap = useMemo<MRT_ColumnDef<PendingItem>[]>(() => [
    { accessorKey: "domicilio_id", header: "ID", size: 80 },
    {
      accessorKey: "direccion",
      header: "Dirección",
      size: 220,
      Cell: ({ row }) => buildDireccion(row.original),
    },
    { accessorKey: "score", header: "Score", size: 80 },
    { accessorKey: "quality", header: "Quality", size: 100 },
    { accessorKey: "geo_status", header: "Status", size: 110 },
  ], []);

  const tableMap = useMaterialReactTable({
    ...TablePendientesStyle,
    columns: columnsMap,
    data: pendientesMap,
    enableEditing: false,
    state: { isLoading: pendingMapLoading },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <Button
        size="small"
        onClick={() => {
          setSelectedPending(row.original);
          setActiveTab("pendientes");
          setPendientesView("manual");
          if (row.original.lat && row.original.lng) {
            setCenter([row.original.lat, row.original.lng]);
            setPin({ lat: row.original.lat, lng: row.original.lng });
          } else {
            setCenter(defaultCenter);
            setPin(null);
          }
        }}
      >
        Geolocalizar
      </Button>
    ),
  });

  return (
    <Box sx={{ display: "flex", alignItems: "center", width: "93vw", mr: "10px", ml: "10px", mt: "15px" }}>
      <Box flex={1}>
        <Paper sx={{ p: 1, mb: 1, display: "flex", bgcolor: "#2B2E34", gap: 2, flexWrap: "wrap", alignItems: "center" }}>
          <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)}>
            <Tab sx={{ color: "white" }} label="Puntos" value="puntos" />
            <Tab sx={{ color: "white" }} label="Heatmap" value="heatmap" />
            <Tab sx={{ color: "white" }} label="Distritos" value="distritos" />
            <Tab sx={{ color: "white" }} label="Pendientes" value="pendientes" />
          </Tabs>
          {activeTab === "pendientes" && pendientesView === "manual" && (
            <Typography variant="subtitle2" sx={{ alignSelf: "center" }}>
              Geolocalización manual
            </Typography>
          )}

          {activeTab !== "pendientes" && (
            <>
              <TextField sx={filtroItemStyles} size="small" type="date" label="Desde" value={desde} onChange={(e) => setDesde(e.target.value)} />
              <TextField sx={filtroItemStyles} size="small" type="date" label="Hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} />

              <Select sx={{ color: "white" }} size="small" value={tipo} onChange={(e) => setTipo(e.target.value)} displayEmpty>
                <MenuItem sx={{ color: "black" }} value="">Tipo (todos)</MenuItem>
                {tipos.map((t) => (
                  <MenuItem sx={{ color: "black" }} key={t} value={t}>{t}</MenuItem>
                ))}
              </Select>

              <Select sx={{ color: "white" }} size="small" value={rubro} onChange={(e) => setRubro(e.target.value)} displayEmpty>
                <MenuItem sx={{ color: "black" }} value="">Rubro (todos)</MenuItem>
                {rubros.map((r) => (
                  <MenuItem sx={{ color: "black" }} key={r.id} value={r.nombre}>{r.nombre}</MenuItem>
                ))}
              </Select>

              <TextField sx={{
                "& .MuiInputLabel-root": {
                  color: "white",
                  fontFamily: '"Tactic Sans", sans-serif',
                  "&.Mui-focused": { color: "#0166FF" },
                },
              }} size="small" label="Distrito ID" value={distritoId} onChange={(e) => setDistritoId(e.target.value)} />

              <Select sx={{ color: "white" }} size="small" value={origin} onChange={(e) => setOrigin(e.target.value)} displayEmpty>
                <MenuItem sx={{ color: "black" }} value="all">Origen: todos</MenuItem>
                <MenuItem sx={{ color: "black" }} value="actuaciones">Solo actuaciones</MenuItem>
                <MenuItem sx={{ color: "black" }} value="relevamientos">Solo relevamientos</MenuItem>
                <MenuItem sx={{ color: "black" }} value="both">Ambos</MenuItem>
              </Select>
            </>
          )}

          {activeTab !== "pendientes" && (
            <Button variant="contained" onClick={loadMapData}>Actualizar</Button>
          )}
        </Paper>

        {activeTab === "pendientes" && (
          <Box display={"flex"} flexDirection={"column"} justifyContent={"center"}>
            <Box sx={{ p: 1, bgcolor: "#2B2E34", display: "flex", gap: 1, flexWrap: "wrap", mb: 2, alignItems: "center", flexDirection: { xs: "column", sm: "row" } }}>
              <TextField sx={filtroItemStyles} size="small" type="date" label="Desde" value={desde} onChange={(e) => setDesde(e.target.value)} />
              <TextField sx={filtroItemStyles} size="small" type="date" label="Hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} />
              <Select sx={{ color: "white" }} size="small" value={scope} onChange={(e) => setScope(e.target.value)} displayEmpty>
                <MenuItem sx={{ color: "black" }} value="all">Todos</MenuItem>
                <MenuItem sx={{ color: "black" }} value="actuaciones">Actuaciones</MenuItem>
                <MenuItem sx={{ color: "black" }} value="relevamientos">Relevamientos</MenuItem>
              </Select>
              <Button variant="contained" onClick={() => { refetchNorm(); refetchMap(); }}>
                Filtrar
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  const range = getCurrentMonthRange();
                  setDesde(range.desde);
                  setHasta(range.hasta);
                  setScope("all");
                  refetchNorm();
                  refetchMap();
                }}
              >
                Limpiar
              </Button>
              <Box display={"flex"} top={0} >
                <Tabs value={pendientesView} onChange={(_, v) => setPendientesView(v)}>
                  <Tab sx={{ color: "white" }} label="Normalización manual" value="norm" />
                  <Tab sx={{ color: "white" }} label="Pendientes en mapa" value="map" />
                  {pendientesView === "manual" && <Tab label="Manual" value="manual" />}
                </Tabs>
              </Box>

            </Box>



            {pendientesView !== "manual" && (
              <Box >
                {pendientesView === "norm" ? (
                  <Box sx={{
                    width: "100%",
                    overflowX: "auto",
                  }}>
                    <Box sx={{ maxWidth: { xs: "500px", sm: "900px", md: "1000px", lg: "100%", xl: "100%" } }}>
                      <MaterialReactTable table={tableNorm} />
                    </Box>
                  </Box>
                ) : (
                  <Box sx={{ maxWidth: { xs: "500px", sm: "900px", md: "1000px", lg: "100%", xl: "100%" } }}>
                    <MaterialReactTable table={tableMap} />
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}

        {activeTab !== "pendientes" && (
          <MapContainer center={defaultCenter} zoom={12} style={{ height: "75vh", width: "100%" }}>
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapCenter center={center} />
            <MapClickHandler
              enabled={false}
              onClick={(lat, lng) => setPin({ lat, lng })}
            />

            <GeoJSON
              data={distritosGeo as any}
              style={(feature: any) => {
                const nombre = feature?.properties?.nombre;
                const value = districtValues[nombre] || 0;
                const intensity = Math.min(1, value / maxDistrictValue);
                return {
                  color: "blue",
                  weight: 1,
                  fillOpacity: activeTab === "distritos" ? 0.1 + intensity * 0.4 : 0.05,
                };
              }}
              onEachFeature={(f, layer) => {
                layer.bindTooltip((f as any).properties?.nombre || "Distrito");
              }}
            />

            {activeTab === "puntos" && points.map((f, idx) => (
              <Marker
                key={idx}
                position={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                icon={getMarkerIcon(f)}
              >
                <Popup className="custom-popup">
                  <Box
                    sx={{
                      backgroundColor: "#2B2E34",
                      borderRadius: "16px",
                      padding: "12px 14px",
                      minWidth: 220,  // parecido al default
                      color: "#EAEAEA",
                      boxShadow: "0 6px 18px rgba(0,0,0,0.25)",
                    }}
                  >
                    <Stack spacing={1}>
                      <Typography
                        variant="subtitle2"
                        sx={{ fontWeight: 600, opacity: 0.9 }}
                      >
                        {f.properties?.has_act && f.properties?.has_rel
                          ? "Ambos"
                          : f.properties?.has_act
                            ? "Actuación"
                            : "Relevamiento"}
                      </Typography>

                      <Typography variant="body2" sx={{ fontSize: 13 }}>
                        Domicilio: {f.properties?.domicilio_id}
                      </Typography>

                      <Stack direction="row" spacing={1}>
                        <Chip
                          label={`Act ${f.properties?.act_count}`}
                          size="small"
                          sx={{
                            backgroundColor: "#E53935",
                            color: "white",
                            fontSize: 11,
                            height: 22,
                          }}
                        />
                        <Chip
                          label={`Rel ${f.properties?.rel_count}`}
                          size="small"
                          sx={{
                            backgroundColor: "#1976D2",
                            color: "white",
                            fontSize: 11,
                            height: 22,
                          }}
                        />
                      </Stack>
                    </Stack>
                  </Box>
                </Popup>
              </Marker>
            ))}

            {activeTab === "heatmap" && heatmap.map((p, idx) => (
              <CircleMarker
                key={idx}
                center={[p.lat, p.lng]}
                radius={6}
                pathOptions={{ color: "red", fillOpacity: 0.5 }}
              />
            ))}
          </MapContainer>
        )}

        {activeTab === "pendientes" && pendientesView === "manual" && (
          <Box sx={{ p: 1 }}>
            <Paper sx={{ p: 1, mb: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
              <TextField
                size="small"
                label="Buscar dirección"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Button variant="outlined" disabled={searching} onClick={onSearch}>
                Buscar
              </Button>
              <Button variant="contained" disabled={!pin} onClick={onSaveManual}>
                Guardar punto
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setPendientesView("map");
                  setSelectedPending(null);
                  setPin(null);
                }}
              >
                Volver
              </Button>
            </Paper>

            {selectedPending && (
              <Paper sx={{ p: 1, mb: 1 }}>
                <Typography variant="subtitle2">
                  Seleccionado: #{selectedPending.domicilio_id} — {buildDireccion(selectedPending)}
                </Typography>
              </Paper>
            )}

            <MapContainer center={defaultCenter} zoom={13} style={{ height: "75vh", width: "100%" }}>
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapCenter center={center} />
              <MapClickHandler
                enabled={!!selectedPending}
                onClick={(lat, lng) => setPin({ lat, lng })}
              />
              {pin && (
                <Marker
                  position={[pin.lat, pin.lng]}
                  icon={manualPinIcon}
                  draggable
                  eventHandlers={{
                    dragend: (e) => {
                      const latlng = (e.target as any).getLatLng();
                      setPin({ lat: latlng.lat, lng: latlng.lng });
                    },
                  }}
                />
              )}
            </MapContainer>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default MapPage;
