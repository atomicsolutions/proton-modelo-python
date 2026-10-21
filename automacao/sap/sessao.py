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

As telas das transações usam as ajudas daqui, em vez de repetir o SAP GUI Scripting:

- barra de status: `barra_de_status()`, `confirmar_avisos()` e `conferir_sem_erro()`, que
  faz do erro da barra (E ou A) uma falha de negócio;
- tabela (GuiTableControl), pelo título da coluna: `ler_celula`, `escrever_celula` e
  `primeira_linha_vazia`;
- elementos: `existe`, `id_pelo_texto`, `id_da_aba` e `subtela`;
- tela de relatório (lista): `tabela_da_tela()`;
- evidência: `print_da_tela(nome)`, na pasta de evidências.

Não há ajuda para matar o `saplogon.exe`: o runner pode rodar várias execuções ao mesmo
tempo na mesma máquina, e matar o processo derruba o SAP de todas. A sessão fecha só a
conexão que abriu.
"""

import logging
import re
import subprocess
import time
from enum import Enum
from pathlib import Path

from automacao.apoio import config, evidencias, sessoes
from automacao.apoio.falhas import FalhaDeNegocio

log = logging.getLogger(__name__)

TEMPO_PARA_ABRIR_O_SAP_LOGON_S = 60
ENTER = 0
# Na tela de relatório (lista), cada texto é um GuiLabel com id lbl[coluna,linha].
_TEXTO_DA_LISTA = re.compile(r"lbl\[(\d+),(\d+)\]$")


class TipoDeMensagem(str, Enum):
    """O tipo da mensagem da barra de status (`MessageType` do SAP GUI)."""

    SUCESSO = "S"
    AVISO = "W"
    ERRO = "E"
    ABORTO = "A"
    INFORMACAO = "I"
    NENHUMA = ""


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
        except _erros_do_com():
            log.info("Iniciando o SAP Logon")
            subprocess.Popen([config.SAP_LOGON])

        limite = time.monotonic() + TEMPO_PARA_ABRIR_O_SAP_LOGON_S

        while time.monotonic() < limite:
            time.sleep(2)
            try:
                return com.GetObject("SAPGUI").GetScriptingEngine
            except _erros_do_com():
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
    """Grava um print da janela ativa do SAP na pasta de evidências (no Proton, a da execução)."""
    return sessoes.obter("sap", SessaoSap).evidencia(nome)


# Barra de status

def barra_de_status() -> tuple[TipoDeMensagem, str]:
    """O tipo e o texto da mensagem da barra de status."""
    barra = sessao().findById("wnd[0]/sbar")
    return TipoDeMensagem(barra.MessageType or ""), barra.Text


def confirmar_avisos(tentativas: int = 5) -> None:
    """Aperta Enter enquanto a barra de status mostra aviso (W), até `tentativas` vezes."""
    for _ in range(tentativas):
        tipo, texto = barra_de_status()

        if tipo is not TipoDeMensagem.AVISO:
            return

        log.info("Aviso do SAP confirmado com Enter: %s", texto)
        sessao().findById("wnd[0]").sendVKey(ENTER)

    tipo, texto = barra_de_status()

    if tipo is TipoDeMensagem.AVISO:
        raise AssertionError(f'O aviso "{texto}" continua na barra de status depois de {tentativas} Enter')


def conferir_sem_erro() -> None:
    """
    Lança `FalhaDeNegocio` quando a barra de status mostra erro (E) ou aborto (A), com o
    texto dela: é o SAP recusando pela regra de negócio ("Material não existe").
    """
    tipo, texto = barra_de_status()

    if tipo in (TipoDeMensagem.ERRO, TipoDeMensagem.ABORTO):
        raise FalhaDeNegocio(f"O SAP recusou: {texto}")


# Tabela (GuiTableControl). A linha conta a partir de 0, entre as linhas visíveis.

def ler_celula(id_da_tabela: str, linha: int, coluna: str) -> str:
    """O texto da célula, pelo título da coluna."""
    tabela = sessao().findById(id_da_tabela)
    return tabela.GetCell(linha, _indice_da_coluna(tabela, coluna)).Text


def escrever_celula(id_da_tabela: str, linha: int, coluna: str, valor: str) -> None:
    """Escreve o valor na célula, pelo título da coluna."""
    tabela = sessao().findById(id_da_tabela)
    tabela.GetCell(linha, _indice_da_coluna(tabela, coluna)).Text = valor


def primeira_linha_vazia(id_da_tabela: str, coluna: str) -> int:
    """A primeira linha visível com a célula da coluna vazia: onde entra o próximo item."""
    tabela = sessao().findById(id_da_tabela)
    indice = _indice_da_coluna(tabela, coluna)

    for linha in range(tabela.VisibleRowCount):
        if not tabela.GetCell(linha, indice).Text.strip():
            return linha

    raise AssertionError(f'A coluna "{coluna}" não tem linha vazia entre as {tabela.VisibleRowCount} visíveis')


def _indice_da_coluna(tabela, titulo: str) -> int:
    titulos = [coluna.Title.strip() for coluna in _itens(tabela.Columns)]

    if titulo.strip() not in titulos:
        raise LookupError(f'A tabela {tabela.Id} não tem a coluna "{titulo}". As colunas são: {", ".join(titulos)}')

    return titulos.index(titulo.strip())


# Elementos

def existe(id_do_elemento: str) -> bool:
    """O elemento está na tela (ex.: `wnd[1]/usr/txtMULTI_LOGON_TEXT`)."""
    return sessao().findById(id_do_elemento, False) is not None


def id_pelo_texto(texto: str, id_do_pai: str = "wnd[0]/usr") -> str:
    """O id do primeiro elemento dentro do pai (botão, rótulo, campo) com o texto visível."""
    for elemento in _descendentes(sessao().findById(id_do_pai)):
        if _texto(elemento) == texto.strip():
            return elemento.Id

    raise LookupError(f'Nenhum elemento com o texto "{texto}" em {id_do_pai}')


def id_da_aba(nome: str, id_do_pai: str = "wnd[0]/usr") -> str:
    """O id da aba (GuiTab) pelo nome que aparece nela. Para abrir: `sessao().findById(id).Select()`."""
    abas = [elemento for elemento in _descendentes(sessao().findById(id_do_pai)) if elemento.Type == "GuiTab"]

    for aba in abas:
        if _texto(aba) == nome.strip():
            return aba.Id

    raise LookupError(f'A aba "{nome}" não existe em {id_do_pai}. As abas são: {", ".join(_texto(aba) for aba in abas)}')


def subtela(prefixo: str, id_do_pai: str = "wnd[0]/usr") -> str:
    """
    O nome da subtela que começa com o prefixo. O número do fim muda conforme a tela
    (`SUB0:SAPLMEGUI:0013`, `SUB0:SAPLMEGUI:0019`), e o id se monta com o nome:
    `f"wnd[0]/usr/sub{subtela('SUB0:SAPLMEGUI:')}/..."`.
    """
    for elemento in _descendentes(sessao().findById(id_do_pai)):
        nome = getattr(elemento, "Name", "") or ""

        if nome.startswith(prefixo):
            return nome

    raise LookupError(f'Nenhuma subtela começa com "{prefixo}" em {id_do_pai}')


# Tela de relatório (lista)

def tabela_da_tela(id_do_pai: str = "wnd[0]/usr") -> list[list[str]]:
    """Os textos de uma tela de relatório, linha a linha, da esquerda para a direita."""
    linhas: dict[int, list[tuple[int, str]]] = {}

    for elemento in _filhos(sessao().findById(id_do_pai)):
        posicao = _TEXTO_DA_LISTA.search(elemento.Id)

        if posicao and elemento.Type == "GuiLabel":
            coluna, linha = (int(numero) for numero in posicao.groups())
            linhas.setdefault(linha, []).append((coluna, _texto(elemento)))

    return [[texto for _, texto in sorted(linhas[linha])] for linha in sorted(linhas)]


def _erros_do_com() -> tuple[type[Exception], ...]:
    """O erro do COM (`pywintypes.com_error`), que só existe no Windows com o pywin32."""
    try:
        from pywintypes import com_error
    except ImportError:
        return ()

    return (com_error,)


def _itens(colecao) -> list:
    """Os itens de uma coleção do SAP GUI (`Children`, `Columns`)."""
    return [colecao.ElementAt(indice) for indice in range(colecao.Count)]


def _filhos(elemento) -> list:
    try:
        return _itens(elemento.Children)
    except (AttributeError, *_erros_do_com()):
        # Campo, botão e rótulo não têm filhos.
        return []


def _descendentes(elemento):
    """Os elementos dentro deste, dos mais de fora para os mais de dentro."""
    fila = _filhos(elemento)

    while fila:
        atual = fila.pop(0)
        yield atual
        fila.extend(_filhos(atual))


def _texto(elemento) -> str:
    try:
        return (elemento.Text or "").strip()
    except (AttributeError, *_erros_do_com()):
        return ""
