/**
 * Vista legacy de mapa (locales/polígonos mock). No está enrutada en App.tsx; la ruta `/mapa` usa `MapPage`.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON } from "react-leaflet";
import L from "leaflet";
import MarkerClusterGroup from "react-leaflet-markercluster";
import { getLocales, createLocal, updateLocalPosition, deleteLocal } from "../../../api/localesApi";
import type { ILocal } from "../../../types/Local"
import distritosGeo from "../distritos.json";
import AddLocalForm from "./AddLocalForm";
import DistrictFilter from "./DistrictFilter";
import SearchBar from "./SearchBar";
import { Box, Button, Paper } from "@mui/material";
import { FeatureGroup } from "react-leaflet";
import { EditControl } from "react-leaflet-draw";
import PolygonForm from "./PolygonForm";
import { createPoligono, deletePoligono, updatePoligono } from "../../../api/poligonosApi";
import { usePoligonos } from "../../../hooks/usePoligonos";
import wellknown from "wellknown"
import { filterLocales } from "../../../utils/filtersMap";
import MapClickHandler from "./MapClickHandler";
import { ConfirmDialog } from "../../../ui";


const defaultCenter: [number, number] = [-26.8241, -65.2226];

const pinIcon = new L.Icon({
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});


export default function MapaView() {
  const [locales, setLocales] = useState<ILocal[]>([]);
  const [openAdd, setOpenAdd] = useState(false);
  const [newPos, setNewPos] = useState<{ lat: number; lng: number }>({ lat: 0, lng: 0 });
  const [openPolyForm, setOpenPolyForm] = useState(false);
  const [pendingPolygon, setPendingPolygon] = useState<any>(null);
  const { poligonos, setPoligonos } = usePoligonos();
  const [pendingWKT, setPendingWKT] = useState<string>("");
  const [mode, setMode] = useState<"normal" | "addLocal" | "draw">("normal");
  const [filterDistrito, setFilterDistrito] = useState("");
  const [search, setSearch] = useState("");
  const [deleteLocalId, setDeleteLocalId] = useState<number | null>(null);
  const [deleteLocalInProgress, setDeleteLocalInProgress] = useState(false);
  const distritosList = useMemo(() => {
    const names = new Set<string>();
    (distritosGeo as any).features?.forEach((f: any) => {
      if (f.properties?.nombre) names.add(f.properties.nombre);
    });
    return Array.from(names);
  }, []);

  const featureGroupRef = useRef<L.FeatureGroup<any>>(null);

  const load = async () => {
    try {
      const data = await getLocales();
      setLocales(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { load(); }, []);

  // Convertir a WKT (opcional pero MUY útil para tu backend)
  function toWKT(layer: any): string {
    const latlngs = layer.getLatLngs()[0];
    const coords = latlngs.map((p: any) => `${p.lng} ${p.lat}`).join(", ");
    return `POLYGON((${coords}))`;
  }


  // Filtrado por distrito y búsqueda
  const filtered = filterLocales(locales, filterDistrito, search);

  const handleCreate = async (formData: FormData) => {
    await createLocal(formData);
    await load();
  };

  const handleDragEnd = async (id: number, e: L.DragEndEvent) => {
    const { lat, lng } = e.target.getLatLng();
    try {
      await updateLocalPosition(id, lat, lng);
      // actualizar local en UI
      setLocales((prev) => prev.map((p) => (p.id === id ? { ...p, lat, lng } : p)));
    } catch (err) {
      console.error(err);
    }
  };

  const performDeleteLocal = async () => {
    if (deleteLocalId == null) return;
    setDeleteLocalInProgress(true);
    try {
      await deleteLocal(deleteLocalId);
      setLocales((prev) => prev.filter((loc) => loc.id !== deleteLocalId));
    } catch (error) {
      console.error("Error eliminando local:", error);
    } finally {
      setDeleteLocalInProgress(false);
      setDeleteLocalId(null);
    }
  };


  const handleCreatePolygon = (e: any) => {
    const layer = e.layer;
    const geojson = layer.toGeoJSON();
    const wkt = toWKT(layer);

    setPendingPolygon(layer);
    setPendingWKT(wkt);

    // Abrir modal
    setOpenPolyForm(true);

    console.log("CREADO");
    console.log("GeoJSON:", geojson);
    console.log("WKT:", wkt);

    // TODO: aquí mandas el WKT al backend
    // await api.savePolygon({ wkt });
  };

  const handleEditPolygon = async (e: any) => {
    e.layers.eachLayer(async (layer: any) => {
      const id = layer?.options?.id;
      if (!id) return console.warn("⚠ No hay ID en el layer editado");

      const newWKT = toWKT(layer);

      try {
        const updated = await updatePoligono(id, { wkt: newWKT });

        // actualizar UI
        setPoligonos((prev) =>
          prev.map((p) => (p.id === id ? { ...p, wkt: newWKT } : p))
        );

        console.log("POLÍGONO EDITADO", updated);
      } catch (err) {
        console.error("Error al editar polígono:", err);
      }
    });
  };


  const handleDeletePolygon = async (e: any) => {
    e.layers.eachLayer(async (layer: any) => {
      const id = layer?.options?.id;
      if (!id) return console.warn("⚠ No hay ID en el layer eliminado");

      try {
        await deletePoligono(id);

        // borrar de UI
        setPoligonos((prev) => prev.filter((p) => p.id !== id));

        console.log("POLÍGONO ELIMINADO");
      } catch (err) {
        console.error("Error al eliminar polígono:", err);
      }
    });
  };



  return (
    <Box sx={{ height: "100vh", width: "95vw", display: "flex", justifyContent: "end", gap: 1, alignContent: "center", flexWrap: "wrap", mt: { xs: 3, sm: 3, md: 0 }, mb: { xs: 3, sm: 3, md: 0 }, }}>

      <MapContainer center={defaultCenter} zoom={12} style={{ height: "80vh", width: "65vw", border: "2px solid black" }}>
        <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        <Paper sx={{ position: "absolute", zIndex: 1000, top: "10px", right: {xs:"0px",sm:"50px"}, p: 1, display: "flex", gap: 1, width: { xs: "200px", md: "380px" } }}>
          <DistrictFilter distritos={distritosList} value={filterDistrito} onChange={setFilterDistrito} />
          <SearchBar value={search} onChange={setSearch} onClear={() => { }} />
        </Paper>

        {/* Codigo de ejemplo visual distritos */}

         <GeoJSON
       data={distritosGeo as any}
      style={() => ({ color: "blue", weight: 1.33, fillOpacity: 0.07 })}
       onEachFeature={(f, layer) => {
        layer.bindTooltip((f as any).properties?.nombre || "Distrito");
           }}
         />  

        {poligonos.map((p) => {
          const geo = wellknown.parse(p.wkt);
          if (!geo) return null;

          return (
            <GeoJSON
              key={p.id}
              data={geo}
              style={{ color: "red", weight: 2 }}
              onEachFeature={(_feature, layer) => {
                (layer as any).options.id = p.id;
                layer.bindPopup(`
          <strong>${p.nombre}</strong><br/>
          ${p.descripcion}
        `);
              }}
            />
          );
        })}

        {mode === "draw" && (
          <FeatureGroup ref={featureGroupRef}>
            <EditControl
              position="topright"
              draw={{
                rectangle: false,
                polyline: false,
                circle: false,
                marker: false,
                circlemarker: false,
                polygon: true,
              }}
              edit={{ remove: true, }}
              onCreated={handleCreatePolygon}
              onEdited={handleEditPolygon}
              onDeleted={handleDeletePolygon}
            />
          </FeatureGroup>
        )}

        <MarkerClusterGroup>
          {filtered.map((loc) => (
            <Marker
              key={loc.id}
              position={[loc.lat, loc.lng]}
              icon={pinIcon}
              draggable={true}
              eventHandlers={{
                dragend: (e) => handleDragEnd(loc.id, e as any),
              }}
            >
              <Popup>
                <strong>{loc.nombre}</strong>
                <div>{loc.descripcion}</div>
                <div><small>{loc.distrito}</small></div>

                {loc.archivos?.map((a, i) => (
                  <div key={i}>
                    <a href={a.url} target="_blank" rel="noreferrer">
                      {a.nombre || "archivo"}
                    </a>
                  </div>
                ))}

                <button
                  style={{ marginTop: "8px", color: "red", cursor: "pointer" }}
                  onClick={() => setDeleteLocalId(loc.id)}
                >
                  🗑 Eliminar
                </button>
              </Popup>

            </Marker>
          ))}
        </MarkerClusterGroup>

        <MapClickHandler
          mode={mode}
          setNewPos={setNewPos}
          setOpenAdd={setOpenAdd}
        />


      </MapContainer>

      <Paper
        sx={{
          display: "flex",
          flexDirection: "column",
          mr: { xs: "60px", sm: 0 },
          alignSelf: "center",
          justifyContent: "center",
          p: 1,
          gap: 1,
          backgroundColor: "#0166FF",
          border:"1px solid black"
        }}
      >
        <Button sx={{ fontSize: { xs: "10px", md: "12px" }, width: "auto",color:"white", border:"1px solid black" }} onClick={() => setMode("addLocal")}>
           Agregar Local
        </Button>

        <Button sx={{ fontSize: { xs: "10px", md: "12px" } ,color:"white",border:"1px solid black" }} onClick={() => setMode("draw")}>
           Dibujar
        </Button>

        <Button sx={{ fontSize: { xs: "10px", md: "12px" } ,color:"white", border:"1px solid black"}} onClick={() => setMode("normal")}>
           Salir Modo
        </Button>
      </Paper>

      <AddLocalForm
        open={openAdd}
        onClose={() => setOpenAdd(false)}
        lat={newPos.lat}
        lng={newPos.lng}
        distritos={distritosList}
        onSave={async (fd) => {
          await handleCreate(fd);
        }}
      />

      <PolygonForm
        open={openPolyForm}
        onClose={() => {
          setOpenPolyForm(false);



          setPendingPolygon(null);
        }}
        onSave={async (info) => {
          await createPoligono({
            nombre: info.nombre,
            descripcion: info.descripcion,
            wkt: pendingWKT,
          });
          console.log("🚀 POLÍGONO GUARDADO");
          console.log("Nombre:", info.nombre);
          console.log("Descripción:", info.descripcion);
          console.log("WKT:", pendingWKT);

          featureGroupRef.current?.addLayer(pendingPolygon);

          // Mostrar la info al usuario (tooltip)
          pendingPolygon.bindPopup(`
      <strong>${info.nombre}</strong><br/>
      ${info.descripcion}
    `);

          setOpenPolyForm(false);
          setPendingPolygon(null);
        }}
      />

      <ConfirmDialog
        open={deleteLocalId !== null}
        onClose={() => setDeleteLocalId(null)}
        onConfirm={performDeleteLocal}
        title="Eliminar local"
        destructive
        loading={deleteLocalInProgress}
        confirmLabel="Eliminar"
      >
        Esta acción quitará el local del mapa. No se podrá deshacer desde esta vista.
      </ConfirmDialog>
    </Box>
  );
}
