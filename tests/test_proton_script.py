"""
Ponto de entrada do runner do Proton, e o único arquivo do projeto que conhece o Proton.

O runner informa o id da execução, e a SDK roda os passos do dataset na ordem: busca os
parâmetros de cada um, chama o componente, grava as saídas, sobe as evidências e registra
o resultado. Os passos podem ser de plataformas diferentes (cada uma um sistema no Proton,
todos ligados a este repositório): a SDK segue enquanto este projeto tiver o componente, e
as sessões abertas valem para a execução inteira.

Sem o Proton, apague este arquivo e a dependência `protoncloud-sdk`: o resto do projeto
não muda.
"""

import os

import pytest
from proton.component_runner import run_components
from proton.proton_automation import get_dataset_run_info
from proton.proton_files_and_resources import download_mobile_app

from automacao.apoio import config, sessoes
from automacao.apoio.passos import localizar


def test_run_proton_execution(request):
    id_dataset_run = request.config.getoption("id_dataset_run") or os.getenv("idDatasetRun")

    if not id_dataset_run:
        pytest.skip("Só roda numa execução do Proton. Fora dele, os cenários rodam em test_cenarios.py.")

    os.environ["idDatasetRun"] = str(id_dataset_run)

    # O runner pode rodar várias execuções ao mesmo tempo, na mesma pasta do projeto: cada
    # uma grava as evidências numa subpasta própria, senão um passo sobe o print da outra.
    config.PASTA_DE_EVIDENCIAS = config.PASTA_DE_EVIDENCIAS / str(id_dataset_run)

    # Execução mobile: o aparelho e o app escolhidos no disparo do Proton.
    execucao = get_dataset_run_info()

    if execucao.get("device"):
        config.MOBILE_DISPOSITIVO = str(execucao["device"])

    if execucao.get("app"):
        config.MOBILE_APP = download_mobile_app(str(execucao["app"])) or config.MOBILE_APP

    with sessoes.abertas():
        run_components(localizar, evidence_dir=str(config.PASTA_DE_EVIDENCIAS))
