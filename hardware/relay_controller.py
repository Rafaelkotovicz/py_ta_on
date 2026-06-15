"""Abstracao do rele que aciona o solenoide da fechadura.

Ativo-alto (maioria dos modulos ML com LED verde sempre aceso + 10k):
  repouso = GPIO LOW | liga = GPIO HIGH | SEM resistor 10k IN->VCC

Ativo-baixo (SRD padrao, com 10k IN->VCC):
  repouso = GPIO INPUT (10k puxa IN para 5V) | liga = GPIO LOW
"""

import time

import uasyncio as asyncio
from machine import Pin


class RelayController:

    def __init__(self, pin, active_high=True, open_time=2, use_pullup_off=False):
        self._pin_num = pin
        self._active_high = active_high
        self._use_pullup_off = use_pullup_off
        self._open_time = open_time
        self._aberto = False
        self._abriu_ms = 0
        self.fechar()
        modo = "ativo-alto" if active_high else "ativo-baixo"
        pull = " +10k IN->VCC" if use_pullup_off else ""
        print("Rele", modo + pull, "GPIO", pin)

    def _nivel_fechado(self):
        return 0 if self._active_high else 1

    def _nivel_aberto(self):
        return 1 if self._active_high else 0

    def abrir(self):
        p = Pin(self._pin_num, Pin.OUT)
        p.value(self._nivel_aberto())
        self._aberto = True
        self._abriu_ms = time.ticks_ms()
        print("Rele LIGA GPIO", self._pin_num, "=", p.value())

    def fechar(self):
        if not self._active_high and self._use_pullup_off:
            # Ativo-baixo + resistor 10k IN->VCC: IN flutuante = 5V = desliga
            Pin(self._pin_num, Pin.IN)
            val = "IN(5V)"
        else:
            p = Pin(self._pin_num, Pin.OUT)
            p.value(self._nivel_fechado())
            val = p.value()
        self._aberto = False
        self._abriu_ms = 0
        print("Rele DESLIGA GPIO", self._pin_num, "=", val)

    async def pulso_sync(self, seconds=None):
        if seconds is None:
            seconds = self._open_time
        self.fechar()
        await asyncio.sleep_ms(150)
        self.abrir()
        print("Pulso", seconds, "s")
        await asyncio.sleep_ms(int(seconds * 1000))
        self.fechar()
        await asyncio.sleep_ms(100)

    def pulso(self, seconds=None):
        asyncio.create_task(self.pulso_sync(seconds))

    async def watchdog(self):
        margem = int(self._open_time * 1000) + 2000
        while True:
            if self._aberto and self._abriu_ms:
                if time.ticks_diff(time.ticks_ms(), self._abriu_ms) > margem:
                    print("Watchdog: rele DESLIGA")
                    self.fechar()
            await asyncio.sleep_ms(500)

    async def liberar_temporariamente(self, seconds=None):
        await self.pulso_sync(seconds)
