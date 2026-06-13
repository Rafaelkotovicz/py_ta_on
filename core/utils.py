"""Utilitarios de dominio (relogio com fuso configuravel).

Mantemos funcoes puras e leves; nenhuma mantem estado para nao reter RAM.
"""

import time


def now_tuple(offset_hours=0):
    """Retorna localtime aplicando o offset de fuso (em horas)."""
    return time.localtime(time.time() + int(offset_hours * 3600))


def now_str(offset_hours=0):
    """Data/hora formatada 'YYYY-MM-DD HH:MM:SS'."""
    t = now_tuple(offset_hours)
    return "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])


def now_hour(offset_hours=0):
    """Hora atual (0-23) ja com o fuso aplicado."""
    return now_tuple(offset_hours)[3]
