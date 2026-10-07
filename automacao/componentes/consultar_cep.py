"""ConsultarCep: consulta o CEP de entrega na API pública do ViaCEP."""

import logging

from automacao.api import sessao as api
from automacao.api.viacep import ViaCep

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    endereco = ViaCep().consultar(parametros["in_cep"])
    api.evidencia("consulta-do-cep")
    log.info("CEP %s: %s/%s", endereco["cep"], endereco["localidade"], endereco["uf"])

    return {"out_cep": endereco["cep"], "out_cidade": endereco["localidade"], "out_uf": endereco["uf"]}
