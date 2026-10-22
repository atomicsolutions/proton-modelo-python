import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Error as ErroDaPlaywright
from playwright.sync_api import expect

from automacao.apoio import config
from automacao.web import sessao


def numero_brasileiro(texto: str) -> Decimal:
    """`5.027,00` vira `Decimal("5027.00")`."""
    return Decimal(texto.strip().replace(".", "").replace(",", "."))


def texto_brasileiro(valor: Decimal) -> str:
    """`Decimal("25000.5")` vira `25000,50`, como se digita no campo (a máscara põe o ponto do milhar)."""
    return f"{valor:.2f}".replace(".", ",")


@dataclass
class Conversao:
    valor: Decimal
    resultado: Decimal
    taxa: Decimal
    data_da_cotacao: str


class PaginaDoConversor:
    """O Conversor de Moedas do Banco Central, com a cotação oficial do dia útil."""

    def __init__(self):
        self.pagina = sessao.pagina()

    def abrir(self) -> "PaginaDoConversor":
        sessao.ir_para(config.URL_DO_CONVERSOR_DE_MOEDAS)
        expect(self.pagina.locator("#button-converter-de")).to_be_visible()
        self._recusar_cookies()
        return self

    def _recusar_cookies(self) -> None:
        """O aviso de cookies cobre o formulário: só os essenciais."""
        botao = self.pagina.get_by_role("button", name="Rejeitar cookies")
        try:
            botao.click(timeout=5000)
        except ErroDaPlaywright:
            pass  # o aviso não apareceu (já respondido nesta sessão)

    def _escolher_moeda(self, lista: str, codigo: str) -> None:
        self.pagina.locator(f"#button-converter-{lista}").click()
        opcao = self.pagina.locator(f"ul[aria-labelledby='button-converter-{lista}'] a.dropdown-item", has_text=f"({codigo})")
        try:
            opcao.first.wait_for(state="visible", timeout=10000)
        except ErroDaPlaywright as erro:
            raise ValueError(f"O conversor não tem a moeda {codigo}") from erro
        opcao.first.click()

    def converter(self, valor: Decimal, de: str, para: str = "BRL") -> Conversao:
        self._escolher_moeda("de", de)
        self._escolher_moeda("para", para)

        campo = self.pagina.locator("input[placeholder='0,00']")
        campo.click()
        campo.press("Control+A")
        # A máscara do campo só entende a digitação, tecla a tecla.
        campo.press_sequentially(texto_brasileiro(valor), delay=40)
        if numero_brasileiro(campo.input_value()) != valor:
            raise AssertionError(f"O campo ficou com {campo.input_value()}, e o valor era {texto_brasileiro(valor)}")

        # O site às vezes calcula com o valor anterior do campo: a conta é conferida e,
        # se não fechar, a conversão é pedida de novo.
        for _ in range(3):
            self.pagina.locator("button[title='Converter']").click()
            conversao = self._ler_resultado(valor, de)
            if abs(conversao.resultado - valor * conversao.taxa) <= valor * conversao.taxa * Decimal("0.001"):
                return conversao
            self.pagina.wait_for_timeout(1000)

        raise AssertionError(
            f"O conversor mostrou {conversao.resultado} para {valor} {de} com a cotação {conversao.taxa}: a conta não fecha")

    def _ler_resultado(self, valor: Decimal, de: str) -> Conversao:
        resultado = self.pagina.locator(".resultado")
        expect(resultado).to_contain_text(f"/{de}")
        texto = " ".join(resultado.inner_text().split())

        convertido = re.search(r"Resultado da conversão:\s*([\d.,]+)", texto)
        a_converter = re.search(r"Valor a converter:\s*([\d.,]+)", texto)
        data = re.search(r"Data cotação utilizada:\s*(\d{2}/\d{2}/\d{4})", texto)
        taxa = re.search(rf"1 [^=]*/{de} \(\d+\) = ([\d.,]+)", texto)

        if not (convertido and a_converter and data and taxa):
            raise AssertionError(f"O resultado do conversor mudou de formato: {texto[:300]}")
        if numero_brasileiro(a_converter.group(1)) != valor:
            raise AssertionError(f"O conversor converteu {a_converter.group(1)}, e o valor era {texto_brasileiro(valor)}")

        return Conversao(valor, numero_brasileiro(convertido.group(1)), numero_brasileiro(taxa.group(1)), data.group(1))
