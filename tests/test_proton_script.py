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
from proton.proton_automation import get_dataset_run_info
from proton.proton_environment import ProtonEnvironmentError, get_environment_variables
from proton.proton_files_and_resources import download_mobile_app
from proton.run_status import FailureReason, failure_reason

from automacao.apoio import config, sessoes
from automacao.apoio.cenarios import executar_cenario
from automacao.apoio.falhas import FalhaDeAmbiente, FalhaDeNegocio
from automacao.apoio.passos import localizar


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

    # Execução mobile: o aparelho e o app escolhidos no disparo do Proton.
    execucao = get_dataset_run_info()

    if execucao.get("device"):
        config.MOBILE_DISPOSITIVO = str(execucao["device"])

    if execucao.get("app"):
        config.MOBILE_APP = download_mobile_app(str(execucao["app"])) or config.MOBILE_APP

    # As sessões abrem quando um passo pede, e a SDK as fecha antes do status.
    run_components(localizar, close_at_end=[sessoes.fechar_todas])


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
