"""
Sessões das plataformas da automação: navegador, API, aparelho, SAP e aplicativos de desktop.

Cada sessão abre na primeira vez que um passo pede e serve aos passos seguintes do mesmo
cenário, mesmo quando eles são de plataformas diferentes. No fim, `fechar_todas()` fecha
todas, na ordem inversa, mesmo com erro. Um cenário só de API nem abre navegador.

    with sessoes.abertas():
        ...  # os passos usam web.pagina(), api.cliente(), sap.sessao(), desktop.janela(...)

Fora do Proton, `abertas()` chama `fechar_todas()` no fim do cenário. Numa execução do
Proton, quem chama é a SDK, antes de gravar o status, para o que sai do fechamento (vídeo,
último print) ainda subir.

A sessão que não abre é falha de ambiente (`FalhaDeAmbiente`), com o erro original como
causa: a culpa é da máquina ou do sistema, e não da automação.

Para uma plataforma nova, crie a pasta dela (como `automacao/web`) com um `sessao.py` cuja
classe tenha `fechar()` e `evidencia(nome)`, e peça a sessão com `sessoes.obter`.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Protocol, TypeVar

from automacao.apoio.falhas import FalhaDeAmbiente

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

        try:
            _abertas[plataforma] = abrir()
        except FalhaDeAmbiente:
            raise
        except Exception as erro:
            raise FalhaDeAmbiente(f"A sessão {plataforma} não abriu: {primeira_linha(erro)}") from erro

    return _abertas[plataforma]


def todas() -> dict[str, Sessao]:
    """As sessões abertas no cenário, na ordem em que abriram."""
    return dict(_abertas)


def fechar_todas() -> None:
    """Fecha as sessões abertas, na ordem inversa. Uma que não fecha não impede as outras."""
    for plataforma, sessao in reversed(list(_abertas.items())):
        try:
            sessao.fechar()
        except Exception:
            log.warning("Não deu para fechar a sessão %s", plataforma, exc_info=True)

    _abertas.clear()


@contextmanager
def abertas():
    """O escopo de um cenário: fecha, no fim, todas as sessões que os passos abriram."""
    try:
        yield
    finally:
        fechar_todas()


def primeira_linha(erro: Exception) -> str:
    """A primeira linha da mensagem do erro (a do navegador, por exemplo, tem dezenas)."""
    texto = str(erro).strip()
    return texto.splitlines()[0] if texto else type(erro).__name__
