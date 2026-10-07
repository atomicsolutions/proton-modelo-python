"""
Evidências: prints e arquivos gravados na pasta de evidências (`PASTA_DE_EVIDENCIAS`).

Fora do Proton, ficam na pasta. Numa execução do Proton, o que aparece na pasta durante
um passo sobe para aquele passo. A automação não precisa saber onde está rodando.

Cada plataforma grava a evidência dela (`web.print_da_tela`, `sap.print_da_tela`,
`desktop.print_da_tela`, `api.evidencia`). Quando um passo falha, `da_falha` pede a
evidência de todas as sessões abertas.
"""

import logging
from datetime import datetime
from pathlib import Path

from automacao.apoio import config, sessoes

log = logging.getLogger(__name__)


def arquivo(nome: str, extensao: str) -> Path:
    """Um caminho novo na pasta de evidências, com data e hora no nome."""
    config.PASTA_DE_EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    return config.PASTA_DE_EVIDENCIAS / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{nome}.{extensao}"


def registrar(caminho: Path) -> Path:
    log.info("Evidência: %s", caminho.name)
    return caminho


def da_falha(componente: str) -> None:
    """A evidência de cada sessão aberta, quando um passo falha."""
    for plataforma, sessao in sessoes.todas().items():
        try:
            sessao.evidencia(f"falha-{componente}-{plataforma}")
        except Exception:
            # Sem evidência (janela já fechada, por exemplo), o erro do passo é o que importa.
            log.warning("Não deu para gravar a evidência de %s na falha de %s", plataforma, componente)
