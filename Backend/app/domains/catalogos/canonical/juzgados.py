"""15 juzgados aprobados (I–XV). Sin IIX (error duplicado de VIII)."""

from __future__ import annotations

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV")

JUZGADOS_CANONICOS: tuple[tuple[str, str], ...] = tuple(
    (f"JF{n}", f"Juzgado de Faltas N° {_ROMAN[n - 1]}")
    for n in range(1, 16)
)
