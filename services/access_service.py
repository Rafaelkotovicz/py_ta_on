"""Service principal de controle de acesso (Service Layer).

Orquestra o fluxo completo de NFC e de senha fisica:
  UID/senha -> usuario -> estrategia -> resultado -> rele/solicitacao -> log

Depende de abstracoes (repositorios, rele, estrategias) injetadas no
construtor (Dependency Injection), facilitando teste e troca de
implementacao sem alterar esta classe.
"""

from core.enums import (
    NivelAcesso,
    MetodoAcesso,
    ResultadoAcesso,
)
from core.models import Log
from core.utils import now_str


class AccessService:

    def __init__(self, user_repo, log_repo, request_service, relay,
                 strategies, config):
        self._users = user_repo
        self._logs = log_repo
        self._requests = request_service
        self._relay = relay
        self._strategies = strategies
        self._cfg = config

    def _registrar(self, uid, metodo, nivel, resultado):
        self._logs.add(Log(uid, now_str(self._cfg.TIMEZONE_OFFSET),
                           metodo, nivel, resultado))

    async def handle_nfc(self, uid):
        """Processa uma leitura NFC. Retorna o ResultadoAcesso."""
        usuario = self._users.find_by_uid(uid)

        # tag desconhecida ou usuario desativado -> NEGADO
        if usuario is None:
            self._registrar(uid, MetodoAcesso.NFC, "DESCONHECIDO",
                            ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO
        if not usuario.ativo:
            self._registrar(uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                            ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO

        estrategia = self._strategies.get(usuario.nivel_acesso)
        if estrategia is None:
            self._registrar(uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                            ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO

        resultado = estrategia.avaliar(usuario, self._cfg.TIMEZONE_OFFSET)

        if resultado == ResultadoAcesso.LIBERADO:
            self._registrar(uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                            ResultadoAcesso.LIBERADO)
            await self._relay.liberar_temporariamente()
        elif resultado == ResultadoAcesso.PENDENTE:
            self._requests.criar(uid)
            self._registrar(uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                            ResultadoAcesso.PENDENTE)
        else:
            self._registrar(uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                            ResultadoAcesso.NEGADO)

        return resultado

    async def handle_password(self, sucesso):
        """Processa o resultado da senha fisica (True=correta)."""
        if sucesso:
            self._registrar("-", MetodoAcesso.SENHA, NivelAcesso.USER,
                            ResultadoAcesso.LIBERADO)
            await self._relay.liberar_temporariamente()
            return ResultadoAcesso.LIBERADO
        self._registrar("-", MetodoAcesso.SENHA, "-",
                        ResultadoAcesso.NEGADO)
        return ResultadoAcesso.NEGADO
