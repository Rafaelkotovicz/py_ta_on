"""Service de solicitacoes (autorizacao de visitantes).

Encapsula as regras de aprovar/negar, mantendo o Router (web) livre de
logica de negocio.
"""

import uasyncio as asyncio

from core.enums import (
    StatusSolicitacao,
    ResultadoAcesso,
    MetodoAcesso,
    NivelAcesso,
)
from core.models import Log
from core.utils import now_str


class RequestService:

    def __init__(self, request_repo, log_repo, relay, config):
        self._requests = request_repo
        self._logs = log_repo
        self._relay = relay
        self._cfg = config

    def criar(self, uid):
        """Registra uma nova solicitacao PENDENTE para um UID."""
        return self._requests.add(uid, now_str(self._cfg.TIMEZONE_OFFSET))

    def listar_pendentes(self):
        return self._requests.pending()

    async def aprovar(self, sid):
        """Aprova: aciona o rele e registra log LIBERADO. Retorna True/False."""
        uid = self._requests.update_status(sid, StatusSolicitacao.APROVADA)
        if uid is None:
            return False
        await self._relay.pulso_sync(self._cfg.RELAY_OPEN_TIME)
        await asyncio.sleep_ms(150)
        self._logs.add(Log(uid, now_str(self._cfg.TIMEZONE_OFFSET),
                           MetodoAcesso.NFC, NivelAcesso.VISITOR,
                           ResultadoAcesso.LIBERADO))
        return True

    def negar(self, sid):
        """Nega a solicitacao e registra log NEGADO. Retorna True/False."""
        uid = self._requests.update_status(sid, StatusSolicitacao.NEGADA)
        if uid is None:
            return False
        self._logs.add(Log(uid, now_str(self._cfg.TIMEZONE_OFFSET),
                           MetodoAcesso.NFC, NivelAcesso.VISITOR,
                           ResultadoAcesso.NEGADO))
        return True
