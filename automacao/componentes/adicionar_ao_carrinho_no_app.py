"""AdicionarAoCarrinhoNoApp: no app, abre o produto pelo nome, põe no carrinho e devolve o preço."""

import logging

from automacao.mobile import sessao as mobile
from automacao.mobile.my_demo_app import TelaDeProdutos

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    produto = parametros["in_produto"]
    tela = TelaDeProdutos().abrir_produto(produto)

    if tela.nome() != produto:
        raise AssertionError(f'O app abriu "{tela.nome()}"; o esperado era "{produto}"')

    preco = tela.preco()
    tela.adicionar_ao_carrinho()
    mobile.print_da_tela("carrinho-no-app")
    log.info("%s no carrinho do app, por %s", produto, preco)

    return {"out_preco_no_app": preco}
