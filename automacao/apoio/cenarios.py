"""
Roda um cenário a partir de um arquivo JSON, sem o Proton.

O arquivo tem o mesmo formato de um dataset do Proton: os passos em ordem, cada um com o
componente e os parâmetros. Os passos podem ser de plataformas diferentes (web, API, SAP,
desktop): cada sessão abre quando o primeiro passo dela pede.

    {
      "descricao": "Compra com sucesso",
      "requer": ["windows"],
      "passos": [
        {"componente": "ConsultarCep", "parametros": {"in_cep": "01310-100"}},
        {"componente": "FazerLogin", "parametros": {"in_usuario": "standard_user"}}
      ]
    }

Dois tipos de referência no valor de um parâmetro:

- `${out_cep}`: a saída de um passo anterior, como a referência a saída no Proton;
- `${env:SENHA_DA_LOJA}`: uma variável de ambiente ou do `.env`, para segredo não ir
  para o git (no Proton, o equivalente é o parâmetro criptografado).

`requer` (opcional) lista o que o cenário precisa da máquina: `windows` (desktop), `sap`
(Windows com o SAP GUI e `SAP_CONEXAO`) e `android` (adb e um aparelho conectado). Sem isso,
o cenário é pulado, e não falha.

`falha_esperada` (opcional) marca o cenário que falha de propósito, com um trecho da
mensagem do erro. Fora do Proton ele conta como falha esperada; no Proton, o mesmo dataset
termina em Failed, com o log, o print e o erro do passo.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from automacao.apoio import config
from automacao.apoio.passos import localizar

REFERENCIA = re.compile(r"\$\{(env:)?([A-Za-z0-9_]+)\}")

log = logging.getLogger(__name__)


def listar() -> list[Path]:
    """Os cenários da pasta `cenarios/`."""
    return sorted(config.PASTA_DE_CENARIOS.glob("*.json"))


def carregar(arquivo: Path | str) -> dict:
    return json.loads(Path(arquivo).read_text(encoding="utf-8"))


def requisitos_que_faltam(cenario: dict) -> list[str]:
    """O que o cenário pede (`requer`) e esta máquina não tem."""
    faltam = []

    for requisito in cenario.get("requer") or []:
        if requisito in ("windows", "sap") and sys.platform != "win32":
            faltam.append(f"{requisito} (só roda no Windows)")
        elif requisito == "sap" and not config.SAP_CONEXAO:
            faltam.append("sap (defina SAP_CONEXAO no .env)")
        elif requisito == "android" and not _aparelho_android_conectado():
            faltam.append("android (adb e um aparelho conectado)")

    return faltam


def conferir_falha_esperada(cenario: dict, erro: Exception | None) -> str | None:
    """
    Confere o resultado do cenário com a `falha_esperada` dele. Devolve a mensagem da falha
    quando ela veio como esperado; sem `falha_esperada`, devolve `None` (ou relança o erro).
    """
    esperada = cenario.get("falha_esperada")

    if not esperada:
        if erro is not None:
            raise erro
        return None

    if erro is None:
        raise AssertionError(f'O cenário devia falhar com "{esperada}", mas passou.')

    if esperada not in str(erro):
        raise erro

    return str(erro)


def _aparelho_android_conectado() -> bool:
    adb = shutil.which("adb")

    if adb is None:
        return False

    saida = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=30).stdout
    aparelhos = [linha.split()[0] for linha in saida.splitlines()[1:] if linha.strip().endswith("device")]
    return bool(aparelhos) and (config.MOBILE_DISPOSITIVO is None or config.MOBILE_DISPOSITIVO in aparelhos)


def executar_cenario(arquivo: Path | str) -> dict:
    """Roda os passos do cenário e devolve as saídas de todos eles."""
    cenario = carregar(arquivo)
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
