"""
A sessão SAP: o SAP GUI for Windows, pelo SAP GUI Scripting (COM, com o pywin32).

Pré-requisitos na máquina que roda a automação:

- SAP GUI instalado, com a conexão cadastrada no SAP Logon. `SAP_CONEXAO` é a descrição
  dela, como aparece na lista (ex.: "QAS - Qualidade");
- scripting habilitado no servidor (parâmetro `sapgui/user_scripting`) e no SAP GUI
  (Opções > Acessibilidade e scripts > Scripting);
- sessão do usuário do Windows aberta (o runner precisa de área de trabalho).

A conexão abre na primeira vez que um passo pede e fecha no fim do cenário. O logon é um
componente (`FazerLoginSap`), porque usuário e senha são parâmetros do cenário.
"""

import logging
import subprocess
import time
from pathlib import Path

from automacao.apoio import config, evidencias, sessoes

log = logging.getLogger(__name__)

TEMPO_PARA_ABRIR_O_SAP_LOGON_S = 60


class SessaoSap:

    def __init__(self):
        if not config.SAP_CONEXAO:
            raise RuntimeError("Defina SAP_CONEXAO no ambiente ou no .env: a descrição da conexão no SAP Logon.")

        # Importado aqui: o pywin32 só existe no Windows, e o resto do projeto roda em
        # qualquer sistema.
        import win32com.client

        motor = self._motor_de_scripting(win32com.client)
        log.info("Abrindo a conexão SAP %s", config.SAP_CONEXAO)
        self.conexao = motor.OpenConnection(config.SAP_CONEXAO, True)
        self.sessao = self.conexao.Children(0)

    def _motor_de_scripting(self, com):
        try:
            return com.GetObject("SAPGUI").GetScriptingEngine
        except Exception:
            log.info("Iniciando o SAP Logon")
            subprocess.Popen([config.SAP_LOGON])

        limite = time.monotonic() + TEMPO_PARA_ABRIR_O_SAP_LOGON_S

        while time.monotonic() < limite:
            time.sleep(2)
            try:
                return com.GetObject("SAPGUI").GetScriptingEngine
            except Exception:
                continue

        raise RuntimeError(f"O SAP Logon não abriu em {TEMPO_PARA_ABRIR_O_SAP_LOGON_S} s: confira SAP_LOGON no .env.")

    def evidencia(self, nome: str) -> Path:
        caminho = evidencias.arquivo(nome, "jpg")
        self.sessao.ActiveWindow.HardCopy(str(caminho), 1)
        return evidencias.registrar(caminho)

    def fechar(self) -> None:
        self.conexao.CloseConnection()


def sessao():
    """A sessão do SAP GUI do cenário (GuiSession)."""
    return sessoes.obter("sap", SessaoSap).sessao


def print_da_tela(nome: str) -> Path:
    """Grava um print da janela ativa do SAP na pasta de evidências."""
    return sessoes.obter("sap", SessaoSap).evidencia(nome)


def existe(id_do_elemento: str) -> bool:
    """O elemento está na tela (ex.: `wnd[1]/usr/txtMULTI_LOGON_TEXT`)."""
    return sessao().findById(id_do_elemento, False) is not None


def barra_de_status() -> tuple[str, str]:
    """O tipo (S sucesso, W aviso, E erro, A cancelamento, I informação) e o texto da barra de status."""
    barra = sessao().findById("wnd[0]/sbar")
    return barra.MessageType, barra.Text
