"""Servicio FX genérico para tasas no-COP/USD.

Para EUR y otras monedas usa el dataset gratuito de Frankfurter
(https://www.frankfurter.app), del Banco Central Europeo. No requiere
API key. Cachea 1h en memoria y guarda el último valor exitoso para
fallback offline.

Para USD seguimos usando ``services.trm`` (dato oficial colombiano).
"""
from __future__ import annotations

import datetime as _dt
import time
from typing import Optional

import requests

# Monedas soportadas además de COP. Mantén COP como divisa contable base.
MONEDAS_FX: list[str] = ["COP", "USD", "EUR"]

_API_FRANKFURTER = "https://api.frankfurter.app/{fecha}"
_CACHE: dict[tuple[str, str], tuple[float, float]] = {}
_TTL_SEG = 60 * 60  # 1h
_ULTIMO_OK: dict[str, float] = {}


def _hoy_iso() -> str:
    return _dt.date.today().isoformat()


def obtener_tasa_a_cop(moneda: str, fecha: Optional[str] = None,
                       timeout: float = 6.0) -> float:
    """Tasa ``moneda → COP`` para la fecha dada.

    - ``COP`` → 1.0
    - ``USD`` → delega en :func:`cuentas_pro.services.trm.obtener_trm`.
    - Otras (``EUR`` por ahora) → frankfurter.app.

    Si la API falla retorna el último valor exitoso (o 0.0 si nunca se
    obtuvo). El caller debe validar > 0.
    """
    moneda = (moneda or "").upper()
    if moneda == "COP":
        return 1.0
    if moneda == "USD":
        from cuentas_pro.services.trm import obtener_trm
        return obtener_trm(fecha, timeout=timeout)

    fecha = fecha or _hoy_iso()
    clave = (moneda, fecha)
    now = time.time()
    cached = _CACHE.get(clave)
    if cached and (now - cached[1]) < _TTL_SEG:
        return cached[0]

    try:
        url = _API_FRANKFURTER.format(fecha=fecha)
        r = requests.get(url, params={"from": moneda, "to": "COP"}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        tasa = float(data.get("rates", {}).get("COP", 0.0))
        if tasa <= 0:
            return _ULTIMO_OK.get(moneda, 0.0)
        _CACHE[clave] = (tasa, now)
        _ULTIMO_OK[moneda] = tasa
        return tasa
    except Exception:
        return _ULTIMO_OK.get(moneda, 0.0)
