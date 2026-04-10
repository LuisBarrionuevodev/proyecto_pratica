"""
Etiquetas y orden de visualización para `actuacion_media.categoria` bajo prefijo `epicollect.`.

Incluye categorías actuales del formulario y alias legados por imports antiguos.
"""

from __future__ import annotations

EPICOLLECT_MEDIA_PREFIX = "epicollect."

# Orden de grupos en UI (solo sufijo, sin prefijo).
EPICOLLECT_EVIDENCIAS_DISPLAY_ORDER: tuple[str, ...] = (
    "salon",
    "salon_principal",
    "deposito",
    "camara_frio",
    "cocina",
    "bano",
    "certificado_desinfeccion",
    "habilitacion",
    "mesada",
    "despensa",
    "heladera",
    "fachada",
    "acta",
    "notificacion",
    "informe",
    "orden_trabajo",
    "direccion",
)

EPICOLLECT_EVIDENCIAS_LABEL_BY_SUFFIX: dict[str, str] = {
    "salon": "Salón",
    "salon_principal": "Salón principal",
    "deposito": "Depósito",
    "camara_frio": "Cámara de frío",
    "cocina": "Cocina",
    "bano": "Baño",
    "certificado_desinfeccion": "Certificado de desinfección",
    "habilitacion": "Habilitación",
    "mesada": "Mesada",
    "despensa": "Despensa",
    "heladera": "Heladera",
    "fachada": "Fachada",
    "acta": "Acta",
    "notificacion": "Notificación",
    "informe": "Informe",
    "orden_trabajo": "Orden de trabajo",
    "direccion": "Dirección",
}


def suffix_from_epicollect_categoria(categoria: str) -> str | None:
    """Devuelve el sufijo tras ``epicollect.`` o None si no aplica."""
    if not categoria or not categoria.startswith(EPICOLLECT_MEDIA_PREFIX):
        return None
    return categoria[len(EPICOLLECT_MEDIA_PREFIX) :]


def label_for_epicollect_suffix(suffix: str) -> str:
    """Etiqueta humana; si no está mapeada, título aproximado desde el sufijo."""
    if suffix in EPICOLLECT_EVIDENCIAS_LABEL_BY_SUFFIX:
        return EPICOLLECT_EVIDENCIAS_LABEL_BY_SUFFIX[suffix]
    return suffix.replace("_", " ").strip().title() or "Otra evidencia"
