"""Repositorio de solicitacoes de acesso (fluxo de autorizacao de VISITOR)."""

from repositories.base_repository import BaseRepository
from core.models import Solicitacao
from core.enums import StatusSolicitacao


class RequestRepository(BaseRepository):

    def _next_id(self, data):
        """Gera o proximo id incremental com base no maior existente."""
        maior = 0
        for d in data:
            try:
                v = int(d.get("id", 0))
            except (TypeError, ValueError):
                v = 0
            if v > maior:
                maior = v
        return maior + 1

    def add(self, uid, data_hora):
        """Cria uma solicitacao PENDENTE e devolve o objeto criado."""
        data = self._read_raw()
        nova = Solicitacao(self._next_id(data), uid, data_hora,
                           StatusSolicitacao.PENDENTE)
        data.append(nova.to_dict())
        self._write_raw(data)
        return nova

    def pending(self):
        """Lista (dicts) apenas das solicitacoes pendentes."""
        return [d for d in self._read_raw()
                if d.get("status") == StatusSolicitacao.PENDENTE]

    def count_pending(self):
        """Conta pendentes sem materializar objetos."""
        n = 0
        for d in self._read_raw():
            if d.get("status") == StatusSolicitacao.PENDENTE:
                n += 1
        return n

    def find_by_id(self, sid):
        for d in self._read_raw():
            if str(d.get("id")) == str(sid):
                return Solicitacao.from_dict(d)
        return None

    def update_status(self, sid, status):
        """Atualiza o status de uma solicitacao. Retorna o uid afetado ou None."""
        data = self._read_raw()
        alvo = None
        for d in data:
            if str(d.get("id")) == str(sid):
                d["status"] = status
                alvo = d.get("uid")
                break
        if alvo is not None:
            self._write_raw(data)
        return alvo
