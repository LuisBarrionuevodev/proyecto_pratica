"""
Proxy hacia staticmap.openstreetmap.de para PDF «resumen de ruta».

Qué hace: normaliza centro y marcadores (URLs más cortas), acota cantidad de pins
y reintenta sin marcadores si OSM devuelve error (502/414/HTML habituales).

Parámetros: strings ya validados por la ruta HTTP (center, zoom, size, markers opcional;
opcional ``pin_g`` / ``pin_o`` para el fallback por teselas; ``pin_lbl`` en query se ignora).

Retorno: tupla (bytes imagen, content-type) o (None, mensaje de error corto).

Errores: no lanza por fallo de red; devuelve (None, descripción).
"""

from __future__ import annotations

import io
import logging
import math
import re
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_OSM_STATIC_BASE = "https://staticmap.openstreetmap.de/staticmap.php"
_TILE_URL_TEMPLATES = (
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
)
_MAX_MARKER_SEGMENTS = 10
_MAX_MARKER_SEGMENTS_RETRY = 5
_UA_APP = "BromatologiaInspectionApp/1.0 (map-proxy; +https://osm.org/copyright)"
_UA_BROWSER = "Mozilla/5.0 (compatible; BromatologiaMapProxy/1.0; +https://osm.org/copyright)"

_STYLE_RE = re.compile(r"^[a-z0-9._-]+$", re.I)

# Colores por grupo (G1, G2, …) alineados con el mapa operativo del front.
_GROUP_FILL = (
    (255, 215, 0),
    (80, 200, 120),
    (100, 200, 255),
    (255, 140, 200),
    (190, 150, 255),
    (255, 170, 80),
)


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


def _parse_center_floats(center: str) -> tuple[float, float] | None:
    parts = center.split(",", 1)
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def _parse_size_wh(size: str) -> tuple[int, int] | None:
    m = re.match(r"^(\d{1,4})x(\d{1,4})$", size.strip())
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    if w < 50 or h < 50 or w > 800 or h > 800:
        return None
    return w, h


def _parse_marker_float_pairs(markers: str | None, limit: int = 24) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    if not markers or not markers.strip():
        return out
    for seg in markers.split("|"):
        bits = [b.strip() for b in seg.split(",")]
        if len(bits) < 2:
            continue
        try:
            out.append((float(bits[0]), float(bits[1])))
        except ValueError:
            continue
        if len(out) >= limit:
            break
    return out


def _lat_lng_to_world_px(lat: float, lng: float, zoom: int) -> tuple[float, float]:
    """Píxeles globales Web Mercator (zoom Z), origen arriba-izquierda como OSM."""
    siny = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    scale = 256.0 * (2.0**zoom)
    x = ((lng + 180.0) / 360.0) * scale
    y = (0.5 - math.log((1.0 + siny) / (1.0 - siny)) / (4.0 * math.pi)) * scale
    return x, y


def _marker_pipe_parts(markers: str | None) -> list[str]:
    if not markers or not markers.strip():
        return []
    return [p.strip() for p in markers.split("|") if p.strip()]


def _trim_pin_strings_to_markers(
    markers_str: str | None,
    pin_g: str | None,
    pin_o: str | None,
    pin_lbl: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Recorta pin_g / pin_o / pin_lbl al mismo número de segmentos que ``markers``
    (p. ej. tras ``normalize_osm_markers`` a 10).
    """
    if not markers_str or not pin_g or not pin_o:
        return None, None, None
    m_n = len(_marker_pipe_parts(markers_str))
    if m_n == 0:
        return None, None, None
    g_parts = [p.strip() for p in pin_g.split("|") if p.strip()]
    o_parts = [p.strip() for p in pin_o.split("|") if p.strip()]
    if len(g_parts) < m_n or len(o_parts) < m_n:
        return None, None, None
    g_out = "|".join(g_parts[:m_n])
    o_out = "|".join(o_parts[:m_n])
    if not pin_lbl or not pin_lbl.strip():
        return g_out, o_out, None
    lbl_parts = [s.strip() for s in pin_lbl.split("|")]
    if len(lbl_parts) < m_n:
        return g_out, o_out, None
    return g_out, o_out, "|".join(lbl_parts[:m_n])


def _parse_pin_meta(pin_g: str | None, pin_o: str | None, marker_count: int) -> tuple[list[int], list[int]] | None:
    if marker_count <= 0 or not pin_g or not pin_o:
        return None
    try:
        gs = [int(x.strip()) for x in pin_g.split("|") if x.strip()][:marker_count]
        os_ = [int(x.strip()) for x in pin_o.split("|") if x.strip()][:marker_count]
    except ValueError:
        return None
    if len(gs) != marker_count or len(os_) != marker_count:
        return None
    for g, o in zip(gs, os_, strict=True):
        if g < 1 or g > 40 or o < 1 or o > 99:
            return None
    return (gs, os_)


def _fetch_osm_tile_png(url: str) -> bytes | None:
    try:
        r = requests.get(
            url,
            timeout=18,
            headers={
                "User-Agent": _UA_APP,
                "Accept": "image/png,*/*;q=0.5",
            },
        )
    except requests.RequestException as exc:
        logger.warning("osm-tile fetch error %s: %s", url, exc)
        return None
    if r.status_code != 200 or len(r.content) < 100:
        return None
    if not r.content.startswith(b"\x89PNG"):
        return None
    return r.content


def _try_tile_composite_png(
    center: str,
    zoom: int,
    size: str,
    markers: str | None,
    pin_g: str | None = None,
    pin_o: str | None = None,
) -> tuple[bytes, str] | None:
    """
    Si staticmap falla, arma un PNG desde teselas OSM.

    - Grilla de teselas según bbox de **todos** los puntos (no se pierden bordes al recortar).
    - Recorte final con relación de aspecto del PDF y `ImageOps.fit`.
    - Opcionalmente `pin_g` / `pin_o` (1-based grupo y orden) para colores, polilínea por grupo
      y leyenda **G1**, **G2**, … dentro del círculo del pin (PDF resumen de ruta).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        logger.warning("Pillow no disponible: omito fallback por teselas OSM")
        return None

    pos = _parse_center_floats(center)
    wh = _parse_size_wh(size)
    if not pos or not wh:
        return None
    lat_c, lng_c = pos
    out_w, out_h = wh

    pairs = _parse_marker_float_pairs(markers, limit=48)
    meta = _parse_pin_meta(pin_g, pin_o, len(pairs)) if (pin_g and pin_o and pairs) else None

    z0 = max(10, min(18, int(zoom)))
    for z in range(z0, 9, -1):
        pts_ll: list[tuple[float, float]] = list(pairs) if pairs else [(lat_c, lng_c)]
        pts_xy = [_lat_lng_to_world_px(lat, lng, z) for lat, lng in pts_ll]
        min_px = min(x for x, _ in pts_xy)
        max_px = max(x for x, _ in pts_xy)
        min_py = min(y for _, y in pts_xy)
        max_py = max(y for _, y in pts_xy)

        span = max(max_px - min_px, max_py - min_py, 120.0)
        pad = max(56.0, 0.14 * span)
        min_px -= pad
        max_px += pad
        min_py -= pad
        max_py += pad

        tmin_x = int(math.floor(min_px / 256.0))
        tmax_x = int(math.floor(max_px / 256.0))
        tmin_y = int(math.floor(min_py / 256.0))
        tmax_y = int(math.floor(max_py / 256.0))

        nx = tmax_x - tmin_x + 1
        ny = tmax_y - tmin_y + 1
        if nx < 1 or ny < 1:
            continue
        if nx * ny > 64:
            continue

        n = 2**z
        origin_x = tmin_x * 256.0
        origin_y = tmin_y * 256.0
        tw = nx * 256
        th = ny * 256

        canvas = Image.new("RGB", (tw, th), (236, 236, 236))
        loaded = 0
        for j in range(ny):
            for i in range(nx):
                xi = tmin_x + i
                yi = tmin_y + j
                xi_mod = int(xi % n)
                yi_clamped = max(0, min(int(yi), n - 1))
                tile_bytes: bytes | None = None
                for tpl in _TILE_URL_TEMPLATES:
                    u = tpl.format(z=z, x=xi_mod, y=yi_clamped)
                    tile_bytes = _fetch_osm_tile_png(u)
                    if tile_bytes:
                        break
                if not tile_bytes:
                    continue
                try:
                    im = Image.open(io.BytesIO(tile_bytes)).convert("RGB")
                    canvas.paste(im, (i * 256, j * 256))
                    loaded += 1
                except OSError:
                    continue

        if loaded < max(1, (nx * ny) // 3):
            continue

        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        rad = 10 if meta else 9

        by_gid_canvas: dict[int, list[tuple[int, int, int]]] = {}
        if pairs and meta:
            for idx, (mlat, mlng) in enumerate(pairs):
                mx, my = _lat_lng_to_world_px(mlat, mlng, z)
                rx = int(mx - origin_x)
                ry = int(my - origin_y)
                gid = meta[0][idx]
                orden = meta[1][idx]
                by_gid_canvas.setdefault(gid, []).append((rx, ry, orden))
            for _gid, lst in sorted(by_gid_canvas.items()):
                sl = sorted(lst, key=lambda t: t[2])
                pts_xy = [(t[0], t[1]) for t in sl]
                if len(pts_xy) >= 2:
                    for i in range(len(pts_xy) - 1):
                        draw.line([pts_xy[i], pts_xy[i + 1]], fill=(28, 28, 28), width=2)

        for idx, (mlat, mlng) in enumerate(pairs):
            mx, my = _lat_lng_to_world_px(mlat, mlng, z)
            rx = int(mx - origin_x)
            ry = int(my - origin_y)
            if meta:
                fill = _GROUP_FILL[(meta[0][idx] - 1) % len(_GROUP_FILL)]
                gid = meta[0][idx]
                lbl = f"G{gid}"
            else:
                fill = (220, 20, 60)
                lbl = str(idx + 1)
            draw.ellipse(
                (rx - rad, ry - rad, rx + rad, ry + rad),
                outline=(255, 255, 255),
                fill=fill,
                width=2,
            )
            bbox = draw.textbbox((0, 0), lbl, font=font)
            twt = bbox[2] - bbox[0]
            tht = bbox[3] - bbox[1]
            tx = rx - twt // 2
            ty = ry - tht // 2
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                draw.text((tx + ox, ty + oy), lbl, fill=(255, 255, 255), font=font)
            draw.text((tx, ty), lbl, fill=(30, 30, 30), font=font)

        rxs = [int(_lat_lng_to_world_px(lat, lng, z)[0] - origin_x) for lat, lng in pts_ll]
        rys = [int(_lat_lng_to_world_px(lat, lng, z)[1] - origin_y) for lat, lng in pts_ll]
        pad_px = max(28, min(out_w, out_h) // 7)
        lft = max(0, min(rxs) - pad_px)
        top = max(0, min(rys) - pad_px)
        rgt = min(tw, max(rxs) + pad_px)
        bot = min(th, max(rys) + pad_px)
        bw = rgt - lft
        bh = bot - top
        if bw < 32 or bh < 32:
            continue
        target_ar = out_w / out_h
        if bw / max(bh, 1) > target_ar:
            nh = max(32, int(bw / target_ar))
            cy = (top + bot) // 2
            top = max(0, cy - nh // 2)
            bot = min(th, top + nh)
        else:
            nw = max(32, int(bh * target_ar))
            cx = (lft + rgt) // 2
            lft = max(0, cx - nw // 2)
            rgt = min(tw, lft + nw)

        lft = max(0, min(lft, tw - 1))
        top = max(0, min(top, th - 1))
        rgt = max(lft + 1, min(rgt, tw))
        bot = max(top + 1, min(bot, th))

        cropped = canvas.crop((lft, top, rgt, bot))
        out_img = ImageOps.fit(cropped, (out_w, out_h), method=Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        if len(data) > 200:
            return (data, "image/png")

    return None


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
    pin_g: str | None = None,
    pin_o: str | None = None,
    pin_lbl: str | None = None,
) -> tuple[bytes, str] | tuple[None, str]:
    """
    Descarga la imagen desde OSM con varias variantes de query hasta obtener PNG/JPEG.

    pin_g / pin_o: opcional, segmentos ``|`` alineados con markers (grupo 1-based y orden en grupo)
    para el fallback por teselas.
    pin_lbl: ignorado en el fallback por teselas (compat. query); la leyenda **Gn** va dentro del pin.

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

    pin_gt, pin_ot, _ = _trim_pin_strings_to_markers(markers_n, pin_g, pin_o, pin_lbl)
    tile_png = _try_tile_composite_png(center_n, zoom, size, markers_n, pin_gt, pin_ot)
    if tile_png:
        logger.info("osm-static-map: mapa generado por teselas (fallback)")
        return tile_png

    return (None, last_msg)
