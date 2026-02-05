import { useCallback, useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, CircleMarker, useMap } from "react-leaflet";
import L from "leaflet";
import {
  Box,
  Button,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import distritosGeo from "../distritos.json";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import { fetchRubros, fetchTiposActuacion } from "../../../api/gridApi";
import {
  getMapPoints,
  getMapHeatmap,
  getMapDistricts,
  getMapPendientes,
  type DistrictMetricItem,
  type HeatmapItem,
  type PendingItem,
} from "../../../api/mapApi";


const defaultCenter: [number, number] = [-26.8241, -65.2226];

const pinIcon = new L.Icon({
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const MapCenter = ({ center }: { center: [number, number] | null }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, 14);
    }
  }, [center, map]);
  return null;
};

export default function MapViewGeo() {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [tab, setTab] = useState<"puntos" | "heatmap" | "distritos" | "pendientes">("puntos");
  const [desde, setDesde] = useState(defaultRange.desde);
  const [hasta, setHasta] = useState(defaultRange.hasta);
  const [tipo, setTipo] = useState<string>("");
  const [rubro, setRubro] = useState<string>("");
  const [distritoId, setDistritoId] = useState<string>("");
  const [scope, setScope] = useState<string>("all");

  const [tipos, setTipos] = useState<string[]>([]);
  const [rubros, setRubros] = useState<string[]>([]);

  const [points, setPoints] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapItem[]>([]);
  const [districts, setDistricts] = useState<DistrictMetricItem[]>([]);
  const [pendientes, setPendientes] = useState<PendingItem[]>([]);
  const [center, setCenter] = useState<[number, number] | null>(null);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [tiposResp, rubrosResp] = await Promise.all([
          fetchTiposActuacion(),
          fetchRubros(),
        ]);
        setTipos(tiposResp.items.map((t: any) => t.nombre));
        setRubros(rubrosResp.items.map((r: any) => r.nombre));
      } catch (err) {
        console.error(err);
      }
    };
    loadCatalogs();
  }, []);

  const loadData = useCallback(async () => {
    const params: Record<string, any> = {
      desde,
      hasta,
      tipo: tipo || undefined,
      rubro: rubro || undefined,
      distrito_id: distritoId || undefined,
      scope: scope || undefined,
    };
    if (tab === "puntos") {
      const fc = await getMapPoints(params);
      setPoints(fc.features);
    } else if (tab === "heatmap") {
      const items = await getMapHeatmap(params);
      setHeatmap(items);
    } else if (tab === "distritos") {
      const items = await getMapDistricts(params);
      setDistricts(items);
    } else {
      const items = await getMapPendientes(params);
      setPendientes(items);
    }
  }, [tab, desde, hasta, tipo, rubro, distritoId, scope]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const districtValues = useMemo(() => {
    const map: Record<string, number> = {};
    districts.forEach((d) => {
      if (d.nombre) map[d.nombre] = d.value;
    });
    return map;
  }, [districts]);

  const maxDistrictValue = useMemo(() => {
    return Math.max(1, ...Object.values(districtValues));
  }, [districtValues]);

  return (
    <Box sx={{ height: "100vh", width: "100%" }}>
      <Paper sx={{ p: 1, mb: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Tabs value={tab} onChange={(_, value) => setTab(value)}>
          <Tab label="Puntos" value="puntos" />
          <Tab label="Heatmap" value="heatmap" />
          <Tab label="Distritos" value="distritos" />
          <Tab label="Pendientes" value="pendientes" />
        </Tabs>

        <TextField size="small" type="date" label="Desde" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <TextField size="small" type="date" label="Hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} />

        <Select size="small" value={tipo} onChange={(e) => setTipo(e.target.value)} displayEmpty>
          <MenuItem value="">Tipo (todos)</MenuItem>
          {tipos.map((t) => (
            <MenuItem key={t} value={t}>{t}</MenuItem>
          ))}
        </Select>

        <Select size="small" value={rubro} onChange={(e) => setRubro(e.target.value)} displayEmpty>
          <MenuItem value="">Rubro (todos)</MenuItem>
          {rubros.map((r) => (
            <MenuItem key={r} value={r}>{r}</MenuItem>
          ))}
        </Select>

        <TextField size="small" label="Distrito ID" value={distritoId} onChange={(e) => setDistritoId(e.target.value)} />

        {tab === "pendientes" && (
          <Select size="small" value={scope} onChange={(e) => setScope(e.target.value)} displayEmpty>
            <MenuItem value="all">Scope: all</MenuItem>
            <MenuItem value="actuaciones">Actuaciones</MenuItem>
            <MenuItem value="relevamientos">Relevamientos</MenuItem>
          </Select>
        )}

        <Button variant="contained" onClick={loadData}>Actualizar</Button>
      </Paper>

      <MapContainer center={defaultCenter} zoom={12} style={{ height: "80vh", width: "100%" }}>
        <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapCenter center={center} />

        <GeoJSON
          data={distritosGeo as any}
          style={(feature: any) => {
            const nombre = feature?.properties?.nombre;
            const value = districtValues[nombre] || 0;
            const intensity = Math.min(1, value / maxDistrictValue);
            return {
              color: "blue",
              weight: 1,
              fillOpacity: tab === "distritos" ? 0.1 + intensity * 0.4 : 0.05,
            };
          }}
          onEachFeature={(f, layer) => {
            layer.bindTooltip((f as any).properties?.nombre || "Distrito");
          }}
        />

        {tab === "puntos" && points.map((f, idx) => (
          <Marker
            key={idx}
            position={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
            icon={pinIcon}
          >
            <Popup>
              <div><strong>{f.properties?.source}</strong></div>
              <div>Domicilio: {f.properties?.domicilio_id}</div>
              <div>Tipo: {f.properties?.tipo || "-"}</div>
              <div>Rubro: {f.properties?.rubro || "-"}</div>
              <div>Fecha: {f.properties?.fecha || "-"}</div>
            </Popup>
          </Marker>
        ))}

        {tab === "heatmap" && heatmap.map((p, idx) => (
          <CircleMarker
            key={idx}
            center={[p.lat, p.lng]}
            radius={6}
            pathOptions={{ color: "red", fillOpacity: 0.5 }}
          />
        ))}
      </MapContainer>

      {tab === "pendientes" && (
        <Paper sx={{ p: 1, mt: 1, maxHeight: "20vh", overflow: "auto" }}>
          <Typography variant="subtitle2">Pendientes ({pendientes.length})</Typography>
          {pendientes.map((p) => (
            <Box key={p.domicilio_id} sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}>
              <span>
                #{p.domicilio_id} {p.calle_raw} {p.numero_raw}
              </span>
              {p.lat && p.lng && (
                <Button size="small" onClick={() => setCenter([p.lat as number, p.lng as number])}>
                  Abrir
                </Button>
              )}
            </Box>
          ))}
        </Paper>
      )}
    </Box>
  );
}
