"""
Campos no-media de sectores / condiciones (SI-NO) para UI del modal de actuaciones.

Orden fijo de visualización; el presenter solo incluye entradas con valor presente en el snapshot.
"""

from __future__ import annotations

# (field_id en payload_non_media.data, etiqueta humana)
EPICOLLECT_SECTORES_CONDICIONES_FIELDS: tuple[tuple[str, str], ...] = (
    ("15_El_local_tiene_sa", "Salón"),
    ("27_El_local_tiene_de", "Depósito"),
    ("31_El_local_tiene_ca", "Cámara de frío"),
    ("35_El_local_tiene_co", "Cocina"),
    ("39_El_local_tiene_Ba", "Baño"),
    ("49_El_local_tiene_Ce", "Certificado de desinfección"),
    ("47_El_local_tiene_Ha", "Habilitación"),
)

EPICOLLECT_SECTOR_FIELD_IDS: frozenset[str] = frozenset(
    fid for fid, _ in EPICOLLECT_SECTORES_CONDICIONES_FIELDS
)
