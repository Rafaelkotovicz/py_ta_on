"""Repositorio de logs com rotacao.

A lista em `logs.json` guarda no maximo `max_logs` registros (FIFO) para
nao estourar RAM/flash. Os contadores do dashboard ficam em `stats_path`
e continuam subindo mesmo quando entradas antigas saem da lista.
"""

import json
import gc

from repositories.base_repository import BaseRepository
from core.models import Log
from core.enums import ResultadoAcesso


class LogRepository(BaseRepository):

    def __init__(self, path, max_logs=100, stats_path=None):
        super().__init__(path)
        self._max_logs = max_logs
        self._stats_path = stats_path or "data/log_stats.json"
        self._ensure_counters()

    def _empty_counters(self):
        return {"total": 0, "liberados": 0, "negados": 0, "pendentes": 0}

    def _read_counters(self):
        try:
            f = open(self._stats_path, "r")
        except OSError:
            return self._empty_counters()
        try:
            data = json.load(f)
        except (ValueError, OSError):
            data = self._empty_counters()
        finally:
            f.close()
        if not isinstance(data, dict):
            return self._empty_counters()
        out = self._empty_counters()
        for k in out:
            out[k] = int(data.get(k, 0))
        return out

    def _write_counters(self, counters):
        f = open(self._stats_path, "w")
        try:
            json.dump(counters, f)
        finally:
            f.close()
        gc.collect()

    def _ensure_counters(self):
        """Cria contadores na primeira execucao (bootstrap a partir dos logs)."""
        try:
            open(self._stats_path, "r").close()
            return
        except OSError:
            pass
        counters = self._empty_counters()
        for d in self._read_raw():
            counters["total"] += 1
            r = d.get("resultado")
            if r == ResultadoAcesso.NEGADO:
                counters["negados"] += 1
            elif r == ResultadoAcesso.LIBERADO:
                counters["liberados"] += 1
            elif r == ResultadoAcesso.PENDENTE:
                counters["pendentes"] += 1
        self._write_counters(counters)

    def _bump_counter(self, resultado):
        counters = self._read_counters()
        counters["total"] += 1
        if resultado == ResultadoAcesso.NEGADO:
            counters["negados"] += 1
        elif resultado == ResultadoAcesso.LIBERADO:
            counters["liberados"] += 1
        elif resultado == ResultadoAcesso.PENDENTE:
            counters["pendentes"] += 1
        self._write_counters(counters)

    def add(self, log):
        """Adiciona um log e aplica a rotacao FIFO."""
        data = self._read_raw()
        data.append(log.to_dict())
        if len(data) > self._max_logs:
            data = data[-self._max_logs:]
        self._write_raw(data)
        self._bump_counter(log.resultado)

    def recent(self, limit=50):
        """Retorna ate `limit` logs (dicts), do mais recente ao mais antigo."""
        data = self._read_raw()
        data.reverse()
        if limit and len(data) > limit:
            data = data[:limit]
        return data

    def stats(self):
        """Contadores acumulados (nao limitados pela rotacao da lista)."""
        return self._read_counters()
