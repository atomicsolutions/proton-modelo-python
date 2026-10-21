"""
A sessão de API: um cliente HTTP (requests) por cenário, compartilhado pelos passos dele.

O cliente tenta de novo, com espera crescente, quando a conexão cai ou o servidor responde
502, 503 ou 504. Se a API segue fora do ar depois disso, é falha de ambiente
(`FalhaDeAmbiente`, com o erro do requests como causa). A evidência de uma chamada é a
última resposta, gravada em JSON: método, endereço, status e corpo. Os cabeçalhos ficam de
fora, porque levam credenciais.
"""

import json
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RetryError
from urllib3.util.retry import Retry

from automacao.apoio import evidencias, sessoes
from automacao.apoio.falhas import FalhaDeAmbiente


class _ComNovasTentativas(HTTPAdapter):
    """As novas tentativas do cliente; a API que não responde depois delas é falha de ambiente."""

    def __init__(self):
        super().__init__(max_retries=Retry(total=4, backoff_factor=1, status_forcelist=(502, 503, 504)))

    def send(self, request, *args, **kwargs):
        try:
            return super().send(request, *args, **kwargs)
        except (requests.ConnectionError, RetryError) as erro:
            # Só o endereço do servidor: a URL inteira pode levar chave na query.
            raise FalhaDeAmbiente(f"A API em {urlsplit(request.url).netloc} não respondeu") from erro


class SessaoApi:

    def __init__(self):
        self.cliente = requests.Session()
        self.cliente.mount("https://", _ComNovasTentativas())
        self.cliente.mount("http://", _ComNovasTentativas())
        self.cliente.hooks["response"].append(self._guardar)
        self.ultima_resposta: requests.Response | None = None

    def _guardar(self, resposta, *args, **kwargs):
        self.ultima_resposta = resposta

    def evidencia(self, nome: str) -> Path | None:
        resposta = self.ultima_resposta

        if resposta is None:
            return None

        try:
            corpo = resposta.json()
        except ValueError:
            corpo = resposta.text

        caminho = evidencias.arquivo(nome, "json")
        registro = {
            "metodo": resposta.request.method,
            "url": resposta.request.url,
            "status": resposta.status_code,
            "resposta": corpo,
        }
        caminho.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
        return evidencias.registrar(caminho)

    def fechar(self) -> None:
        self.cliente.close()


def cliente() -> requests.Session:
    """O cliente HTTP do cenário."""
    return sessoes.obter("api", SessaoApi).cliente


def evidencia(nome: str) -> Path | None:
    """Grava a última resposta como evidência na pasta de evidências."""
    return sessoes.obter("api", SessaoApi).evidencia(nome)
