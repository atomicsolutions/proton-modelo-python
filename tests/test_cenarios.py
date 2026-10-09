"""Os cenários da pasta `cenarios/`, sem o Proton: um teste por arquivo."""

import pytest

from automacao.apoio import sessoes
from automacao.apoio.cenarios import carregar, conferir_falha_esperada, executar_cenario, listar, requisitos_que_faltam


@pytest.mark.parametrize("arquivo", listar(), ids=lambda arquivo: arquivo.stem)
def test_cenario(arquivo):
    cenario = carregar(arquivo)
    faltam = requisitos_que_faltam(cenario)

    if faltam:
        pytest.skip(f"falta {', '.join(faltam)}")

    erro = None

    try:
        with sessoes.abertas():
            executar_cenario(arquivo)
    except Exception as falha:
        erro = falha

    falha_esperada = conferir_falha_esperada(cenario, erro)

    if falha_esperada:
        pytest.xfail(f"falha proposital: {falha_esperada}")
