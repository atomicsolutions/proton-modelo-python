"""
Configuração da automação, lida das variáveis de ambiente e do arquivo `.env`.

O `.env` não vai para o git: copie o `.env.example` e ajuste. Uma variável definida no
ambiente vale mais que o `.env`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ_DO_PROJETO / ".env")

URL_DA_LOJA = os.getenv("URL_DA_LOJA", "https://www.saucedemo.com")
HEADLESS = os.getenv("HEADLESS", "true").strip().lower() != "false"
# Vazio usa o Chromium que a Playwright baixa (`playwright install chromium`). "chrome" ou
# "msedge" usam o navegador já instalado na máquina, sem download.
CANAL_DO_NAVEGADOR = os.getenv("CANAL_DO_NAVEGADOR", "").strip() or None
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "15000"))
PASTA_DE_EVIDENCIAS = RAIZ_DO_PROJETO / os.getenv("PASTA_DE_EVIDENCIAS", "evidencias")
PASTA_DE_CENARIOS = RAIZ_DO_PROJETO / "cenarios"
