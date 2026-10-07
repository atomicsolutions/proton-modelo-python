"""FazerLoginSap: abre a conexão SAP_CONEXAO no SAP GUI e faz o logon."""

import logging

from automacao.sap import sessao as sap
from automacao.sap.logon import TelaDeLogon

log = logging.getLogger(__name__)


def executar(parametros: dict) -> None:
    TelaDeLogon().entrar(
        usuario=parametros["in_usuario"],
        senha=parametros["in_senha"],
        mandante=parametros.get("in_mandante", ""),
    )
    sap.print_da_tela("logon-sap")
    log.info("Logon no SAP feito com %s", parametros["in_usuario"])
