"""
A sessão de desktop: os aplicativos do Windows abertos pelos passos, fechados no fim do
cenário. Usa o pywinauto com o UI Automation do Windows: age pelos identificadores de
acessibilidade (AutomationId), sem depender da posição na tela.

Os passos pedem a janela com `janela(apelido, comando, titulo)`: a primeira chamada abre o
aplicativo, as seguintes reaproveitam a mesma janela. O aplicativo que não abre é falha de
ambiente (`FalhaDeAmbiente`). Só roda no Windows, com a sessão do usuário aberta (o runner
precisa de área de trabalho).
"""

import importlib
import logging
import sys
import tempfile
import time
from pathlib import Path

from automacao.apoio import evidencias, sessoes
from automacao.apoio.falhas import FalhaDeAmbiente

log = logging.getLogger(__name__)

TEMPO_PARA_ABRIR_S = 30
# Quanto uma execução espera outra largar um aplicativo de uma janela só (a Calculadora).
TEMPO_NA_FILA_S = 300


def _importar_pywinauto():
    """
    O pywinauto gera o módulo do UI Automation em `comtypes.gen` na primeira vez que roda
    numa pasta de projeto. Duas execuções ao mesmo tempo (o runner roda em paralelo) podem
    ler o arquivo pela metade ("has no attribute 'CUIAutomation'"): espera a outra terminar
    de gerar e importa de novo.
    """
    for tentativa in range(1, 4):
        try:
            from pywinauto import Application, Desktop
            return Application, Desktop
        except AttributeError as erro:
            if "CUIAutomation" not in str(erro) or tentativa == 3:
                raise
            log.warning("O módulo do UI Automation ainda estava sendo gerado; nova tentativa em %d s", 2 * tentativa)
            for nome in [m for m in sys.modules if m.startswith(("pywinauto", "comtypes.gen"))]:
                del sys.modules[nome]
            importlib.invalidate_caches()
            time.sleep(2 * tentativa)


class _Vez:
    """
    A vez de uma execução num aplicativo que só tem uma janela na máquina (a Calculadora do
    Windows abre sempre a mesma). O runner roda execuções em paralelo: sem a vez, dois
    robôs apertariam botões na mesma janela. É uma trava de arquivo, que vale entre processos
    e some sozinha se o processo morrer.
    """

    def __init__(self, apelido: str):
        import msvcrt

        self._msvcrt = msvcrt
        self._arquivo = open(Path(tempfile.gettempdir()) / f"proton-modelo-{apelido}.vez", "a+")
        limite = time.monotonic() + TEMPO_NA_FILA_S
        avisou = False

        while True:
            try:
                self._arquivo.seek(0)
                msvcrt.locking(self._arquivo.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() > limite:
                    self._arquivo.close()
                    raise TimeoutError(f"{apelido} seguiu ocupado por outra execução por {TEMPO_NA_FILA_S} s")
                if not avisou:
                    log.info("%s está com outra execução; esperando a vez", apelido)
                    avisou = True
                time.sleep(0.5)

    def largar(self) -> None:
        try:
            self._arquivo.seek(0)
            self._msvcrt.locking(self._arquivo.fileno(), self._msvcrt.LK_UNLCK, 1)
        finally:
            self._arquivo.close()


class SessaoDesktop:

    def __init__(self):
        # Importado aqui: o pywinauto só existe no Windows, e o resto do projeto roda em
        # qualquer sistema.
        self._application, self._desktop = _importar_pywinauto()
        self.janelas = {}
        self._vezes = {}

    def janela(self, apelido: str, comando: str, titulo: str):
        if apelido not in self.janelas:
            log.info("Abrindo %s", apelido)

            try:
                self._vezes[apelido] = _Vez(apelido)
                self._application(backend="uia").start(comando)
                janela = self._desktop(backend="uia").window(title_re=titulo, control_type="Window", found_index=0)
                janela.wait("exists visible ready", timeout=TEMPO_PARA_ABRIR_S)
            except Exception as erro:
                raise FalhaDeAmbiente(f"{apelido} não abriu ({comando}): {sessoes.primeira_linha(erro)}") from erro

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

        # A vez fica até a janela fechar: a próxima execução abre a dela do zero.
        for vez in self._vezes.values():
            vez.largar()
        self._vezes.clear()


def janela(apelido: str, comando: str, titulo: str):
    """A janela do aplicativo: abre na primeira vez, reaproveita nas seguintes."""
    return sessoes.obter("desktop", SessaoDesktop).janela(apelido, comando, titulo)


def print_da_tela(nome: str) -> Path | None:
    """Grava um print de cada janela aberta na pasta de evidências."""
    return sessoes.obter("desktop", SessaoDesktop).evidencia(nome)
