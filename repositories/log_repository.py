"""Repositorio de logs com rotacao.

Para nao estourar a RAM/flash do ESP32, mantemos no maximo `max_logs`
registros (FIFO): ao adicionar, descartamos os mais antigos.
`stats()` calcula os contadores do dashboard em UMA passada, sem criar
objetos Log intermediarios.
"""

from repositories.base_repository import BaseRepository
from core.models import Log
from core.enums import ResultadoAcesso


class LogRepository(BaseRepository):

    def __init__(self, path, max_logs=100):
        super().__init__(path)
        self._max_logs = max_logs

    def add(self, log):
        """Adiciona um log e aplica a rotacao FIFO."""
        data = self._read_raw()
        data.append(log.to_dict())
        if len(data) > self._max_logs:
            # mantem apenas os mais recentes
            data = data[-self._max_logs:]
        self._write_raw(data)

    def recent(self, limit=50):
        """Retorna ate `limit` logs (dicts), do mais recente ao mais antigo."""
        data = self._read_raw()
        data.reverse()
        if limit and len(data) > limit:
            data = data[:limit]
        return data

    def stats(self):
        """Contadores agregados sem materializar objetos Log."""
        total = 0
        negados = 0
        liberados = 0
        for d in self._read_raw():
            total += 1
            r = d.get("resultado")
            if r == ResultadoAcesso.NEGADO:
                negados += 1
            elif r == ResultadoAcesso.LIBERADO:
                liberados += 1
        return {"total": total, "liberados": liberados, "negados": negados}
