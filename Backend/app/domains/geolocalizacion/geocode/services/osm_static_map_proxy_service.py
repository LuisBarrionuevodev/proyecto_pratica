"""
Proxy hacia staticmap.openstreetmap.de para PDF «resumen de ruta».

Qué hace: normaliza centro y marcadores (URLs más cortas), acota cantidad de pins
y reintenta sin marcadores si OSM devuelve error (502/414/HTML habituales).

Parámetros: strings ya validados por la ruta HTTP (center, zoom, size, markers opcional).

Retorno: tupla (bytes imagen, content-type) o (None, mensaje de error corto).

Errores: no lanza por fallo de red; devuelve (None, descripción).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_OSM_STATIC_BASE = "https://staticmap.openstreetmap.de/staticmap.php"
_MAX_MARKER_SEGMENTS = 10
_MAX_MARKER_SEGMENTS_RETRY = 5
_UA_APP = "BromatologiaInspectionApp/1.0 (map-proxy; +https://osm.org/copyright)"
_UA_BROWSER = "Mozilla/5.0 (compatible; BromatologiaMapProxy/1.0; +https://osm.org/copyright)"

_STYLE_RE = re.compile(r"^[a-z0-9._-]+$", re.I)


def _round_pair(lat_s: str, lng_s: str) -> tuple[str, str] | None:
    try:
        la = round(float(lat_s.strip()), 5)
        ln = round(float(lng_s.strip()), 5)
        return (str(la), str(ln))
    except ValueError:
        return None


def normalize_osm_center(center: str) -> str:
    """
    Redondea lat,lng del parámetro center para acortar la URL y evitar floats enormes de JS.
    """
    parts = center.split(",", 1)
    if len(parts) != 2:
        return center
    rp = _round_pair(parts[0], parts[1])
    if not rp:
        return center
    return f"{rp[0]},{rp[1]}"


def normalize_osm_markers(markers: str | None, max_segments: int = _MAX_MARKER_SEGMENTS) -> str | None:
    """
    Acota cantidad de pins y redondea coordenadas de cada segmento ``lat,lng,estilo``.
    """
    if not markers or not markers.strip():
        return None
    segments = [s.strip() for s in markers.split("|") if s.strip()]
    out: list[str] = []
    for seg in segments[:max_segments]:
        bits = [b.strip() for b in seg.split(",")]
        if len(bits) < 2:
            continue
        rp = _round_pair(bits[0], bits[1])
        if not rp:
            continue
        style = bits[2] if len(bits) > 2 else "red-pushpin"
        if not _STYLE_RE.fullmatch(style):
            style = "red-pushpin"
        out.append(f"{rp[0]},{rp[1]},{style}")
    return "|".join(out) if out else None


def _is_image_response(r: requests.Response) -> bool:
    if r.status_code != 200:
        return False
    ct = (r.headers.get("Content-Type") or "").lower()
    if "image/png" in ct or "image/jpeg" in ct or "image/jpg" in ct:
        return True
    data = r.content[:8]
    return data.startswith(b"\x89PNG\r\n") or data.startswith(b"\xff\xd8\xff")


def _build_query(center: str, zoom: int, size: str, markers: str | None) -> dict[str, str]:
    q: dict[str, str] = {
        "center": center,
        "zoom": str(zoom),
        "size": size,
        "maptype": "mapnik",
    }
    if markers:
        q["markers"] = markers
    return q


def fetch_osm_static_map_bytes(
    center: str,
    zoom: int,
    size: str,
    markers: str | None,
) -> tuple[bytes, str] | tuple[None, str]:
    """
    Descarga la imagen desde OSM con varias variantes de query hasta obtener PNG/JPEG.

    Errores esperados: ninguna excepción hacia arriba; (None, str) si todas las variantes fallan.
    """
    center_n = normalize_osm_center(center)
    markers_n = normalize_osm_markers(markers)

    marker_variants: list[str | None] = []
    if markers_n:
        marker_variants.append(markers_n)
        parts = markers_n.split("|")
        if len(parts) > _MAX_MARKER_SEGMENTS_RETRY:
            short = "|".join(parts[:_MAX_MARKER_SEGMENTS_RETRY])
            if short != markers_n:
                marker_variants.append(short)
    marker_variants.append(None)

    seen: set[str] = set()
    last_msg = "sin respuesta de imagen"

    for mk in marker_variants:
        q = _build_query(center_n, zoom, size, mk)
        url = f"{_OSM_STATIC_BASE}?{urlencode(q)}"
        if url in seen:
            continue
        seen.add(url)
        for ua in (_UA_APP, _UA_BROWSER):
            try:
                r = requests.get(
                    url,
                    timeout=25,
                    headers={
                        "User-Agent": ua,
                        "Accept": "image/png,image/webp,image/*;q=0.8,*/*;q=0.5",
                    },
                )
            except requests.RequestException as exc:
                last_msg = f"red: {exc}"
                logger.warning("osm-static-map request error url=%s: %s", url[:160], exc)
                continue
            if _is_image_response(r):
                ct = r.headers.get("Content-Type") or "image/png"
                return (r.content, ct)
            last_msg = f"HTTP {r.status_code}, ct={r.headers.get('Content-Type')}, len={len(r.content)}"
            logger.warning("osm-static-map no imagen: %s", last_msg)

    return (None, last_msg)
