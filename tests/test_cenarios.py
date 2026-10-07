"""Os cenários da pasta `cenarios/`, sem o Proton: um teste por arquivo."""

import pytest

from automacao.apoio import navegador
from automacao.apoio.cenarios import executar_cenario, listar


@pytest.mark.parametrize("arquivo", listar(), ids=lambda arquivo: arquivo.stem)
def test_cenario(arquivo):
    with navegador.aberto():
        executar_cenario(arquivo)
