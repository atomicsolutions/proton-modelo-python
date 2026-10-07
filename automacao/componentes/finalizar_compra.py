"""FinalizarCompra: preenche a entrega, confere o total dos itens e conclui a compra."""

import logging

from automacao.apoio import evidencias
from automacao.paginas.carrinho import PaginaDoCarrinho
from automacao.paginas.checkout import PaginaDeCheckout
from automacao.paginas.produtos import PaginaDeProdutos

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    PaginaDeProdutos().abrir_carrinho()
    PaginaDoCarrinho().ir_para_o_checkout()

    checkout = PaginaDeCheckout()
    checkout.preencher_entrega(parametros["in_nome"], parametros["in_sobrenome"], parametros["in_cep"])

    esperado = parametros.get("in_preco_esperado", "")
    total_dos_itens = checkout.total_dos_itens()

    if esperado and total_dos_itens != esperado:
        raise AssertionError(f"Total dos itens {total_dos_itens}; o esperado era {esperado}")

    total = checkout.total()
    evidencias.print_da_tela("resumo-da-compra")
    checkout.concluir()
    log.info("Compra concluída: total %s", total)

    return {"out_total": total}
