"""
O navegador da automação: um por cenário, compartilhado pelos passos dele.

    with navegador.aberto():
        ...  # os passos usam navegador.pagina()
"""

import logging
import subprocess
import sys
import time
from contextlib import contextmanager

from playwright.sync_api import Error as ErroDaPlaywright
from playwright.sync_api import Page, sync_playwright

from automacao.apoio import config

log = logging.getLogger(__name__)

_pagina: Page | None = None

# Queda de conexão (net::...) e a página de erro do Chrome interrompendo a navegação seguinte.
_QUEDAS_DE_REDE = ("net::", "interrupted by another navigation")


@contextmanager
def aberto():
    """Abre o navegador para os passos de um cenário e o fecha no fim, mesmo com erro."""
    global _pagina

    with sync_playwright() as playwright:
        navegador = _lancar(playwright)
        contexto = navegador.new_context(viewport={"width": 1366, "height": 768})
        _pagina = contexto.new_page()
        _pagina.set_default_timeout(config.TIMEOUT_MS)

        try:
            yield _pagina
        finally:
            _pagina = None
            contexto.close()
            navegador.close()


def _lancar(playwright):
    try:
        return playwright.chromium.launch(headless=config.HEADLESS, channel=config.CANAL_DO_NAVEGADOR)
    except ErroDaPlaywright as erro:
        # Na primeira execução numa máquina (o runner do Proton, por exemplo), o Chromium
        # da versão da Playwright ainda não está lá: instala e tenta de novo.
        if config.CANAL_DO_NAVEGADOR or "Executable doesn't exist" not in str(erro):
            raise

    log.info("Instalando o Chromium da Playwright (só na primeira execução nesta máquina)")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    return playwright.chromium.launch(headless=config.HEADLESS, channel=config.CANAL_DO_NAVEGADOR)


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


def pagina() -> Page:
    """A página aberta, para as páginas da automação (`automacao/paginas`)."""
    if _pagina is None:
        raise RuntimeError("Navegador fechado: rode os passos dentro de navegador.aberto().")

    return _pagina
