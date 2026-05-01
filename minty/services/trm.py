"""Servicio TRM (Tasa Representativa del Mercado USD→COP).

Fuente: Portal de Datos Abiertos de Colombia (dataset oficial de la
Superintendencia Financiera). No requiere API key.

Dataset: https://www.datos.gov.co/resource/32sa-8pi3.json
"""
from __future__ import annotations

import datetime as _dt
import time
from typing import Optional

import requests

_API = "https://www.datos.gov.co/resource/32sa-8pi3.json"
_CACHE: dict[str, tuple[float, float]] = {}  # iso_date -> (trm, timestamp)
_TTL_SEG = 60 * 60  # 1 hora
_ULTIMA_TRM_OK: float = 0.0  # último valor obtenido con éxito (fallback offline)


def _hoy_iso() -> str:
    return _dt.date.today().isoformat()


def obtener_trm(fecha: Optional[str] = None, timeout: float = 6.0) -> float:
    """Devuelve la TRM vigente para la fecha dada (hoy por defecto).

    - Si falla la petición, retorna 0.0 (el caller decide fallback).
    - Cachea 1h en memoria por fecha.
    """
    global _ULTIMA_TRM_OK
    fecha = fecha or _hoy_iso()
    now = time.time()
    cached = _CACHE.get(fecha)
    if cached and (now - cached[1]) < _TTL_SEG:
        return cached[0]

    try:
        # La API devuelve registros con vigenciadesde / vigenciahasta.
        # Filtramos por rango.
        params = {
            "$where": f"vigenciadesde <= '{fecha}T00:00:00.000' "
                      f"AND vigenciahasta >= '{fecha}T00:00:00.000'",
            "$limit": 1,
        }
        r = requests.get(_API, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if not data:
            # fallback: último registro disponible
            r2 = requests.get(_API,
                              params={"$order": "vigenciadesde DESC", "$limit": 1},
                              timeout=timeout)
            r2.raise_for_status()
            data = r2.json()
        if not data:
            return _ULTIMA_TRM_OK
        trm = float(data[0]["valor"])
        _CACHE[fecha] = (trm, now)
        _ULTIMA_TRM_OK = trm
        return trm
    except Exception:
        # Fallback: último valor conocido (puede ser 0.0 si nunca se obtuvo).
        return _ULTIMA_TRM_OK
