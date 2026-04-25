"""Utilidades de exportación a CSV (en memoria, listo para descarga)."""
from __future__ import annotations

import csv
import io
from typing import Iterable, Sequence


def filas_a_csv(headers: Sequence[str], filas: Iterable[Sequence]) -> bytes:
    """Genera un CSV UTF-8 con BOM (compatible con Excel) en memoria.

    - ``headers``: encabezados de columnas.
    - ``filas``: iterable de tuplas/listas con valores.

    Devuelve los bytes del archivo listo para enviarse vía ``rx.download``.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for fila in filas:
        writer.writerow(fila)
    # BOM UTF-8 para que Excel detecte la codificación correctamente.
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
