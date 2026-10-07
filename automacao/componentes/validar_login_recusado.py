"""ValidarLoginRecusado: tenta entrar e confere a mensagem de erro do login recusado."""

import logging

from automacao.web import sessao as web
from automacao.web.login import PaginaDeLogin

log = logging.getLogger(__name__)


def executar(parametros: dict) -> None:
    login = PaginaDeLogin().abrir()
    login.entrar(parametros["in_usuario"], parametros["in_senha"])
    mensagem = login.mensagem_de_erro()

    if parametros["in_mensagem"] not in mensagem:
        raise AssertionError(f'Mensagem "{mensagem}"; o esperado era conter "{parametros["in_mensagem"]}"')

    web.print_da_tela("login-recusado")
    log.info("Login recusado, como esperado: %s", mensagem)
