"""
Evidências: prints gravados na pasta de evidências (`PASTA_DE_EVIDENCIAS`).

Fora do Proton, ficam na pasta. Numa execução do Proton, o que aparece na pasta durante
um passo sobe para aquele passo. A automação não precisa saber onde está rodando.
"""

import logging
from datetime import datetime
from pathlib import Path

from automacao.apoio import config, navegador

log = logging.getLogger(__name__)


def print_da_tela(nome: str) -> Path:
    """Grava um print da página inteira e devolve o caminho do arquivo."""
    config.PASTA_DE_EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    arquivo = config.PASTA_DE_EVIDENCIAS / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{nome}.png"
    navegador.pagina().screenshot(path=arquivo, full_page=True)
    log.info("Print: %s", arquivo.name)
    return arquivo
