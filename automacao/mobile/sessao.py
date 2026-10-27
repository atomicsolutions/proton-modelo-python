"""
A sessão mobile: um aparelho Android pelo Appium (UiAutomator2), por cenário.

Configuração (`.env`): `APPIUM_URL`, `MOBILE_DISPOSITIVO` (o serial do `adb devices`; vazio
usa o primeiro conectado), `MOBILE_APP` (o caminho do .apk; vazio abre o app já instalado,
pelo `MOBILE_PACOTE` e pela `MOBILE_ACTIVITY`).

Uma sessão por sistema: um cenário pode passar por dois apps (o do cliente e o do
entregador, por exemplo), cada um no seu aparelho. Numa execução do Proton, o ponto de
entrada informa, antes de cada passo, o aparelho e o app do sistema dele (`usar_aparelho`),
e a sessão fica guardada como `mobile:<id do sistema>`. Cada aparelho local tem o seu
`systemPort` no UiAutomator2, para dois aparelhos não disputarem a mesma porta. Fora do
Proton, vale o aparelho do `.env`, numa sessão só.

Pré-requisitos na máquina: Android SDK (adb), Appium com o driver UiAutomator2
(`npm install -g appium` e `appium driver install uiautomator2`) e o aparelho com a
depuração USB ligada. Se o Appium não estiver no ar no endereço local configurado, a sessão
o inicia e o encerra no fim do cenário.
"""

import logging
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.appium_service import AppiumService

from automacao.apoio import config, evidencias, sessoes

log = logging.getLogger(__name__)

TEMPO_PARA_O_APPIUM_SUBIR_S = 60


@dataclass(frozen=True)
class Aparelho:
    """O aparelho de um sistema mobile: o serial (vazio, o primeiro conectado) e o .apk."""

    sistema: str | None = None
    serial: str | None = None
    app: str | None = None

    @property
    def chave(self) -> str:
        """A chave da sessão: uma por sistema, e uma só fora do Proton."""
        return f"mobile:{self.sistema}" if self.sistema else "mobile"


_aparelho_do_passo: Aparelho | None = None


def usar_aparelho(aparelho: Aparelho | None) -> None:
    """O aparelho do passo que vai rodar; `None` volta ao do `.env`."""
    global _aparelho_do_passo
    _aparelho_do_passo = aparelho


def aparelho_do_passo() -> Aparelho:
    """O aparelho informado para o passo, ou o do `.env`."""
    return _aparelho_do_passo or Aparelho(serial=config.MOBILE_DISPOSITIVO, app=config.MOBILE_APP)


class SessaoMobile:

    def __init__(self, aparelho: Aparelho | None = None):
        aparelho = aparelho or aparelho_do_passo()
        self._servico = None if _appium_no_ar() else _iniciar_appium()

        opcoes = UiAutomator2Options()
        opcoes.new_command_timeout = 300
        opcoes.auto_grant_permissions = True
        # Muitos apps abrem por uma tela de abertura que some logo: qualquer tela do app
        # serve como sinal de que ele abriu.
        opcoes.app_wait_activity = "*"
        # O UiAutomator2 fala com o aparelho por uma porta da máquina (8200, se ninguém
        # escolher): com dois aparelhos na mesma execução, cada um precisa da sua.
        opcoes.system_port = _porta_livre()

        if aparelho.serial:
            opcoes.udid = aparelho.serial

        if aparelho.app:
            opcoes.app = str(Path(aparelho.app).resolve())
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


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as porta:
        porta.bind(("127.0.0.1", 0))
        return porta.getsockname()[1]


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


def _sessao() -> SessaoMobile:
    aparelho = aparelho_do_passo()
    return sessoes.obter(aparelho.chave, lambda: SessaoMobile(aparelho))


def driver() -> webdriver.Remote:
    """O driver do Appium do aparelho do passo."""
    return _sessao().driver


def print_da_tela(nome: str) -> Path:
    """Grava um print da tela do aparelho do passo na pasta de evidências."""
    return _sessao().evidencia(nome)
