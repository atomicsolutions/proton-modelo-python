"""
Do nome do componente ao passo que o executa.

O nome é o mesmo no Proton e nos cenários (`FazerLogin`), e o arquivo do componente é o
nome em minúsculas, com `_` entre as palavras (`automacao/componentes/fazer_login.py`).
Cada componente tem uma função `executar(parametros) -> dict | None`.

Quando o passo falha, fica um print da tela na pasta de evidências, com e sem o Proton.
"""

import importlib
import logging
import re
import unicodedata
from typing import Callable

from automacao.apoio import evidencias

Passo = Callable[[dict], dict | None]

PACOTE_DOS_COMPONENTES = "automacao.componentes"

log = logging.getLogger(__name__)


def nome_do_arquivo(componente: str) -> str:
    """`FazerLogin`, `Fazer login` e `fazer_login` viram `fazer_login`."""
    sem_acento = unicodedata.normalize("NFKD", componente).encode("ascii", "ignore").decode()
    separado = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", sem_acento)
    return re.sub(r"[^0-9a-zA-Z]+", "_", separado).strip("_").lower()


def localizar(componente: str) -> Passo | None:
    """O passo do componente, ou `None` se ele não existe no projeto."""
    modulo = f"{PACOTE_DOS_COMPONENTES}.{nome_do_arquivo(componente)}"

    try:
        implementacao = importlib.import_module(modulo)
    except ModuleNotFoundError as erro:
        # Só "componente não existe" vira None; um import quebrado dentro dele é erro.
        if erro.name == modulo:
            return None
        raise

    def passo(parametros: dict) -> dict | None:
        try:
            return implementacao.executar(parametros)
        except Exception:
            _print_da_falha(componente)
            raise

    return passo


def _print_da_falha(componente: str) -> None:
    try:
        evidencias.print_da_tela(f"falha-{nome_do_arquivo(componente)}")
    except Exception:
        # Sem print (navegador fechado, por exemplo), o erro do passo é o que importa.
        log.warning("Não deu para gravar o print da falha de %s", componente)
