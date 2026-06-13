"""Senha fisica por dois botoes.

Botao A -> '0'   |   Botao B -> '1'
Responsabilidade unica: capturar pressionamentos com debounce, montar a
sequencia, validar contra a senha configurada e disparar um callback de
sucesso/falha. Nao conhece rele, logs nem rede (Single Responsibility).

O metodo `poll()` e nao bloqueante e deve ser chamado por uma task
`uasyncio`; assim evitamos IRQs (que poderiam reentrar no allocator do
MicroPython) e mantemos um unico event loop.
"""

import time
from machine import Pin


class PasswordController:

    def __init__(self, pin_a, pin_b, senha="0101", active_low=True,
                 debounce_ms=200, timeout_ms=8000,
                 on_success=None, on_fail=None):
        pull = Pin.PULL_UP if active_low else None
        self._btn_a = Pin(pin_a, Pin.IN, pull)
        self._btn_b = Pin(pin_b, Pin.IN, pull)
        self._active_low = active_low
        self._senha = senha
        self._debounce = debounce_ms
        self._timeout = timeout_ms
        self._on_success = on_success
        self._on_fail = on_fail

        self._seq = ""
        self._last_press = 0
        self._last_state_a = self._raw(self._btn_a)
        self._last_state_b = self._raw(self._btn_b)

    def _raw(self, pin):
        """True quando o botao esta pressionado, respeitando a polaridade."""
        v = pin.value()
        return (v == 0) if self._active_low else (v == 1)

    def _append(self, digito):
        agora = time.ticks_ms()
        # reseta a sequencia se o usuario demorou demais entre digitos
        if self._seq and time.ticks_diff(agora, self._last_press) > self._timeout:
            self._seq = ""
        self._last_press = agora
        self._seq += digito
        if len(self._seq) >= len(self._senha):
            self._validar()

    def _validar(self):
        ok = self._seq == self._senha
        self._seq = ""
        if ok:
            if self._on_success:
                self._on_success()
        else:
            if self._on_fail:
                self._on_fail()

    def poll(self):
        """Le os botoes uma vez (deteccao de borda + debounce)."""
        agora = time.ticks_ms()
        a = self._raw(self._btn_a)
        b = self._raw(self._btn_b)

        if a and not self._last_state_a:
            if time.ticks_diff(agora, self._last_press) > self._debounce:
                self._append("0")
        if b and not self._last_state_b:
            if time.ticks_diff(agora, self._last_press) > self._debounce:
                self._append("1")

        self._last_state_a = a
        self._last_state_b = b
