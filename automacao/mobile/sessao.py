"""
A sessão mobile: um aparelho Android pelo Appium (UiAutomator2), por cenário.

Configuração (`.env`): `APPIUM_URL`, `MOBILE_DISPOSITIVO` (o serial do `adb devices`; vazio
usa o primeiro conectado), `MOBILE_APP` (o caminho do .apk; vazio abre o app já instalado,
pelo `MOBILE_PACOTE` e pela `MOBILE_ACTIVITY`). Numa execução do Proton, o aparelho e o app
escolhidos no disparo chegam pelo ponto de entrada do Proton.

Pré-requisitos na máquina: Android SDK (adb), Appium com o driver UiAutomator2
(`npm install -g appium` e `appium driver install uiautomator2`) e o aparelho com a
depuração USB ligada. Se o Appium não estiver no ar no endereço local configurado, a sessão
o inicia e o encerra no fim do cenário.
"""

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.appium_service import AppiumService

from automacao.apoio import config, evidencias, sessoes

log = logging.getLogger(__name__)

TEMPO_PARA_O_APPIUM_SUBIR_S = 60


class SessaoMobile:

    def __init__(self):
        self._servico = None if _appium_no_ar() else _iniciar_appium()

        opcoes = UiAutomator2Options()
        opcoes.new_command_timeout = 300
        opcoes.auto_grant_permissions = True
        # Muitos apps abrem por uma tela de abertura que some logo: qualquer tela do app
        # serve como sinal de que ele abriu.
        opcoes.app_wait_activity = "*"

        if config.MOBILE_DISPOSITIVO:
            opcoes.udid = config.MOBILE_DISPOSITIVO

        if config.MOBILE_APP:
            opcoes.app = str(Path(config.MOBILE_APP).resolve())
        else:
            opcoes.app_package = config.MOBILE_PACOTE
            opcoes.app_activity = config.MOBILE_ACTIVITY

        try:
            self.driver = webdriver.Remote(config.APPIUM_URL, options=opcoes)
        except Exception:
            self._parar_appium()
            raise

        log.info("Aparelho %s", self.driver.capabilities.get("deviceUDID") or self.driver.capabilities.get("udid"))

    def evidencia(self, nome: str) -> Path:
        caminho = evidencias.arquivo(nome, "png")
        self.driver.get_screenshot_as_file(str(caminho))
        return evidencias.registrar(caminho)

    def fechar(self) -> None:
        try:
            self.driver.quit()
        finally:
            self._parar_appium()

    def _parar_appium(self) -> None:
        if self._servico is not None:
            self._servico.stop()
            self._servico = None


def _appium_no_ar() -> bool:
    try:
        return requests.get(f"{config.APPIUM_URL}/status", timeout=3).ok
    except requests.RequestException:
        return False


def _iniciar_appium() -> AppiumService:
    endereco = urlparse(config.APPIUM_URL)

    if endereco.hostname not in ("127.0.0.1", "localhost"):
        raise RuntimeError(f"O Appium não responde em {config.APPIUM_URL}.")

    log.info("Iniciando o Appium em %s", config.APPIUM_URL)
    servico = AppiumService()
    servico.start(args=["--address", endereco.hostname, "--port", str(endereco.port or 4723)], timeout_ms=60000)

    # O serviço devolve o controle antes de o Appium aceitar conexões: espera o /status.
    limite = time.monotonic() + TEMPO_PARA_O_APPIUM_SUBIR_S

    while not _appium_no_ar():
        if time.monotonic() > limite:
            servico.stop()
            raise RuntimeError(f"O Appium não respondeu em {TEMPO_PARA_O_APPIUM_SUBIR_S} s em {config.APPIUM_URL}.")
        time.sleep(1)

    return servico


def driver() -> webdriver.Remote:
    """O driver do Appium do cenário."""
    return sessoes.obter("mobile", SessaoMobile).driver


def print_da_tela(nome: str) -> Path:
    """Grava um print da tela do aparelho na pasta de evidências."""
    return sessoes.obter("mobile", SessaoMobile).evidencia(nome)
