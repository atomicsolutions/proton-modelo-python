"""
A sessão mobile por sistema: dois apps no mesmo cenário (o do cliente e o do entregador,
por exemplo) abrem dois aparelhos, cada um na sua sessão. Rodam sem aparelho e sem Appium.
"""

import socket

import pytest

from automacao.apoio import config, sessoes
from automacao.mobile import sessao as mobile


class _SessaoFalsa:
    def __init__(self, aparelho):
        self.aparelho = aparelho
        self.driver = f"driver de {aparelho.serial}"
        self.fechada = False

    def evidencia(self, nome):
        return None

    def fechar(self):
        self.fechada = True


@pytest.fixture
def aparelhos(monkeypatch):
    monkeypatch.setattr(mobile, "SessaoMobile", _SessaoFalsa)
    monkeypatch.setattr(config, "MOBILE_DISPOSITIVO", "emulator-5554")
    monkeypatch.setattr(config, "MOBILE_APP", None)
    yield
    mobile.usar_aparelho(None)
    sessoes.fechar_todas()


def test_cada_sistema_tem_a_sua_sessao(aparelhos):
    with sessoes.abertas():
        mobile.usar_aparelho(mobile.Aparelho(sistema="12", serial="R58M123", app="cliente.apk"))
        assert mobile.driver() == "driver de R58M123"

        mobile.usar_aparelho(mobile.Aparelho(sistema="15", serial="R58M999", app="entregador.apk"))
        assert mobile.driver() == "driver de R58M999"

        # O passo seguinte do primeiro sistema volta ao aparelho dele, sem abrir outro.
        mobile.usar_aparelho(mobile.Aparelho(sistema="12", serial="R58M123", app="cliente.apk"))
        assert mobile.driver() == "driver de R58M123"

        assert list(sessoes.todas()) == ["mobile:12", "mobile:15"]


def test_fora_do_proton_vale_o_aparelho_do_env_numa_sessao_so(aparelhos):
    with sessoes.abertas():
        assert mobile.driver() == "driver de emulator-5554"
        assert mobile.driver() == "driver de emulator-5554"
        assert list(sessoes.todas()) == ["mobile"]


def test_as_sessoes_dos_aparelhos_fecham_no_fim_do_cenario(aparelhos):
    with sessoes.abertas():
        mobile.usar_aparelho(mobile.Aparelho(sistema="12", serial="R58M123"))
        mobile.driver()
        mobile.usar_aparelho(mobile.Aparelho(sistema="15", serial="R58M999"))
        mobile.driver()
        abertas = list(sessoes.todas().values())

    assert all(sessao.fechada for sessao in abertas)
    assert sessoes.todas() == {}


def test_cada_aparelho_local_tem_a_sua_porta():
    porta = mobile._porta_livre()

    # A porta devolvida está livre: dá para abrir um servidor nela.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", porta))
