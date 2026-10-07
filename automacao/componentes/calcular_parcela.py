"""CalcularParcela: divide o total da compra em parcelas na Calculadora do Windows."""

import logging
from decimal import ROUND_HALF_UP, Decimal

from automacao.desktop import sessao as desktop
from automacao.desktop.calculadora import Calculadora

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    total, parcelas = parametros["in_total"], int(parametros["in_parcelas"])
    resultado = Calculadora().calcular(f"{total}/{parcelas}")
    desktop.print_da_tela("parcela-na-calculadora")

    parcela = resultado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    log.info("%s em %dx: %s por parcela", total, parcelas, parcela)
    return {"out_valor_da_parcela": str(parcela)}
