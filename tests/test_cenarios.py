"""Os cenários da pasta `cenarios/`, sem o Proton: um teste por arquivo."""

import pytest

from automacao.apoio import sessoes
from automacao.apoio.cenarios import carregar, executar_cenario, listar, requisitos_que_faltam


@pytest.mark.parametrize("arquivo", listar(), ids=lambda arquivo: arquivo.stem)
def test_cenario(arquivo):
    faltam = requisitos_que_faltam(carregar(arquivo))

    if faltam:
        pytest.skip(f"falta {', '.join(faltam)}")

    with sessoes.abertas():
        executar_cenario(arquivo)
