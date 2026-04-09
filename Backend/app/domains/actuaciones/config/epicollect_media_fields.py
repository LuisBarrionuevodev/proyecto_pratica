"""
Allowlist EpiCollect5: campos reales del formulario de inspecciones → categorías en DB.

Cada tupla es (field_id_exacto_en_payload, categoria_sin_prefijo).
La categoría persistida en `actuacion_media.categoria` es `epicollect.<categoria>`.

Orden:
- Define el recorrido del import y el `orden` incremental dentro de cada categoría.
"""

from __future__ import annotations

# Formulario Bromatología digitaliza — sectores y documentación (field_id confirmados).
EPICOLLECT_MEDIA_FIELDS: tuple[tuple[str, str], ...] = (
    # Salón principal
    ("17_Saln_principal_fo", "salon"),
    ("18_Saln_principal_fo", "salon"),
    # Depósito
    ("29_Deposito_Foto_1", "deposito"),
    ("30_Deposito_Foto_2", "deposito"),
    # Cámara de frío
    ("33_Cmara_de_Frio_Fot", "camara_frio"),
    ("34_Cmara_de_Frio_Fot", "camara_frio"),
    # Cocina
    ("37_Cocina_Foto_1", "cocina"),
    ("38_Cocina_Foto_2", "cocina"),
    # Baño
    ("41_Bao_Foto_1", "bano"),
    ("42_Bao_Foto_2", "bano"),
    # Certificado de desinfección
    ("50_Foto_del_Certific", "certificado_desinfeccion"),
    # Evidencia habitación / habilitación (formulario abrevia "habili")
    ("48_Foto_de_la_habili", "habilitacion"),
    # Mesada
    ("45_Mesada_Foto_1", "mesada"),
    ("46_Mesada_Foto_2", "mesada"),
    # Despensa
    ("21_Despensa_Foto_1", "despensa"),
    ("22_Despensa_Foto_2", "despensa"),
    # Heladera
    ("25_Heladera_Foto_1", "heladera"),
    ("26_Heladera_Foto_2", "heladera"),
)

MEDIA_FIELD_IDS: frozenset[str] = frozenset(fid for fid, _ in EPICOLLECT_MEDIA_FIELDS)
