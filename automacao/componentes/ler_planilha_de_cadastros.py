"""
LerPlanilhaDeCadastros: baixa a planilha de cadastros do RPA Challenge e confere as colunas.

Devolve o caminho da planilha, e não as linhas: a saída de um passo no Proton é um texto
curto, e uma planilha de verdade tem milhares de linhas. O passo seguinte lê o arquivo.
"""

import logging

from automacao.apoio import evidencias
from automacao.arquivos.excel import ler_registros
from automacao.web.rpa_challenge import CAMPOS, PaginaDoDesafio

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    # A planilha fica na pasta de evidências: no Proton, ela aparece no passo, junto com o log.
    planilha = PaginaDoDesafio().abrir().baixar_planilha(evidencias.arquivo("planilha-de-cadastros", "xlsx"))
    evidencias.registrar(planilha)

    cadastros = ler_registros(planilha)
    if not cadastros:
        raise AssertionError("A planilha de cadastros veio sem nenhuma linha")

    faltam = [campo for campo in CAMPOS if campo not in cadastros[0]]
    if faltam:
        raise AssertionError(f"A planilha não tem as colunas {', '.join(faltam)}")

    log.info("Planilha com %d cadastros (o primeiro: %s %s)", len(cadastros), cadastros[0]["First Name"], cadastros[0]["Last Name"])
    return {"out_planilha": str(planilha), "out_quantidade": str(len(cadastros))}
