import re

from automacao.apoio import config
from automacao.api import sessao


class ViaCep:
    """A API pública de CEP do ViaCEP (viacep.com.br)."""

    def __init__(self):
        self.cliente = sessao.cliente()

    def consultar(self, cep: str) -> dict:
        """O endereço do CEP; erro se o CEP não existe."""
        digitos = re.sub(r"\D", "", cep)

        if len(digitos) != 8:
            raise AssertionError(f'CEP "{cep}" inválido: são 8 dígitos')

        resposta = self.cliente.get(f"{config.URL_DA_API_DE_CEP}/{digitos}/json/", timeout=config.TIMEOUT_DA_API_S)
        resposta.raise_for_status()
        endereco = resposta.json()

        if endereco.get("erro"):
            raise AssertionError(f"CEP {cep} não encontrado")

        return endereco
