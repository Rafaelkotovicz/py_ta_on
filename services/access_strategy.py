"""Estrategias de acesso por nivel (Strategy Pattern).

Demonstra heranca, polimorfismo e abstracao: cada nivel implementa
`avaliar()` retornando um ResultadoAcesso. Adicionar um novo nivel nao
exige tocar no AccessService (principio aberto/fechado).

Decisao de memoria: as estrategias sao SEM estado, entao instanciamos
uma unica vez (singletons via STRATEGIES) e reutilizamos para todos os
acessos, em vez de criar objetos a cada leitura.
"""

from core.enums import NivelAcesso, ResultadoAcesso
from core.utils import now_hour


class AccessStrategy:
    """Contrato abstrato. Subclasses definem a politica de cada nivel."""

    def avaliar(self, usuario, offset_hours=0):
        raise NotImplementedError


class AdminStrategy(AccessStrategy):
    def avaliar(self, usuario, offset_hours=0):
        return ResultadoAcesso.LIBERADO


class UserStrategy(AccessStrategy):
    def avaliar(self, usuario, offset_hours=0):
        return ResultadoAcesso.LIBERADO


class TimeRestrictedStrategy(AccessStrategy):
    """Libera somente dentro da janela [inicio, fim)."""

    def __init__(self, inicio=12, fim=18):
        self._inicio = inicio
        self._fim = fim

    def avaliar(self, usuario, offset_hours=0):
        h = now_hour(offset_hours)
        if self._inicio <= h < self._fim:
            return ResultadoAcesso.LIBERADO
        return ResultadoAcesso.NEGADO


class VisitorStrategy(AccessStrategy):
    def avaliar(self, usuario, offset_hours=0):
        return ResultadoAcesso.PENDENTE


class PinRequiredStrategy(AccessStrategy):
    """Exige tag NFC + senha nos botoes (sessao aberta pelo AccessService)."""

    def avaliar(self, usuario, offset_hours=0):
        if not usuario.senha:
            return ResultadoAcesso.NEGADO
        return ResultadoAcesso.AGUARDANDO_SENHA


def build_strategies(tr_inicio=12, tr_fim=18):
    """Fabrica o mapa nivel -> estrategia (instancias unicas reutilizaveis)."""
    return {
        NivelAcesso.ADMIN: AdminStrategy(),
        NivelAcesso.USER: UserStrategy(),
        NivelAcesso.TIME_RESTRICTED: TimeRestrictedStrategy(tr_inicio, tr_fim),
        NivelAcesso.VISITOR: VisitorStrategy(),
        NivelAcesso.PIN_REQUIRED: PinRequiredStrategy(),
    }
