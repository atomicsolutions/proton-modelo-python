"""
Roda um cenário a partir de um arquivo JSON, sem o Proton.

O arquivo tem o mesmo formato de um dataset do Proton: os passos em ordem, cada um com o
componente e os parâmetros.

    {
      "descricao": "Compra com sucesso",
      "passos": [
        {"componente": "FazerLogin", "parametros": {"in_usuario": "standard_user"}},
        {"componente": "AdicionarAoCarrinho", "parametros": {"in_produto": "Sauce Labs Backpack"}}
      ]
    }

Dois tipos de referência no valor de um parâmetro:

- `${out_preco}`: a saída de um passo anterior, como a referência a saída no Proton;
- `${env:SENHA_DA_LOJA}`: uma variável de ambiente ou do `.env`, para segredo não ir
  para o git (no Proton, o equivalente é o parâmetro criptografado).
"""

import json
import logging
import os
import re
from pathlib import Path

from automacao.apoio import config
from automacao.apoio.passos import localizar

REFERENCIA = re.compile(r"\$\{(env:)?([A-Za-z0-9_]+)\}")

log = logging.getLogger(__name__)


def listar() -> list[Path]:
    """Os cenários da pasta `cenarios/`."""
    return sorted(config.PASTA_DE_CENARIOS.glob("*.json"))


def executar_cenario(arquivo: Path | str) -> dict:
    """Roda os passos do cenário e devolve as saídas de todos eles."""
    cenario = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    log.info("Cenário: %s", cenario.get("descricao") or Path(arquivo).stem)
    saidas: dict = {}

    for numero, passo in enumerate(cenario["passos"], start=1):
        componente = passo["componente"]
        executar = localizar(componente)

        if executar is None:
            raise LookupError(f'O componente "{componente}" não existe em automacao/componentes.')

        parametros = {nome: _resolver(valor, saidas) for nome, valor in (passo.get("parametros") or {}).items()}
        log.info("Passo %d: %s", numero, componente)
        saidas.update(executar(parametros) or {})

    return saidas


def _resolver(valor, saidas: dict) -> str:
    def substituir(referencia):
        ambiente, nome = referencia.groups()

        if ambiente:
            if nome not in os.environ:
                raise KeyError(f"Defina {nome} no ambiente ou no .env (veja o .env.example).")
            return os.environ[nome]

        if nome not in saidas:
            raise KeyError(f'A saída "{nome}" ainda não foi gerada por nenhum passo anterior.')
        return str(saidas[nome])

    return REFERENCIA.sub(substituir, "" if valor is None else str(valor))
