import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  CircleMarker,
  useMap,
} from "react-leaflet";
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
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { fetchTiposActuacion } from "../../../api/gridApi";
import { fetchRubrosCatalogoCached } from "../../../utils/rubrosCatalogCache";
import {
  getMapPointsV2,
  getMapHeatmap,
  getMapDistricts,
  getMapDetails,
  type DistrictMetricItem,
  type HeatmapItem,
} from "../../../api/mapApi";
import { getGeoPending, setGeoManual, reverseGeo, type GeoPendingItem } from "../../../api/geoApi";


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
  const [origin, setOrigin] = useState<string>("all");

  const [tipos, setTipos] = useState<string[]>([]);
  const [rubros, setRubros] = useState<{ id: number; nombre: string }[]>([]);

  const [points, setPoints] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapItem[]>([]);
  const [districts, setDistricts] = useState<DistrictMetricItem[]>([]);
  const [pendientes, setPendientes] = useState<GeoPendingItem[]>([]);
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [selected, setSelected] = useState<any>(null);
  const [selectedDetails, setSelectedDetails] = useState<any>(null);
  const [manualPin, setManualPin] = useState<{ domicilioId: number; lat: number; lng: number } | null>(null);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [tiposResp, rubrosItems] = await Promise.all([
          fetchTiposActuacion(),
          fetchRubrosCatalogoCached(),
        ]);
        setTipos(tiposResp.items.map((t: any) => t.nombre));
        setRubros(rubrosItems.map((r) => ({ id: r.id, nombre: r.nombre })));
      } catch (err) {
        console.error(err);
      }
    };
    loadCatalogs();
  }, []);

  const loadData = useCallback(async () => {
    const rubroId = rubros.find((r) => r.nombre === rubro)?.id;
    const params: Record<string, any> = {
      from: desde || undefined,
      to: hasta || undefined,
      tipo: tipo || undefined,
      rubro_id: rubroId || undefined,
      distrito_id: distritoId || undefined,
      origin: origin || undefined,
    };
    if (tab === "puntos") {
      const fc = await getMapPointsV2(params);
      setPoints(fc.features);
    } else if (tab === "heatmap") {
      const items = await getMapHeatmap(params);
      setHeatmap(items);
    } else if (tab === "distritos") {
      const items = await getMapDistricts(params);
      setDistricts(items);
    } else {
      const items = await getGeoPending();
      setPendientes(items);
    }
  }, [tab, desde, hasta, tipo, rubro, rubros, distritoId, origin]);

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
            <MenuItem key={r.id} value={r.nombre}>{r.nombre}</MenuItem>
          ))}
        </Select>

        <TextField size="small" label="Distrito ID" value={distritoId} onChange={(e) => setDistritoId(e.target.value)} />

        <Select size="small" value={origin} onChange={(e) => setOrigin(e.target.value)} displayEmpty>
          <MenuItem value="all">Origen: todos</MenuItem>
          <MenuItem value="actuaciones">Solo actuaciones</MenuItem>
          <MenuItem value="relevamientos">Solo relevamientos</MenuItem>
          <MenuItem value="both">Ambos</MenuItem>
        </Select>

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
            eventHandlers={{
              click: async () => {
                setSelected(f);
                const id = f.properties?.domicilio_id;
                if (id) {
                  const details = await getMapDetails(id, { from: desde, to: hasta });
                  setSelectedDetails(details);
                }
              },
            }}
          >
            <Popup>
              <div><strong>{f.properties?.has_act && f.properties?.has_rel ? "Ambos" : f.properties?.has_act ? "Actuación" : "Relevamiento"}</strong></div>
              <div>Domicilio: {f.properties?.domicilio_id}</div>
              <div>Actuaciones: {f.properties?.act_count}</div>
              <div>Relevamientos: {f.properties?.rel_count}</div>
              {selectedDetails && selected?.properties?.domicilio_id === f.properties?.domicilio_id && (
                <div>
                  <div>Última act.: {selectedDetails.last_act_fecha || "-"}</div>
                  <div>Último rel.: {selectedDetails.last_rel_fecha || "-"}</div>
                  <div>Rubro: {selectedDetails.rubro || "-"}</div>
                  <div>Contribuyente: {selectedDetails.contribuyente || "-"}</div>
                </div>
              )}
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

        {tab === "pendientes" && manualPin && (
          <Marker
            position={[manualPin.lat, manualPin.lng]}
            icon={pinIcon}
            draggable
            eventHandlers={{
              dragend: (e) => {
                const latlng = (e.target as any).getLatLng();
                setManualPin({ ...manualPin, lat: latlng.lat, lng: latlng.lng });
              },
            }}
          >
            <Popup>
              <div>Domicilio #{manualPin.domicilioId}</div>
              <Button
                size="small"
                variant="contained"
                onClick={async () => {
                  await setGeoManual(manualPin.domicilioId, manualPin.lat, manualPin.lng);
                  setManualPin(null);
                  await loadData();
                }}
              >
                Guardar manual
              </Button>
              <Button
                size="small"
                variant="outlined"
                sx={{ ml: 1 }}
                onClick={async () => {
                  await reverseGeo(manualPin.domicilioId, manualPin.lat, manualPin.lng);
                  setManualPin(null);
                  await loadData();
                }}
              >
                Reverse
              </Button>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {selectedDetails && (
        <Paper sx={{ p: 1, mt: 1 }}>
          <Typography variant="subtitle2">
            {selectedDetails.act_count > 0 && selectedDetails.rel_count > 0
              ? "Ambos"
              : selectedDetails.act_count > 0
              ? "Actuación"
              : "Relevamiento"}
          </Typography>
          <div>
            Domicilio:{" "}
            {formatDomicilioLineaVisible({
              calle_normalizada: selectedDetails.calle,
              numero: selectedDetails.numero,
              numero_tipo: selectedDetails.numero_tipo,
              esquina_normalizada: selectedDetails.esquina,
              esquina_raw: selectedDetails.esquina_raw,
            }) || "-"}
          </div>
          <div>Contribuyente: {selectedDetails.contribuyente || "-"}</div>
          <div>Rubro: {selectedDetails.rubro || "-"}</div>
          <div>Inspeccionado {selectedDetails.act_count} veces</div>
          <div>Relevamientos {selectedDetails.rel_count}</div>
          <div>ODT: {(selectedDetails.odt_list || []).join(", ") || "-"}</div>
          <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle2">Actuaciones</Typography>
            {(selectedDetails.actuaciones || []).map((a: any) => (
              <div key={a.id}>
                {a.fecha} - {a.tipo} {a.contraproducencia || ""}
              </div>
            ))}
          </Box>
          <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle2">Relevamientos</Typography>
            {(selectedDetails.relevamientos || []).map((r: any) => (
              <div key={r.id}>
                {r.fecha} - {r.inspector || "-"} {r.rubro || ""}
              </div>
            ))}
          </Box>
        </Paper>
      )}

      {tab === "pendientes" && (
        <Paper sx={{ p: 1, mt: 1, maxHeight: "20vh", overflow: "auto" }}>
          <Typography variant="subtitle2">Pendientes ({pendientes.length})</Typography>
          {pendientes.map((p) => (
            <Box key={p.domicilio_id} sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}>
              <span>
                #{p.domicilio_id}{" "}
                {formatDomicilioLineaVisible(p) || "-"}
              </span>
              <Button
                size="small"
                onClick={() => {
                  setCenter(center || defaultCenter);
                  setManualPin({
                    domicilioId: p.domicilio_id,
                    lat: center ? center[0] : defaultCenter[0],
                    lng: center ? center[1] : defaultCenter[1],
                  });
                }}
              >
                Ubicar
              </Button>
            </Box>
          ))}
        </Paper>
      )}
    </Box>
  );
}
