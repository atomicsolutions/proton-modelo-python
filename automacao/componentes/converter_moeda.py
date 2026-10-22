"""ConverterMoeda: converte um valor em moeda estrangeira para reais pela cotação do Banco Central."""

import logging
from decimal import Decimal, InvalidOperation

from automacao.web import sessao as web
from automacao.web.conversor_de_moedas import PaginaDoConversor

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    moeda = parametros["in_moeda"].strip().upper()

    try:
        valor = Decimal(parametros["in_valor"].strip())
    except InvalidOperation as erro:
        raise ValueError(f'O valor deve vir com ponto decimal (ex.: 25000.00), e veio "{parametros["in_valor"]}"') from erro

    conversao = PaginaDoConversor().abrir().converter(valor, moeda)
    web.print_da_tela("conversao-no-banco-central")

    log.info("%s %s = R$ %s (cotação de %s: 1 %s = R$ %s)", valor, moeda, conversao.resultado,
             conversao.data_da_cotacao, moeda, conversao.taxa)

    return {
        "out_valor_em_reais": f"{conversao.resultado:.2f}",
        "out_cotacao": str(conversao.taxa),
        "out_data_da_cotacao": conversao.data_da_cotacao,
    }
