"""
Roda cenários sem pytest e sem Proton, como um robô comum:

    uv run python -m automacao cenarios/compra-com-sucesso.json

Sem arquivo, roda todos os cenários da pasta `cenarios/`.
"""

import logging
import sys

from automacao.apoio import sessoes
from automacao.apoio.cenarios import carregar, conferir_falha_esperada, executar_cenario, listar, requisitos_que_faltam


def main(arquivos: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    falhas = 0

    for arquivo in arquivos or listar():
        cenario = carregar(arquivo)
        faltam = requisitos_que_faltam(cenario)

        if faltam:
            logging.warning("Pulado: %s (falta %s)", arquivo, ", ".join(faltam))
            continue

        erro = None

        try:
            with sessoes.abertas():
                executar_cenario(arquivo)
        except Exception as falha:
            erro = falha

        try:
            falha_esperada = conferir_falha_esperada(cenario, erro)
        except Exception:
            logging.exception("Falhou: %s", arquivo)
            falhas += 1
            continue

        if falha_esperada:
            logging.warning("Falhou como esperado: %s (%s)", arquivo, falha_esperada)

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
