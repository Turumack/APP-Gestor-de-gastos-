"""State base con el período (mes/año) compartido por todas las páginas."""
from datetime import date
import reflex as rx
from minty.finance import MESES_NOMBRE


def _month_bounds(mes: int, anio: int) -> tuple[date, date]:
    inicio = date(anio, mes, 1)
    if mes == 12:
        fin = date(anio + 1, 1, 1)
    else:
        fin = date(anio, mes + 1, 1)
    return inicio, fin


class PeriodoState(rx.State):
    """Mes y año activos; compartido globalmente."""
    mes: int = date.today().month
    anio: int = date.today().year

    @rx.var
    def mes_nombre(self) -> str:
        return MESES_NOMBRE[self.mes]

    @rx.var
    def periodo_label(self) -> str:
        return f"{MESES_NOMBRE[self.mes]} {self.anio}"

    @rx.var
    def fecha_inicio(self) -> str:
        inicio, _ = _month_bounds(self.mes, self.anio)
        return inicio.isoformat()

    @rx.var
    def fecha_fin(self) -> str:
        _, fin = _month_bounds(self.mes, self.anio)
        return fin.isoformat()

    @rx.event
    async def mes_anterior(self):
        if self.mes == 1:
            self.mes = 12
            self.anio -= 1
        else:
            self.mes -= 1
        await self._broadcast()

    @rx.event
    async def mes_siguiente(self):
        if self.mes == 12:
            self.mes = 1
            self.anio += 1
        else:
            self.mes += 1
        await self._broadcast()

    @rx.event
    async def set_hoy(self):
        hoy = date.today()
        self.mes = hoy.month
        self.anio = hoy.year
        await self._broadcast()

    async def _broadcast(self):
        """Dispara recarga en todos los states que dependen del período."""
        from minty.state.ingresos import IngresosState
        from minty.state.gastos import GastosState
        from minty.state.resumen import ResumenState
        from minty.state.cajas import CajasState
        from minty.state.presupuestos import PresupuestosState

        ing = await self.get_state(IngresosState)
        await ing.load()
        g = await self.get_state(GastosState)
        await g.load()
        res = await self.get_state(ResumenState)
        await res.load()
        cajas = await self.get_state(CajasState)
        await cajas.load()
        pres = await self.get_state(PresupuestosState)
        await pres.load()
