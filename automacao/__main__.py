"""
Roda cenários sem pytest e sem Proton, como um robô comum:

    uv run python -m automacao cenarios/compra-com-sucesso.json

Sem arquivo, roda todos os cenários da pasta `cenarios/`.
"""

import logging
import sys

from automacao.apoio import navegador
from automacao.apoio.cenarios import executar_cenario, listar


def main(arquivos: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    falhas = 0

    for arquivo in arquivos or listar():
        try:
            with navegador.aberto():
                executar_cenario(arquivo)
        except Exception:
            logging.exception("Falhou: %s", arquivo)
            falhas += 1

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
