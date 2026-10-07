"""AdicionarAoCarrinho: adiciona o produto pelo nome e devolve o preço dele."""

import logging

from automacao.web.produtos import PaginaDeProdutos

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    preco = PaginaDeProdutos().adicionar_ao_carrinho(parametros["in_produto"])
    log.info("%s no carrinho, por %s", parametros["in_produto"], preco)
    return {"out_preco": preco}
