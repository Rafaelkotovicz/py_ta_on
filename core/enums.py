"""Enumeracoes do dominio.

O MicroPython nao traz o modulo `enum` da stdlib, entao usamos classes
com constantes string. Ocupam menos memoria e serializam direto em JSON.
"""


class NivelAcesso:
    ADMIN = "ADMIN"
    USER = "USER"
    TIME_RESTRICTED = "TIME_RESTRICTED"
    VISITOR = "VISITOR"
    PIN_REQUIRED = "PIN_REQUIRED"


class MetodoAcesso:
    NFC = "NFC"
    SENHA = "SENHA"


class ResultadoAcesso:
    LIBERADO = "LIBERADO"
    NEGADO = "NEGADO"
    PENDENTE = "PENDENTE"
    AGUARDANDO_SENHA = "AGUARDANDO_SENHA"


class StatusSolicitacao:
    PENDENTE = "PENDENTE"
    APROVADA = "APROVADA"
    NEGADA = "NEGADA"
