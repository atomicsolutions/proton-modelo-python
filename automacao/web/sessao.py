"""
A sessão web: um navegador (Playwright) por cenário, compartilhado pelos passos dele.

As páginas usam `pagina()`; o navegador abre na primeira vez que alguém pede.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import Error as ErroDaPlaywright
from playwright.sync_api import Page, sync_playwright

from automacao.apoio import config, evidencias, sessoes

log = logging.getLogger(__name__)

# Queda de conexão (net::...) e a página de erro do Chrome interrompendo a navegação seguinte.
_QUEDAS_DE_REDE = ("net::", "interrupted by another navigation")


class SessaoWeb:

    def __init__(self):
        self._playwright = sync_playwright().start()
        self._navegador = self._lancar()
        self._contexto = self._navegador.new_context(viewport={"width": 1366, "height": 768})
        self.pagina = self._contexto.new_page()
        self.pagina.set_default_timeout(config.TIMEOUT_MS)

    def _lancar(self):
        try:
            return self._playwright.chromium.launch(headless=config.HEADLESS, channel=config.CANAL_DO_NAVEGADOR)
        except ErroDaPlaywright as erro:
            # Na primeira execução numa máquina (o runner do Proton, por exemplo), o Chromium
            # da versão da Playwright ainda não está lá: instala e tenta de novo.
            if config.CANAL_DO_NAVEGADOR or "Executable doesn't exist" not in str(erro):
                raise

        log.info("Instalando o Chromium da Playwright (só na primeira execução nesta máquina)")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return self._playwright.chromium.launch(headless=config.HEADLESS, channel=config.CANAL_DO_NAVEGADOR)

    def evidencia(self, nome: str) -> Path:
        caminho = evidencias.arquivo(nome, "png")
        self.pagina.screenshot(path=caminho, full_page=True)
        return evidencias.registrar(caminho)

    def fechar(self) -> None:
        try:
            self._contexto.close()
            self._navegador.close()
        finally:
            self._playwright.stop()


def pagina() -> Page:
    """A página do navegador do cenário."""
    return sessoes.obter("web", SessaoWeb).pagina


def print_da_tela(nome: str) -> Path:
    """Grava um print da página inteira na pasta de evidências."""
    return sessoes.obter("web", SessaoWeb).evidencia(nome)


def ir_para(url: str, tentativas: int = 4) -> None:
    """Abre o endereço, tentando de novo, com espera crescente, quando a rede cai."""
    for tentativa in range(1, tentativas + 1):
        try:
            pagina().goto(url)
            return
        except ErroDaPlaywright as erro:
            if not any(sinal in str(erro) for sinal in _QUEDAS_DE_REDE) or tentativa == tentativas:
                raise
            espera = 2 ** tentativa
            log.warning("Rede instável ao abrir %s (tentativa %d de %d), nova tentativa em %d s: %s",
                        url, tentativa, tentativas, espera, str(erro).splitlines()[0])
            time.sleep(espera)
