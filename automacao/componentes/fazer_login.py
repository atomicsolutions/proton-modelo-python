"""FazerLogin: abre a loja e entra com usuário e senha."""

import logging

from automacao.web.login import PaginaDeLogin
from automacao.web.produtos import PaginaDeProdutos

log = logging.getLogger(__name__)


def executar(parametros: dict) -> None:
    PaginaDeLogin().abrir().entrar(parametros["in_usuario"], parametros["in_senha"])
    PaginaDeProdutos().conferir_que_abriu()
    log.info("Login feito com %s", parametros["in_usuario"])
