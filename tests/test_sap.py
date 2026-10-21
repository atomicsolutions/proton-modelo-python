"""
As ajudas do SAP (`automacao/sap/sessao.py`), com objetos falsos no lugar do SAP GUI: rodam
em qualquer máquina, sem SAP e sem pywin32.
"""

from types import SimpleNamespace

import pytest

from automacao.apoio import config, sessoes
from automacao.apoio.falhas import FalhaDeNegocio
from automacao.sap import sessao as sap


class Colecao:
    """Imita `Children` e `Columns`: `Count` e `ElementAt`."""

    def __init__(self, itens):
        self._itens = list(itens)

    @property
    def Count(self):
        return len(self._itens)

    def ElementAt(self, indice):
        return self._itens[indice]


class Elemento:
    """Imita um elemento do SAP GUI: `Id`, `Type`, `Name`, `Text` e, nos contêineres, `Children`."""

    def __init__(self, Id, Type="GuiTextField", Text="", filhos=()):
        self.Id, self.Type, self.Text = Id, Type, Text
        self.Name = Id.rsplit("/", 1)[-1][3:]

        if filhos:
            self.Children = Colecao(filhos)


class Tabela(Elemento):
    """Imita um GuiTableControl: `Columns`, `GetCell` e `VisibleRowCount`."""

    def __init__(self, Id, titulos, linhas):
        super().__init__(Id, "GuiTableControl")
        self.Columns = Colecao(SimpleNamespace(Title=titulo) for titulo in titulos)
        self.celulas = [[SimpleNamespace(Text=valor) for valor in linha] for linha in linhas]
        self.VisibleRowCount = len(linhas)

    def GetCell(self, linha, coluna):
        return self.celulas[linha][coluna]


class Barra:
    """Imita a barra de status: `MessageType` e `Text` da mensagem da vez."""

    def __init__(self, *mensagens):
        self.mensagens = list(mensagens) or [("", "")]

    @property
    def MessageType(self):
        return self.mensagens[0][0]

    @property
    def Text(self):
        return self.mensagens[0][1]


class Janela:
    """Imita a janela principal: cada Enter (`sendVKey(0)`) passa para a próxima mensagem."""

    def __init__(self, barra):
        self.barra, self.enters = barra, 0

    def sendVKey(self, tecla):
        assert tecla == sap.ENTER
        self.enters += 1

        if len(self.barra.mensagens) > 1:
            self.barra.mensagens.pop(0)


class GuiSession:
    """Imita a GuiSession: `findById` pelo id relativo, como `wnd[0]/usr`."""

    def __init__(self, elementos):
        self.elementos = elementos

    def findById(self, id_do_elemento, erro_se_nao_existe=True):
        if id_do_elemento in self.elementos:
            return self.elementos[id_do_elemento]
        if erro_se_nao_existe:
            raise LookupError(id_do_elemento)
        return None


@pytest.fixture
def sap_falso():
    """Põe uma GuiSession falsa no lugar da sessão SAP do cenário."""

    def instalar(elementos: dict):
        gui = GuiSession(elementos)
        falsa = SimpleNamespace(sessao=gui, fechar=lambda: None, evidencia=lambda nome: None)
        sessoes.obter("sap", lambda: falsa)
        return gui

    with sessoes.abertas():
        yield instalar


def com_barra(sap_falso, *mensagens):
    barra = Barra(*mensagens)
    janela = Janela(barra)
    sap_falso({"wnd[0]/sbar": barra, "wnd[0]": janela})
    return janela


# Barra de status

def test_barra_de_status_com_o_tipo(sap_falso):
    com_barra(sap_falso, ("W", "Data no passado"))
    assert sap.barra_de_status() == (sap.TipoDeMensagem.AVISO, "Data no passado")


def test_barra_vazia(sap_falso):
    com_barra(sap_falso)
    assert sap.barra_de_status() == (sap.TipoDeMensagem.NENHUMA, "")


@pytest.mark.parametrize("tipo", ["E", "A"])
def test_erro_na_barra_e_falha_de_negocio(sap_falso, tipo):
    com_barra(sap_falso, (tipo, "Material 4711 não existe"))

    with pytest.raises(FalhaDeNegocio, match="Material 4711 não existe") as falha:
        sap.conferir_sem_erro()

    assert falha.value.failure_reason == "business_error"


@pytest.mark.parametrize("tipo", ["S", "W", "I", ""])
def test_sem_erro_na_barra(sap_falso, tipo):
    com_barra(sap_falso, (tipo, "Documento 4500000001 gravado"))
    sap.conferir_sem_erro()


def test_confirmar_avisos_aperta_enter_ate_o_aviso_sumir(sap_falso):
    janela = com_barra(sap_falso, ("W", "Data no passado"), ("W", "Preço zerado"), ("S", "Gravado"))
    sap.confirmar_avisos()
    assert janela.enters == 2


def test_confirmar_avisos_para_no_limite(sap_falso):
    janela = com_barra(sap_falso, ("W", "Aviso que não sai"))

    with pytest.raises(AssertionError, match="depois de 3 Enter"):
        sap.confirmar_avisos(tentativas=3)

    assert janela.enters == 3


# Tabela

ID_DA_TABELA = "wnd[0]/usr/tblITENS"


def tabela_de_itens(sap_falso):
    tabela = Tabela(ID_DA_TABELA, [" Material ", "Quantidade"], [["4711", "2"], ["4712", "1"], ["", ""], ["", ""]])
    sap_falso({ID_DA_TABELA: tabela})
    return tabela


def test_ler_e_escrever_celula_pelo_titulo(sap_falso):
    tabela = tabela_de_itens(sap_falso)

    assert sap.ler_celula(ID_DA_TABELA, 1, "Material") == "4712"

    sap.escrever_celula(ID_DA_TABELA, 2, "Quantidade", "5")
    assert tabela.celulas[2][1].Text == "5"


def test_primeira_linha_vazia(sap_falso):
    tabela_de_itens(sap_falso)
    assert sap.primeira_linha_vazia(ID_DA_TABELA, "Material") == 2


def test_tabela_sem_linha_vazia(sap_falso):
    tabela = tabela_de_itens(sap_falso)

    for linha in tabela.celulas:
        linha[0].Text = "4711"

    with pytest.raises(AssertionError, match="não tem linha vazia"):
        sap.primeira_linha_vazia(ID_DA_TABELA, "Material")


def test_coluna_que_nao_existe(sap_falso):
    tabela_de_itens(sap_falso)

    with pytest.raises(LookupError, match='não tem a coluna "Centro". As colunas são: Material, Quantidade'):
        sap.ler_celula(ID_DA_TABELA, 0, "Centro")


# Elementos

def tela_com_abas(sap_falso):
    abas = Elemento("wnd[0]/usr/tabsABAS", "GuiTabStrip", filhos=[
        Elemento("wnd[0]/usr/tabsABAS/tabpT01", "GuiTab", "Dados básicos"),
        Elemento("wnd[0]/usr/tabsABAS/tabpT02", "GuiTab", " Parceiros "),
    ])
    subtela = Elemento("wnd[0]/usr/subSUB0:SAPLMEGUI:0013", "GuiSimpleContainer", filhos=[
        Elemento("wnd[0]/usr/subSUB0:SAPLMEGUI:0013/btnSALVAR", "GuiButton", "Salvar"),
    ])
    usr = Elemento("wnd[0]/usr", "GuiUserArea", filhos=[Elemento("wnd[0]/usr/lblTITULO", "GuiLabel", "Pedido"), abas, subtela])
    sap_falso({"wnd[0]/usr": usr})


def test_id_pelo_texto(sap_falso):
    tela_com_abas(sap_falso)
    assert sap.id_pelo_texto("Salvar") == "wnd[0]/usr/subSUB0:SAPLMEGUI:0013/btnSALVAR"


def test_id_pelo_texto_que_nao_existe(sap_falso):
    tela_com_abas(sap_falso)

    with pytest.raises(LookupError, match='Nenhum elemento com o texto "Cancelar"'):
        sap.id_pelo_texto("Cancelar")


def test_id_da_aba(sap_falso):
    tela_com_abas(sap_falso)
    assert sap.id_da_aba("Parceiros") == "wnd[0]/usr/tabsABAS/tabpT02"


def test_aba_que_nao_existe(sap_falso):
    tela_com_abas(sap_falso)

    with pytest.raises(LookupError, match="As abas são: Dados básicos, Parceiros"):
        sap.id_da_aba("Textos")


def test_subtela_pelo_prefixo(sap_falso):
    tela_com_abas(sap_falso)
    assert sap.subtela("SUB0:SAPLMEGUI:") == "SUB0:SAPLMEGUI:0013"


def test_subtela_que_nao_existe(sap_falso):
    tela_com_abas(sap_falso)

    with pytest.raises(LookupError, match='Nenhuma subtela começa com "SUB1:"'):
        sap.subtela("SUB1:")


# Tela de relatório

def test_tabela_da_tela(sap_falso):
    rotulos = [
        Elemento("wnd[0]/usr/lbl[20,4]", "GuiLabel", "Centro"),
        Elemento("wnd[0]/usr/lbl[1,4]", "GuiLabel", "Material"),
        Elemento("wnd[0]/usr/lbl[20,5]", "GuiLabel", " 1000 "),
        Elemento("wnd[0]/usr/lbl[1,5]", "GuiLabel", "4711"),
        Elemento("wnd[0]/usr/txtFILTRO", "GuiTextField", "fora da lista"),
    ]
    sap_falso({"wnd[0]/usr": Elemento("wnd[0]/usr", "GuiUserArea", filhos=rotulos)})

    assert sap.tabela_da_tela() == [["Material", "Centro"], ["4711", "1000"]]


# Print

def test_print_vai_para_a_pasta_de_evidencias(monkeypatch, tmp_path):
    pasta = tmp_path / "evidencias" / "123"
    monkeypatch.setattr(config, "PASTA_DE_EVIDENCIAS", pasta)

    def hard_copy(caminho, tipo):
        open(caminho, "wb").close()

    sessao_sap = sap.SessaoSap.__new__(sap.SessaoSap)
    sessao_sap.sessao = SimpleNamespace(ActiveWindow=SimpleNamespace(HardCopy=hard_copy))
    sessao_sap.conexao = SimpleNamespace(CloseConnection=lambda: None)

    with sessoes.abertas():
        sessoes.obter("sap", lambda: sessao_sap)
        caminho = sap.print_da_tela("pedido-gravado")

    assert caminho.parent == pasta
    assert caminho.is_file()
