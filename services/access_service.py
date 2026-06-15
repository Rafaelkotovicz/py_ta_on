"""Service principal de controle de acesso (Service Layer).

Orquestra o fluxo completo de NFC e de senha fisica:
  UID/senha -> usuario -> estrategia -> resultado -> rele/solicitacao -> log

Depende de abstracoes (repositorios, rele, estrategias) injetadas no
construtor (Dependency Injection), facilitando teste e troca de
implementacao sem alterar esta classe.
"""

import gc

import uasyncio as asyncio

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
        self._pin_ctrl = None
        self._pin_sessao = None
        self._pin_sessao_id = 0

    def bind_pin_input(self, pin_ctrl):
        """Liga o PasswordController (arm/disarm apos leitura NFC)."""
        self._pin_ctrl = pin_ctrl

    def _registrar(self, uid, metodo, nivel, resultado):
        self._logs.add(Log(uid, now_str(self._cfg.TIMEZONE_OFFSET),
                           metodo, nivel, resultado))

    async def _registrar_depois(self, uid, metodo, nivel, resultado):
        """Grava log apos rele fechar (flash nao compete com bobina do rele)."""
        await asyncio.sleep_ms(150)
        self._registrar(uid, metodo, nivel, resultado)
        gc.collect()

    async def _liberar(self, uid, metodo, nivel):
        await self._relay.pulso_sync(self._cfg.RELAY_OPEN_TIME)
        await self._registrar_depois(uid, metodo, nivel, ResultadoAcesso.LIBERADO)

    def _limpar_sessao_pin(self):
        self._pin_sessao = None
        if self._pin_ctrl is not None:
            self._pin_ctrl.disarm()

    def _iniciar_sessao_pin(self, usuario):
        self._limpar_sessao_pin()
        self._pin_sessao_id += 1
        sid = self._pin_sessao_id
        self._pin_sessao = {
            "uid": usuario.uid,
            "senha": usuario.senha,
            "nivel": usuario.nivel_acesso,
        }
        if self._pin_ctrl is not None:
            self._pin_ctrl.arm(usuario.senha)
        asyncio.create_task(self._expirar_sessao_pin(sid))
        print("Sessao PIN aberta para", usuario.uid)
        print("Digite", len(usuario.senha), "digitos (A=0 B=1)")

    async def _expirar_sessao_pin(self, sid):
        await asyncio.sleep_ms(self._cfg.PIN_SESSION_TIMEOUT_MS)
        if self._pin_sessao is not None and self._pin_sessao_id == sid:
            uid = self._pin_sessao["uid"]
            nivel = self._pin_sessao["nivel"]
            self._limpar_sessao_pin()
            await self._registrar_depois(uid, MetodoAcesso.SENHA, nivel,
                                         ResultadoAcesso.NEGADO)
            print("Sessao PIN expirada")

    async def handle_nfc(self, uid):
        """Processa uma leitura NFC. Retorna o ResultadoAcesso."""
        usuario = self._users.find_by_uid(uid)

        if usuario is None:
            await self._registrar_depois(uid, MetodoAcesso.NFC, "DESCONHECIDO",
                                         ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO
        if not usuario.ativo:
            await self._registrar_depois(uid, MetodoAcesso.NFC,
                                         usuario.nivel_acesso,
                                         ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO

        estrategia = self._strategies.get(usuario.nivel_acesso)
        if estrategia is None:
            await self._registrar_depois(uid, MetodoAcesso.NFC,
                                         usuario.nivel_acesso,
                                         ResultadoAcesso.NEGADO)
            return ResultadoAcesso.NEGADO

        resultado = estrategia.avaliar(usuario, self._cfg.TIMEZONE_OFFSET)

        if resultado == ResultadoAcesso.AGUARDANDO_SENHA:
            self._iniciar_sessao_pin(usuario)
            asyncio.create_task(self._registrar_depois(
                uid, MetodoAcesso.NFC, usuario.nivel_acesso,
                ResultadoAcesso.AGUARDANDO_SENHA))
            return resultado

        if resultado == ResultadoAcesso.LIBERADO:
            await self._liberar(uid, MetodoAcesso.NFC, usuario.nivel_acesso)
        elif resultado == ResultadoAcesso.PENDENTE:
            self._requests.criar(uid)
            await self._registrar_depois(uid, MetodoAcesso.NFC,
                                         usuario.nivel_acesso,
                                         ResultadoAcesso.PENDENTE)
        else:
            await self._registrar_depois(uid, MetodoAcesso.NFC,
                                         usuario.nivel_acesso,
                                         ResultadoAcesso.NEGADO)

        return resultado

    async def handle_pin_sequence(self, seq):
        """Valida senha digitada apos tag PIN_REQUIRED (sem sessao = ignora)."""
        sessao = self._pin_sessao
        if sessao is None:
            return None

        uid = sessao["uid"]
        nivel = sessao["nivel"]
        self._limpar_sessao_pin()

        if seq == sessao["senha"]:
            await self._liberar(uid, MetodoAcesso.SENHA, nivel)
            print("Senha OK:", uid)
            return ResultadoAcesso.LIBERADO

        await self._registrar_depois(uid, MetodoAcesso.SENHA, nivel,
                                     ResultadoAcesso.NEGADO)
        print("Senha incorreta (recebido", seq, ")")
        return ResultadoAcesso.NEGADO
