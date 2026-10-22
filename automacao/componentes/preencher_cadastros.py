"""
PreencherCadastros: preenche no formulário do RPA Challenge cada cadastro da planilha
(`in_planilha`, o caminho que o LerPlanilhaDeCadastros devolve).

`in_pausa_ms` (opcional) espera entre um cadastro e outro, para quem assiste acompanhar.
"""

import logging
import re
from pathlib import Path

from automacao.arquivos.excel import ler_registros
from automacao.web import sessao as web
from automacao.web.rpa_challenge import PaginaDoDesafio

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    planilha = Path(parametros["in_planilha"])
    if not planilha.is_file():
        raise FileNotFoundError(f"A planilha de cadastros não está em {planilha}")
    cadastros = ler_registros(planilha)
    pausa_ms = int(parametros.get("in_pausa_ms") or 0)
    desafio = PaginaDoDesafio().garantir_aberta()
    desafio.comecar()

    for numero, cadastro in enumerate(cadastros, start=1):
        desafio.preencher(cadastro)
        if numero == 1:
            web.print_da_tela("primeiro-cadastro-preenchido")
        desafio.enviar()
        if pausa_ms:
            web.pagina().wait_for_timeout(pausa_ms)
        log.info("Cadastro %d de %d: %s %s, %s", numero, len(cadastros), cadastro["First Name"], cadastro["Last Name"], cadastro["Company Name"])

    resultado = desafio.resultado()
    web.print_da_tela("resultado-do-desafio")

    acerto = re.search(r"(\d+)%", resultado)
    tempo = re.search(r"in (\d+) milliseconds", resultado)
    if not acerto or acerto.group(1) != "100":
        raise AssertionError(f"Esperava 100% dos campos certos, e o desafio respondeu: {resultado}")

    log.info(resultado)
    return {
        "out_resultado": resultado,
        "out_taxa_de_acerto": f"{acerto.group(1)}%",
        "out_tempo_ms": tempo.group(1) if tempo else "",
    }
