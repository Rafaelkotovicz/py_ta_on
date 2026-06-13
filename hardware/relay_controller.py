"""Abstracao do rele que aciona o solenoide da fechadura.

Suporta modulos ativo-alto e ativo-baixo. A abertura temporaria e
assincrona (`uasyncio`) para nao bloquear o event loop enquanto o
portao fica liberado.
"""

import uasyncio as asyncio
from machine import Pin


class RelayController:

    def __init__(self, pin, active_high=True, open_time=5):
        self._active_high = active_high
        self._open_time = open_time
        # inicia fechado (estado seguro)
        nivel_fechado = 0 if active_high else 1
        self._pin = Pin(pin, Pin.OUT, value=nivel_fechado)
        self._aberto = False

    def abrir(self):
        """Energiza o rele (libera a fechadura)."""
        self._pin.value(1 if self._active_high else 0)
        self._aberto = True

    def fechar(self):
        """Desenergiza o rele (tranca)."""
        self._pin.value(0 if self._active_high else 1)
        self._aberto = False

    @property
    def aberto(self):
        return self._aberto

    async def liberar_temporariamente(self, seconds=None):
        """Abre, aguarda `seconds` (ou o padrao) e fecha automaticamente."""
        if seconds is None:
            seconds = self._open_time
        self.abrir()
        try:
            await asyncio.sleep(seconds)
        finally:
            self.fechar()
