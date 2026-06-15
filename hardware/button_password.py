"""Senha fisica por dois botoes.

Aceita varios GPIOs (A=0 e B=1) para tolerar fiação em 32/33 ou 25/26.
"""

import time
from machine import Pin


class PasswordController:

    def __init__(self, pins_a, pins_b, active_low=True,
                 debounce_ms=80, timeout_ms=10000):
        self._active_low = active_low
        self._debounce = debounce_ms
        self._timeout = timeout_ms
        self._senha = ""
        self._on_sequence = None

        self._pins_a = [self._mkpin(g) for g in pins_a]
        self._pins_b = [self._mkpin(g) for g in pins_b]
        self._nums_a = pins_a
        self._nums_b = pins_b
        self._last_a = [self._pressed(p) for p in self._pins_a]
        self._last_b = [self._pressed(p) for p in self._pins_b]
        self._edge_ms_a = [0] * len(self._pins_a)
        self._edge_ms_b = [0] * len(self._pins_b)

        self._seq = ""
        self._last_press = 0
        print("Botoes A GPIO", pins_a, "-> 0")
        print("Botoes B GPIO", pins_b, "-> 1")
        self._print_estado()

    def _mkpin(self, gpio):
        pull = Pin.PULL_UP if self._active_low else None
        return Pin(gpio, Pin.IN, pull)

    def _pressed(self, pin):
        v = pin.value()
        if self._active_low:
            return v == 0
        return v == 1

    def _print_estado(self):
        sa = [str(p.value()) for p in self._pins_a]
        sb = [str(p.value()) for p in self._pins_b]
        print("Estado A", sa, "B", sb, "(0=pressionado se active_low)")

    def arm(self, senha):
        self._senha = senha
        self._seq = ""
        print("Teclado ARMADO:", len(senha), "digitos. Senha: A-B-A-B para 0101")
        self._print_estado()

    def disarm(self):
        self._senha = ""
        self._seq = ""

    @property
    def armado(self):
        return bool(self._senha)

    def _append(self, digito):
        if not self._senha:
            return
        agora = time.ticks_ms()
        if self._seq and time.ticks_diff(agora, self._last_press) > self._timeout:
            self._seq = ""
        self._last_press = agora
        self._seq += digito
        print("Senha:", self._seq)
        if len(self._seq) >= len(self._senha):
            seq = self._seq
            self._seq = ""
            if self._on_sequence:
                self._on_sequence(seq)

    def _check_group(self, pins, nums, last, edge_ms, digito):
        agora = time.ticks_ms()
        for i, pin in enumerate(pins):
            cur = self._pressed(pin)
            if cur and not last[i]:
                if time.ticks_diff(agora, edge_ms[i]) > self._debounce:
                    edge_ms[i] = agora
                    if self._senha:
                        print("Botao", digito, "GPIO", nums[i])
                        self._append(digito)
                    else:
                        print("GPIO", nums[i], "- passe tag PIN_REQUIRED antes")
            last[i] = cur

    def poll(self):
        self._check_group(self._pins_a, self._nums_a, self._last_a,
                          self._edge_ms_a, "0")
        self._check_group(self._pins_b, self._nums_b, self._last_b,
                          self._edge_ms_b, "1")
