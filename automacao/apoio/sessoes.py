"""
Sessões das plataformas da automação: navegador, API, SAP e aplicativos de desktop.

Cada sessão abre na primeira vez que um passo pede e serve aos passos seguintes do mesmo
cenário, mesmo quando eles são de plataformas diferentes. No fim, `abertas()` fecha todas,
na ordem inversa, mesmo com erro. Um cenário só de API nem abre navegador.

    with sessoes.abertas():
        ...  # os passos usam web.pagina(), api.cliente(), sap.sessao(), desktop.janela(...)

Para uma plataforma nova, crie a pasta dela (como `automacao/web`) com um `sessao.py` cuja
classe tenha `fechar()` e `evidencia(nome)`, e peça a sessão com `sessoes.obter`.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Protocol, TypeVar

log = logging.getLogger(__name__)


class Sessao(Protocol):

    def fechar(self) -> None:
        """Fecha a sessão (navegador, conexão, aplicativo)."""

    def evidencia(self, nome: str) -> Path | None:
        """Grava a evidência da tela (ou da última resposta) e devolve o arquivo."""


S = TypeVar("S", bound=Sessao)

_abertas: dict[str, Sessao] = {}


def obter(plataforma: str, abrir: Callable[[], S]) -> S:
    """A sessão da plataforma: abre na primeira vez, reaproveita nas seguintes."""
    if plataforma not in _abertas:
        log.info("Abrindo a sessão %s", plataforma)
        _abertas[plataforma] = abrir()

    return _abertas[plataforma]


def todas() -> dict[str, Sessao]:
    """As sessões abertas no cenário, na ordem em que abriram."""
    return dict(_abertas)


@contextmanager
def abertas():
    """O escopo de um cenário: fecha, no fim, todas as sessões que os passos abriram."""
    try:
        yield
    finally:
        for plataforma, sessao in reversed(list(_abertas.items())):
            try:
                sessao.fechar()
            except Exception:
                log.warning("Não deu para fechar a sessão %s", plataforma, exc_info=True)

        _abertas.clear()
