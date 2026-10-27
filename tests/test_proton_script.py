"""
Ponto de entrada do runner do Proton, e o único arquivo do projeto que conhece o Proton.

O runner informa o id da execução, e a SDK roda os passos do dataset na ordem: busca os
parâmetros de cada um, chama o componente, grava as saídas, sobe as evidências e registra
o resultado. Os passos podem ser de plataformas diferentes (cada uma um sistema no Proton,
todos ligados a este repositório): a SDK segue enquanto este projeto tiver o componente, e
as sessões abertas valem para a execução inteira.

No fim, quando um passo falha e quando o próximo passo é de outro projeto, a SDK fecha as
sessões e sobe o que sai do fechamento antes de gravar o status. Na falha, o Proton separa
o motivo pela exceção (`automacao/apoio/falhas.py`): de negócio, de ambiente ou técnica.

Sem o Proton, apague este arquivo e a dependência `protoncloud-sdk`: o resto do projeto
não muda.
"""

import os
import sys

import pytest
from proton.component_runner import run_components, run_evidence_dir
from proton.proton_automation import get_current_component_device
from proton.proton_environment import ProtonEnvironmentError, get_environment_variables
from proton.proton_files_and_resources import download_mobile_app
from proton.run_status import FailureReason, failure_reason

from automacao.apoio import config, sessoes
from automacao.apoio.cenarios import executar_cenario
from automacao.apoio.falhas import FalhaDeAmbiente, FalhaDeNegocio
from automacao.apoio.passos import Passo, localizar
from automacao.mobile import sessao as mobile


def test_run_proton_execution(request):
    id_dataset_run = request.config.getoption("id_dataset_run") or os.getenv("idDatasetRun")

    if not id_dataset_run:
        pytest.skip("Só roda numa execução do Proton. Fora dele, os cenários rodam em test_cenarios.py.")

    os.environ["idDatasetRun"] = str(id_dataset_run)

    # O runner pode rodar várias execuções ao mesmo tempo, na mesma pasta do projeto: cada
    # uma grava em evidencias/<id da execução>, e a SDK sobe para ela só o que é dela.
    config.PASTA_DE_EVIDENCIAS = config.RAIZ_DO_PROJETO / run_evidence_dir()

    # O navegador na tela do runner: HEADLESS=false no ambiente da execução (Configurações >
    # Ambientes, no Proton) vale como no .env, que o runner não tem.
    _navegador_pelo_ambiente()

    # As sessões abrem quando um passo pede, e a SDK as fecha antes do status. Cada passo
    # leva o aparelho do sistema dele (uma execução pode ter vários sistemas mobile).
    run_components(_localizar_com_aparelho, close_at_end=[sessoes.fechar_todas])


def _localizar_com_aparelho(componente: str) -> Passo | None:
    """O passo do componente, com o aparelho e o app que o disparo escolheu para o sistema dele."""
    passo = localizar(componente)

    if passo is None:
        return None

    # Lido agora, antes de o passo começar: o Proton responde pelo passo que ainda não começou.
    aparelho = _aparelho_do_passo()

    def com_aparelho(parametros: dict) -> dict | None:
        mobile.usar_aparelho(aparelho)
        return passo(parametros)

    return com_aparelho


_apps_baixados: dict[str, str] = {}


def _aparelho_do_passo() -> mobile.Aparelho | None:
    """O aparelho do sistema do passo, ou `None` (passo de outra plataforma: vale o do `.env`)."""
    aparelho = get_current_component_device()

    if not aparelho:
        return None

    app = config.MOBILE_APP

    if aparelho.get("app"):
        id_do_app = str(aparelho["app"])

        if id_do_app not in _apps_baixados:
            _apps_baixados[id_do_app] = download_mobile_app(id_do_app)

        app = _apps_baixados[id_do_app] or app

    sistema = aparelho.get("idSystem")
    return mobile.Aparelho(sistema=str(sistema) if sistema is not None else None,
                           serial=aparelho.get("device") or config.MOBILE_DISPOSITIVO,
                           app=app)


def _navegador_pelo_ambiente() -> None:
    try:
        ambiente = get_environment_variables()
    except ProtonEnvironmentError:
        return  # sem ambiente legível, vale a configuração do projeto

    if "HEADLESS" in ambiente:
        config.HEADLESS = ambiente["HEADLESS"].strip().lower() != "false"
    if ambiente.get("CANAL_DO_NAVEGADOR", "").strip():
        config.CANAL_DO_NAVEGADOR = ambiente["CANAL_DO_NAVEGADOR"].strip()


# O motivo que o Proton grava para as falhas do projeto. Rodam fora do Proton, com o pytest.

def test_falha_proposital_e_de_negocio():
    with pytest.raises(FalhaDeNegocio, match="Last Name is required") as falha:
        with sessoes.abertas():
            executar_cenario(config.PASTA_DE_CENARIOS / "compra-com-falha-proposital.json")

    assert failure_reason(falha.value) is FailureReason.BUSINESS


def test_sessao_que_nao_abre_e_falha_de_ambiente():
    def abrir():
        raise ConnectionRefusedError("o aparelho não respondeu")

    with pytest.raises(FalhaDeAmbiente) as falha:
        with sessoes.abertas():
            sessoes.obter("aparelho", abrir)

    assert isinstance(falha.value.__cause__, ConnectionRefusedError)
    assert failure_reason(falha.value) is FailureReason.ENVIRONMENT


def test_navegador_na_tela_pelo_ambiente_do_proton(monkeypatch):
    monkeypatch.setattr(config, "HEADLESS", True)
    monkeypatch.setattr(config, "CANAL_DO_NAVEGADOR", None)
    monkeypatch.setattr(sys.modules[__name__], "get_environment_variables",
                        lambda: {"HEADLESS": "false", "CANAL_DO_NAVEGADOR": "msedge"})

    _navegador_pelo_ambiente()

    assert config.HEADLESS is False
    assert config.CANAL_DO_NAVEGADOR == "msedge"


def test_sem_ambiente_legivel_vale_a_configuracao_do_projeto(monkeypatch):
    def sem_ambiente():
        raise ProtonEnvironmentError("sem ambiente", "httpError")

    monkeypatch.setattr(config, "HEADLESS", True)
    monkeypatch.setattr(sys.modules[__name__], "get_environment_variables", sem_ambiente)

    _navegador_pelo_ambiente()

    assert config.HEADLESS is True


# O aparelho de cada passo: uma execução pode ter vários sistemas mobile, cada um com o seu.

@pytest.fixture
def execucao_com_dois_apps(monkeypatch):
    aparelhos = {
        "PedirNoApp": {"idSystem": 12, "deviceFarm": "local", "device": "R58M123", "app": "301"},
        "EntregarNoApp": {"idSystem": 15, "deviceFarm": "local", "device": "R58M999", "app": "302"},
        "ConferirNoSite": None,
    }
    estado = {"componente": None, "downloads": []}

    def localizar_falso(componente):
        estado["componente"] = componente
        return lambda parametros: mobile.aparelho_do_passo()

    def baixar(id_do_app):
        estado["downloads"].append(id_do_app)
        return f"/apps/{id_do_app}.apk"

    modulo = sys.modules[__name__]
    monkeypatch.setattr(modulo, "localizar", localizar_falso)
    monkeypatch.setattr(modulo, "get_current_component_device", lambda: aparelhos[estado["componente"]])
    monkeypatch.setattr(modulo, "download_mobile_app", baixar)
    monkeypatch.setattr(modulo, "_apps_baixados", {})
    monkeypatch.setattr(config, "MOBILE_DISPOSITIVO", None)
    monkeypatch.setattr(config, "MOBILE_APP", None)
    yield estado
    mobile.usar_aparelho(None)


def test_cada_passo_usa_o_aparelho_do_sistema_dele(execucao_com_dois_apps):
    pedir = _localizar_com_aparelho("PedirNoApp")
    entregar = _localizar_com_aparelho("EntregarNoApp")

    assert pedir({}) == mobile.Aparelho(sistema="12", serial="R58M123", app="/apps/301.apk")
    assert entregar({}) == mobile.Aparelho(sistema="15", serial="R58M999", app="/apps/302.apk")
    assert mobile.Aparelho(sistema="12").chave == "mobile:12"


def test_o_app_de_cada_sistema_e_baixado_uma_vez(execucao_com_dois_apps):
    _localizar_com_aparelho("PedirNoApp")
    _localizar_com_aparelho("EntregarNoApp")
    _localizar_com_aparelho("PedirNoApp")

    assert execucao_com_dois_apps["downloads"] == ["301", "302"]


def test_passo_de_outra_plataforma_volta_ao_aparelho_do_env(execucao_com_dois_apps, monkeypatch):
    monkeypatch.setattr(config, "MOBILE_DISPOSITIVO", "emulator-5554")
    _localizar_com_aparelho("PedirNoApp")({})

    assert _localizar_com_aparelho("ConferirNoSite")({}) == mobile.Aparelho(serial="emulator-5554")


def test_componente_de_outro_projeto_nao_pede_o_aparelho(monkeypatch):
    chamadas = []
    monkeypatch.setattr(sys.modules[__name__], "localizar", lambda componente: None)
    monkeypatch.setattr(sys.modules[__name__], "get_current_component_device", lambda: chamadas.append(1))

    assert _localizar_com_aparelho("DeOutroProjeto") is None
    assert chamadas == []
