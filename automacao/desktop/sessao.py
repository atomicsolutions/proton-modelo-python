"""
A sessão de desktop: os aplicativos do Windows abertos pelos passos, fechados no fim do
cenário. Usa o pywinauto com o UI Automation do Windows: age pelos identificadores de
acessibilidade (AutomationId), sem depender da posição na tela.

Os passos pedem a janela com `janela(apelido, comando, titulo)`: a primeira chamada abre o
aplicativo, as seguintes reaproveitam a mesma janela. Só roda no Windows, com a sessão do
usuário aberta (o runner precisa de área de trabalho).
"""

import logging
from pathlib import Path

from automacao.apoio import evidencias, sessoes

log = logging.getLogger(__name__)

TEMPO_PARA_ABRIR_S = 30


class SessaoDesktop:

    def __init__(self):
        # Importado aqui: o pywinauto só existe no Windows, e o resto do projeto roda em
        # qualquer sistema.
        from pywinauto import Application, Desktop

        self._application = Application
        self._desktop = Desktop
        self.janelas = {}

    def janela(self, apelido: str, comando: str, titulo: str):
        if apelido not in self.janelas:
            log.info("Abrindo %s", apelido)
            self._application(backend="uia").start(comando)
            janela = self._desktop(backend="uia").window(title_re=titulo, control_type="Window", found_index=0)
            janela.wait("exists visible ready", timeout=TEMPO_PARA_ABRIR_S)
            self.janelas[apelido] = janela

        return self.janelas[apelido]

    def evidencia(self, nome: str) -> Path | None:
        caminho = None

        for apelido, janela in self.janelas.items():
            caminho = evidencias.arquivo(f"{nome}-{apelido}" if len(self.janelas) > 1 else nome, "png")
            janela.capture_as_image().save(caminho)
            evidencias.registrar(caminho)

        return caminho

    def fechar(self) -> None:
        for apelido, janela in reversed(list(self.janelas.items())):
            try:
                janela.close()
            except Exception:
                log.warning("Não deu para fechar %s", apelido)


def janela(apelido: str, comando: str, titulo: str):
    """A janela do aplicativo: abre na primeira vez, reaproveita nas seguintes."""
    return sessoes.obter("desktop", SessaoDesktop).janela(apelido, comando, titulo)


def print_da_tela(nome: str) -> Path | None:
    """Grava um print de cada janela aberta na pasta de evidências."""
    return sessoes.obter("desktop", SessaoDesktop).evidencia(nome)
