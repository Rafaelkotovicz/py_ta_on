"""Modelos de dominio (entidades).

Cada entidade conhece apenas a sua propria serializacao (to_dict/from_dict),
mantendo a persistencia desacoplada das regras de negocio.
Optamos por UMA classe `Usuario` (em vez de uma subclasse por nivel): o
comportamento por nivel vive nas `AccessStrategy`, evitando objetos extras
na RAM e respeitando o principio aberto/fechado.
"""

from core.enums import (
    NivelAcesso,
    MetodoAcesso,
    ResultadoAcesso,
    StatusSolicitacao,
)


class Usuario:
    """Usuario identificado por UID da tag NFC."""

    __slots__ = ("uid", "nivel_acesso", "ativo", "nome")

    def __init__(self, uid, nivel_acesso=NivelAcesso.USER, ativo=True, nome=""):
        self.uid = uid
        self.nivel_acesso = nivel_acesso
        self.ativo = ativo
        self.nome = nome

    def to_dict(self):
        return {
            "uid": self.uid,
            "nivel_acesso": self.nivel_acesso,
            "ativo": self.ativo,
            "nome": self.nome,
        }

    @staticmethod
    def from_dict(d):
        return Usuario(
            d.get("uid"),
            d.get("nivel_acesso", NivelAcesso.USER),
            d.get("ativo", True),
            d.get("nome", ""),
        )


class Log:
    """Registro imutavel de um evento de acesso."""

    __slots__ = ("uid", "data_hora", "metodo", "nivel_acesso", "resultado")

    def __init__(self, uid, data_hora, metodo, nivel_acesso, resultado):
        self.uid = uid
        self.data_hora = data_hora
        self.metodo = metodo
        self.nivel_acesso = nivel_acesso
        self.resultado = resultado

    def to_dict(self):
        return {
            "uid": self.uid,
            "data_hora": self.data_hora,
            "metodo": self.metodo,
            "nivel_acesso": self.nivel_acesso,
            "resultado": self.resultado,
        }

    @staticmethod
    def from_dict(d):
        return Log(
            d.get("uid"),
            d.get("data_hora"),
            d.get("metodo"),
            d.get("nivel_acesso"),
            d.get("resultado"),
        )


class Solicitacao:
    """Pedido de acesso gerado por um VISITOR (fluxo de autorizacao)."""

    __slots__ = ("id", "uid", "data_hora", "status")

    def __init__(self, id, uid, data_hora, status=StatusSolicitacao.PENDENTE):
        self.id = id
        self.uid = uid
        self.data_hora = data_hora
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "data_hora": self.data_hora,
            "status": self.status,
        }

    @staticmethod
    def from_dict(d):
        return Solicitacao(
            d.get("id"),
            d.get("uid"),
            d.get("data_hora"),
            d.get("status", StatusSolicitacao.PENDENTE),
        )
